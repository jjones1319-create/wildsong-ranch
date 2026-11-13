import { PerspectiveCamera, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { cineParams, cinePoints, cineShot, flyPoints, flyShotInside } from './cineShot.ts'
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

  // a flying Hearthwing (ultra/flight.ts): 1 m tall, hovering 1.2 m up, its wings 2.4 m open (2.64 with the margin);
  // grown: twice that. In the Guild ring the cameras keep within about 5.5 m of the centre
  const fence = (p: Vector3) => {
    const r = Math.hypot(p.x, p.z)
    if (r > 5.5) p.multiplyScalar(5.5 / r)
    return p
  }
  for (const [name, aspect] of [['upright', UPRIGHT], ['sideways', SIDEWAYS]] as const) {
    for (const k of [1, 2]) {
      for (const [gap, off] of [[3, 0], [4.4, 0], [6, 0], [4.4, 2]] as const) {
        it(`${name}, flying (${k} m tall), ${gap} m apart${off ? ' off-centre' : ''}: the whole flier in the sky above the target, not too big`, () => {
          const air = { liftM: 1.2 * k, spanM: 2.64 * k }
          const a = new Vector3(-gap / 2 + off, 0, 0.3)
          const b = new Vector3(gap / 2 + off, 0, -0.3)
          const heights = [k, 1] as const
          const s = cineShot(a, b, aspect, 1, fence, heights, air)
          const cam = new PerspectiveCamera(s.fov, aspect, 0.05, 1000)
          cam.position.copy(s.from)
          cam.lookAt(s.look)
          cam.updateMatrixWorld()
          const band = sideFraming(aspect).band
          const pts = flyPoints(a, b, heights, air)
          // always its whole body up there and the target's chest in the clear band; sideways everything (both wingtips,
          // the target whole); upright the narrow band may let the wingtips reach the edges or the target's feet tuck
          // under the cards
          const chest = b.clone().setY(0.6)
          for (const p of [...pts.body, chest]) {
            const q = p.clone().project(cam)
            expect(q.z).toBeLessThan(1)
            expect(bandNeed(q.x, q.y, band)).toBeLessThanOrEqual(1.001)
          }
          if (aspect > 1) expect(s.fits).toBe(true)
          // the flier at most about 40% of the screen (its box, wings and all), above the target
          const box = (vs: readonly Vector3[]) => {
            const ps = vs.map((v) => v.clone().project(cam))
            return { x0: Math.min(...ps.map((p) => p.x)), x1: Math.max(...ps.map((p) => p.x)), y0: Math.min(...ps.map((p) => p.y)), y1: Math.max(...ps.map((p) => p.y)) }
          }
          const f = box(pts.flier)
          expect(((f.x1 - f.x0) * (f.y1 - f.y0)) / 4).toBeLessThanOrEqual(ART.duel.flight.cut.maxCoverPct / 100 + 0.01)
          const body = box(pts.body)
          const tg = box(pts.target)
          expect((body.y0 + body.y1) / 2).toBeGreaterThan((tg.y0 + tg.y1) / 2)
          expect(s.fov).toBeLessThanOrEqual(Math.max(...ART.duel.flight.cut.fovsDeg))
          // inside the fence (beyond it the crowd, banners and gate posts block the view); only the grown form upright and
          // far apart has no shot inside
          if (!(aspect < 1 && k === 2 && gap >= 6)) expect(Math.hypot(s.from.x, s.from.z)).toBeLessThanOrEqual(5.5 + 1e-6)
        })
      }
    }
  }

  it('a flier whose cut would stand beyond the fence hovers lower (to 0.8× its height at the lowest) until it is inside', () => {
    const FL = ART.duel.flight
    for (const [aspect, k, gap] of [[UPRIGHT, 2, 6], [UPRIGHT, 2, 6.5], [UPRIGHT, 1, 4.4], [SIDEWAYS, 2, 6]] as const) {
      const a = new Vector3(-gap / 2, 0, 0.3)
      const b = new Vector3(gap / 2, 0, -0.3)
      const air = { liftM: (k * FL.peakPct) / 100, spanM: 2.66 * k }
      const own = cineShot(a, b, aspect, 1, fence, [k, 1], air)
      const f = flyShotInside(a, b, aspect, 1, fence, [k, 1], air)
      // never higher, never below minPeakPct, the lens no wider than the cut's
      expect(f.liftM).toBeLessThanOrEqual(air.liftM)
      expect(f.liftM).toBeGreaterThanOrEqual((k * FL.minPeakPct) / 100 - 1e-9)
      expect(f.shot.fov).toBeLessThanOrEqual(Math.max(...FL.cut.fovsDeg))
      if (own.inside) expect(f.liftM).toBe(air.liftM)
      // lowered only when that brings it inside the fence; otherwise its own height and the shot beyond it
      if (f.liftM < air.liftM) expect(f.shot.inside).toBe(true)
      else expect(f.shot.inside).toBe(own.inside)
    }
  })

  it('the target stays big enough to read upright at Near (its height at least a fifth of the screen)', () => {
    const { ndc } = shot(UPRIGHT, 3)
    expect((ndc[2]!.y - ndc[1]!.y) / 2).toBeGreaterThan(0.2)
  })
})
