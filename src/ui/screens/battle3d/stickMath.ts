import { INPUT } from '../../../data/tuning.ts'

/**
 * docs/BATTLE_3D.md §5: what the stick means, read against the camera. `basis` holds the player's monster's forward
 * (toward the opponent) and left directions as they look on screen (unit vectors, CSS px, y down).
 */
export type Vec = { x: number; y: number }
export interface ScreenBasis {
  fwd: Vec
  left: Vec
}

function axis(v: number): -1 | 0 | 1 {
  return v > INPUT.stick.dead ? 1 : v < -INPUT.stick.dead ? -1 : 0
}

/** The held direction: forward/back and strafe (+1 left), from the stick's offset (−1…1 each way). */
export function stickIntent(v: Vec, b: ScreenBasis): { dir: -1 | 0 | 1; side: -1 | 0 | 1 } {
  return { dir: axis(v.x * b.fwd.x + v.y * b.fwd.y), side: axis(v.x * b.left.x + v.y * b.left.y) }
}

/** A quick flick (released fast, after reaching far): a sidestep across the screen, a dash toward the opponent. */
export function flickIntent(peak: Vec, ms: number, b: ScreenBasis): { kind: 'sidestep'; dir: -1 | 1 } | { kind: 'dash' } | null {
  if (ms > INPUT.stick.flickMs || Math.hypot(peak.x, peak.y) < INPUT.stick.flickReach) return null
  const f = peak.x * b.fwd.x + peak.y * b.fwd.y
  const l = peak.x * b.left.x + peak.y * b.left.y
  if (Math.abs(l) > Math.abs(f)) return { kind: 'sidestep', dir: l > 0 ? 1 : -1 }
  return f > 0 ? { kind: 'dash' } : null
}
