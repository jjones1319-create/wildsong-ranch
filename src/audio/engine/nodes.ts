/**
 * SOUND_UPGRADE §14.1: the only file that creates oscillators, PeriodicWaves and compressors. It asserts at
 * runtime that no square or sawtooth wave is ever asked for, that a PeriodicWave has at most 8 harmonics,
 * and that every compressor has an explicit knee and a gain after it that cancels the automatic makeup.
 * No WaveShaper exists anywhere (a Vitest lint checks the whole source tree).
 */

export type AllowedWave = 'sine' | 'triangle' | 'custom'

export function makeOscillator(ctx: BaseAudioContext, type: AllowedWave, hz: number, wave?: PeriodicWave): OscillatorNode {
  if ((type as string) === 'square' || (type as string) === 'sawtooth') throw new Error(`banned oscillator type ${type}`)
  const osc = ctx.createOscillator()
  if (type === 'custom') {
    if (!wave) throw new Error('a custom oscillator needs a PeriodicWave')
    osc.setPeriodicWave(wave)
  } else osc.type = type
  osc.frequency.value = hz
  return osc
}

export const MAX_HARMONICS = 8

/** A band-limited wave from harmonic amplitudes (index 1 = fundamental), at most 8 of them. */
export function makePeriodicWave(ctx: BaseAudioContext, harmonics: readonly number[]): PeriodicWave {
  if (harmonics.length > MAX_HARMONICS) throw new Error(`a PeriodicWave may hold at most ${MAX_HARMONICS} harmonics`)
  const real = new Float32Array(harmonics.length + 1)
  const imag = new Float32Array(harmonics.length + 1)
  harmonics.forEach((a, i) => {
    imag[i + 1] = a
  })
  return ctx.createPeriodicWave(real, imag, { disableNormalization: false })
}

export interface CompressorSpec {
  thresholdDb: number
  kneeDb: number
  ratio: number
  attackSec: number
  releaseSec: number
}

/**
 * A compressor with an explicit knee, followed by a gain that cancels the Web Audio makeup gain
 * ((1 / curve(1.0)) ^ 0.6 for an input at full scale, far above the knee).
 */
export function makeCompressor(ctx: BaseAudioContext, spec: CompressorSpec): { input: DynamicsCompressorNode; output: GainNode } {
  if (!Number.isFinite(spec.kneeDb)) throw new Error('a compressor needs an explicit knee')
  const comp = ctx.createDynamicsCompressor()
  comp.threshold.value = spec.thresholdDb
  comp.knee.value = spec.kneeDb
  comp.ratio.value = spec.ratio
  comp.attack.value = spec.attackSec
  comp.release.value = spec.releaseSec
  const cancel = ctx.createGain()
  cancel.gain.value = makeupCancelGain(spec)
  comp.connect(cancel)
  return { input: comp, output: cancel }
}

/** The linear gain that undoes the automatic makeup of a compressor with these settings. */
export function makeupCancelGain(spec: CompressorSpec): number {
  const outDb = spec.thresholdDb + (0 - spec.thresholdDb) / spec.ratio
  const compressedFullScale = Math.pow(10, outDb / 20)
  const makeup = Math.pow(1 / compressedFullScale, 0.6)
  return 1 / makeup
}

export function dbToGain(db: number): number {
  return Math.pow(10, db / 20)
}

export function gainToDb(g: number): number {
  return g > 0 ? 20 * Math.log10(g) : -Infinity
}

/** A biquad with its three parameters set. */
export function makeFilter(ctx: BaseAudioContext, type: BiquadFilterType, hz: number, q = 0.707, gainDb = 0): BiquadFilterNode {
  const f = ctx.createBiquadFilter()
  f.type = type
  f.frequency.value = hz
  f.Q.value = q
  f.gain.value = gainDb
  return f
}

export function makeGain(ctx: BaseAudioContext, value = 1): GainNode {
  const g = ctx.createGain()
  g.gain.value = value
  return g
}

/** Ramps a gain param to `value` over `seconds` from `at`, never a hard jump (§4.5: every stop is a ramp). */
export function rampTo(param: AudioParam, value: number, at: number, seconds: number): void {
  param.cancelScheduledValues(at)
  param.setValueAtTime(Math.max(1e-5, param.value), at)
  if (seconds <= 0) param.setValueAtTime(value, at)
  else if (value <= 1e-5) param.exponentialRampToValueAtTime(1e-5, at + seconds)
  else param.linearRampToValueAtTime(value, at + seconds)
}
