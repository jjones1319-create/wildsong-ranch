/**
 * SOUND_UPGRADE §14.3: loudness per ITU-R BS.1770-4, in pure TypeScript so the Node tools, Vitest and the
 * in-page render harness share one meter. K-weighting is a high shelf then a high-pass, both designed for
 * the given sample rate (the published 48 kHz table falls out of the same formulas). Integrated loudness is
 * gated at −70 LUFS absolute and −10 LU relative over 400 ms blocks with 75% overlap.
 */

export interface Biquad {
  b0: number
  b1: number
  b2: number
  a1: number
  a2: number
}

/** The two K-weighting stages for a sample rate. */
export function kWeighting(sampleRate: number): [Biquad, Biquad] {
  const f0 = 1681.974450955533
  const gainDb = 3.999843853973347
  const q = 0.7071752369554196
  const k = Math.tan((Math.PI * f0) / sampleRate)
  const vh = Math.pow(10, gainDb / 20)
  const vb = Math.pow(vh, 0.4996667741545416)
  const a0 = 1 + k / q + k * k
  const shelf: Biquad = {
    b0: (vh + (vb * k) / q + k * k) / a0,
    b1: (2 * (k * k - vh)) / a0,
    b2: (vh - (vb * k) / q + k * k) / a0,
    a1: (2 * (k * k - 1)) / a0,
    a2: (1 - k / q + k * k) / a0,
  }
  const f1 = 38.13547087602444
  const q1 = 0.5003270373238773
  const k1 = Math.tan((Math.PI * f1) / sampleRate)
  const a01 = 1 + k1 / q1 + k1 * k1
  const highPass: Biquad = {
    b0: 1,
    b1: -2,
    b2: 1,
    a1: (2 * (k1 * k1 - 1)) / a01,
    a2: (1 - k1 / q1 + k1 * k1) / a01,
  }
  return [shelf, highPass]
}

export function applyBiquad(x: Float32Array, c: Biquad): Float32Array {
  const y = new Float32Array(x.length)
  let x1 = 0
  let x2 = 0
  let y1 = 0
  let y2 = 0
  for (let i = 0; i < x.length; i++) {
    const xi = x[i]!
    const yi = c.b0 * xi + c.b1 * x1 + c.b2 * x2 - c.a1 * y1 - c.a2 * y2
    y[i] = yi
    x2 = x1
    x1 = xi
    y2 = y1
    y1 = yi
  }
  return y
}

export interface LoudnessResult {
  /** Gated integrated loudness in LUFS; −Infinity for silence. */
  integrated: number
  /** The loudest 3 s window, LUFS. */
  shortTermMax: number
  /** The loudest 400 ms window, LUFS. */
  momentaryMax: number
  /** Short-term loudness at every 100 ms, LUFS (partial windows at the start). */
  shortTerm: Float32Array
  /** Momentary loudness at every 100 ms, LUFS. */
  momentary: Float32Array
}

const ABSOLUTE_GATE = -70
const RELATIVE_GATE = -10

export function lufsOf(meanSquare: number): number {
  return meanSquare > 0 ? -0.691 + 10 * Math.log10(meanSquare) : -Infinity
}

function windowed(blockMs: Float64Array, len: number): Float32Array {
  const out = new Float32Array(blockMs.length)
  let sum = 0
  for (let b = 0; b < blockMs.length; b++) {
    sum += blockMs[b]!
    if (b >= len) sum -= blockMs[b - len]!
    out[b] = lufsOf(Math.max(0, sum) / Math.min(b + 1, len))
  }
  return out
}

function maxFrom(values: Float32Array, from: number): number {
  let m = -Infinity
  for (let i = Math.max(0, Math.min(from, values.length - 1)); i < values.length; i++) if (values[i]! > m) m = values[i]!
  return m
}

/** Loudness of a multichannel signal (every channel weighted 1, as for left and right). */
export function loudness(channels: readonly Float32Array[], sampleRate: number): LoudnessResult {
  const n = channels[0]?.length ?? 0
  const hop = Math.max(1, Math.round(sampleRate * 0.1))
  const blocks = Math.floor(n / hop)
  const blockMs = new Float64Array(blocks)
  const [shelf, highPass] = kWeighting(sampleRate)
  for (const ch of channels) {
    const w = applyBiquad(applyBiquad(ch, shelf), highPass)
    for (let b = 0; b < blocks; b++) {
      let s = 0
      const from = b * hop
      for (let i = from; i < from + hop; i++) s += w[i]! * w[i]!
      blockMs[b] += s / hop
    }
  }
  const momentary = windowed(blockMs, 4)
  const shortTerm = windowed(blockMs, 30)
  const gatingBlocks: number[] = []
  for (let b = 3; b < blocks; b++) gatingBlocks.push((blockMs[b - 3]! + blockMs[b - 2]! + blockMs[b - 1]! + blockMs[b]!) / 4)
  if (gatingBlocks.length === 0 && blocks > 0) gatingBlocks.push(blockMs.reduce((a, b) => a + b, 0) / blocks)
  let integrated = -Infinity
  const absGated = gatingBlocks.filter((m) => lufsOf(m) > ABSOLUTE_GATE)
  if (absGated.length > 0) {
    const mean = absGated.reduce((a, b) => a + b, 0) / absGated.length
    const threshold = lufsOf(mean) + RELATIVE_GATE
    const relGated = absGated.filter((m) => lufsOf(m) > threshold)
    if (relGated.length > 0) integrated = lufsOf(relGated.reduce((a, b) => a + b, 0) / relGated.length)
  }
  return {
    integrated,
    shortTermMax: blocks >= 30 ? maxFrom(shortTerm, 29) : maxFrom(shortTerm, 0),
    momentaryMax: blocks >= 4 ? maxFrom(momentary, 3) : maxFrom(momentary, 0),
    shortTerm,
    momentary,
  }
}

/** Sample peak in dBFS. */
export function peakDb(channels: readonly Float32Array[]): number {
  let p = 0
  for (const ch of channels) for (let i = 0; i < ch.length; i++) p = Math.max(p, Math.abs(ch[i]!))
  return p > 0 ? 20 * Math.log10(p) : -Infinity
}

/** RMS over all channels in dBFS. */
export function rmsDb(channels: readonly Float32Array[]): number {
  let s = 0
  let n = 0
  for (const ch of channels) {
    for (let i = 0; i < ch.length; i++) s += ch[i]! * ch[i]!
    n += ch.length
  }
  return n > 0 && s > 0 ? 10 * Math.log10(s / n) : -Infinity
}

/** Crest factor in dB (sample peak over RMS). Natural music sits around 12–20 dB. */
export function crestDb(channels: readonly Float32Array[]): number {
  const p = peakDb(channels)
  const r = rmsDb(channels)
  return Number.isFinite(p) && Number.isFinite(r) ? p - r : 0
}

/** Mixes any number of channels to one (for the mono checks). */
export function mixdown(channels: readonly Float32Array[]): Float32Array {
  const n = channels[0]?.length ?? 0
  const out = new Float32Array(n)
  if (channels.length === 0) return out
  for (const ch of channels) for (let i = 0; i < n; i++) out[i] = out[i]! + ch[i]! / channels.length
  return out
}
