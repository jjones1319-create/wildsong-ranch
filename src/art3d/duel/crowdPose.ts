import { hash01, type Occupant, type Tuning } from './crowdPlan.ts'
import { ART } from '../../data/tuning.ts'

const CROWD = ART.duel.crowd

/**
 * docs/BATTLE_3D.md §8: how one person in the stands moves at a moment, and the small matrix helpers that write the
 * crowd's instance matrices straight into their arrays (no per-frame objects). Pure: the same time, excitement and
 * person always give the same pose.
 */

/** Row-major 3×3. */
export type M3 = Float64Array

export const m3 = (): M3 => new Float64Array(9)

/** out = Ry(yaw) · Rx(pitch) · Rz(roll): pitch > 0 leans forward (toward +z), roll sways sideways. */
export function rotYXZ(out: M3, yaw: number, pitch: number, roll: number): M3 {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cx = Math.cos(pitch), sx = Math.sin(pitch), cz = Math.cos(roll), sz = Math.sin(roll)
  out[0] = cy * cz + sy * sx * sz; out[1] = -cy * sz + sy * sx * cz; out[2] = sy * cx
  out[3] = cx * sz; out[4] = cx * cz; out[5] = -sx
  out[6] = -sy * cz + cy * sx * sz; out[7] = sy * sz + cy * sx * cz; out[8] = cy * cx
  return out
}

/**
 * An arm's own turn at the shoulder, out = Rz(spread) · Rx(−raise): an arm hangs down its −y; `raise` swings it forward,
 * `spread` swings it out to the side (positive = toward +x, the person's left) and on up over the head.
 */
export function armRot(out: M3, raise: number, spread: number): M3 {
  const ca = Math.cos(raise), sa = Math.sin(raise), cb = Math.cos(spread), sb = Math.sin(spread)
  out[0] = cb; out[1] = -sb * ca; out[2] = -sb * sa
  out[3] = sb; out[4] = cb * ca; out[5] = cb * sa
  out[6] = 0; out[7] = -sa; out[8] = ca
  return out
}

export function mul3(out: M3, a: M3, b: M3): M3 {
  for (let r = 0; r < 3; r++) {
    const a0 = a[r * 3]!, a1 = a[r * 3 + 1]!, a2 = a[r * 3 + 2]!
    out[r * 3] = a0 * b[0]! + a1 * b[3]! + a2 * b[6]!
    out[r * 3 + 1] = a0 * b[1]! + a1 * b[4]! + a2 * b[7]!
    out[r * 3 + 2] = a0 * b[2]! + a1 * b[5]! + a2 * b[8]!
  }
  return out
}

/** Instance `i` of a three.js instanceMatrix array (column-major 4×4): rotation R scaled per axis, then moved to t. */
export function writeMatrix(arr: Float32Array, i: number, R: M3, sx: number, sy: number, sz: number, tx: number, ty: number, tz: number): void {
  const o = i * 16
  arr[o] = R[0]! * sx; arr[o + 1] = R[3]! * sx; arr[o + 2] = R[6]! * sx; arr[o + 3] = 0
  arr[o + 4] = R[1]! * sy; arr[o + 5] = R[4]! * sy; arr[o + 6] = R[7]! * sy; arr[o + 7] = 0
  arr[o + 8] = R[2]! * sz; arr[o + 9] = R[5]! * sz; arr[o + 10] = R[8]! * sz; arr[o + 11] = 0
  arr[o + 12] = tx; arr[o + 13] = ty; arr[o + 14] = tz; arr[o + 15] = 1
}

/** A hidden instance (scale zero). */
export function writeHidden(arr: Float32Array, i: number): void {
  arr.fill(0, i * 16, i * 16 + 16)
}

/** out = t + R · v (a point of a frame). */
export function place(out: Float64Array, R: M3, t: ArrayLike<number>, vx: number, vy: number, vz: number): Float64Array {
  out[0] = t[0]! + R[0]! * vx + R[1]! * vy + R[2]! * vz
  out[1] = t[1]! + R[3]! * vx + R[4]! * vy + R[5]! * vz
  out[2] = t[2]! + R[6]! * vx + R[7]! * vy + R[8]! * vz
  return out
}

export interface Pose {
  /** Up and down (m): the idle bob plus any hop. */
  lift: number
  /** Lean forward and sway (radians). */
  lean: number
  roll: number
  /** Each arm's forward raise and outward spread (radians). */
  leftRaise: number
  leftSpread: number
  rightRaise: number
  rightSpread: number
  /** Looking up a little when excited (radians, negative = up). */
  nod: number
  /** On their feet (seated people stand for the ovation). */
  standing: boolean
}

const TAU = Math.PI * 2
const smooth = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x))
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const DEG = Math.PI / 180

/** Arms: hanging, holding a pennant or foam hand up and out (its face to the ring), and up over the head in a V. */
const HANG = { raise: 0.14, spread: 0.1 }
const HOLD = { raise: 0.3, spread: 2.45 }
const UP = { raise: 0.32, spread: 2.55 }
const WAVE_SECONDS = 1.6

/** One person's pose at `now` (seconds) with excitement `e` (0–1) and the ovation's share `ovation` (0–1). */
export function poseOf(o: Occupant, now: number, e: number, ovation: number, reduce: boolean, seed: number, T: Tuning = CROWD): Pose {
  const k = reduce ? T.reducePct / 100 : 1
  const I = T.idle
  const X = T.excite
  const t = now * o.hz + o.phase
  // the bob only rises (a seat or the ground is under everyone)
  let lift = I.bobM * (0.5 + 0.5 * Math.sin(TAU * t)) * k
  if (!reduce && e > X.armPct / 100) {
    const hop = X.hopM * smooth((e - X.armPct / 100) / 0.3) * Math.abs(Math.sin(Math.PI * (X.hopHz * now + o.phase)))
    lift += o.pose === 'sit' ? hop * 0.45 : hop
  }
  const roll = I.swayDeg * DEG * Math.sin(TAU * (t * 0.5 + o.phase * 0.7)) * k * (1 + e)
  const lean = X.leanDeg * DEG * e * k
  // arms: the first goes up past armPct, the second past bothArmsPct; up arms wave
  const first = smooth((e - X.armPct / 100) / 0.15)
  const both = smooth((e - X.bothArmsPct / 100) / 0.15)
  const waveA = 0.32 * Math.sin(TAU * (I.waveHz * now + o.phase)) * k
  // now and then someone waves with no cheer at all
  const period = I.waveSec * (0.7 + 0.6 * o.phase)
  const cycle = Math.floor((now + o.phase * period) / period)
  const idleWave = hash01(seed, o.seat, 300 + cycle) * 100 < I.wavePct && (now + o.phase * period) % period < WAVE_SECONDS ? 1 : 0
  const leftFirst = o.phase < 0.5
  // (Reduce motion keeps the arms going up, a pose, but waves them gently and never hops)
  const left = Math.max(leftFirst ? first : both, leftFirst ? 0 : idleWave)
  const right = Math.max(leftFirst ? both : first, leftFirst ? idleWave : 0)
  const holder = o.held !== null
  const arm = (up: number, side: number, holds: boolean) => {
    const base = holds ? HOLD : HANG
    const swing = 0.05 * Math.sin(TAU * (t + side * 0.25)) * k
    return { raise: lerp(base.raise, UP.raise, up) + swing, spread: side * (lerp(base.spread, UP.spread, up) + up * waveA) }
  }
  const L = arm(left, 1, false)
  const R = arm(right, -1, holder)
  return {
    lift,
    lean,
    roll,
    leftRaise: L.raise,
    leftSpread: L.spread,
    rightRaise: R.raise,
    rightSpread: R.spread,
    nod: -0.18 * e * k,
    standing: !reduce && o.pose === 'sit' && ovation * 100 > X.standPct,
  }
}
