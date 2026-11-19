/**
 * The land's noise (docs/WORLD_3D.md §4): a port of Gloamvault's `Land.cs` helpers (Hash, Noise, Fbm, Smooth) and the
 * Unity maths they lean on. The hash is integer-only and bit-exact; the rest is in doubles, not Unity's float32, so a
 * height differs from Gloamvault's by ~1e-5 m. From W0 on, this port is the reference.
 */

/** Unity's Mathf.Clamp01. */
export const clamp01 = (t: number): number => (t < 0 ? 0 : t > 1 ? 1 : t)

/** Unity's Mathf.Clamp (min first, then max). */
export const clamp = (v: number, min: number, max: number): number => (v < min ? min : v > max ? max : v)

/** Unity's Mathf.Lerp: t is clamped to 0..1. */
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * clamp01(t)

/** Land.Smooth: smoothstep over a clamped t. */
export function smooth(t: number): number {
  t = clamp01(t)
  return t * t * (3 - 2 * t)
}

/** The seed's own hash term (Land: `seedHash = seed * 7919`, int arithmetic). */
export const seedHashOf = (seed: number): number => Math.imul(seed, 7919)

/**
 * Land.Hash: 0..1 from an integer lattice point, the land's seed and a salt. Bit-exact with C#'s unchecked uint maths.
 */
export function hash(seedHash: number, ix: number, iz: number, salt = 0): number {
  let h = (Math.imul(ix, 374761393) ^ Math.imul(iz, 668265263) ^ ((seedHash + Math.imul(salt, 1013904223)) | 0)) >>> 0
  h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0
  h = (h ^ (h >>> 16)) >>> 0
  return (h & 0xffffff) / 0x1000000
}

/** Land.Noise: value noise in −1..1 at a scale, smoothly interpolated between lattice hashes. */
export function noise(seedHash: number, x: number, z: number, scale: number, salt = 0): number {
  const fx = x / scale
  const fz = z / scale
  const ix = Math.floor(fx)
  const iz = Math.floor(fz)
  const tx = smooth(fx - ix)
  const tz = smooth(fz - iz)
  const a = hash(seedHash, ix, iz, salt)
  const b = hash(seedHash, ix + 1, iz, salt)
  const c = hash(seedHash, ix, iz + 1, salt)
  const d = hash(seedHash, ix + 1, iz + 1, salt)
  return lerp(lerp(a, b, tx), lerp(c, d, tx), tz) * 2 - 1
}

/** Land.Fbm: octaves of noise, each half the scale and half the weight; the octave index is the salt. */
export function fbm(seedHash: number, x: number, z: number, scale: number, octaves: number): number {
  let sum = 0
  let amp = 1
  let norm = 0
  for (let o = 0; o < Math.max(1, octaves); o++) {
    sum += amp * noise(seedHash, x, z, scale, o)
    norm += amp
    scale *= 0.5
    amp *= 0.5
  }
  return sum / norm
}
