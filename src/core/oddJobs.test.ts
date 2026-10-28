import { describe, expect, it } from 'vitest'
import { ODD_JOBS } from '../data/tuning.ts'
import { applyOddJob, binFor, canPlayOddJob, gapMsAt, inOvertime, overtimeWindowMs, slideMsAt, turnipDealer, turnipPay, type Produce } from './oddJobs.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('Turnip Sort (CONTENT §13)', () => {
  it('pays +5G per sorted item and −5G per mix-up, never below 0, with no cap', () => {
    expect(turnipPay(10, 2)).toBe(40)
    expect(turnipPay(0, 5)).toBe(0)
    expect(turnipPay(40, 0)).toBe(200)
    expect(turnipPay(31, 1)).toBe(150)
    expect(turnipPay(0, 0)).toBe(0)
    expect(turnipPay(Number.NaN, 0)).toBe(0)
  })

  it('reaches overtime at 150G', () => {
    expect(inOvertime(30, 0)).toBe(true)
    expect(inOvertime(31, 1)).toBe(true)
    expect(inOvertime(29, 0)).toBe(false)
    expect(inOvertime(32, 3)).toBe(false)
  })

  it('sorts each kind into its own bin', () => {
    expect(binFor('turnip')).toBe('basket')
    expect(binFor('rock')).toBe('rocks')
    expect(binFor('weed')).toBe('compost')
  })

  it('is a free action once per in-game week, needs a monster, and keeps the best', () => {
    const g = createGameState({ monster: makeMonster() })
    g.week = 12
    expect(canPlayOddJob(g)).toEqual({ ok: true })
    const played = applyOddJob(g, 12, 3)
    expect(played.refused).toBeNull()
    expect(played.pay).toBe(45)
    expect(played.state.money).toBe(g.money + 45)
    expect(played.state.oddJobWeek).toBe(12)
    expect(played.state.turnipBest).toBe(12)
    expect(played.newBest).toBe(true)
    expect(applyOddJob(played.state, 20, 0)).toMatchObject({ pay: 0, refused: 'played' })
    expect(canPlayOddJob({ ...played.state, week: 13 })).toEqual({ ok: true })
    expect(applyOddJob({ ...g, monster: null }, 5, 0).refused).toBe('noMonster')
    expect(applyOddJob({ ...g, monster: null }, 5, 0, true).refused).toBe('noMonster')
    expect(applyOddJob(g, 2.9, -4).pay).toBe(10)
    // No cap: a long overtime pays every item.
    expect(applyOddJob(g, 70, 1).pay).toBe(345)
  })

  it('practice pays nothing and leaves the week alone, but keeps a best score', () => {
    const g = createGameState({ monster: makeMonster() })
    g.week = 4
    const p = applyOddJob(g, 41, 2, true)
    expect(p.refused).toBeNull()
    expect(p.pay).toBe(0)
    expect(p.state.money).toBe(g.money)
    expect(p.state.oddJobWeek).toBeNull()
    expect(p.state.turnipBest).toBe(41)
    const paid = applyOddJob(p.state, 20, 0)
    expect(paid.state.turnipBest).toBe(41)
    expect(paid.newBest).toBe(false)
    // A played week still allows practice.
    expect(applyOddJob(paid.state, 5, 0, true).refused).toBeNull()
  })

  it('deals the first phase exactly as before: turnips and rocks, mostly turnips', () => {
    for (let seed = 1; seed <= 20; seed++) {
      const old = createRng(seed)
      const dealer = turnipDealer(seed)
      for (let i = 0; i < 80; i++) expect(dealer.next(false)).toBe(old.chance(ODD_JOBS.turnipPct) ? 'turnip' : 'rock')
    }
    const dealer = turnipDealer(42)
    const items = Array.from({ length: 200 }, () => dealer.next(false))
    expect(items).not.toContain('weed')
    const turnips = items.filter((p) => p === 'turnip').length
    expect(turnips / items.length).toBeGreaterThan(0.45)
    expect(turnips / items.length).toBeLessThan(0.75)
    const other = turnipDealer(43)
    expect(Array.from({ length: 40 }, () => other.next(false))).not.toEqual(items.slice(0, 40))
  })

  it('deals overtime from its own stream: a weed first, then all three kinds, whenever it began', () => {
    const early = turnipDealer(9)
    for (let i = 0; i < 5; i++) early.next(false)
    const late = turnipDealer(9)
    for (let i = 0; i < 37; i++) late.next(false)
    const a = Array.from({ length: 300 }, () => early.next(true))
    const b = Array.from({ length: 300 }, () => late.next(true))
    expect(a).toEqual(b)
    expect(a[0]).toBe('weed')
    const counts: Record<Produce, number> = { turnip: 0, rock: 0, weed: 0 }
    for (const p of a) counts[p] += 1
    for (const k of ['turnip', 'rock', 'weed'] as const) expect(counts[k]).toBeGreaterThan(50)
  })

  it('ramps the first phase over 30 seconds and shrinks the overtime window item by item down to a floor', () => {
    expect(slideMsAt(0)).toBe(ODD_JOBS.slideMs.start)
    expect(slideMsAt(ODD_JOBS.seconds * 1000)).toBe(ODD_JOBS.slideMs.end)
    expect(slideMsAt(ODD_JOBS.seconds * 500)).toBe(Math.round((ODD_JOBS.slideMs.start + ODD_JOBS.slideMs.end) / 2))
    expect(slideMsAt(1e9)).toBe(ODD_JOBS.slideMs.end)
    expect(gapMsAt(0)).toBe(ODD_JOBS.gapMs.start)
    expect(gapMsAt(ODD_JOBS.seconds * 1000)).toBe(ODD_JOBS.gapMs.end)
    expect(overtimeWindowMs(0)).toBe(1300)
    expect(overtimeWindowMs(1)).toBe(1288)
    expect(overtimeWindowMs(50)).toBe(700)
    expect(overtimeWindowMs(80)).toBe(ODD_JOBS.overtime.windowMs.floor)
    expect(overtimeWindowMs(10_000)).toBe(ODD_JOBS.overtime.windowMs.floor)
    expect(overtimeWindowMs(-3)).toBe(1300)
  })
})
