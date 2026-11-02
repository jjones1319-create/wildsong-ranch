import { describe, expect, it } from 'vitest'
import { pathOf } from '../../data/paths.ts'
import { TECHNIQUES } from '../../data/techniques.ts'
import { BATTLE } from '../../data/tuning.ts'
import { npcMonster } from '../npc.ts'
import { makeMonster } from '../test-helpers.ts'
import { createBattle, currentBand, gapUnits, runBattle, step, timerTicksFor, type Battle } from './engine.ts'
import { WALL } from './geometry.ts'
import type { BattleEvent, BattleInput, FighterSetup } from './types.ts'

/** docs/BATTLE_3D.md: the lock-on duel (Battle 3D). */

const player = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'player', personality: 'Steady' })
const ai = (monster: FighterSetup['monster'], tier?: FighterSetup['tier']): FighterSetup => ({ monster, control: 'ai', personality: 'Steady', tier })
const duel = (seed: number) => ({ seed, timerTicks: timerTicksFor(60), mode: 'duel' as const })

function act(b: Battle, side: 0 | 1, action: BattleInput['action']): BattleEvent[] {
  return step(b, [{ tick: b.state.tick + 1, side, action }])
}

/** Two player-controlled Puddlepups that know Belly Flop (Heavy, Close, a straight line) and Soggy Cloud (Wither, a sweep). */
function setup(seed = 3): Battle {
  const m = makeMonster({ stats: { LIF: 600, POW: 300, INT: 300, SKI: 300, SPD: 300, DEF: 300 } })
  m.techniques.push({ ...m.techniques[0]!, id: 'puddlepup.belly-flop' }, { ...m.techniques[0]!, id: 'puddlepup.soggy-cloud' })
  const b = createBattle(player(m), player(structuredClone(m)), duel(seed))
  for (const f of b.state.fighters) f.distractCooldown = 100_000 // no dawdling in these tests
  return b
}

function walkTo(b: Battle, band: number): void {
  for (let i = 0; i < 300 && currentBand(b.state) !== band; i++) act(b, 0, { kind: 'move', dir: currentBand(b.state) > band ? 1 : -1 })
  act(b, 0, { kind: 'move', dir: 0 })
}

describe('the duel (docs/BATTLE_3D.md)', () => {
  it('strafing circles the opponent: the gap stays, the fighter moves round', () => {
    const b = setup()
    const gap = gapUnits(b.state)
    act(b, 0, { kind: 'move', dir: 0, side: 1 })
    for (let i = 0; i < 90; i++) step(b)
    expect(Math.abs(gapUnits(b.state) - gap)).toBeLessThanOrEqual(1)
    expect(Math.abs(b.state.fighters[0].y)).toBeGreaterThan(5000)
  })

  it('a technique lands after its wind-up, aimed at where the defender stood', () => {
    const b = setup()
    walkTo(b, 1)
    const fired = act(b, 0, { kind: 'fire', tech: 'puddlepup.belly-flop' }).find((e) => e.kind === 'fire')
    expect(fired).toMatchObject({ kind: 'fire', lands: b.state.tick + BATTLE.duel.windup.Heavy, path: 'line' })
    const land = (fired as { lands: number }).lands
    while (b.state.tick < land - 1) {
      step(b)
      expect(b.state.log.some((e) => (e.kind === 'hit' || e.kind === 'miss') && e.side === 0)).toBe(false)
    }
    const events = step(b)
    expect(events.some((e) => (e.kind === 'hit' || e.kind === 'miss') && e.side === 0)).toBe(true)
  })

  it('a sidestep timed in the wind-up carries the defender out of a straight-line technique: it misses', () => {
    const b = setup()
    walkTo(b, 1)
    act(b, 0, { kind: 'fire', tech: 'puddlepup.belly-flop' })
    const before = b.state.fighters[1].guts
    const ss = act(b, 1, { kind: 'sidestep', dir: 1 })
    expect(ss.some((e) => e.kind === 'sidestep' && e.side === 1)).toBe(true)
    expect(b.state.fighters[1].guts).toBeLessThanOrEqual(before - BATTLE.duel.sidestep.cost + 1)
    for (let i = 0; i < BATTLE.duel.windup.Heavy; i++) step(b)
    const out = b.state.log.filter((e) => (e.kind === 'hit' || e.kind === 'miss') && e.side === 0)
    expect(out).toHaveLength(1)
    expect(out[0]).toMatchObject({ kind: 'miss', dodged: true })
  })

  it('a wide sweep cannot be sidestepped', () => {
    const b = setup()
    walkTo(b, 3)
    const fired = act(b, 0, { kind: 'fire', tech: 'puddlepup.soggy-cloud' }).find((e) => e.kind === 'fire')
    expect(fired).toMatchObject({ path: 'sweep' })
    act(b, 1, { kind: 'sidestep', dir: -1 })
    for (let i = 0; i < BATTLE.duel.windup.Wither + 1; i++) step(b)
    expect(b.state.log.some((e) => e.kind === 'miss' && e.dodged)).toBe(false)
    expect(b.state.log.some((e) => (e.kind === 'hit' || e.kind === 'miss') && e.side === 0)).toBe(true)
  })

  it('a sidestep costs guts and has a cooldown', () => {
    const b = setup()
    act(b, 1, { kind: 'sidestep', dir: 1 })
    for (let i = 0; i < BATTLE.duel.sidestep.ticks; i++) step(b)
    const again = act(b, 1, { kind: 'sidestep', dir: 1 })
    expect(again.some((e) => e.kind === 'sidestep')).toBe(false)
    expect(b.state.fighters[1].guts).toBeLessThan(BATTLE.guts.start)
  })

  it('is deterministic, keeps everyone inside the ring and apart, and the AI circles and sidesteps', () => {
    let sidesteps = 0
    let dodged = 0
    let circled = 0
    for (let s = 0; s < 24; s++) {
      const a = npcMonster({ breed: s % 2 ? 'quillion' : 'puddlepup', total: 1500 + 100 * (s % 5), seed: 40 + s })
      const c = npcMonster({ breed: s % 3 ? 'cobblemaw' : 'galeheron', total: 1500 + 100 * (s % 4), seed: 90 + s })
      const b = createBattle(ai(a, 'expert'), ai(c, 'expert'), duel(500 + s))
      while (!b.state.outcome) {
        step(b)
        for (const f of b.state.fighters) {
          expect(f.x * f.x + f.y * f.y).toBeLessThanOrEqual(WALL * WALL)
          expect(Number.isFinite(f.x) && Number.isFinite(f.y)).toBe(true)
          if (f.y !== 0) circled++
        }
        expect(gapUnits(b.state)).toBeGreaterThanOrEqual(0)
      }
      sidesteps += b.state.log.filter((e) => e.kind === 'sidestep').length
      dodged += b.state.log.filter((e) => e.kind === 'miss' && e.dodged).length
      const again = runBattle(ai(a, 'expert'), ai(c, 'expert'), duel(500 + s))
      expect(again.log).toEqual(b.state.log)
    }
    expect(circled).toBeGreaterThan(0)
    expect(sidesteps).toBeGreaterThan(0)
    expect(dodged).toBeGreaterThan(0)
  })

  it('expert AIs sidestep more than rookies', () => {
    const count = (tier: 'rookie' | 'expert') => {
      let n = 0
      for (let s = 0; s < 12; s++) {
        const a = npcMonster({ breed: 'puddlepup', total: 1600, seed: 7 + s })
        const r = runBattle(ai(a, tier), ai(structuredClone(a), tier), duel(70 + s))
        n += r.log.filter((e) => e.kind === 'sidestep').length
      }
      return n
    }
    expect(count('expert')).toBeGreaterThan(count('rookie'))
  })

  it('the line battle is untouched: no wind-up fields, nobody leaves the line', () => {
    const a = npcMonster({ breed: 'puddlepup', total: 1500, seed: 11 })
    const c = npcMonster({ breed: 'cobblemaw', total: 1500, seed: 12 })
    const r = runBattle(ai(a), ai(c), { seed: 777, timerTicks: timerTicksFor(60) })
    expect(r.log.some((e) => e.kind === 'fire' && (e.lands !== undefined || e.path !== undefined))).toBe(false)
    expect(r.log.some((e) => e.kind === 'sidestep')).toBe(false)
    expect(r.fighters.every((f) => f.y === 0)).toBe(true)
  })
})

describe('technique paths (docs/BATTLE_3D.md §3)', () => {
  it('sorts techniques into straight lines and wide sweeps by the rule', () => {
    const byId = (id: string) => TECHNIQUES.find((t) => t.id === id)!
    expect(pathOf(byId('puddlepup.splash-nip'))).toBe('line')
    expect(pathOf(byId('puddlepup.belly-flop'))).toBe('line')
    expect(pathOf(byId('puddlepup.soggy-cloud'))).toBe('sweep') // Wither
    expect(pathOf(byId('frostlance.polar-spiral'))).toBe('sweep') // three hits
    expect(pathOf(byId('plumdrake.cloud-gust-blast'))).toBe('sweep') // a gust
    const sweeps = TECHNIQUES.filter((t) => pathOf(t) === 'sweep').length / TECHNIQUES.length
    // most techniques can be sidestepped; a solid share can't
    expect(sweeps).toBeGreaterThan(0.2)
    expect(sweeps).toBeLessThan(0.5)
  })
})
