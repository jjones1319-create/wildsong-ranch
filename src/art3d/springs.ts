import { ART } from '../data/tuning.ts'

/**
 * Secondary motion (ART_2_PLAN §2.1, §3.2): ears, tails and the like get a light damped spring on top of the
 * clip, driven by how their parent bone moves, so they lag behind the body. Pure maths; the actor applies the
 * angles to bones after the mixer.
 */

export interface SpringParams {
  /** Pull back toward rest (1/s²). */
  stiffness: number
  /** Velocity damping (1/s). */
  damping: number
  /** Angular acceleration per metre/s² of the parent's acceleration. */
  gain: number
  /** The swing cap in degrees. */
  maxDeg: number
}

export interface SpringState {
  /** Angles in radians about the bone's two swing axes, and their velocities. */
  x: number
  y: number
  vx: number
  vy: number
}

export function springParams(kind: string): SpringParams {
  const table = ART.spring as Record<string, SpringParams>
  return table[kind] ?? ART.spring.default
}

const MAX_STEP = 1 / 120

/** Semi-implicit Euler with sub-steps, so a long frame never blows the spring up. */
export function stepSpring(s: SpringState, pushX: number, pushY: number, dtSec: number, p: SpringParams): void {
  let remaining = Math.min(0.1, Math.max(0, dtSec))
  const cap = (p.maxDeg * Math.PI) / 180
  while (remaining > 0) {
    const h = Math.min(MAX_STEP, remaining)
    remaining -= h
    const ax = -p.stiffness * s.x - p.damping * s.vx - p.gain * pushX
    const ay = -p.stiffness * s.y - p.damping * s.vy - p.gain * pushY
    s.vx += ax * h
    s.vy += ay * h
    s.x += s.vx * h
    s.y += s.vy * h
    if (s.x > cap) {
      s.x = cap
      s.vx = Math.min(0, s.vx)
    } else if (s.x < -cap) {
      s.x = -cap
      s.vx = Math.max(0, s.vx)
    }
    if (s.y > cap) {
      s.y = cap
      s.vy = Math.min(0, s.vy)
    } else if (s.y < -cap) {
      s.y = -cap
      s.vy = Math.max(0, s.vy)
    }
  }
}

/** A chain of bones (ear.1 → ear.2): each link follows the one before it, so motion ripples to the tip. */
export class ChainSpring {
  readonly states: SpringState[]
  private readonly params: SpringParams[]

  constructor(length: number, base: SpringParams) {
    this.states = []
    this.params = []
    for (let i = 0; i < length; i++) {
      this.states.push({ x: 0, y: 0, vx: 0, vy: 0 })
      const soften = Math.pow(0.82, i)
      this.params.push({ ...base, stiffness: base.stiffness * soften, damping: base.damping * Math.pow(0.9, i) })
    }
  }

  /** `pushX`/`pushY`: the parent's acceleration (m/s²) along the chain's two swing axes. */
  update(pushX: number, pushY: number, dtSec: number): SpringState[] {
    let inX = pushX
    let inY = pushY
    for (let i = 0; i < this.states.length; i++) {
      const s = this.states[i]!
      const p = this.params[i]!
      stepSpring(s, inX, inY, dtSec, p)
      // the next link is pushed by this one's swing velocity (a share of the parent's push carries on)
      const prevV = this.states[i]!
      inX = pushX * 0.35 + (prevV.vx * p.stiffness) / Math.max(1, p.gain * 6)
      inY = pushY * 0.35 + (prevV.vy * p.stiffness) / Math.max(1, p.gain * 6)
    }
    return this.states
  }

  reset(): void {
    for (const s of this.states) s.x = s.y = s.vx = s.vy = 0
  }
}

/** Finite-difference acceleration of a position sample (metres), smoothed over a few frames. */
export class AccelTracker {
  private prev: [number, number, number] | null = null
  private prevV: [number, number, number] | null = null
  readonly accel: [number, number, number] = [0, 0, 0]

  push(pos: readonly [number, number, number], dtSec: number): [number, number, number] {
    if (dtSec <= 0) return this.accel
    if (this.prev) {
      const v: [number, number, number] = [(pos[0] - this.prev[0]) / dtSec, (pos[1] - this.prev[1]) / dtSec, (pos[2] - this.prev[2]) / dtSec]
      if (this.prevV) {
        const k = 1 / ART.arena.velocitySmoothFrames
        for (let i = 0; i < 3; i++) {
          const a = (v[i]! - this.prevV[i]!) / dtSec
          this.accel[i] = this.accel[i]! * (1 - k) + a * k
        }
      }
      this.prevV = v
    }
    this.prev = [pos[0], pos[1], pos[2]]
    return this.accel
  }

  reset(): void {
    this.prev = null
    this.prevV = null
    this.accel[0] = this.accel[1] = this.accel[2] = 0
  }
}
