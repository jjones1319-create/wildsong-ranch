import { describe, expect, it } from 'vitest'
import { cyrb53 } from '../hash.ts'
import { simulateLife, type LifeSimOptions } from './lifeSim.ts'

/**
 * A golden record of six fixed-seed lives. v1.11 added growth grade S and per-grade stat caps (E 1000 … S 1500,
 * up from a flat 999); below the caps every gain must stay exactly what it was, so this hash was taken on the
 * commit before that change. The guard below shows why it holds: no simulated stat gets near 1000.
 */
const LIVES: LifeSimOptions[] = [
  { breed: 'puddlepup', policy: 'Good', seed: 11 },
  { breed: 'cobblemaw', policy: 'Good', seed: 12, grades: { LIF: 'A', POW: 'A', INT: 'B', SKI: 'B', SPD: 'B', DEF: 'A' } },
  { breed: 'tumblefox', policy: 'Great', seed: 13 },
  { breed: 'aurelwyrm', policy: 'Good', seed: 14 },
  { breed: 'gearhoot', policy: 'Good', seed: 15 },
  { breed: 'bloatoad', policy: 'OK', seed: 16 },
]

describe('raising golden record', () => {
  it('six fixed lives give the same years as before the grade-S change, and no stat gets near 1000', () => {
    const reports = LIVES.map((o) => simulateLife(o))
    expect(reports[0]!.weeksLived).toBeGreaterThan(100)
    const withoutLines = reports.map((r) => ({ ...r, lines: [] }))
    expect(cyrb53(JSON.stringify(withoutLines))).toBe(5344971507563367)
    for (const r of reports) for (const y of r.years) expect(Math.max(...Object.values(y.stats))).toBeLessThan(1000)
  })
})
