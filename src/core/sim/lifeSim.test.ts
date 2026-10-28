import { describe, expect, it } from 'vitest'
import { STRAIN } from '../../data/tuning.ts'
import { averageReports, simulateLife, type PolicyName } from './lifeSim.ts'

/**
 * GAME_DESIGN §26 raising targets, measured over 40 seeds each, without Stat Sweets, Songsheets or edits.
 *
 * The Great / Good / OK life bands need the strain-debt rule (STRAIN.mode = 'debt', the rule since the owner's
 * M1 decision); under the original ladder they are unreachable and are skipped. See docs/PROGRESS.md.
 */

const SEEDS = 40
const SMOOTH_RULE = STRAIN.mode === 'debt'
const runMany = (policy: PolicyName, breed: 'puddlepup' | 'cobblemaw' = 'puddlepup', grades?: Parameters<typeof simulateLife>[0]['grades']) =>
  Array.from({ length: SEEDS }, (_, i) => simulateLife({ breed, policy, seed: 1000 + i, grades }))

const between = (value: number, lo: number, hi: number) => {
  expect(value).toBeGreaterThanOrEqual(lo)
  expect(value).toBeLessThanOrEqual(hi)
}

describe('determinism', () => {
  it('the same seed gives the identical life', () => {
    const a = simulateLife({ breed: 'puddlepup', policy: 'Good', seed: 7 })
    const b = simulateLife({ breed: 'puddlepup', policy: 'Good', seed: 7 })
    expect(a).toEqual(b)
    expect(a.endedBy).toBe('passed')
    expect(a.weeksLived).toBeGreaterThan(100)
  })
})

describe('life lived vs nominal (§26)', () => {
  const great = () => averageReports(runMany('Great'))
  const good = () => averageReports(runMany('Good'))
  const ok = () => averageReports(runMany('OK'))
  const neglect = () => averageReports(runMany('Neglect'))

  it.skipIf(!SMOOTH_RULE)('Great care: 82–92%', () => between(great().lifeLivedPct, 82, 92))
  it.skipIf(!SMOOTH_RULE)('Good care: 76–88%', () => between(good().lifeLivedPct, 76, 88))
  it.skipIf(!SMOOTH_RULE)('OK care: 62–78%', () => between(ok().lifeLivedPct, 62, 78))

  it('Neglect: 25–45% with several breakdowns per life', () => {
    const avg = neglect()
    between(avg.lifeLivedPct, 25, 45)
    expect(avg.breakdowns).toBeGreaterThanOrEqual(2)
  })

  it('better care always means a longer life', () => {
    const [g, gd, o, n] = [great().lifeLivedPct, good().lifeLivedPct, ok().lifeLivedPct, neglect().lifeLivedPct]
    expect(g).toBeGreaterThanOrEqual(gd)
    expect(gd).toBeGreaterThan(o)
    expect(o).toBeGreaterThan(n)
  })
})

describe('stat totals with Good care (§26)', () => {
  it('a Steady breed with mostly C grades reaches about 700 / 1,450 / 2,350 at years 1 / 3 / 5', () => {
    const avg = averageReports(runMany('Good'))
    const [y1, , y3, , y5] = avg.totalsByYear
    between(y1!, 700 * 0.8, 700 * 1.2)
    between(y3!, 1450 * 0.8, 1450 * 1.2)
    between(y5!, 2350 * 0.8, 2350 * 1.2)
  })

  it('a Late bloomer with A/B grades reaches about 2,700 at year 5 and 3,200 at year 6', () => {
    const avg = averageReports(runMany('Good', 'cobblemaw', { LIF: 'B', POW: 'A', INT: 'B', SKI: 'A', SPD: 'B', DEF: 'A' }))
    // "A/B grades" is a hypothetical monster; ours is all A/B, so it runs a little hot. ±25% keeps the shape honest.
    // The result levels (v1.9) add their bonus above the gain caps, so loyal A/B monsters grow past the old 2,550 / 2,950.
    between(avg.totalsByYear[4]!, 2700 * 0.75, 2700 * 1.25)
    between(avg.totalsByYear[5]!, 3200 * 0.75, 3200 * 1.25)
  })
})

describe('drill outcome rates over a Good-care life (§26)', () => {
  it('Great and up 17–25% (Perfect 2–8%), Fine and Good 52–65%, Cheat 7–12%, Fail 8–14%', () => {
    const o = averageReports(runMany('Good')).outcomesPct
    between(o.Perfect + o.Superb + o.Great, 17, 25)
    between(o.Perfect, 2, 8)
    between(o.Good + o.Success, 52, 65)
    between(o.Cheat, 7, 12)
    between(o.Fail, 8, 14)
  })
})
