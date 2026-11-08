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
 */

const D = ART.duel
const C = D.cine.attack

export interface CineShot {
  from: Vector3
  look: Vector3
  fov: number
}

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
 * the camera stands back and up in proportion to the attacker's (the numbers are Puddlepup's).
 */
export function cineShot(
  attacker: Vector3,
  target: Vector3,
  aspect: number,
  sideSign: number,
  fence: (p: Vector3) => Vector3 = (p) => p,
  heights: readonly [number, number] = [D.monsterHeightM, D.monsterHeightM],
): CineShot {
  const p0 = cineParams(aspect)
  const k = heights[0] / D.monsterHeightM
  const q = { ...p0, back: p0.back * k, side: p0.side * k, height: p0.height * k, lookY: p0.lookY * k }
  const u = target.clone().sub(attacker).setY(0)
  if (u.lengthSq() < 1e-6) u.set(0, 0, 1)
  u.normalize()
  const n = new Vector3(-u.z, 0, u.x)
  const from = fence(attacker.clone().addScaledVector(u, -q.back).addScaledVector(n, q.side * sideSign).setY(attacker.y + q.height))
  const look = attacker.clone().lerp(target, q.lookPct / 100)
  look.y += q.lookY
  const band = sideFraming(aspect).band
  const cam = new PerspectiveCamera(D.fov, aspect, 0.05, D.far)
  cam.position.copy(from)
  cam.lookAt(look)
  cam.updateMatrixWorld()
  const pts = cinePoints(attacker, target, heights)
  let fov = fitLens(cam, pts, band)
  // far apart, the plain aim can't hold both: aim at the middle of the points instead (the band's centre), and refit
  if (fov > C.recentreFov) {
    const p = new Vector3()
    const box = [Infinity, -Infinity, Infinity, -Infinity]
    for (const v of pts) {
      p.copy(v).project(cam)
      box[0] = Math.min(box[0]!, p.x)
      box[1] = Math.max(box[1]!, p.x)
      box[2] = Math.min(box[2]!, p.y)
      box[3] = Math.max(box[3]!, p.y)
    }
    const t = Math.tan((fov * Math.PI) / 360)
    const d = from.distanceTo(look)
    const e = cam.matrixWorld.elements
    const right = new Vector3(e[0], e[1], e[2]).normalize()
    const up = new Vector3(e[4], e[5], e[6]).normalize()
    look.addScaledVector(right, ((box[0]! + box[1]!) / 2 - (band.left + band.right) / 2) * d * t * aspect)
    look.addScaledVector(up, ((box[2]! + box[3]!) / 2 - (band.top + band.bottom) / 2) * d * t)
    cam.lookAt(look)
    cam.updateMatrixWorld()
    fov = fitLens(cam, pts, band)
  }
  return { from, look, fov }
}

/** The narrowest lens (from the duel's own, up to the widest allowed) that holds every point in the band. */
function fitLens(cam: PerspectiveCamera, pts: readonly Vector3[], band: ReturnType<typeof sideFraming>['band']): number {
  const p = new Vector3()
  let fov: number = D.fov
  for (; fov < D.confine.maxFov; fov += 1) {
    cam.fov = fov
    cam.updateProjectionMatrix()
    if (pts.every((v) => (p.copy(v).project(cam), p.z < 1 && bandNeed(p.x, p.y, band) <= 1))) break
  }
  return Math.min(fov, D.confine.maxFov)
}
