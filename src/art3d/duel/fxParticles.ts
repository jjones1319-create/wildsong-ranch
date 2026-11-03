import { Vector3, type Camera } from 'three'
import type { QuadBatch } from './fxBatch.ts'

/**
 * docs/BATTLE_3D.md §7: the attack effects' particles. A fixed pool (no allocation while the battle runs): each
 * particle moves on a closed-form path from its start time (so a delayed one simply waits), faces the camera, its
 * flight, the floor or across a direction, and is written into the glowing or the solid quad batch each frame.
 */

/** How a particle moves: thrown (gravity), held at an anchor, drawn in to an anchor, or flown between two points. */
export const MOVE = { free: 0, anchor: 1, gather: 2, path: 3 } as const
/** How it faces: the camera (turning with `spin`), stretched along its flight, flat on the floor, or across `n`. */
export const FACE = { camera: 0, stretch: 1, ground: 2, across: 3 } as const
/** How it fades: bright at once then out, building up to its end, or holding then out. */
export const FADE = { pop: 0, swell: 1, hold: 2 } as const

export class Particle {
  alive = false
  glow = true
  cell = 0
  move = 0
  face = 0
  fade = 0
  t0 = 0
  life = 1
  /** Free: the start; anchor and gather: the offset from the anchor; path: the start when `from` is −1. */
  x = 0
  y = 0
  z = 0
  vx = 0
  vy = 0
  vz = 0
  /** Gravity (m/s², + falls). */
  g = 0
  /** Anchor and gather: the anchor; path: the target anchor, or −1 for the fixed point t. */
  anchor = -1
  from = -1
  tx = 0
  ty = 0
  tz = 0
  /** Path: seconds to arrive (it flies on past after), the height of its arc, and a sideways veer from devAt (a miss). */
  travel = 0.3
  arc = 0
  devX = 0
  devZ = 0
  devAt = -1
  s0 = 0.1
  s1 = 0.1
  stretch = 1
  rot = 0
  /** Gather: how fast the offset turns round the anchor (rad/s); sizes grow linearly instead of easing out. */
  swirl = 0
  linear = false
  spin = 0
  /** Ground: its long axis; across: the plane's normal. */
  nx = 1
  ny = 0
  nz = 0
  r0 = 1
  g0 = 1
  b0 = 1
  r1 = 1
  g1 = 1
  b1 = 1
  a = 1
  /** The side whose projectile this is (its hit or miss finds it), and which of several. */
  owner = -1
  /** A serial number from the pool (a tracked particle that was reused gets a new one). */
  id = 0
  seq = 0
}

const FRESH = new Particle()

/** A repeatable 0–1 noise from a whole number (the picture repeats exactly with the battle). */
export function noise(i: number): number {
  let h = Math.imul(i ^ 0x9e3779b9, 0x85ebca6b)
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35)
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296
}

const R = new Vector3()
const U = new Vector3()
const V = new Vector3()
const P = new Vector3()
const VEL = new Vector3()
const A = new Vector3()
const B = new Vector3()

/** Where a particle is now, and which way it is going. */
export function place(p: Particle, now: number, anchors: readonly Vector3[], pos: Vector3, vel: Vector3): void {
  const t = now - p.t0
  if (p.move === MOVE.free) {
    pos.set(p.x + p.vx * t, p.y + p.vy * t - 0.5 * p.g * t * t, p.z + p.vz * t)
    vel.set(p.vx, p.vy - p.g * t, p.vz)
  } else if (p.move === MOVE.anchor) {
    const a = anchors[p.anchor]!
    pos.set(a.x + p.x + p.vx * t, a.y + p.y + p.vy * t, a.z + p.z + p.vz * t)
    vel.set(p.vx, p.vy + 1e-3, p.vz)
  } else if (p.move === MOVE.gather) {
    const a = anchors[p.anchor]!
    const k = Math.min(1, t / p.life)
    const f = 1 - k * k * (3 - 2 * k)
    const c = Math.cos(p.swirl * t)
    const s = Math.sin(p.swirl * t)
    const ox = (p.x * c - p.z * s) * f
    const oz = (p.x * s + p.z * c) * f
    pos.set(a.x + ox, a.y + p.y * f, a.z + oz)
    vel.set(-ox, -p.y * f, -oz)
  } else {
    const from = p.from >= 0 ? anchors[p.from]! : null
    const to = p.anchor >= 0 ? anchors[p.anchor]! : null
    const fx = from ? from.x : p.x
    const fy = from ? from.y : p.y
    const fz = from ? from.z : p.z
    const dx = (to ? to.x : p.tx) - fx
    const dy = (to ? to.y : p.ty) - fy
    const dz = (to ? to.z : p.tz) - fz
    const k = t / Math.max(1e-3, p.travel)
    const lift = k < 1 ? Math.sin(Math.PI * k) * p.arc : 0
    pos.set(fx + dx * k, fy + dy * k + lift, fz + dz * k)
    vel.set(dx, dy + (k < 1 ? Math.cos(Math.PI * k) * Math.PI * p.arc : 0), dz)
    if (p.devAt >= 0 && now > p.devAt) {
      const m = Math.min(1, (now - p.devAt) / 0.12)
      pos.x += p.devX * m
      pos.z += p.devZ * m
    }
  }
}

function fadeOf(kind: number, k: number): number {
  if (kind === FADE.swell) return k < 0.85 ? 0.25 + (0.75 * k) / 0.85 : (1 - k) / 0.15
  if (kind === FADE.hold) return Math.min(1, k * 10, (1 - k) * 4)
  return Math.min(1, k * 12) * (1 - k)
}

export class ParticlePool {
  readonly items: Particle[]
  private cursor = 0
  private ids = 0

  constructor(max: number) {
    this.items = Array.from({ length: max }, () => new Particle())
  }

  /** A particle to fill in: a free one, or else the next in turn (the oldest effects give way). */
  spawn(): Particle {
    const n = this.items.length
    let p = this.items[this.cursor]!
    for (let i = 0; i < n; i++) {
      const q = this.items[(this.cursor + i) % n]!
      if (!q.alive) {
        p = q
        this.cursor = (this.cursor + i + 1) % n
        break
      }
    }
    if (p.alive) this.cursor = (this.cursor + 1) % n
    Object.assign(p, FRESH)
    p.alive = true
    p.id = ++this.ids
    return p
  }

  /** Moves and draws every live particle into its batch (the batches' begin/end are the caller's). */
  draw(now: number, anchors: readonly Vector3[], camera: Camera, glow: QuadBatch, solid: QuadBatch): void {
    const e = camera.matrixWorld.elements
    R.set(e[0]!, e[1]!, e[2]!).normalize()
    U.set(e[4]!, e[5]!, e[6]!).normalize()
    V.set(e[8]!, e[9]!, e[10]!).normalize()
    for (const p of this.items) {
      if (!p.alive) continue
      if (now >= p.t0 + p.life) {
        p.alive = false
        continue
      }
      if (now < p.t0) continue
      const t = now - p.t0
      const k = t / p.life
      place(p, now, anchors, P, VEL)
      const size = p.s0 + (p.s1 - p.s0) * (p.linear ? k : 1 - (1 - k) * (1 - k))
      const alpha = fadeOf(p.fade, k) * p.a
      let face = p.face
      if (face === FACE.stretch) {
        A.copy(VEL).addScaledVector(V, -VEL.dot(V))
        const len = A.length()
        if (len < 1e-4) face = FACE.camera
        else {
          A.multiplyScalar((size * p.stretch) / len)
          B.crossVectors(V, A).setLength(size)
        }
      }
      if (face === FACE.camera) {
        const c = Math.cos(p.rot + p.spin * t)
        const s = Math.sin(p.rot + p.spin * t)
        A.set(R.x * c + U.x * s, R.y * c + U.y * s, R.z * c + U.z * s).multiplyScalar(size * p.stretch)
        B.set(U.x * c - R.x * s, U.y * c - R.y * s, U.z * c - R.z * s).multiplyScalar(size)
      } else if (face === FACE.ground) {
        const c = Math.cos(p.rot + p.spin * t)
        const s = Math.sin(p.rot + p.spin * t)
        A.set(p.nx * c - p.nz * s, 0, p.nx * s + p.nz * c).multiplyScalar(size * p.stretch)
        B.set(-A.z, 0, A.x).multiplyScalar(1 / p.stretch)
      } else if (face === FACE.across) {
        B.set(p.nx, p.ny, p.nz)
        A.set(-p.nz, 0, p.nx)
        if (A.lengthSq() < 1e-6) A.set(1, 0, 0)
        A.setLength(size)
        B.crossVectors(B, A).setLength(size)
      }
      const r = p.r0 + (p.r1 - p.r0) * k
      const g = p.g0 + (p.g1 - p.g0) * k
      const b = p.b0 + (p.b1 - p.b0) * k
      ;(p.glow ? glow : solid).quad(P.x, P.y, P.z, A.x, A.y, A.z, B.x, B.y, B.z, p.cell, r, g, b, alpha)
    }
  }

  /** Every live particle of `owner`'s projectile `seq` (or all of them with seq −1). */
  forOwner(owner: number, seq: number, fn: (p: Particle) => void): void {
    for (const p of this.items) if (p.alive && p.owner === owner && (seq < 0 || p.seq === seq)) fn(p)
  }

  clear(): void {
    for (const p of this.items) p.alive = false
  }
}
