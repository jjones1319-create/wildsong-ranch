import { BATTLE, BATTLE_CAMERA } from '../../data/tuning.ts'

/**
 * §12.11 the arena camera (M10). Pure: no DOM. Floats are fine here, since the camera only decides where
 * pixels go; the engine's fixed-point positions are never touched.
 *
 * World x runs −halfWidth…+halfWidth in arena units; a sprite's drawn box is 2 × spriteHalf units wide,
 * bottom-anchored on the floor. Screen x of a world point = (x − centre) · pxPerUnit + width / 2.
 */

export interface CameraTarget {
  /** Zoom: screen pixels per arena unit. */
  pxPerUnit: number
  /** The world x at the middle of the arena. */
  centre: number
}

export interface Camera extends CameraTarget {
  /** Spring velocities (units/ms and px-per-unit/ms). */
  vCentre: number
  vPx: number
}

export interface FrameInput {
  xA: number
  xB: number
  /** The arena element's size in pixels. */
  width: number
  height: number
}

/** How far a sprite box reaches past the physics body (fluffy parts). */
export const OVERHANG = BATTLE_CAMERA.spriteHalf - BATTLE.arena.bodyRadius

/** Half the drawable world: the walls plus the sprite overhang beyond them. */
export const WORLD_HALF = BATTLE.arena.halfWidth + OVERHANG

/**
 * The zoom's bounds for one viewport: at `min` the whole arena (walls and overhang) fits the width; at `max`
 * one sprite is at most maxSpritePct of the width and leaves reservePx for the ruler and floor. On a wide,
 * short viewport the second rule wins, and the arena then sits narrower than the screen.
 */
export function zoomBounds(width: number, height: number): { min: number; max: number } {
  const max = Math.min((width * BATTLE_CAMERA.maxSpritePct) / 100, height - BATTLE_CAMERA.reservePx) / (2 * BATTLE_CAMERA.spriteHalf)
  const min = Math.min(width / (2 * WORLD_HALF), max)
  return { min, max }
}

/** Where the camera wants to be for these two positions: centred on their midpoint, zoomed to fit both. */
export function frameCamera(input: FrameInput): CameraTarget {
  const { width, height } = input
  const left = Math.min(input.xA, input.xB)
  const right = Math.max(input.xA, input.xB)
  const span = right - left + 2 * BATTLE_CAMERA.spriteHalf + 2 * BATTLE_CAMERA.margin
  const bounds = zoomBounds(width, height)
  const pxPerUnit = Math.min(bounds.max, Math.max(bounds.min, width / span))
  const visibleHalf = width / (2 * pxPerUnit)
  const reach = WORLD_HALF - visibleHalf
  const mid = (left + right) / 2
  const centre = reach <= 0 ? 0 : Math.min(reach, Math.max(-reach, mid))
  return { pxPerUnit, centre }
}

/** Screen x (px from the arena's left edge) of a world x. */
export function screenX(x: number, cam: CameraTarget, width: number): number {
  return (x - cam.centre) * cam.pxPerUnit + width / 2
}

/** The CSS scale for a sprite rendered at basePx so its box is 2 × spriteHalf units wide. */
export function spriteScale(cam: CameraTarget): number {
  return (cam.pxPerUnit * 2 * BATTLE_CAMERA.spriteHalf) / BATTLE_CAMERA.basePx
}

/** One critically damped spring step (exact solution, so any dt is stable and it never overshoots from rest). */
function springStep(x: number, v: number, target: number, dtMs: number, snapEps: number): [number, number] {
  const w = (2 * Math.PI * BATTLE_CAMERA.springHz) / 1000
  const e = Math.exp(-w * dtMs)
  const dx = x - target
  const temp = (v + w * dx) * dtMs
  let nx = target + (dx + temp) * e
  let nv = (v - w * temp) * e
  if (Math.abs(nx - target) < snapEps && Math.abs(nv) < snapEps) {
    nx = target
    nv = 0
  }
  return [nx, nv]
}

/** Reduced motion: a plain exponential ease toward the target, no velocity. */
function easeStep(x: number, target: number, dtMs: number, snapEps: number): number {
  const nx = target + (x - target) * Math.exp(-dtMs / BATTLE_CAMERA.easeMs)
  return Math.abs(nx - target) < snapEps ? target : nx
}

const CENTRE_EPS = 0.01
const PX_EPS = 0.00001

/** Moves the camera toward `target` over `dtMs`. The first call (prev null) snaps straight there. */
export function stepCamera(prev: Camera | null, target: CameraTarget, dtMs: number, reduceMotion: boolean): Camera {
  if (!prev || !(dtMs > 0)) return { pxPerUnit: target.pxPerUnit, centre: target.centre, vCentre: 0, vPx: 0 }
  if (reduceMotion) {
    return { centre: easeStep(prev.centre, target.centre, dtMs, CENTRE_EPS), pxPerUnit: easeStep(prev.pxPerUnit, target.pxPerUnit, dtMs, PX_EPS), vCentre: 0, vPx: 0 }
  }
  const [centre, vCentre] = springStep(prev.centre, prev.vCentre, target.centre, dtMs, CENTRE_EPS)
  const [pxPerUnit, vPx] = springStep(prev.pxPerUnit, prev.vPx, target.pxPerUnit, dtMs, PX_EPS)
  return { centre, pxPerUnit, vCentre, vPx }
}
