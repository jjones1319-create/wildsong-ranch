import { PerspectiveCamera, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { cineParams, cinePoints, cineShot } from './cineShot.ts'
import { bandNeed, sideFraming } from './framing.ts'

/** docs/BATTLE_3D.md §6: a Special's or Signature's cut shows the attacker's shoulders and the whole target. */
describe('the over-the-shoulder cut', () => {
  const C = ART.duel.cine.attack
  const UPRIGHT = 412 / 892
  const SIDEWAYS = 892 / 412

  /** Where the cut puts the attacker's shoulders and the target's feet and head (NDC), and how far into the band. */
  function shot(aspect: number, gap: number, sideSign = 1) {
    const a = new Vector3(-gap / 2, 0, 0.4)
    const b = new Vector3(gap / 2, 0, -0.3)
    const s = cineShot(a, b, aspect, sideSign)
    const cam = new PerspectiveCamera(s.fov, aspect, 0.05, 1000)
    cam.position.copy(s.from)
    cam.lookAt(s.look)
    cam.updateMatrixWorld()
    const band = sideFraming(aspect).band
    const ndc = cinePoints(a, b).map((p) => p.clone().project(cam))
    return { s, ndc, need: Math.max(...ndc.map((p) => bandNeed(p.x, p.y, band))) }
  }

  it('sideways keeps the v1.21 shot (beside and behind the attacker)', () => {
    expect(cineParams(SIDEWAYS)).toEqual({ back: C.back, side: C.side, height: C.height, lookPct: C.lookPct, lookY: C.lookY })
    const { s } = shot(SIDEWAYS, 3)
    expect(s.from.y).toBeCloseTo(C.height)
  })

  it('upright stands higher and more directly behind', () => {
    const p = cineParams(UPRIGHT)
    expect(p.height).toBeGreaterThan(C.height)
    expect(p.side).toBeLessThan(C.side)
  })

  for (const [name, aspect] of [['upright', UPRIGHT], ['sideways', SIDEWAYS], ['square-ish', 1.1]] as const) {
    for (const gap of [2.2, 3, 5, 8]) {
      it(`${name}, ${gap} m apart: shoulders and the whole target in the clear band`, () => {
        for (const sign of [1, -1]) {
          const { s, ndc, need } = shot(aspect, gap, sign)
          expect(need).toBeLessThanOrEqual(1.001)
          expect(s.fov).toBeLessThanOrEqual(ART.duel.confine.maxFov)
          for (const p of ndc) expect(p.z).toBeLessThan(1)
          // the attacker is nearer the bottom than the target's head (its back in the foreground)
          expect(ndc[0]!.y).toBeLessThan(ndc[2]!.y)
        }
      })
    }
  }

  it('the target stays big enough to read upright at Near (its height at least a fifth of the screen)', () => {
    const { ndc } = shot(UPRIGHT, 3)
    expect((ndc[2]!.y - ndc[1]!.y) / 2).toBeGreaterThan(0.2)
  })
})
