import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { lungeFor, lungeReach } from './attacks.ts'

/** docs/BATTLE_3D.md §7: a melee attack reaches its target exactly on the engine's landing, then comes home. */
describe('the melee lunge', () => {
  const A = ART.duel.attack

  it('starts home, reaches contact on the landing, holds, and comes back', () => {
    const l = lungeFor(10, 0.4)
    expect(l.impact).toBeCloseTo(10.4)
    expect(lungeReach(10, l)).toBe(0)
    expect(lungeReach(l.start, l)).toBe(0)
    expect(lungeReach(l.impact, l)).toBe(1)
    expect(lungeReach(l.impact + A.lungeHoldSec / 2, l)).toBe(1)
    expect(lungeReach(l.end, l)).toBe(0)
    expect(lungeReach(l.end + 1, l)).toBe(0)
  })

  it('leans in smoothly and only over the end of the wind-up', () => {
    const l = lungeFor(0, 0.4)
    expect(l.start).toBeCloseTo(0.4 - A.lungeSec)
    let last = 0
    for (let t = l.start; t <= l.impact; t += 0.02) {
      const r = lungeReach(t, l)
      expect(r).toBeGreaterThanOrEqual(last - 1e-9)
      last = r
    }
    // a quick technique (shorter wind-up than the lean) still starts at once and lands on time
    const quick = lungeFor(5, 0.1)
    expect(quick.start).toBeCloseTo(5)
    expect(quick.impact).toBeCloseTo(5.1)
  })
})
