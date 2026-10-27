/**
 * SOUND_UPGRADE §14.3: true peak per BS.1770-4 Annex 2, by 4× oversampling with a polyphase windowed-sinc
 * interpolator. Pure TypeScript, shared by the tools, the tests and the in-page harness.
 */

const PHASES = 4
const TAPS = 24

function buildPhases(): Float64Array[] {
  const half = TAPS / 2
  const phases: Float64Array[] = []
  for (let p = 0; p < PHASES; p++) {
    const h = new Float64Array(TAPS)
    const frac = p / PHASES
    let sum = 0
    for (let k = 0; k < TAPS; k++) {
      const t = k - half + 1 - frac
      const sinc = t === 0 ? 1 : Math.sin(Math.PI * t) / (Math.PI * t)
      // Hann window over the tap span.
      const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * (k + 1 - frac)) / (TAPS + 1))
      h[k] = sinc * w
      sum += h[k]!
    }
    // Unity gain at DC for every phase.
    for (let k = 0; k < TAPS; k++) h[k] = h[k]! / sum
    phases.push(h)
  }
  return phases
}

let cached: Float64Array[] | null = null

/** The largest interpolated absolute sample across all channels (linear). */
export function truePeak(channels: readonly Float32Array[]): number {
  cached ??= buildPhases()
  const half = TAPS / 2
  let peak = 0
  for (const ch of channels) {
    const n = ch.length
    for (let i = 0; i < n; i++) {
      const direct = Math.abs(ch[i]!)
      if (direct > peak) peak = direct
      for (let p = 1; p < PHASES; p++) {
        const h = cached[p]!
        let acc = 0
        for (let k = 0; k < TAPS; k++) {
          const idx = i + k - half + 1
          if (idx >= 0 && idx < n) acc += ch[idx]! * h[k]!
        }
        const a = Math.abs(acc)
        if (a > peak) peak = a
      }
    }
  }
  return peak
}

export function truePeakDb(channels: readonly Float32Array[]): number {
  const p = truePeak(channels)
  return p > 0 ? 20 * Math.log10(p) : -Infinity
}
