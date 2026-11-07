import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { telegraphAlpha } from './telegraph.ts'

/** docs/BATTLE_3D.md §7: the floor telegraphs are quiet and step aside for the attack's own effects. */
describe('wind-up telegraphs', () => {
  const T = ART.duel.telegraph
  const peak = T.opacity

  it('is quieter than the v1.21 lanes (a 50% fill), and its fill fainter still', () => {
    expect(peak).toBeLessThanOrEqual(0.6)
    expect((peak * T.fillPct) / 100).toBeLessThan(0.25)
    expect(T.widthPct).toBeLessThan(100)
  })

  it('fades in, holds, and fades out from the release to nothing at the landing', () => {
    // a Heavy: 0.4 s wind-up, released (the lunge) for the last 0.3 s, but held to holdPct of it at least
    const [born, release, land] = [0, 0.1, 0.4]
    expect(telegraphAlpha(-0.01, born, release, land)).toBe(0)
    expect(telegraphAlpha(0.01, born, release, land)).toBeLessThan(peak)
    const holdTo = (0.4 * T.holdPct) / 100
    expect(telegraphAlpha(holdTo - 0.01, born, release, land)).toBeCloseTo(peak)
    const late = telegraphAlpha(0.35, born, release, land)
    expect(late).toBeGreaterThan(0)
    expect(late).toBeLessThan(peak / 2)
    expect(telegraphAlpha(0.4, born, release, land)).toBe(0)
  })

  it('a short wind-up (released at once) still shows at full for a moment', () => {
    const w = 0.167
    expect(telegraphAlpha((w * T.holdPct) / 100 - 0.005, 0, 0, w)).toBeCloseTo(peak)
  })
})
