import { ART } from '../data/tuning.ts'

/**
 * The one camera model every 3D host uses (ART_2_PLAN §3.2, §7.3): the arena's five numbers reproduced by a
 * perspective camera at a fixed distance whose field of view is computed per frame. On the floor plane (z = 0)
 * it projects exactly like the arena's CSS and the effects layer, so feet stay on the floor line at every zoom,
 * and anything off the plane gets a little real depth. Pure: the stage turns these numbers into a three camera.
 */

export interface StageCamera {
  /** The world x at the middle of the host (arena units). */
  centre: number
  /** Host pixels per arena unit. */
  pxPerUnit: number
  /** The host's size in CSS pixels. */
  width: number
  height: number
  /** Where the floor line sits, in CSS pixels above the host's bottom edge. */
  floorPx: number
  /** Portraits look slightly down at the monster; the arena looks straight on. */
  pitchDeg?: number
}

export interface CameraNumbers {
  fovDeg: number
  aspect: number
  /** The eye height: the world y that lands at the host's vertical middle. */
  eyeY: number
  distance: number
  near: number
  far: number
  position: [number, number, number]
  lookAt: [number, number, number]
}

export function cameraNumbers(c: StageCamera, distance: number = ART.arena.cameraDistance): CameraNumbers {
  const fov = 2 * Math.atan(c.height / (2 * c.pxPerUnit * distance))
  const eyeY = (c.height / 2 - c.floorPx) / c.pxPerUnit
  const pitch = ((c.pitchDeg ?? 0) * Math.PI) / 180
  return {
    fovDeg: (fov * 180) / Math.PI,
    aspect: c.width / Math.max(1, c.height),
    eyeY,
    distance,
    near: Math.max(1, distance - ART.arena.depth),
    far: distance + ART.arena.depth,
    position: [c.centre, eyeY + distance * Math.sin(pitch), distance * Math.cos(pitch)],
    lookAt: [c.centre, eyeY, 0],
  }
}

/** The square portrait host: the body fills `bodyFrac` of it and the feet sit `floorFrac` up, like the Classic ground line. */
export function portraitCamera(sizePx: number, heightUnits: number, pitchDeg: number = ART.portrait.pitchDeg): StageCamera {
  return {
    centre: 0,
    pxPerUnit: (sizePx * ART.portrait.bodyFrac) / heightUnits,
    width: sizePx,
    height: sizePx,
    floorPx: sizePx * ART.portrait.floorFrac,
    pitchDeg,
  }
}

export function sameStageCamera(a: StageCamera | null, b: StageCamera): boolean {
  return !!a && a.centre === b.centre && a.pxPerUnit === b.pxPerUnit && a.width === b.width && a.height === b.height && a.floorPx === b.floorPx && (a.pitchDeg ?? 0) === (b.pitchDeg ?? 0)
}

/** Screen x of a world x on the floor plane, as the arena's CSS computes it. */
export function floorScreenX(x: number, c: StageCamera): number {
  return (x - c.centre) * c.pxPerUnit + c.width / 2
}
