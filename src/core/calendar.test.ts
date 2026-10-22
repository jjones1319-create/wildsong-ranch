import { describe, expect, it } from 'vitest'
import { dateOf, isMonthStart, isUpgradeOfferWeek, rollWeather, seasonOf, weekIndexOf, WEEKS_PER_YEAR } from './calendar.ts'
import { createRng } from './rng.ts'

describe('calendar (§3)', () => {
  it('has 48 weeks per year and starts in Year 1, January, week 1', () => {
    expect(WEEKS_PER_YEAR).toBe(48)
    expect(dateOf(0)).toEqual({ year: 1, month: 1, week: 1 })
    expect(dateOf(3)).toEqual({ year: 1, month: 1, week: 4 })
    expect(dateOf(4)).toEqual({ year: 1, month: 2, week: 1 })
    expect(dateOf(47)).toEqual({ year: 1, month: 12, week: 4 })
    expect(dateOf(48)).toEqual({ year: 2, month: 1, week: 1 })
  })

  it('round-trips week indexes through dates', () => {
    for (let i = 0; i < 500; i += 7) expect(weekIndexOf(dateOf(i))).toBe(i)
  })

  it('maps months to seasons', () => {
    expect([12, 1, 2].map(seasonOf)).toEqual(['Winter', 'Winter', 'Winter'])
    expect([3, 4, 5].map(seasonOf)).toEqual(['Spring', 'Spring', 'Spring'])
    expect([6, 7, 8].map(seasonOf)).toEqual(['Summer', 'Summer', 'Summer'])
    expect([9, 10, 11].map(seasonOf)).toEqual(['Autumn', 'Autumn', 'Autumn'])
  })

  it('knows month starts and the May week 4 upgrade offer', () => {
    expect([0, 4, 8, 48].every(isMonthStart)).toBe(true)
    expect([1, 2, 3, 5].some(isMonthStart)).toBe(false)
    expect(isUpgradeOfferWeek(weekIndexOf({ year: 1, month: 5, week: 4 }))).toBe(true)
    expect(isUpgradeOfferWeek(weekIndexOf({ year: 3, month: 5, week: 4 }))).toBe(true)
    expect(isUpgradeOfferWeek(weekIndexOf({ year: 1, month: 5, week: 3 }))).toBe(false)
  })

  it('rolls Storm only in summer and Snow only in winter, roughly 20% storms', () => {
    const rng = createRng(42)
    const counts = { summerStorm: 0, winterSnow: 0, bad: 0 }
    const n = 3000
    for (let i = 0; i < n; i++) {
      const summer = rollWeather(rng, 7)
      const winter = rollWeather(rng, 1)
      const spring = rollWeather(rng, 4)
      if (summer === 'Storm') counts.summerStorm++
      if (summer === 'Snow') counts.bad++
      if (winter === 'Snow') counts.winterSnow++
      if (winter === 'Storm') counts.bad++
      if (spring === 'Storm' || spring === 'Snow') counts.bad++
    }
    expect(counts.bad).toBe(0)
    expect(counts.summerStorm / n).toBeGreaterThan(0.15)
    expect(counts.summerStorm / n).toBeLessThan(0.25)
    expect(counts.winterSnow).toBeGreaterThan(0)
  })
})
