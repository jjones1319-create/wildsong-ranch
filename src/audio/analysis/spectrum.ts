/**
 * SOUND_UPGRADE §14.3 brightness: the share of a signal's energy in frequency bands (2–6 kHz, above 8 kHz),
 * from Hann-windowed FFT frames averaged over the whole signal. Reported, never gated.
 */

/** In-place radix-2 FFT on interleaved real/imag arrays; n must be a power of two. */
export function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1
    for (; j & bit; bit >>= 1) j ^= bit
    j ^= bit
    if (i < j) {
      const tr = re[i]!
      re[i] = re[j]!
      re[j] = tr
      const ti = im[i]!
      im[i] = im[j]!
      im[j] = ti
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len
    const wr = Math.cos(ang)
    const wi = Math.sin(ang)
    for (let i = 0; i < n; i += len) {
      let cr = 1
      let ci = 0
      for (let k = 0; k < len / 2; k++) {
        const a = i + k
        const b = a + len / 2
        const xr = re[b]! * cr - im[b]! * ci
        const xi = re[b]! * ci + im[b]! * cr
        re[b] = re[a]! - xr
        im[b] = im[a]! - xi
        re[a] = re[a]! + xr
        im[a] = im[a]! + xi
        const ncr = cr * wr - ci * wi
        ci = cr * wi + ci * wr
        cr = ncr
      }
    }
  }
}

/** The averaged power spectrum (n/2 bins) of a mono signal, Hann windows with 50% overlap. */
export function powerSpectrum(x: Float32Array, n = 4096): Float64Array {
  const bins = new Float64Array(n / 2)
  const re = new Float64Array(n)
  const im = new Float64Array(n)
  const hop = n / 2
  let frames = 0
  for (let start = 0; start + n <= x.length; start += hop) {
    for (let i = 0; i < n; i++) {
      const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1))
      re[i] = x[start + i]! * w
      im[i] = 0
    }
    fft(re, im)
    for (let k = 0; k < n / 2; k++) bins[k] += re[k]! * re[k]! + im[k]! * im[k]!
    frames++
  }
  if (frames === 0 && x.length > 0) {
    // Shorter than one frame: zero-pad a single frame.
    for (let i = 0; i < n; i++) {
      const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1))
      re[i] = i < x.length ? x[i]! * w : 0
      im[i] = 0
    }
    fft(re, im)
    for (let k = 0; k < n / 2; k++) bins[k] += re[k]! * re[k]! + im[k]! * im[k]!
    frames = 1
  }
  if (frames > 0) for (let k = 0; k < bins.length; k++) bins[k] = bins[k]! / frames
  return bins
}

/** The share (0..1) of the energy inside each [lowHz, highHz) band. DC is ignored. */
export function bandShares(channels: readonly Float32Array[], sampleRate: number, bands: readonly (readonly [number, number])[], n = 4096): number[] {
  const total = new Float64Array(n / 2)
  for (const ch of channels) {
    const p = powerSpectrum(ch, n)
    for (let k = 1; k < total.length; k++) total[k] += p[k]!
  }
  let all = 0
  for (let k = 1; k < total.length; k++) all += total[k]!
  const hzPerBin = sampleRate / n
  return bands.map(([lo, hi]) => {
    if (all <= 0) return 0
    let s = 0
    for (let k = 1; k < total.length; k++) {
      const hz = k * hzPerBin
      if (hz >= lo && hz < hi) s += total[k]!
    }
    return s / all
  })
}
