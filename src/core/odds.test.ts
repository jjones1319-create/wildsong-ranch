import { describe, expect, it } from 'vitest'
import { TRANSPARENCY } from '../data/tuning.ts'
import { drillOdds, oddsWord } from './odds.ts'
import { makeMonster } from './test-helpers.ts'

describe('drill odds words (§6.8)', () => {
  it('maps the good-outcome chance to the four words at the band edges', () => {
    const b = TRANSPARENCY.oddsBands
    expect(oddsWord(100)).toBe('eager')
    expect(oddsWord(b.eager)).toBe('eager')
    expect(oddsWord(b.eager - 0.01)).toBe('likely')
    expect(oddsWord(b.likely)).toBe('likely')
    expect(oddsWord(b.likely - 0.01)).toBe('risky')
    expect(oddsWord(b.risky)).toBe('risky')
    expect(oddsWord(b.risky - 0.01)).toBe('veryRisky')
    expect(oddsWord(0)).toBe('veryRisky')
  })

  it('a fresh baby looks eager; a wrecked monster is very risky, with truancy taken off the top', () => {
    const fresh = drillOdds(makeMonster({ agePct: 0 }), 'log-toss')
    expect(fresh.truancyPct).toBe(0)
    expect(fresh.good).toBeGreaterThan(TRANSPARENCY.oddsBands.eager)
    expect(fresh.word).toBe('eager')
    expect(Math.round(fresh.pct.great + fresh.pct.success + fresh.pct.cheat + fresh.pct.fail)).toBe(100)
    const wrecked = drillOdds(makeMonster({ agePct: 25, fatigue: 90, stress: 80, spoil: 20, fear: 20, nature: -10 }), 'log-toss')
    expect(wrecked.truancyPct).toBeGreaterThan(0)
    expect(wrecked.good).toBeLessThan(wrecked.pct.great + wrecked.pct.success)
    expect(wrecked.word).toBe('veryRisky')
  })
})
