import { describe, expect, it } from 'vitest'
import { STARTING_UNLOCKED } from '../data/breeds.ts'
import type { BreedId } from '../data/types.ts'
import { DASH } from '../data/tuning.ts'
import { applyEchoStones } from './echoStones.ts'
import {
  applyDash,
  canPlayDash,
  createDashHeat,
  dashPay,
  dashRivalBreeds,
  dashRivalRatesX10,
  dashSpdBonusPct,
  dashTapBoost,
  dashTargetSpeed,
  stepDash,
  type DashHeat,
} from './meadowDash.ts'
import { applyOddJob } from './oddJobs.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const OWN: BreedId = STARTING_UNLOCKED[0]!

function heatOf(heat: number, spd = 1, relaxed = false, runSeed = 1): DashHeat {
  return createDashHeat({ runSeed, heat, spd, unlocked: STARTING_UNLOCKED, ownBreed: OWN, relaxed })
}

/** Runs a heat to the end, tapping once every `every` ticks (0 = never). */
function run(h: DashHeat, every: number): DashHeat {
  let x = h
  while (x.winner === null) x = stepDash(x, every > 0 && x.tick % every === 0 ? 1 : 0)
  return x
}

/** Turns a heat's rivals into fixed-speed runners for crafted finishes. */
function crafted(runners: { pos: number; v: number }[]): DashHeat {
  const h = heatOf(1)
  const targets = runners.slice(1).map((r) => Array.from({ length: 4 }, () => r.v))
  return { ...h, runners, prev: runners.map((r) => r.pos), targets }
}

function deepFreeze<T>(o: T): T {
  if (o && typeof o === 'object') {
    for (const v of Object.values(o)) deepFreeze(v)
    Object.freeze(o)
  }
  return o
}

describe('Meadow Dash (CONTENT §13)', () => {
  it('turns SPD into up to 25% more per tap', () => {
    expect(dashSpdBonusPct(1)).toBe(0)
    expect(dashSpdBonusPct(500)).toBe(12)
    expect(dashSpdBonusPct(999)).toBe(25)
    expect(dashSpdBonusPct(5000)).toBe(25)
    expect(dashSpdBonusPct(-3)).toBe(0)
    expect(dashSpdBonusPct(Number.NaN)).toBe(0)
    expect(dashTapBoost(1)).toBe(3800)
    expect(dashTapBoost(999)).toBe(4750)
  })

  it('settles steady tapping at the speed the rivals are paced by', () => {
    for (const every of [6, 8, 12]) {
      let h = heatOf(1)
      let from = 0
      for (let t = 0; t < 250; t++) {
        if (t === 130) from = h.runners[0]!.pos
        h = stepDash(h, t % every === 0 ? 1 : 0)
      }
      const average = (h.runners[0]!.pos - from) / 120
      const expected = (DASH.tapBoost * 100) / (DASH.dragPct * every)
      expect(Math.abs(average - expected) / expected).toBeLessThan(0.01)
    }
    expect(dashTargetSpeed(35)).toBe(6650)
  })

  it('fades to a stop without going backwards, and never passes the top speed', () => {
    let h = stepDash(heatOf(1), 1)
    for (let t = 0; t < 400; t++) {
      h = stepDash(h, 0)
      expect(h.runners[0]!.v).toBeGreaterThanOrEqual(0)
    }
    expect(h.runners[0]!.v).toBe(0)
    const mashed = stepDash(heatOf(1), 100)
    expect(mashed.runners[0]!.pos).toBe(DASH.vMax)
    expect(mashed.runners[0]!.v).toBeLessThanOrEqual(DASH.vMax)
  })

  it('deals the same heat from the same seed, with rivals that ease to their pace without overshooting', () => {
    expect(heatOf(3, 200, false, 77)).toEqual(heatOf(3, 200, false, 77))
    expect(heatOf(3, 200, false, 77)).not.toEqual(heatOf(3, 200, false, 78))
    let h = heatOf(5)
    for (let t = 0; t < 300 && h.winner === null; t++) {
      const before = h
      h = stepDash(h, 0)
      for (let i = 1; i <= 3; i++) {
        const schedule = before.targets[i - 1]!
        const target = schedule[Math.floor(before.tick / DASH.wobble.everyTicks)]!
        const was = before.runners[i]!.v - target
        const now = h.runners[i]!.v - target
        expect(Math.abs(now)).toBeLessThanOrEqual(Math.abs(was))
        expect(was * now).toBeGreaterThanOrEqual(0)
      }
    }
  })

  it('wobbles each rival in pairs that cancel out, within ±6%', () => {
    const h = heatOf(4, 1, false, 12)
    for (const schedule of h.targets) {
      const mean = (schedule[0]! + schedule[1]!) / 2
      for (let k = 0; k + 1 < schedule.length; k += 2) {
        expect(Math.abs(schedule[k]! + schedule[k + 1]! - 2 * mean)).toBeLessThanOrEqual(2)
        expect(Math.abs(schedule[k]! - mean)).toBeLessThanOrEqual(mean * 0.061)
      }
    }
  })

  it('paces the rivals faster every heat; Relaxed slows them', () => {
    expect(dashRivalRatesX10(1, false)).toEqual([35, 31, 27])
    expect(dashRivalRatesX10(2, false)[0]).toBe(41)
    expect(dashRivalRatesX10(1, true)).toEqual([28, 25, 22])
    let last = Infinity
    for (let heat = 1; heat <= 30; heat++) {
      const h = run(heatOf(heat), 0)
      expect(h.winner).not.toBe(0)
      expect(h.tick).toBeLessThan(last)
      last = h.tick
    }
  })

  it('a tap every 8 ticks (6.25 a second) wins heat 1 and loses heat 12', () => {
    for (let seed = 1; seed <= 20; seed++) {
      expect(run(heatOf(1, 1, false, seed), 8).winner).toBe(0)
      expect(run(heatOf(12, 1, false, seed), 8).winner).not.toBe(0)
    }
  })

  it('SPD and Relaxed help: at heat 7 the same taps lose at SPD 1, win at SPD 999, and win at SPD 1 with Relaxed', () => {
    for (let seed = 1; seed <= 10; seed++) {
      expect(run(heatOf(7, 1, false, seed), 8).winner).not.toBe(0)
      expect(run(heatOf(7, 999, false, seed), 8).winner).toBe(0)
      expect(run(heatOf(7, 1, true, seed), 8).winner).toBe(0)
    }
  })

  it('no taps never wins, and even a tap every tick at SPD 999 loses by heat 45, so every run ends', () => {
    const idle = run(heatOf(1), 0)
    expect(idle.winner).not.toBe(0)
    expect(idle.tick).toBeLessThan(DASH.maxTicks)
    let lostAt = 0
    for (let heat = 1; heat <= 45 && lostAt === 0; heat++) if (run(heatOf(heat, 999), 1).winner !== 0) lostAt = heat
    expect(lostAt).toBeGreaterThan(20)
    expect(lostAt).toBeLessThanOrEqual(45)
  })

  it('a close finish goes to whoever crossed first, not who ends up further; a dead heat goes to the player', () => {
    const t = DASH.track
    // The player crosses half-way through the tick, the rival at 60%, but the rival ends further past the line.
    expect(stepDash(crafted([{ pos: t - 1000, v: 2000 }, { pos: t - 3000, v: 5000 }, { pos: 0, v: 10 }, { pos: 0, v: 10 }]), 0).winner).toBe(0)
    expect(stepDash(crafted([{ pos: t - 3000, v: 5000 }, { pos: t - 1000, v: 2000 }, { pos: 0, v: 10 }, { pos: 0, v: 10 }]), 0).winner).toBe(1)
    expect(stepDash(crafted([{ pos: t - 1000, v: 2000 }, { pos: t - 2000, v: 4000 }, { pos: 0, v: 10 }, { pos: 0, v: 10 }]), 0).winner).toBe(0)
  })

  it('steps without touching the heat it was given', () => {
    const h = deepFreeze(heatOf(2))
    const next = stepDash(h, 3)
    expect(next.tick).toBe(1)
    expect(h.tick).toBe(0)
    expect(h.runners[0]!.pos).toBe(0)
  })

  it('picks three different rivals, never your own breed, topping up from the starters', () => {
    for (let seed = 1; seed <= 30; seed++) {
      const b = heatOf(1, 1, false, seed).breeds
      expect(new Set(b).size).toBe(3)
      expect(b).not.toContain(OWN)
    }
    const few = dashRivalBreeds(createRng(4), [OWN], OWN)
    expect(new Set(few).size).toBe(3)
    expect(few).not.toContain(OWN)
    for (const id of few) expect(STARTING_UNLOCKED).toContain(id)
    expect(new Set(dashRivalBreeds(createRng(5), [], OWN)).size).toBe(3)
  })

  it('pays 25G a heat with no cap, once a week on its own, and practice only keeps the best', () => {
    expect(dashPay(0)).toBe(0)
    expect(dashPay(6)).toBe(150)
    expect(dashPay(21)).toBe(525)
    expect(dashPay(-2)).toBe(0)
    const g = createGameState({ monster: makeMonster() })
    g.week = 30
    expect(canPlayDash(g)).toEqual({ ok: true })
    const r = applyDash(g, 9, false)
    expect(r).toMatchObject({ pay: 225, newBest: true, refused: null })
    expect(r.state.money).toBe(g.money + 225)
    expect(r.state.dashWeek).toBe(30)
    expect(r.state.dashBest).toBe(9)
    expect(applyDash(r.state, 3, false)).toMatchObject({ pay: 0, refused: 'played' })
    expect(canPlayDash({ ...r.state, week: 31 })).toEqual({ ok: true })
    // The other two jobs keep their own weeks.
    expect(applyOddJob(r.state, 10, 0).refused).toBeNull()
    expect(applyEchoStones(r.state, 4, false).refused).toBeNull()
    const p = applyDash(r.state, 12, true)
    expect(p).toMatchObject({ pay: 0, newBest: true, refused: null })
    expect(p.state.money).toBe(r.state.money)
    expect(p.state.dashBest).toBe(12)
    expect(applyDash(p.state, 2, true).newBest).toBe(false)
    expect(applyDash({ ...g, monster: null }, 3, true).refused).toBe('noMonster')
  })
})
