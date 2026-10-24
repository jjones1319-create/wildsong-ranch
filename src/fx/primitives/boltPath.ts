import { FX } from '../../data/tuning.ts'
import type { FxRng } from '../rng.ts'

/**
 * Procedural lightning geometry (pure): midpoint displacement from A to B, plus optional branches that fork off
 * the main bolt and fade out shorter. Returned as flat polylines ready for Graphics.
 */
export interface Bolt {
  /** [x0, y0, x1, y1, …] */
  points: number[]
  /** 1 for the trunk; branches are thinner. */
  weight: number
}

export function boltPoints(ax: number, ay: number, bx: number, by: number, rng: FxRng, levels: number = FX.lightning.levels, jitter: number = FX.lightning.jitter): number[] {
  let pts = [ax, ay, bx, by]
  const len = Math.hypot(bx - ax, by - ay)
  let offset = len * jitter
  for (let l = 0; l < levels; l++) {
    const next: number[] = []
    for (let i = 0; i < pts.length - 2; i += 2) {
      const x0 = pts[i]!
      const y0 = pts[i + 1]!
      const x1 = pts[i + 2]!
      const y1 = pts[i + 3]!
      const mx = (x0 + x1) / 2
      const my = (y0 + y1) / 2
      // Displace along the segment's normal.
      const dx = x1 - x0
      const dy = y1 - y0
      const d = Math.hypot(dx, dy) || 1
      const nx = -dy / d
      const ny = dx / d
      const k = rng.range(-offset, offset)
      next.push(x0, y0, mx + nx * k, my + ny * k)
    }
    next.push(bx, by)
    pts = next
    offset *= 0.5
  }
  return pts
}

export function boltWithBranches(ax: number, ay: number, bx: number, by: number, rng: FxRng, branches: boolean, chance: number = FX.lightning.branchChance, scale: number = FX.lightning.branchScale): Bolt[] {
  const trunk = boltPoints(ax, ay, bx, by, rng)
  const out: Bolt[] = [{ points: trunk, weight: 1 }]
  if (!branches) return out
  const total = Math.hypot(bx - ax, by - ay)
  // Fork from the inner vertices (never the endpoints), heading onward with a twist.
  for (let i = 2; i < trunk.length - 4; i += 2) {
    if (rng.next() > chance) continue
    const x = trunk[i]!
    const y = trunk[i + 1]!
    const ang = Math.atan2(by - ay, bx - ax) + rng.range(-0.9, 0.9)
    const len = total * scale * rng.range(0.4, 1)
    out.push({ points: boltPoints(x, y, x + Math.cos(ang) * len, y + Math.sin(ang) * len, rng, Math.max(2, FX.lightning.levels - 2)), weight: 0.45 })
  }
  return out
}

/** Length of a polyline, for tests and glow sizing. */
export function polylineLength(points: readonly number[]): number {
  let l = 0
  for (let i = 0; i < points.length - 2; i += 2) l += Math.hypot(points[i + 2]! - points[i]!, points[i + 3]! - points[i + 1]!)
  return l
}
