/**
 * A seeded generator for *visual* randomness (particle spread, bolt jitter). Separate from core/rng.ts on purpose:
 * effects never touch the simulation's RNG, so a battle replays the same whatever the effects did.
 */
export interface FxRng {
  next(): number
  range(lo: number, hi: number): number
  sign(): 1 | -1
  pick<T>(items: readonly T[]): T
  reseed(seed: number): void
}

export function createFxRng(seed = 1): FxRng {
  let a = seed >>> 0 || 1
  const next = (): number => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  return {
    next,
    range: (lo, hi) => lo + (hi - lo) * next(),
    sign: () => (next() < 0.5 ? -1 : 1),
    pick: (items) => items[Math.min(items.length - 1, Math.floor(next() * items.length))]!,
    reseed(s) {
      a = s >>> 0 || 1
    },
  }
}
