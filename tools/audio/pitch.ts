/**
 * SOUND_UPGRADE §5.3 step 2: the real pitch of a sample, by the YIN estimator on a few frames of its steady
 * part, with parabolic interpolation and the median across frames. Never trusts the file name, but a named
 * sample may offer candidate frequencies (its name in each octave convention), tried from the highest down:
 * each gets a short analysis window sized to its own period, and the first with a clear dip wins. That keeps
 * a fast-decaying high pluck from reading as its body resonance or as the sub-octave that YIN also matches.
 */

export interface PitchResult {
  hz: number
  midi: number
  /** Offset from the nearest MIDI note, in cents (−50…+50). */
  cents: number
  /** 1 − YIN's aperiodicity at the chosen lag: above 0.8 is a clear pitch. */
  confidence: number
}

/** The cumulative mean normalised difference function of one frame. */
function yinCmnd(x: Float32Array, from: number, window: number, tauMax: number): Float64Array {
  const d = new Float64Array(tauMax + 1)
  for (let tau = 1; tau <= tauMax; tau++) {
    let s = 0
    for (let j = 0; j < window; j++) {
      const diff = x[from + j]! - x[from + j + tau]!
      s += diff * diff
    }
    d[tau] = s
  }
  const cmnd = new Float64Array(tauMax + 1)
  cmnd[0] = 1
  let running = 0
  for (let tau = 1; tau <= tauMax; tau++) {
    running += d[tau]!
    cmnd[tau] = running > 0 ? (d[tau]! * tau) / running : 1
  }
  return cmnd
}

function refine(cmnd: Float64Array, tau: number): { tau: number; aperiodicity: number } {
  const a = cmnd[tau - 1] ?? cmnd[tau]!
  const b = cmnd[tau]!
  const c = cmnd[tau + 1] ?? b
  const denom = a - 2 * b + c
  const shift = denom !== 0 ? (0.5 * (a - c)) / denom : 0
  return { tau: tau + Math.max(-1, Math.min(1, shift)), aperiodicity: Math.max(0, Math.min(1, b)) }
}

function pickUnguided(cmnd: Float64Array, tauMin: number, threshold: number): number | null {
  const tauMax = cmnd.length - 1
  for (let t = Math.max(2, tauMin); t < tauMax; t++) {
    if (cmnd[t]! < threshold) {
      while (t + 1 < tauMax && cmnd[t + 1]! < cmnd[t]!) t++
      return t
    }
  }
  let best = Math.max(2, tauMin)
  for (let t = best + 1; t < tauMax; t++) if (cmnd[t]! < cmnd[best]!) best = t
  return cmnd[best]! > 0.5 ? null : best
}

/** The deepest dip within ±6 semitones of `tauCenter`. */
function pickNear(cmnd: Float64Array, tauCenter: number): number | null {
  const lo = Math.max(2, Math.floor(tauCenter / 1.42))
  const hi = Math.min(cmnd.length - 2, Math.ceil(tauCenter * 1.42))
  if (lo >= hi) return null
  let best = lo
  for (let t = lo + 1; t <= hi; t++) if (cmnd[t]! < cmnd[best]!) best = t
  return best
}

function summarise(results: { hz: number; conf: number }[]): PitchResult {
  results.sort((p, q) => p.hz - q.hz)
  const mid = results[Math.floor(results.length / 2)]!
  const conf = results.reduce((s, r) => s + r.conf, 0) / results.length
  const midiExact = 69 + 12 * Math.log2(mid.hz / 440)
  const midi = Math.round(midiExact)
  return { hz: mid.hz, midi, cents: Math.round((midiExact - midi) * 100), confidence: conf }
}

/**
 * Detects the pitch in the steady part of `x`, starting `fromSec` in, over up to `frames` frames.
 * Returns null when nothing periodic is found.
 */
export function detectPitch(x: Float32Array, sampleRate: number, opts: { fromSec?: number; frames?: number; minHz?: number; maxHz?: number; candidatesHz?: readonly number[] } = {}): PitchResult | null {
  const frames = opts.frames ?? 5
  const start = Math.round((opts.fromSec ?? 0.1) * sampleRate)
  // Guided: each candidate, highest first, with a window of about eight of its periods.
  if (opts.candidatesHz?.length) {
    const cands = [...opts.candidatesHz].sort((a, b) => b - a)
    for (const hz of cands) {
      const tauC = sampleRate / hz
      const window = Math.max(512, Math.min(8192, Math.round(10 * tauC)))
      const tauMax = Math.ceil(tauC * 1.5)
      // Spread the frames over the whole sounding part, so a short note's median is not its sharp attack.
      const hop = Math.max(Math.round(window / 2), Math.floor((x.length - start - window - tauMax) / frames))
      const results: { hz: number; conf: number }[] = []
      let dipSum = 0
      for (let f = 0; f < frames; f++) {
        const from = start + f * hop
        if (from + window + tauMax >= x.length) break
        const cmnd = yinCmnd(x, from, window, tauMax)
        const t = pickNear(cmnd, tauC)
        if (t === null) continue
        const r = refine(cmnd, t)
        dipSum += r.aperiodicity
        results.push({ hz: sampleRate / r.tau, conf: 1 - r.aperiodicity })
      }
      if (results.length > 0 && dipSum / results.length <= 0.5) return summarise(results)
    }
  }
  // Unguided YIN.
  const minHz = opts.minHz ?? 60
  const maxHz = opts.maxHz ?? 4200
  const tauMax = Math.ceil(sampleRate / minHz)
  const tauMin = Math.max(2, Math.floor(sampleRate / maxHz))
  let window = 2048
  while (window < tauMax * 2 && window < 16384) window *= 2
  const hop = Math.round(window / 2)
  const results: { hz: number; conf: number }[] = []
  for (let f = 0; f < frames; f++) {
    const from = start + f * hop
    if (from + window + tauMax >= x.length) break
    const cmnd = yinCmnd(x, from, window, tauMax)
    const tau = pickUnguided(cmnd, tauMin, 0.12)
    if (tau === null || tau < tauMin) continue
    const r = refine(cmnd, tau)
    results.push({ hz: sampleRate / r.tau, conf: 1 - r.aperiodicity })
  }
  return results.length === 0 ? null : summarise(results)
}

export function midiToHz(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12)
}
