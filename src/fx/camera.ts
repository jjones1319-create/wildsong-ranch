/**
 * The effects camera: the same numbers the arena camera writes to CSS (M10), kept as plain values so the
 * fx layer can place its world container every frame. World x in arena units; world y down with 0 on the floor.
 */
export interface FxCamera {
  /** The world x at the middle of the arena. */
  centre: number
  /** Screen pixels per arena unit. */
  pxPerUnit: number
  /** The host element's size in CSS pixels. */
  width: number
  height: number
  /** Where the floor line sits, in CSS pixels above the host's bottom edge. */
  floorPx: number
}

export const DEFAULT_CAMERA: FxCamera = { centre: 0, pxPerUnit: 0.4865, width: 360, height: 220, floorPx: 40 }

export function worldToScreenX(x: number, cam: FxCamera): number {
  return (x - cam.centre) * cam.pxPerUnit + cam.width / 2
}

export function worldToScreenY(y: number, cam: FxCamera): number {
  return cam.height - cam.floorPx + y * cam.pxPerUnit
}

/** The world container's transform for this camera: position of world (0, 0) on screen and the uniform scale. */
export function worldTransform(cam: FxCamera): { x: number; y: number; scale: number } {
  return { x: worldToScreenX(0, cam), y: worldToScreenY(0, cam), scale: cam.pxPerUnit }
}

export function sameCamera(a: FxCamera, b: FxCamera): boolean {
  return a.centre === b.centre && a.pxPerUnit === b.pxPerUnit && a.width === b.width && a.height === b.height && a.floorPx === b.floorPx
}
