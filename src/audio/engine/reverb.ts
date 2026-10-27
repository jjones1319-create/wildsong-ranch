/**
 * SOUND_UPGRADE §4.6: impulse responses generated at engine init with the audio RNG: decorrelated stereo
 * noise times an exponential decay, 6–10 early reflections, and a lowpass that darkens over the tail.
 * Two slots only (music: hall or room; place: outdoor, room, cave or underwater), each a ConvolverNode with
 * `normalize = false` and calibrated wet gains. Changing a slot's preset fades its output out over 300 ms,
 * swaps the buffer and fades it back in.
 */
import { makeGain, makeFilter, rampTo } from './nodes.ts'
import { createRng, type Rng } from './rng.ts'

export const REVERB_PRESETS = ['hall', 'room', 'outdoor', 'cave', 'underwater'] as const
export type ReverbPreset = (typeof REVERB_PRESETS)[number]

export interface ReverbSpec {
  rt60: number
  preDelayMs: number
  earlyCount: number
  /** The tail's lowpass sweeps from the first to the second value (Hz). */
  darkening: readonly [number, number]
  /** An overall lowpass (underwater). */
  lowpassHz?: number
  /** Wet gain, calibrated so each preset sits at a similar level. */
  wetDb: number
}

export const REVERBS: Record<ReverbPreset, ReverbSpec> = {
  hall: { rt60: 2.6, preDelayMs: 18, earlyCount: 8, darkening: [9000, 2500], wetDb: 0 },
  room: { rt60: 0.9, preDelayMs: 6, earlyCount: 10, darkening: [10000, 4000], wetDb: -1 },
  outdoor: { rt60: 1.4, preDelayMs: 10, earlyCount: 6, darkening: [8000, 2000], wetDb: -2 },
  cave: { rt60: 4.5, preDelayMs: 40, earlyCount: 8, darkening: [5000, 1200], wetDb: 0 },
  underwater: { rt60: 1.8, preDelayMs: 12, earlyCount: 6, darkening: [2000, 600], lowpassHz: 900, wetDb: 0 },
}

/** One channel of a tail: noise × exp decay, darkening along the way, with energy normalised to 1. */
function tail(n: number, sr: number, spec: ReverbSpec, rng: Rng): Float32Array {
  const out = new Float32Array(n)
  const decayPerSample = Math.pow(10, -3 / (spec.rt60 * sr))
  let env = 1
  let lp = 0
  for (let i = 0; i < n; i++) {
    const t = i / n
    const cutoff = spec.darkening[0] + (spec.darkening[1] - spec.darkening[0]) * t
    const k = 1 - Math.exp((-2 * Math.PI * cutoff) / sr)
    const white = rng() * 2 - 1
    lp += k * (white - lp)
    out[i] = lp * env
    env *= decayPerSample
  }
  return out
}

export function makeImpulse(ctx: BaseAudioContext, preset: ReverbPreset, seed = 0x1e5e4b): AudioBuffer {
  const spec = REVERBS[preset]
  const sr = ctx.sampleRate
  const pre = Math.round((spec.preDelayMs / 1000) * sr)
  const length = pre + Math.round(spec.rt60 * sr)
  const buffer = ctx.createBuffer(2, length, sr)
  for (let ch = 0; ch < 2; ch++) {
    const rng = createRng(seed + ch * 7919 + preset.length)
    const data = buffer.getChannelData(ch)
    const t = tail(length - pre, sr, spec, rng)
    // Early reflections in the first 80 ms, then the diffuse tail.
    for (let e = 0; e < spec.earlyCount; e++) {
      const at = pre + Math.round(((0.005 + 0.075 * rng()) * sr) / 1)
      const g = (0.4 + 0.5 * rng()) * (rng() < 0.5 ? -1 : 1) * (1 - e / spec.earlyCount)
      if (at < length) data[at] = data[at]! + g * 0.5
    }
    for (let i = 0; i < t.length; i++) data[pre + i] = data[pre + i]! + t[i]!
    // Energy normalisation so every preset's wet level is comparable (normalize = false on the node).
    let energy = 0
    for (let i = 0; i < length; i++) energy += data[i]! * data[i]!
    const scale = energy > 0 ? 1 / Math.sqrt(energy) : 1
    for (let i = 0; i < length; i++) data[i] = data[i]! * scale * 0.5
  }
  return buffer
}

export class ReverbSlot {
  readonly ctx: BaseAudioContext
  readonly input: GainNode
  readonly output: GainNode
  preset: ReverbPreset
  private convolver: ConvolverNode
  private wet: GainNode
  private lowpass: BiquadFilterNode
  private cache = new Map<ReverbPreset, AudioBuffer>()
  private seed: number

  constructor(ctx: BaseAudioContext, dest: AudioNode, preset: ReverbPreset, seed = 0x1e5e4b) {
    this.ctx = ctx
    this.seed = seed
    this.preset = preset
    this.input = makeGain(ctx, 1)
    this.convolver = ctx.createConvolver()
    this.convolver.normalize = false
    this.lowpass = makeFilter(ctx, 'lowpass', 20000, 0.5)
    this.wet = makeGain(ctx, 1)
    this.output = makeGain(ctx, 1)
    this.input.connect(this.convolver)
    this.convolver.connect(this.lowpass)
    this.lowpass.connect(this.wet)
    this.wet.connect(this.output)
    this.output.connect(dest)
    this.apply(preset)
  }

  private impulse(preset: ReverbPreset): AudioBuffer {
    let b = this.cache.get(preset)
    if (!b) {
      b = makeImpulse(this.ctx, preset, this.seed)
      this.cache.set(preset, b)
    }
    return b
  }

  private apply(preset: ReverbPreset): void {
    const spec = REVERBS[preset]
    this.convolver.buffer = this.impulse(preset)
    this.lowpass.frequency.value = spec.lowpassHz ?? 20000
    this.wet.gain.value = Math.pow(10, spec.wetDb / 20)
    this.preset = preset
  }

  /** Fades out over 300 ms, swaps the buffer, fades back in. */
  setPreset(preset: ReverbPreset): void {
    if (preset === this.preset) return
    const now = this.ctx.currentTime
    rampTo(this.output.gain, 0, now, 0.3)
    const swapAt = now + 0.3
    const done = () => {
      this.apply(preset)
      rampTo(this.output.gain, 1, this.ctx.currentTime, 0.3)
    }
    if (typeof setTimeout === 'function' && 'state' in this.ctx && (this.ctx as AudioContext).state === 'running' && !('startRendering' in this.ctx)) setTimeout(done, 320)
    else {
      // Offline or a test: swap at once after the fade is scheduled.
      this.apply(preset)
      rampTo(this.output.gain, 1, swapAt, 0.3)
    }
  }
}
