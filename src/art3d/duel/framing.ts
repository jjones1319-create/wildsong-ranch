import { ART } from '../../data/tuning.ts'

/**
 * docs/BATTLE_3D.md §6: the side-on camera's framing for the screen's shape. Upright phones get a three-quarter view
 * framed between the top bar and the cards; sideways phones a nearly square side view, left of the cards along the
 * right edge. Between the two shapes it blends, so turning the phone swings the camera smoothly.
 */

export interface Band {
  left: number
  right: number
  top: number
  bottom: number
}

export interface Framing {
  yawDeg: number
  elevationDeg: number
  /** The clear part of the screen in NDC (−1…1) where both monsters must fit. */
  band: Band
}

const lerp = (a: number, b: number, k: number) => a + (b - a) * k

export function sideFraming(aspect: number): Framing {
  const P = ART.duel.side.portrait
  const L = ART.duel.side.landscape
  const k = Math.min(1, Math.max(0, (aspect - P.aspect) / (L.aspect - P.aspect)))
  return {
    yawDeg: lerp(P.yawDeg, L.yawDeg, k),
    elevationDeg: lerp(P.elevationDeg, L.elevationDeg, k),
    band: {
      left: lerp(P.band.left, L.band.left, k),
      right: lerp(P.band.right, L.band.right, k),
      top: lerp(P.band.top, L.band.top, k),
      bottom: lerp(P.band.bottom, L.band.bottom, k),
    },
  }
}

/** How much bigger the view must be for a point at NDC (x, y) to sit inside the band, around the band's centre. */
export function bandNeed(x: number, y: number, b: Band): number {
  const cx = (b.left + b.right) / 2
  const cy = (b.top + b.bottom) / 2
  const nx = x > cx ? (x - cx) / (b.right - cx) : (cx - x) / (cx - b.left)
  const ny = y > cy ? (y - cy) / (b.top - cy) : (cy - y) / (cy - b.bottom)
  return Math.max(nx, ny)
}
