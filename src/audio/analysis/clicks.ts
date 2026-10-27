/**
 * SOUND_UPGRADE §14.3: clicks (a sample-to-sample jump above 0.2 outside ±5 ms of a scheduled onset) and
 * dropouts (a stretch below −60 dBFS for more than 300 ms outside the written rests).
 */

export interface Click {
  /** Seconds. */
  t: number
  jump: number
  channel: number
}

export function findClicks(channels: readonly Float32Array[], sampleRate: number, allowAtSec: readonly number[] = [], threshold = 0.2, toleranceMs = 5): Click[] {
  const out: Click[] = []
  const tol = toleranceMs / 1000
  const allowed = [...allowAtSec].sort((a, b) => a - b)
  const isAllowed = (t: number): boolean => {
    // Binary search for the nearest allowed onset.
    let lo = 0
    let hi = allowed.length - 1
    while (lo <= hi) {
      const mid = (lo + hi) >> 1
      const v = allowed[mid]!
      if (Math.abs(v - t) <= tol) return true
      if (v < t) lo = mid + 1
      else hi = mid - 1
    }
    return false
  }
  // A click is an isolated jump far larger than the signal's own sample-to-sample movement on both sides of
  // it. Loud broadband noise (a splash, a crackle) moves by more than 0.2 between samples all the time, and
  // a noise burst's attack is big movement that keeps going; neither is a click. A hard cut (big movement
  // before, silence after) and a spike in a smooth signal both are. Two tests: the jump against the mean
  // movement of the 10 ms on each side (cheap, from prefix sums), then against the largest single movement
  // on each side, so a crackle's own extremes a few ms after its onset (where the mean before it is diluted
  // by silence) don't count.
  const win = Math.max(8, Math.round(sampleRate * 0.01))
  channels.forEach((ch, c) => {
    const n = ch.length
    if (n < 2) return
    const diffs = new Float32Array(n)
    for (let i = 1; i < n; i++) diffs[i] = Math.abs(ch[i]! - ch[i - 1]!)
    const prefix = new Float64Array(n + 1)
    for (let i = 0; i < n; i++) prefix[i + 1] = prefix[i]! + diffs[i]!
    const mean = (from: number, to: number) => {
      const a = Math.max(0, from)
      const b = Math.min(n, to)
      return b > a ? (prefix[b]! - prefix[a]!) / (b - a) : 0
    }
    for (let i = 1; i < n; i++) {
      const jump = diffs[i]!
      if (jump <= threshold) continue
      const before = mean(i - win, i)
      const after = mean(i + 1, i + 1 + win)
      if (jump <= 6 * Math.max(before, after)) continue
      let biggest = 0
      for (let k = Math.max(1, i - win); k < Math.min(n, i + 1 + win); k++) if (k !== i && diffs[k]! > biggest) biggest = diffs[k]!
      if (jump > 3 * biggest) {
        const t = i / sampleRate
        if (!isAllowed(t)) out.push({ t, jump, channel: c })
      }
    }
  })
  return out
}

export interface Dropout {
  start: number
  end: number
}

/** RMS per 10 ms block below `floorDb` for longer than `minMs`. `restsSec` are [start, end] stretches to ignore. */
export function findDropouts(channels: readonly Float32Array[], sampleRate: number, floorDb = -60, minMs = 300, restsSec: readonly (readonly [number, number])[] = []): Dropout[] {
  const n = channels[0]?.length ?? 0
  const block = Math.max(1, Math.round(sampleRate * 0.01))
  const blocks = Math.floor(n / block)
  const quiet: boolean[] = []
  const floor = Math.pow(10, floorDb / 10)
  for (let b = 0; b < blocks; b++) {
    let s = 0
    for (const ch of channels) for (let i = b * block; i < (b + 1) * block; i++) s += ch[i]! * ch[i]!
    quiet.push(s / (block * Math.max(1, channels.length)) < floor)
  }
  const out: Dropout[] = []
  let runStart = -1
  const flush = (endBlock: number) => {
    if (runStart < 0) return
    const start = (runStart * block) / sampleRate
    const end = (endBlock * block) / sampleRate
    const inRest = restsSec.some(([a, b]) => start >= a - 0.02 && end <= b + 0.02)
    if ((end - start) * 1000 > minMs && !inRest) out.push({ start, end })
    runStart = -1
  }
  for (let b = 0; b < blocks; b++) {
    if (quiet[b]) {
      if (runStart < 0) runStart = b
    } else flush(b)
  }
  flush(blocks)
  return out
}
