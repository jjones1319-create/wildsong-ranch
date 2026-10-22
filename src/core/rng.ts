/**
 * The game's only source of randomness: mulberry32, a tiny 32-bit generator whose whole state is one number
 * that goes into the save file. Same seed → same sequence on every device. Core code never calls Math.random.
 */
export interface Rng {
  /** The current state; store it to resume the exact same sequence later. */
  getState(): number
  setState(state: number): void
  /** Uniform integer in [0, 2^32). */
  nextU32(): number
  /** Uniform float in [0, 1). */
  nextFloat(): number
  /** Uniform integer in [lo, hi], both inclusive. */
  nextInt(lo: number, hi: number): number
  /** True with probability `pct` percent. Always consumes exactly one number. */
  chance(pct: number): boolean
  pick<T>(items: readonly T[]): T
  /** Pick by weight (weights ≥ 0, at least one positive). */
  weightedPick<T>(items: readonly T[], weight: (item: T, index: number) => number): T
  /** A shuffled copy (Fisher–Yates). */
  shuffle<T>(items: readonly T[]): T[]
}

/** One splitmix32-style mixing step, so that nearby seeds (1, 2, 3…) start from unrelated states. */
export function scrambleSeed(seed: number): number {
  let z = (seed + 0x9e3779b9) >>> 0
  z = Math.imul(z ^ (z >>> 16), 0x21f0aaad)
  z = Math.imul(z ^ (z >>> 15), 0x735a2d97)
  return (z ^ (z >>> 15)) >>> 0
}

export function createRng(seed: number): Rng {
  let a = scrambleSeed(seed)

  const nextU32 = (): number => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return (t ^ (t >>> 14)) >>> 0
  }

  const nextFloat = (): number => nextU32() / 4294967296

  const rng: Rng = {
    getState: () => a,
    setState: (state) => {
      a = state >>> 0
    },
    nextU32,
    nextFloat,
    nextInt(lo, hi) {
      if (hi < lo) throw new Error(`nextInt: hi (${hi}) < lo (${lo})`)
      const span = hi - lo + 1
      return lo + (nextU32() % span)
    },
    chance(pct) {
      const roll = nextFloat() * 100
      return roll < pct
    },
    pick(items) {
      if (items.length === 0) throw new Error('pick: empty list')
      return items[nextU32() % items.length]!
    },
    weightedPick(items, weight) {
      let total = 0
      for (let i = 0; i < items.length; i++) total += Math.max(0, weight(items[i]!, i))
      if (total <= 0) throw new Error('weightedPick: no positive weight')
      let roll = nextFloat() * total
      for (let i = 0; i < items.length; i++) {
        const w = Math.max(0, weight(items[i]!, i))
        if (roll < w) return items[i]!
        roll -= w
      }
      return items[items.length - 1]!
    },
    shuffle(items) {
      const out = [...items]
      for (let i = out.length - 1; i > 0; i--) {
        const j = nextU32() % (i + 1)
        const tmp = out[i]!
        out[i] = out[j]!
        out[j] = tmp
      }
      return out
    },
  }
  return rng
}
