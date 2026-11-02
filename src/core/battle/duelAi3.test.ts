import { describe, expect, it } from 'vitest'
import { AI, BATTLE } from '../../data/tuning.ts'
import { npcMonster } from '../npc.ts'
import { makeMonster } from '../test-helpers.ts'
import { canAct, canFire, createBattle, runBattle, step, timerTicksFor, type Battle } from './engine.ts'
import { senseOfMonster, senseReasons, tierForSense } from './duelSense.ts'
import { WALL, herdDir, strafeAround } from './geometry.ts'
import type { Personality } from '../../data/types.ts'
import type { BattleInput, FighterSetup, FighterState } from './types.ts'

/** docs/BATTLE_3D.md §4 AI 3.0: battle sense, punishing, reading habits, the ring, styles and spoiled monsters. */

const player = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'player', personality: 'Steady' })
const ai = (monster: FighterSetup['monster'], tier: FighterSetup['tier'], personality: Personality = 'Steady'): FighterSetup => ({ monster, control: 'ai', personality, tier })
const duel = (seed: number) => ({ seed, timerTicks: timerTicksFor(60), mode: 'duel' as const })
const AUTO_ON: BattleInput = { tick: 1, side: 0, action: { kind: 'auto', on: true, style: 'balanced' } }

function raised(battles: number, spoil: number, fear: number) {
  const m = npcMonster({ breed: 'puddlepup', total: 1600, seed: 31 })
  m.records.wins = Math.ceil(battles / 2)
  m.records.losses = Math.floor(battles / 2)
  m.records.draws = 0
  m.spoil = spoil
  m.fear = fear
  return m
}

/** Run a duel with a scripted player on side 0 against `cpu`; `script` gives side 0's action each tick (or null). */
function scripted(cpu: FighterSetup, seed: number, script: (b: Battle) => BattleInput['action'] | null): Battle {
  const me = makeMonster({ stats: { LIF: 900, POW: 300, INT: 300, SKI: 300, SPD: 300, DEF: 300 } })
  const b = createBattle(player(me), cpu, duel(seed))
  while (!b.state.outcome) {
    const action = script(b)
    step(b, action ? [{ tick: b.state.tick + 1, side: 0, action }] : [])
  }
  return b
}

describe('AI 3.0 (docs/BATTLE_3D.md §4)', () => {
  it('§4.1 battle sense comes from how the monster was raised', () => {
    expect(senseOfMonster(raised(0, 50, 50)).sense).toBe(AI.duel.sense.base)
    const veteran = senseOfMonster(raised(40, 80, 80))
    expect(veteran.sense).toBe(30 + 35 + 12)
    expect(tierForSense(veteran.sense)).toBe('expert')
    const spoiled = senseOfMonster(raised(0, 95, 10))
    expect(spoiled.spoiled).toBe(2)
    expect(spoiled.sense).toBeLessThan(AI.duel.sense.base)
    expect(tierForSense(spoiled.sense)).toBe('rookie')
    expect(senseReasons(veteran)).toEqual(['seasoned', 'loyal'])
    expect(senseReasons(spoiled)).toEqual(['untrained', 'spoiled'])
  })

  it('§4.1 the CPU takes it from its tier, the player from the monster; the line has none', () => {
    const m = raised(0, 50, 50)
    const b = createBattle({ ...player(m), tier: 'expert' }, ai(structuredClone(m), 'skilled'), duel(1))
    expect(b.state.fighters[0].sense).toBe(30)
    expect(b.state.fighters[0].tier).toBe('rookie')
    expect(b.state.fighters[1].sense).toBe(AI.duel.sense.tier.skilled)
    const line = createBattle(player(m), ai(structuredClone(m), 'skilled'), { seed: 1, timerTicks: timerTicksFor(60) })
    expect(line.state.fighters.every((f) => f.duelBias === null)).toBe(true)
  })

  it('§4.5 a fighter shoved into the fence is stunned there; in the middle it just slides', () => {
    const shove = (atX: number) => {
      const m = makeMonster({ stats: { LIF: 900, POW: 300, INT: 300, SKI: 300, SPD: 300, DEF: 300 } })
      const b = createBattle(player(m), player(structuredClone(m)), duel(2))
      const [a, o] = b.state.fighters
      o.x = atX
      a.x = atX - (2 * BATTLE.arena.bodyRadius + 20) * 100
      for (const f of b.state.fighters) f.distractCooldown = 100_000
      step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'push' } }])
      for (let i = 0; i < 20; i++) step(b)
      return b.state.log.filter((e) => e.kind === 'fence' && e.side === 1).length
    }
    expect(shove(WALL - 5000)).toBe(1)
    expect(shove(0)).toBe(0)
  })

  it('§4.5 herding circles toward the side between the opponent and the middle', () => {
    const cosToMiddle = (f: Pick<FighterState, 'x' | 'y'>, o: Pick<FighterState, 'x' | 'y'>) => {
      const dx = f.x - o.x, dy = f.y - o.y
      return (dx * -o.x + dy * -o.y) / (Math.hypot(dx, dy) * Math.hypot(o.x, o.y))
    }
    const opp = { x: 30_000, y: 0 } as FighterState
    for (const start of [{ x: 30_000, y: 25_000 }, { x: 30_000, y: -25_000 }, { x: 45_000, y: 8_000 }]) {
      const f = { ...start } as FighterState
      const dir = herdDir(f, opp, AI.duel.herd.alignPct)
      expect(dir).not.toBe(0)
      const before = cosToMiddle(f, opp)
      strafeAround(f, opp, dir * 3000)
      expect(cosToMiddle(f, opp)).toBeGreaterThan(before)
    }
    expect(herdDir({ x: 5_000, y: 0 } as FighterState, opp, AI.duel.herd.alignPct)).toBe(0)
  })

  it('§4.4 it reads a sidestepper, a rusher and a favourite range', () => {
    const cpu = () => ai(npcMonster({ breed: 'quillion', total: 1600, seed: 5 }), 'expert')
    const sidestepper = scripted(cpu(), 11, (b) => {
      const [me, it] = b.state.fighters
      return it.pending?.path === 'line' && me.sidestepCooldown === 0 && me.sidestepTicks === 0 ? { kind: 'sidestep', dir: b.state.tick % 2 ? 1 : -1 } : null
    })
    expect(sidestepper.state.fighters[1].duelBias!.sweepPct).toBeGreaterThan(100)
    const idle = scripted(cpu(), 11, () => null)
    expect(idle.state.fighters[1].duelBias!.sweepPct).toBe(100)
    const rusher = scripted(cpu(), 12, (b) => (b.state.fighters[0].moveDir === 1 ? null : { kind: 'move', dir: 1 }))
    expect(rusher.state.fighters[1].readAdvance * 100).toBeGreaterThanOrEqual(rusher.state.fighters[1].readTicks * AI.duel.read.rusher.sharePct)
    const close = scripted(cpu(), 13, (b) => {
      const me = b.state.fighters[0]
      const t = me.techniques.find((x) => x.id === 'puddlepup.splash-nip')
      return t && me.guts >= 20 && me.busyTicks === 0 ? { kind: 'assist', tech: t.id } : null
    })
    const seen = close.state.fighters[1]
    if (seen.readBand.reduce((s, n) => s + n, 0) >= AI.duel.read.favourite.minFires) expect(seen.duelBias!.avoidBand).toBe(1)
  })

  it('§4.3 given an opening it can use, an expert punishes it far more often than a rookie', () => {
    const share = (tier: 'rookie' | 'expert') => {
      let usable = 0
      let punished = 0
      for (let s = 0; s < 10; s++) {
        const a = npcMonster({ breed: 'puddlepup', total: 1600, seed: 7 + s })
        const b = createBattle(ai(a, tier), ai(structuredClone(a), tier), duel(80 + s))
        // per side: inside an opening the other side could use (it could act with a technique ready), and answered yet
        const state = [{ open: false, usable: false, answered: false }, { open: false, usable: false, answered: false }]
        while (!b.state.outcome) {
          for (const side of [0, 1] as const) {
            const o = b.state.fighters[side]
            const f = b.state.fighters[1 - side]!
            const open = (o.busyTicks > 0 && o.pending === null) || o.stunTicks > 0 || o.dawdleTicks > 0
            const st = state[side]!
            if (!open) Object.assign(st, { open: false, usable: false, answered: false })
            else {
              st.open = true
              if (!st.usable && canAct(f) && f.techniques.some((t) => canFire(b.state, f, t.id))) {
                st.usable = true
                usable++
              }
            }
          }
          for (const e of step(b)) {
            if (e.kind !== 'fire') continue
            const st = state[1 - e.side]!
            if (st.usable && !st.answered) {
              st.answered = true
              punished++
            }
          }
        }
      }
      return punished / usable
    }
    expect(share('expert')).toBeGreaterThan(share('rookie') * 1.5)
  })

  it('§4.1 and §4.7: a seasoned, loyal monster on Auto beats its spoiled, untrained twin', () => {
    const wins = (m: FighterSetup['monster']) => {
      let n = 0
      for (let s = 0; s < 40; s++) {
        const r = runBattle(player(structuredClone(m)), ai(raised(0, 50, 50), 'skilled'), duel(300 + s), [AUTO_ON])
        if (r.outcome.winner === 0) n++
      }
      return n
    }
    expect(wins(raised(40, 80, 80))).toBeGreaterThanOrEqual(wins(raised(0, 98, 5)) + 5)
  })

  it('§4.6 styles you can see: careful fighters circle more than rushers', () => {
    const circling = (p: Personality) => {
      let ticks = 0
      let strafing = 0
      for (let s = 0; s < 8; s++) {
        const a = npcMonster({ breed: 'puddlepup', total: 1600, seed: 21 + s })
        const b = createBattle(ai(a, 'expert', p), ai(structuredClone(a), 'expert'), duel(400 + s))
        while (!b.state.outcome) {
          step(b)
          ticks++
          if (b.state.fighters[0].strafeDir !== 0) strafing++
        }
      }
      return strafing / ticks
    }
    expect(circling('Cautious')).toBeGreaterThan(circling('Aggressive'))
  })
})
