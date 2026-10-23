import { describe, expect, it } from 'vitest'
import { ODD_JOBS } from '../data/tuning.ts'
import { applyOddJob, canPlayOddJob, gapMsAt, slideMsAt, turnipPay, turnipSequence } from './oddJobs.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('Turnip Sort (CONTENT §13)', () => {
  it('pays +5G per sorted item and −5G per mix-up, never below 0, capped at 150G', () => {
    expect(turnipPay(10, 2)).toBe(40)
    expect(turnipPay(0, 5)).toBe(0)
    expect(turnipPay(40, 0)).toBe(ODD_JOBS.cap)
    expect(turnipPay(31, 1)).toBe(150)
    expect(turnipPay(0, 0)).toBe(0)
  })

  it('is a free action once per in-game week, and needs a monster', () => {
    const g = createGameState({ monster: makeMonster() })
    g.week = 12
    expect(canPlayOddJob(g)).toEqual({ ok: true })
    const played = applyOddJob(g, 12, 3)
    expect(played.refused).toBeNull()
    expect(played.pay).toBe(45)
    expect(played.state.money).toBe(g.money + 45)
    expect(played.state.oddJobWeek).toBe(12)
    expect(applyOddJob(played.state, 20, 0)).toMatchObject({ pay: 0, refused: 'played' })
    expect(canPlayOddJob({ ...played.state, week: 13 })).toEqual({ ok: true })
    expect(applyOddJob({ ...g, monster: null }, 5, 0).refused).toBe('noMonster')
    expect(applyOddJob(g, 2.9, -4).pay).toBe(10)
  })

  it('deals a deterministic chute of mostly turnips, and the ramp shortens the window over the round', () => {
    const a = turnipSequence(42)
    expect(a).toEqual(turnipSequence(42))
    expect(a).toHaveLength(ODD_JOBS.items)
    const turnips = a.filter((p) => p === 'turnip').length
    expect(turnips / a.length).toBeGreaterThan(0.45)
    expect(turnips / a.length).toBeLessThan(0.75)
    expect(a).not.toEqual(turnipSequence(43))
    expect(slideMsAt(0)).toBe(ODD_JOBS.slideMs.start)
    expect(slideMsAt(ODD_JOBS.seconds * 1000)).toBe(ODD_JOBS.slideMs.end)
    expect(slideMsAt(ODD_JOBS.seconds * 500)).toBe(Math.round((ODD_JOBS.slideMs.start + ODD_JOBS.slideMs.end) / 2))
    expect(slideMsAt(1e9)).toBe(ODD_JOBS.slideMs.end)
    expect(gapMsAt(0)).toBe(ODD_JOBS.gapMs.start)
    expect(gapMsAt(ODD_JOBS.seconds * 1000)).toBe(ODD_JOBS.gapMs.end)
  })
})
