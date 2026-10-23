import { describe, expect, it } from 'vitest'
import { BATTLE } from '../../data/tuning.ts'
import { npcMonster } from '../npc.ts'
import { makeMonster } from '../test-helpers.ts'
import { createBattle, currentBand, gapUnits, runBattle, step, timerTicksFor } from './engine.ts'
import type { BattleInput, FighterSetup } from './types.ts'

const ai = (monster: FighterSetup['monster'], personality: FighterSetup['personality'] = 'Steady'): FighterSetup => ({ monster, control: 'ai', personality })
const player = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'player', personality: 'Steady' })
const opts = (seed: number) => ({ seed, timerTicks: timerTicksFor(60) })

describe('the battle engine (§12)', () => {
  it('starts at the §12.1 positions: gap 300, Near band, 50 guts, full HP', () => {
    const b = createBattle(ai(makeMonster()), ai(makeMonster()), opts(1))
    expect(gapUnits(b.state)).toBe(300)
    expect(currentBand(b.state)).toBe(2)
    expect(b.state.fighters.map((f) => f.guts)).toEqual([50, 50])
    expect(b.state.fighters[0].hp).toBe(b.state.fighters[0].maxHp)
  })

  it('is deterministic: the same seed and inputs give the identical log', () => {
    const a = npcMonster({ breed: 'puddlepup', total: 1500, seed: 11 })
    const b = npcMonster({ breed: 'cobblemaw', total: 1500, seed: 12 })
    const r1 = runBattle(ai(a), ai(b), opts(777))
    const r2 = runBattle(ai(a), ai(b), opts(777))
    expect(r2.log).toEqual(r1.log)
    expect(r2.outcome).toEqual(r1.outcome)
    const r3 = runBattle(ai(a), ai(b), opts(778))
    expect(r3.log).not.toEqual(r1.log)
  })

  it('ends on time with the higher HP % winning, or a draw when equal', () => {
    const a = makeMonster({ stats: { LIF: 300, POW: 200, SKI: 200, SPD: 200, DEF: 200 } })
    const b = makeMonster({ stats: { LIF: 300, POW: 200, SKI: 200, SPD: 200, DEF: 200 } })
    const r = runBattle(ai(a), ai(b), opts(3))
    expect(r.outcome.ticks).toBeLessThanOrEqual(timerTicksFor(60))
    if (r.outcome.how === 'time') {
      const [pa, pb] = r.outcome.hpPct
      expect(r.outcome.winner).toBe(pa > pb ? 0 : pb > pa ? 1 : null)
    }
    expect(r.log[r.log.length - 1]!.kind).toBe('end')
  })

  it('a much stronger monster usually knocks out a weak one', () => {
    const strong = npcMonster({ breed: 'cobblemaw', total: 2500, seed: 1 })
    const weak = npcMonster({ breed: 'puddlepup', total: 700, seed: 2 })
    let kos = 0
    for (let seed = 0; seed < 20; seed++) {
      const r = runBattle(ai(strong), ai(weak), opts(seed))
      expect(r.outcome.winner).toBe(0)
      if (r.outcome.how === 'ko') kos++
      expect(r.fighters[1].hp).toBeGreaterThanOrEqual(0)
    }
    expect(kos).toBeGreaterThan(15)
  })

  it('a player side does nothing on its own, and forfeit ends the match as a loss', () => {
    const b = createBattle(player(makeMonster()), ai(makeMonster()), opts(5))
    for (let i = 0; i < 300; i++) step(b)
    expect(b.state.fighters[0].attacks).toBe(0)
    expect(b.state.fighters[1].attacks).toBeGreaterThan(0)
    step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'forfeit' } }])
    expect(b.state.outcome).toMatchObject({ how: 'forfeit', winner: 1 })
    expect(step(b)).toEqual([])
  })

  it('player inputs: walking changes the gap, firing in range spends guts and logs a fire, Auto hands over to the AI', () => {
    const m = makeMonster({ stats: { SKI: 300, POW: 300, LIF: 400 } })
    const b = createBattle(player(m), player(m), opts(9))
    const start = gapUnits(b.state)
    step(b, [{ tick: 1, side: 0, action: { kind: 'move', dir: 1 } }])
    for (let i = 0; i < 29; i++) step(b)
    expect(gapUnits(b.state)).toBeLessThan(start)
    step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'move', dir: 0 } }])
    // Walk back into the Near band if needed and fire the Near-range starter.
    const near = 'puddlepup.splash-nip' // Close
    while (currentBand(b.state) > 1) step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'move', dir: 1 } }])
    const before = b.state.fighters[0].guts
    const events = step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'fire', tech: near } }])
    const fired = events.find((e) => e.kind === 'fire') ?? b.state.log.find((e) => e.kind === 'fire' && e.side === 0)
    const distracted = events.find((e) => e.kind === 'distracted' && e.side === 0)
    expect(fired || distracted).toBeTruthy()
    if (fired) expect(b.state.fighters[0].guts).toBe(before - 10)
    step(b, [{ tick: b.state.tick + 1, side: 1, action: { kind: 'auto', on: true } }])
    for (let i = 0; i < 400 && !b.state.outcome; i++) step(b)
    expect(b.state.fighters[1].attacks).toBeGreaterThan(0)
  })

  it('Assist walks to the technique’s band and fires on arrival', () => {
    const m = makeMonster({ stats: { SKI: 300, POW: 300, INT: 300, LIF: 400 } })
    const b = createBattle(player(m), player(m), opts(21))
    step(b, [{ tick: 1, side: 0, action: { kind: 'assist', tech: 'puddlepup.bubble-pop' } }]) // Mid range
    for (let i = 0; i < 200 && !b.state.log.some((e) => (e.kind === 'fire' || e.kind === 'distracted') && e.side === 0); i++) step(b)
    expect(b.state.log.some((e) => (e.kind === 'fire' || e.kind === 'distracted') && e.side === 0)).toBe(true)
  })

  it('dash needs the gap and guts, push needs touching', () => {
    const m = makeMonster({ stats: { SPD: 300 } })
    const b = createBattle(player(m), player(m), opts(4))
    step(b, [{ tick: 1, side: 0, action: { kind: 'dash' } }])
    expect(b.state.log.some((e) => e.kind === 'dash')).toBe(true)
    expect(b.state.fighters[0].guts).toBe(50 - BATTLE.dash.cost)
    step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'push' } }])
    expect(b.state.log.some((e) => e.kind === 'push')).toBe(false)
    while (gapUnits(b.state) > BATTLE.push.maxGap) step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'move', dir: 1 } }])
    const xBefore = b.state.fighters[1].x
    step(b, [{ tick: b.state.tick + 1, side: 0, action: { kind: 'push' } }])
    for (let i = 0; i < BATTLE.push.ticks; i++) step(b)
    expect(b.state.log.some((e) => e.kind === 'push')).toBe(true)
    expect(b.state.fighters[1].x).toBeGreaterThan(xBefore)
  })

  it('1,000 seeds: no NaN, no negative HP, ends by the timer, both sides act', () => {
    const a = npcMonster({ breed: 'tumblefox', total: 1200, seed: 5 })
    const b = npcMonster({ breed: 'moatshell', total: 1200, seed: 6 })
    const t0 = Date.now()
    let bothActed = 0
    for (let seed = 0; seed < 1000; seed++) {
      const r = runBattle(ai(a, seed % 2 ? 'Aggressive' : 'Cautious'), ai(b, 'Brawler'), opts(seed))
      expect(r.outcome.ticks).toBeLessThanOrEqual(timerTicksFor(60))
      for (const f of r.fighters) {
        expect(Number.isFinite(f.hp) && Number.isFinite(f.guts) && Number.isFinite(f.x)).toBe(true)
        expect(f.hp).toBeGreaterThanOrEqual(0)
        expect(f.guts).toBeGreaterThanOrEqual(0)
        expect(f.guts).toBeLessThanOrEqual(BATTLE.guts.cap)
        expect(Math.abs(f.x)).toBeLessThanOrEqual((BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius) * 100)
      }
      if (r.fighters[0].attacks > 0 && r.fighters[1].attacks > 0) bothActed++
    }
    const ms = Date.now() - t0
    // eslint-disable-next-line no-console
    console.log(`1,000 battles in ${ms} ms (${(ms / 1000).toFixed(2)} ms each)`)
    expect(bothActed).toBeGreaterThan(990)
  })

  it('replays a recorded player battle identically', () => {
    const m = makeMonster({ stats: { SKI: 300, POW: 300, LIF: 400 } })
    const inputs: BattleInput[] = [
      { tick: 1, side: 0, action: { kind: 'move', dir: 1 } },
      { tick: 40, side: 0, action: { kind: 'move', dir: 0 } },
      { tick: 41, side: 0, action: { kind: 'assist', tech: 'puddlepup.splash-nip' } },
      { tick: 200, side: 0, action: { kind: 'auto', on: true } },
    ]
    const r1 = runBattle(player(m), ai(m), opts(31), inputs)
    const r2 = runBattle(player(m), ai(m), opts(31), inputs)
    expect(r1.log).toEqual(r2.log)
  })
})
