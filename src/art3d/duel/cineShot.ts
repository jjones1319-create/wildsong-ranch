import { PerspectiveCamera, Vector3 } from 'three'
import { ART } from '../../data/tuning.ts'
import { bandNeed, sideFraming } from './framing.ts'

/**
 * docs/BATTLE_3D.md §6–§7.1: the cut for a Special or Signature, over the attacker's shoulder toward the target, framed
 * for the screen's shape. Sideways, the camera stands beside and behind the attacker. Upright the lens is narrow, so a
 * shoulder beside the target falls off the screen's edge (the v1.21 review); instead the camera stands higher and more
 * directly behind, looking down past the attacker's head: its back low in the picture, the target above it. Between
 * the two shapes it blends. Then the lens widens until the attacker's shoulders and the whole target sit in the clear
 * band (between the top bar and the technique panel, or left of the cards).
 *
 * A flying attacker (§8.5) gets its own cut instead (flyShot): the whole flier in the sky, wings spread, the target
 * and the fire's landing below it.
 */

const D = ART.duel
const C = D.cine.attack
const FC = D.flight.cut

/** A flying attacker (ultra/flight.ts): its hover height (feet off the floor) and its open wingspan, in metres. */
export interface CineAir {
  liftM: number
  spanM: number
}

export interface CineShot {
  from: Vector3
  look: Vector3
  fov: number
  /** Every point that must be in the shot is. */
  fits: boolean
  /** The camera stands inside the fence (beyond it, only when nothing inside holds the shot). */
  inside: boolean
}

type Band = ReturnType<typeof sideFraming>['band']

const lerp = (a: number, b: number, k: number) => a + (b - a) * k

/** The shot's numbers for this screen shape: upright (portrait) → sideways (the landscape numbers), blended between. */
export function cineParams(aspect: number): { back: number; side: number; height: number; lookPct: number; lookY: number } {
  const P = C.portrait
  const k = Math.min(1, Math.max(0, (aspect - D.side.portrait.aspect) / (D.side.landscape.aspect - D.side.portrait.aspect)))
  return { back: lerp(P.back, C.back, k), side: lerp(P.side, C.side, k), height: lerp(P.height, C.height, k), lookPct: lerp(P.lookPct, C.lookPct, k), lookY: lerp(P.lookY, C.lookY, k) }
}

/** The points that must be in the shot: the attacker's shoulders, and the target's feet and head (heights in metres). */
export function cinePoints(attacker: Vector3, target: Vector3, heights: readonly [number, number] = [D.monsterHeightM, D.monsterHeightM]): Vector3[] {
  return [attacker.clone().setY(attacker.y + 0.75 * heights[0]), target.clone().setY(target.y + 0.05), target.clone().setY(target.y + heights[1])]
}

/**
 * The cut from `attacker` toward `target` (their feet), on the side-on camera's side (`sideSign`). `fence` keeps the
 * camera inside the fence (it may move it); the lens is then fitted from there. `heights` are the two monsters' (m):
 * the camera stands back and up in proportion to the attacker's (the numbers are Puddlepup's). A flying attacker
 * (`air`): flyShot.
 */
export function cineShot(
  attacker: Vector3,
  target: Vector3,
  aspect: number,
  sideSign: number,
  fence: (p: Vector3) => Vector3 = (p) => p,
  heights: readonly [number, number] = [D.monsterHeightM, D.monsterHeightM],
  air?: CineAir,
): CineShot {
  if (air && air.liftM > 0) return flyShot(attacker, target, aspect, sideSign, fence, heights, air)
  const p0 = cineParams(aspect)
  const k = heights[0] / D.monsterHeightM
  const q = { ...p0, back: p0.back * k, side: p0.side * k, height: p0.height * k, lookY: p0.lookY * k }
  const u = flat(attacker, target)
  const n = new Vector3(-u.z, 0, u.x)
  const from = fence(attacker.clone().addScaledVector(u, -q.back).addScaledVector(n, q.side * sideSign).setY(attacker.y + q.height))
  const look = attacker.clone().lerp(target, q.lookPct / 100)
  look.y += q.lookY
  const best = frame(from, look, cinePoints(attacker, target, heights), aspect, sideFraming(aspect).band)
  return { from, look: best.look, fov: best.fov, fits: best.fits, inside: true }
}

/** The unit direction from a to b on the floor. */
function flat(a: Vector3, b: Vector3): Vector3 {
  const u = b.clone().sub(a).setY(0)
  if (u.lengthSq() < 1e-6) u.set(0, 0, 1)
  return u.normalize()
}

/**
 * Aims from `from` at `look` and fits the lens to the points; far apart, the plain aim can't hold them: aim at their
 * middle instead (the band's centre), and refit. `fits`: every point is in the band.
 */
function frame(from: Vector3, look0: Vector3, pts: readonly Vector3[], aspect: number, band: Band): { look: Vector3; fov: number; fits: boolean } {
  const look = look0.clone()
  const cam = new PerspectiveCamera(D.fov, aspect, 0.05, D.far)
  cam.position.copy(from)
  cam.lookAt(look)
  cam.updateMatrixWorld()
  let fov = fitLens(cam, pts, band)
  if (fov > C.recentreFov) {
    recentre(cam, look, pts, band, fov, aspect)
    fov = fitLens(cam, pts, band)
  }
  cam.fov = fov
  cam.updateProjectionMatrix()
  return { look, fov, fits: allIn(cam, pts, band) }
}

/** Turns the camera so the points' box sits in the band's centre (it moves `look`). */
function recentre(cam: PerspectiveCamera, look: Vector3, pts: readonly Vector3[], band: Band, fov: number, aspect: number): void {
  const box = boxOf(cam, pts)
  const t = Math.tan((fov * Math.PI) / 360)
  const d = cam.position.distanceTo(look)
  const e = cam.matrixWorld.elements
  const right = new Vector3(e[0], e[1], e[2]).normalize()
  const up = new Vector3(e[4], e[5], e[6]).normalize()
  look.addScaledVector(right, ((box[0] + box[1]) / 2 - (band.left + band.right) / 2) * d * t * aspect)
  look.addScaledVector(up, ((box[2] + box[3]) / 2 - (band.top + band.bottom) / 2) * d * t)
  cam.lookAt(look)
  cam.updateMatrixWorld()
}

const P = new Vector3()

/** The points' box on screen (NDC): left, right, bottom, top. */
function boxOf(cam: PerspectiveCamera, pts: readonly Vector3[]): [number, number, number, number] {
  const box: [number, number, number, number] = [Infinity, -Infinity, Infinity, -Infinity]
  for (const v of pts) {
    P.copy(v).project(cam)
    box[0] = Math.min(box[0], P.x)
    box[1] = Math.max(box[1], P.x)
    box[2] = Math.min(box[2], P.y)
    box[3] = Math.max(box[3], P.y)
  }
  return box
}

function allIn(cam: PerspectiveCamera, pts: readonly Vector3[], band: Band): boolean {
  return pts.every((v) => (P.copy(v).project(cam), P.z < 1 && bandNeed(P.x, P.y, band) <= 1.001))
}

/** The narrowest lens (from the duel's own, up to the widest allowed) that holds every point in the band. */
function fitLens(cam: PerspectiveCamera, pts: readonly Vector3[], band: Band): number {
  let fov: number = D.fov
  for (; fov < D.confine.maxFov; fov += 1) {
    cam.fov = fov
    cam.updateProjectionMatrix()
    if (pts.every((v) => (P.copy(v).project(cam), P.z < 1 && bandNeed(P.x, P.y, band) <= 1))) break
  }
  return Math.min(fov, D.confine.maxFov)
}

/* ---------------------------------------------------------------------------------------------- the flier's cut */

/** A box's eight corners: centre on the floor at `at`, `len` along u, `wide` across, from `y0` up `tall`. */
function corners(at: Vector3, u: Vector3, len: number, wide: number, y0: number, tall: number): Vector3[] {
  const n = new Vector3(-u.z, 0, u.x)
  const out: Vector3[] = []
  for (const a of [-0.5, 0.5]) for (const b of [-0.5, 0.5]) for (const y of [y0, y0 + tall]) out.push(at.clone().addScaledVector(u, a * len).addScaledVector(n, b * wide).setY(at.y + y))
  return out
}

/**
 * What a flier's cut must hold: the flier at its hover (its body box, its head, its open wingtips either side) and
 * its middle half way up (`floor`: most of the climb and the landing, which happen in the cut too); the target whole.
 * Sizes from the heights (a body about 1.4 × its height long and 0.6 × wide).
 */
export function flyPoints(attacker: Vector3, target: Vector3, heights: readonly [number, number], air: CineAir): { flier: Vector3[]; body: Vector3[]; target: Vector3[]; floor: Vector3 } {
  const u = flat(attacker, target)
  const [h0, h1] = heights
  const body = corners(attacker, u, 1.4 * h0, 0.6 * h0, air.liftM, h0)
  const n = new Vector3(-u.z, 0, u.x).multiplyScalar(air.spanM / 2)
  const wingY = attacker.y + air.liftM + 0.6 * h0
  const flier = [...body, attacker.clone().add(n).setY(wingY), attacker.clone().sub(n).setY(wingY)]
  return { flier, body, target: corners(target, u, 1.4 * h1, 0.6 * h1, 0, h1), floor: attacker.clone().setY(attacker.y + air.liftM / 2 + 0.5 * h0) }
}

/** The share of the screen a set of points' box covers (0–1). */
function cover(cam: PerspectiveCamera, pts: readonly Vector3[]): number {
  const b = boxOf(cam, pts)
  const w = Math.max(0, Math.min(1, b[1]) - Math.max(-1, b[0]))
  const h = Math.max(0, Math.min(1, b[3]) - Math.max(-1, b[2]))
  return (w * h) / 4
}

/** How much of the second box the first hides on screen (0–1). */
function hides(cam: PerspectiveCamera, front: readonly Vector3[], back: readonly Vector3[]): number {
  const a = boxOf(cam, front)
  const b = boxOf(cam, back)
  const w = Math.max(0, Math.min(a[1], b[1]) - Math.max(a[0], b[0]))
  const h = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[2], b[2]))
  const area = Math.max(1e-6, (b[1] - b[0]) * (b[3] - b[2]))
  return (w * h) / area
}

/**
 * A flier's cut (the owner's ask, Nov 12: "the whole dragon in the air with wings spread, above the target"): from
 * further back at a low three-quarter or side angle, so the whole flier (head to tail, both wings) is in the sky with
 * the target and the fire's landing below it, the flier at most maxCoverPct of the screen. Tries the angles round the
 * pair on the side camera's side (azimuthsDeg from the line to the target: 0 behind the target, 90 side-on, 180 behind
 * the flier), the elevations and the lenses; each stands back until everything sits in the clear band and the flier is
 * small enough. Of those that keep the target clear of its body (at most hiddenPct of it hidden) and the flier above
 * it on screen, the best (tuning: ART.duel.flight.cut): the flier near coverGoalPct of the screen, inside the fence
 * (a cut may stand beyond it when nothing inside holds it well), near side-on, the narrower lens, level.
 */
function flyShot(attacker: Vector3, target: Vector3, aspect: number, sideSign: number, fence: (p: Vector3) => Vector3, heights: readonly [number, number], air: CineAir): CineShot {
  const band = sideFraming(aspect).band
  const pts = flyPoints(attacker, target, heights, air)
  const all = [...pts.flier, ...pts.target, pts.floor]
  const u = flat(attacker, target)
  const n = new Vector3(-u.z, 0, u.x).multiplyScalar(sideSign)
  const mid = attacker.clone().lerp(target, 0.5).setY((air.liftM + heights[0]) / 2)
  const cam = new PerspectiveCamera(D.fov, aspect, 0.05, D.far)
  type Pick = { from: Vector3; look: Vector3; fov: number; score: number; inside: boolean }
  /** The best shot that holds `must` in the clear band (inside the fence only, unless `anywhere`). */
  const search = (must: readonly Vector3[], anywhere: boolean): Pick | null => {
    let best: Pick | null = null
    for (const az of FC.azimuthsDeg) {
      const a = (az * Math.PI) / 180
      const flatDir = u.clone().multiplyScalar(-Math.cos(a)).addScaledVector(n, Math.sin(a)).normalize()
      for (const el of FC.elevationsDeg) {
        const e = (el * Math.PI) / 180
        const dir = flatDir.clone().multiplyScalar(Math.cos(e)).setY(Math.sin(e))
        for (const fov of FC.fovsDeg) {
          cam.fov = fov
          cam.aspect = aspect
          cam.updateProjectionMatrix()
          const look = mid.clone()
          // stand back until it all fits and the flier is small enough (both only get easier further back)
          const ok = (d: number): boolean => {
            cam.position.copy(mid).addScaledVector(dir, d)
            if (cam.position.y < FC.minCameraM) return false
            look.copy(mid)
            cam.lookAt(look)
            cam.updateMatrixWorld()
            recentre(cam, look, must, band, fov, aspect)
            return allIn(cam, must, band) && cover(cam, pts.flier) * 100 <= FC.maxCoverPct && cover(cam, pts.target) * 100 <= FC.targetCoverPct
          }
          // inside the fence only: search no further than where this line leaves it
          let hi: number = FC.maxDistM
          if (!anywhere) {
            let a0 = 0
            let a1 = hi
            const at = new Vector3()
            for (let i = 0; i < 12; i++) {
              const m = (a0 + a1) / 2
              at.copy(mid).addScaledVector(dir, m)
              if (fence(at.clone()).distanceToSquared(at) < 1e-6) a0 = m
              else a1 = m
            }
            hi = a0
          }
          let lo = 0.5
          if (hi <= lo || !ok(hi)) continue
          for (let i = 0; i < 10; i++) {
            const m = (lo + hi) / 2
            if (ok(m)) hi = m
            else lo = m
          }
          ok(hi)
          const from = cam.position.clone()
          // the nearest that holds it is past the fence: nothing nearer on this line does
          const inside = fence(from.clone()).distanceToSquared(from) < 1e-6
          if (!inside && !anywhere) continue
          // the target clear of its body, and the flier above it
          if (hides(cam, pts.body, pts.target) * 100 > FC.hiddenPct) continue
          const fy = boxOf(cam, pts.body)
          const ty = boxOf(cam, pts.target)
          if ((fy[2] + fy[3]) / 2 <= (ty[2] + ty[3]) / 2) continue
          const small = Math.max(0, FC.coverGoalPct - cover(cam, pts.flier) * 100)
          const score = small * FC.coverWeight + (inside ? 0 : FC.outsidePenalty) + Math.abs(az - 90) * FC.sideWeight + fov * FC.lensWeight + Math.abs(el) * FC.levelWeight
          if (!best || score < best.score) best = { from, look: look.clone(), fov, score, inside }
        }
      }
    }
    return best
  }
  // inside the fence (beyond it the crowd, banners and gate posts block the view), giving way a step at a time: all of
  // it; the wingtips may reach past the edges; the target's feet may tuck under the cards (its body still clear); only
  // the flier's body and the target's chest. Only when none of those holds, beyond the fence
  const h1 = heights[1]
  const targetTop = corners(target, u, 1.4 * h1, 0.6 * h1, 0.45 * h1, 0.55 * h1)
  const chest = target.clone().setY(target.y + 0.6 * h1)
  const best =
    search(all, false) ??
    search([...pts.body, ...pts.target, pts.floor], false) ??
    search([...pts.body, ...targetTop], false) ??
    search([...pts.body, chest], false) ??
    search(all, true)
  if (best) {
    cam.position.copy(best.from)
    cam.fov = best.fov
    cam.updateProjectionMatrix()
    cam.lookAt(best.look)
    cam.updateMatrixWorld()
    return { from: best.from, look: best.look, fov: best.fov, fits: allIn(cam, all, band), inside: best.inside }
  }
  // nothing clears (fighters nose to nose): the ground cut, lens fitted to the flier's hover
  const p0 = cineParams(aspect)
  const k = heights[0] / D.monsterHeightM
  const from = fence(attacker.clone().addScaledVector(u, -p0.back * k).addScaledVector(n, p0.side * k).setY(attacker.y + p0.height * k + air.liftM))
  const look = attacker.clone().lerp(target, p0.lookPct / 100)
  look.y += p0.lookY * k + air.liftM / 2
  const f = frame(from, look, all, aspect, band)
  return { from, look: f.look, fov: f.fov, fits: f.fits, inside: fence(from.clone()).distanceToSquared(from) < 1e-6 }
}

/**
 * A flier's cut that stays inside the fence: when the shot at its hover height would stand beyond it (the grown
 * Hearthwing upright, far apart), its hover comes down peakStepPct of its height at a time, to minPeakPct at the
 * lowest, until a shot inside holds it; the lens stays within the cut's (at most 86°, wider distorts). If none does,
 * its own height and the shot beyond the fence. `liftM`: the hover height to fly at.
 */
export function flyShotInside(
  attacker: Vector3,
  target: Vector3,
  aspect: number,
  sideSign: number,
  fence: (p: Vector3) => Vector3,
  heights: readonly [number, number],
  air: CineAir,
): { shot: CineShot; liftM: number } {
  const first = cineShot(attacker, target, aspect, sideSign, fence, heights, air)
  if (first.inside) return { shot: first, liftM: air.liftM }
  const FL = D.flight
  for (let pct = FL.peakPct - FL.peakStepPct; pct >= FL.minPeakPct - 1e-9; pct -= FL.peakStepPct) {
    const liftM = (heights[0] * pct) / 100
    if (liftM >= air.liftM) continue
    const shot = cineShot(attacker, target, aspect, sideSign, fence, heights, { ...air, liftM })
    if (shot.inside) return { shot, liftM }
  }
  return { shot: first, liftM: air.liftM }
}
