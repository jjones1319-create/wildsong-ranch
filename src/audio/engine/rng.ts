/**
 * SOUND_UPGRADE §4: the audio's own random generator (mulberry32). Humanising, ambience events, variations and
 * breath lengths draw from it. It is seeded per session in play and fixed per item in renders, and it never
 * touches the game's RNG or Math.random.
 */

export type Rng = () => number

export function createRng(seed: number): Rng {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** A seed from a string (cyrb-style hash), for per-item render seeds. */
export function seedFrom(text: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

export function between(rng: Rng, lo: number, hi: number): number {
  return lo + (hi - lo) * rng()
}

/** A roughly normal value in [−1, 1] (the mean of three draws). */
export function jitter(rng: Rng): number {
  return (rng() + rng() + rng()) / 1.5 - 1
}

export function pick<T>(rng: Rng, list: readonly T[]): T {
  return list[Math.min(list.length - 1, Math.floor(rng() * list.length))]!
}
