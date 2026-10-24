/**
 * The particle simulation: typed arrays, no Pixi, no DOM, so it is unit-tested and never allocates per frame.
 * Positions are world units (y down, 0 at the floor), velocities are units per second, times are ms.
 * Dead particles are swap-removed, so index i may change identity after `update`; the Pixi binding mirrors the
 * same swaps on its own array of Particle objects.
 */

export interface SpawnSpec {
  x: number
  y: number
  vx: number
  vy: number
  /** Units/s² (positive pulls toward the floor). */
  gravity: number
  /** Velocity kept per second (1 = none, 0.9 = brisk air). */
  drag: number
  lifeMs: number
  /** Size (world units) at birth and at death. */
  size0: number
  size1: number
  rotation: number
  /** Radians per second. */
  spin: number
  /** Share of the life spent fading in (0 = pop in). */
  fadeIn: number
  /** Where the fade-out begins (1 = never fades, 0.5 = fades over the second half). */
  fadeFrom: number
  /** Texture frame index in the atlas. */
  frame: number
  /** Colour ramp index (see elements.ts) and a per-particle seed for flicker. */
  ramp: number
  seed: number
  /** 0 = normal blend, 1 = additive. */
  additive: 0 | 1
  /** Bounce off the floor (0 = pass through, 0.5 = half the speed back up). */
  bounce: number
  /** The brightest the particle gets (1 = opaque; mist and smoke stay translucent). */
  alpha: number
}

export class ParticleSim {
  count = 0
  readonly x: Float32Array
  readonly y: Float32Array
  readonly vx: Float32Array
  readonly vy: Float32Array
  readonly gravity: Float32Array
  readonly drag: Float32Array
  readonly age: Float32Array
  readonly life: Float32Array
  readonly size0: Float32Array
  readonly size1: Float32Array
  readonly rotation: Float32Array
  readonly spin: Float32Array
  readonly fadeIn: Float32Array
  readonly fadeFrom: Float32Array
  readonly frame: Uint16Array
  readonly ramp: Uint16Array
  readonly seed: Float32Array
  readonly additive: Uint8Array
  readonly bounce: Float32Array
  readonly alpha: Float32Array
  readonly capacity: number

  constructor(capacity: number) {
    this.capacity = capacity
    const f = () => new Float32Array(capacity)
    this.x = f()
    this.y = f()
    this.vx = f()
    this.vy = f()
    this.gravity = f()
    this.drag = f()
    this.age = f()
    this.life = f()
    this.size0 = f()
    this.size1 = f()
    this.rotation = f()
    this.spin = f()
    this.fadeIn = f()
    this.fadeFrom = f()
    this.frame = new Uint16Array(capacity)
    this.ramp = new Uint16Array(capacity)
    this.seed = f()
    this.additive = new Uint8Array(capacity)
    this.bounce = f()
    this.alpha = f()
  }

  /** Adds a particle; returns its index, or −1 when the sim is full. */
  spawn(s: SpawnSpec): number {
    if (this.count >= this.capacity) return -1
    const i = this.count++
    this.x[i] = s.x
    this.y[i] = s.y
    this.vx[i] = s.vx
    this.vy[i] = s.vy
    this.gravity[i] = s.gravity
    this.drag[i] = s.drag
    this.age[i] = 0
    this.life[i] = Math.max(1, s.lifeMs)
    this.size0[i] = s.size0
    this.size1[i] = s.size1
    this.rotation[i] = s.rotation
    this.spin[i] = s.spin
    this.fadeIn[i] = s.fadeIn
    this.fadeFrom[i] = s.fadeFrom
    this.frame[i] = s.frame
    this.ramp[i] = s.ramp
    this.seed[i] = s.seed
    this.additive[i] = s.additive
    this.bounce[i] = s.bounce
    this.alpha[i] = s.alpha
    return i
  }

  /**
   * Advances every particle by dtMs. Calls `onSwap(from, to)` whenever a dead particle is replaced by the last
   * live one, and `onDie(i)` for each removed slot, so a mirror array can follow. Returns the number removed.
   */
  update(dtMs: number, onSwap?: (from: number, to: number) => void, onDie?: (lastIndex: number) => void): number {
    const dt = dtMs / 1000
    let removed = 0
    let i = 0
    while (i < this.count) {
      const age = this.age[i]! + dtMs
      if (age >= this.life[i]!) {
        const last = this.count - 1
        if (i !== last) {
          this.copy(last, i)
          onSwap?.(last, i)
        }
        onDie?.(last)
        this.count = last
        removed += 1
        continue
      }
      this.age[i] = age
      const keep = this.drag[i]! === 1 ? 1 : Math.pow(this.drag[i]!, dt)
      let vx = this.vx[i]! * keep
      let vy = (this.vy[i]! + this.gravity[i]! * dt) * keep
      let y = this.y[i]! + vy * dt
      if (y > 0 && this.bounce[i]! > 0 && vy > 0) {
        y = -y * this.bounce[i]!
        vy = -vy * this.bounce[i]!
        vx *= 0.8
      }
      this.vx[i] = vx
      this.vy[i] = vy
      this.x[i] = this.x[i]! + vx * dt
      this.y[i] = y
      this.rotation[i] = this.rotation[i]! + this.spin[i]! * dt
      i += 1
    }
    return removed
  }

  clear(): void {
    this.count = 0
  }

  /** 0 at birth, 1 at death. */
  progress(i: number): number {
    return this.age[i]! / this.life[i]!
  }

  sizeAt(i: number): number {
    const p = this.progress(i)
    return this.size0[i]! + (this.size1[i]! - this.size0[i]!) * p
  }

  alphaAt(i: number): number {
    return alphaCurve(this.progress(i), this.fadeIn[i]!, this.fadeFrom[i]!) * this.alpha[i]!
  }

  private copy(from: number, to: number): void {
    this.x[to] = this.x[from]!
    this.y[to] = this.y[from]!
    this.vx[to] = this.vx[from]!
    this.vy[to] = this.vy[from]!
    this.gravity[to] = this.gravity[from]!
    this.drag[to] = this.drag[from]!
    this.age[to] = this.age[from]!
    this.life[to] = this.life[from]!
    this.size0[to] = this.size0[from]!
    this.size1[to] = this.size1[from]!
    this.rotation[to] = this.rotation[from]!
    this.spin[to] = this.spin[from]!
    this.fadeIn[to] = this.fadeIn[from]!
    this.fadeFrom[to] = this.fadeFrom[from]!
    this.frame[to] = this.frame[from]!
    this.ramp[to] = this.ramp[from]!
    this.seed[to] = this.seed[from]!
    this.additive[to] = this.additive[from]!
    this.bounce[to] = this.bounce[from]!
    this.alpha[to] = this.alpha[from]!
  }
}

/** Fade in over `fadeIn` of the life, hold, then ease out from `fadeFrom` to the end. */
export function alphaCurve(p: number, fadeIn: number, fadeFrom: number): number {
  const up = fadeIn <= 0 ? 1 : Math.min(1, p / fadeIn)
  const down = fadeFrom >= 1 ? 1 : p <= fadeFrom ? 1 : 1 - (p - fadeFrom) / (1 - fadeFrom)
  return Math.max(0, Math.min(1, up * down * down))
}

/** Linear interpolation between the colours of a ramp (0xRRGGBB) at p in 0..1. */
export function rampColor(ramp: readonly number[], p: number): number {
  if (ramp.length === 0) return 0xffffff
  if (ramp.length === 1) return ramp[0]!
  const t = Math.max(0, Math.min(0.99999, p)) * (ramp.length - 1)
  const i = Math.floor(t)
  const f = t - i
  return lerpColor(ramp[i]!, ramp[i + 1]!, f)
}

export function lerpColor(a: number, b: number, f: number): number {
  const ar = (a >> 16) & 255
  const ag = (a >> 8) & 255
  const ab = a & 255
  const br = (b >> 16) & 255
  const bg = (b >> 8) & 255
  const bb = b & 255
  const r = Math.round(ar + (br - ar) * f)
  const g = Math.round(ag + (bg - ag) * f)
  const bl = Math.round(ab + (bb - ab) * f)
  return (r << 16) | (g << 8) | bl
}

/** The horizontal direction from one side toward the other (+1 = right). */
export function dirTo(fromX: number, toX: number): 1 | -1 {
  return toX >= fromX ? 1 : -1
}
