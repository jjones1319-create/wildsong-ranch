import { Scene, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { aimStudioRims, buildStudio, dirFrom } from './content.ts'

/** Nov 13: the rims stay behind the subject as the camera sees it, so a back view isn't lit face-on by them. */
describe('the studio rims and the camera (aimStudioRims)', () => {
  const S = ART.ultra.studio
  const focus = new Vector3(0, 0.5, 0)
  const studio = buildStudio(new Scene(), null, focus, 2)
  const at = (azDeg: number) => {
    aimStudioRims(studio, focus.clone().add(dirFrom(azDeg, 14).multiplyScalar(5)), focus)
    return [studio.rim.intensity, studio.rim2.intensity]
  }

  it('front, three-quarter and side views keep both rims at full strength (as before)', () => {
    for (const az of [0, 35, -35, 60, -60, 80, -80]) expect(at(az)).toEqual([S.rim.intensity, S.rim2.intensity])
  })

  it('from behind (a back view, the behind camera) both dim, the one nearest the camera most (to minPct)', () => {
    const [a, b] = at(180)
    expect(a).toBeLessThan(S.rim.intensity * 0.5)
    expect(b).toBeLessThan(S.rim2.intensity * 0.3)
    expect(b).toBeGreaterThanOrEqual((S.rim2.intensity * S.rimFacing.minPct) / 100 - 1e-9)
    // straight into a rim: the least it gets
    aimStudioRims(studio, focus.clone().add(dirFrom(S.rim.azDeg, 14).multiplyScalar(5)), focus)
    expect(studio.rim.intensity).toBeCloseTo((S.rim.intensity * S.rimFacing.minPct) / 100, 5)
  })

  it('in between it changes smoothly (no pop as the camera swings round)', () => {
    let prev = at(0)
    for (let az = 5; az <= 180; az += 5) {
      const now = at(az)
      expect(Math.abs(now[0]! - prev[0]!)).toBeLessThan(S.rim.intensity * 0.2)
      expect(Math.abs(now[1]! - prev[1]!)).toBeLessThan(S.rim2.intensity * 0.2)
      prev = now
    }
  })
})
