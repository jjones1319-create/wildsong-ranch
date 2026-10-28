import { describe, expect, it } from 'vitest'
import { BREED_IDS } from '../../data/types.ts'
import { averageReports, simulateLife } from './lifeSim.ts'

/**
 * M9 per-breed raising guards. The full 30 × 4 matrix over 40 seeds lives in docs/BALANCE_REPORT.md
 * (`npm run sim:balance`); this keeps every breed honest with a handful of seeds per run: a Good-care life sits
 * near the §26 band (widened for the small sample), the stat total grows year on year, and Neglect is a
 * clearly shorter life with breakdowns.
 */

const GOOD_SEEDS = 8
const NEGLECT_SEEDS = 4

describe('every breed under Good and Neglect care (§26, sampled)', () => {
  for (const breed of BREED_IDS) {
    it(`${breed}: Good care 70–92 % of its life with growing totals; Neglect far shorter`, () => {
      const good = averageReports(Array.from({ length: GOOD_SEEDS }, (_, i) => simulateLife({ breed, policy: 'Good', seed: 500 + i })))
      expect(good.lifeLivedPct).toBeGreaterThanOrEqual(70)
      expect(good.lifeLivedPct).toBeLessThanOrEqual(92)
      const [y1, , y3] = good.totalsByYear
      expect(y1!).toBeGreaterThan(400)
      expect(y3!).toBeGreaterThan(y1! * 1.5)
      const o = good.outcomesPct
      expect(o.Perfect + o.Superb + o.Great + o.Good + o.Success).toBeGreaterThan(70)

      const neglect = averageReports(Array.from({ length: NEGLECT_SEEDS }, (_, i) => simulateLife({ breed, policy: 'Neglect', seed: 700 + i })))
      expect(neglect.lifeLivedPct).toBeLessThan(good.lifeLivedPct - 25)
      expect(neglect.breakdowns).toBeGreaterThanOrEqual(2)
    })
  }
})
