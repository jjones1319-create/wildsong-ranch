/**
 * SOUND_UPGRADE §4.5: sample voices. The nearest sample of the right articulation plays at the rate for the
 * pitch; velocity sets a dB gain and a per-voice lowpass so soft notes are darker; attacks are at least
 * 3 ms, plucks ring and are damped after the note, winds and pads release in their own time, and every
 * stop is a ramp. Phrase starts on winds scoop up 30 cents over 60 ms. Grace notes are a 35 ms ornament.
 */
import { AUDIO } from '../../data/tuning.ts'
import { INSTRUMENTS, type InstrumentId } from '../recipes/instruments.ts'
import { dbToGain, makeFilter, makeGain } from './nodes.ts'
import type { SampleBank } from './samples.ts'

export interface NoteParams {
  inst: InstrumentId
  art: string
  midi: number
  /** 0..1. */
  vel: number
  /** Audio-clock start, seconds. */
  time: number
  /** Seconds the note is held (plucks ring on their own after it). */
  dur: number
  pan?: number
  gainDb?: number
  grace?: readonly number[]
  phraseStart?: boolean
  /** ±cents of pitch variation (Foley, drums). */
  detuneCents?: number
  /** Playback-rate multiplier (the Slacked sag ramps it). */
  rateScale?: number
}

export interface Voice {
  /** Fades the voice out over `releaseSec` from `at` and stops its source. */
  stop(at: number, releaseSec?: number): void
  /** When the voice ends on its own (the note end plus release, or the sample's natural end). */
  endsAt: number
  /** The voice's last node (for the pool to count and the Lab to meter). */
  out: AudioNode
  source: AudioBufferSourceNode | null
  rate: AudioParam | null
  stopped: boolean
}

const PP = 0.25
const F = 0.78
const LOWPASS_PP = 1800
const LOWPASS_F = 12000

export function velocityDb(vel: number): number {
  return -AUDIO.velocityRangeDb * (1 - Math.max(0, Math.min(1, vel)))
}

export function velocityLowpassHz(vel: number): number {
  const t = Math.max(0, Math.min(1, (vel - PP) / (F - PP)))
  return LOWPASS_PP * Math.pow(LOWPASS_F / LOWPASS_PP, t)
}

/** Plays one sampled note. Returns null when the bank has no decoded sample for it (the caller falls back). */
export function playSample(ctx: BaseAudioContext, bank: SampleBank, dest: AudioNode, p: NoteParams): Voice | null {
  const def = INSTRUMENTS[p.inst]
  const unpitched = def.melody === undefined && !def.pitchedPerc
  const picked = unpitched ? bank.take(p.inst, p.art) : bank.pick(p.inst, p.art, p.midi)
  if (!picked) return null
  const { sample, buffer } = picked
  let rate = picked.rate * (p.rateScale ?? 1)
  if (def.pitchedPerc && !unpitched) rate = Math.pow(2, (p.midi - sample.root - sample.cents / 100) / 12)
  if (p.detuneCents) rate *= Math.pow(2, p.detuneCents / 1200)
  const now = ctx.currentTime
  const source = ctx.createBufferSource()
  source.buffer = buffer
  source.playbackRate.value = rate
  const looping = sample.loopStart !== null && sample.loopEnd !== null
  if (looping) {
    source.loop = true
    source.loopStart = sample.loopStart!
    source.loopEnd = sample.loopEnd!
  }
  const attackSec = Math.max(0.003, def.attackMs / 1000)
  const releaseSec = Math.max(0.03, def.releaseMs / 1000)
  const env = makeGain(ctx, 0)
  const gain = dbToGain(velocityDb(p.vel) + (p.gainDb ?? 0))
  const lp = makeFilter(ctx, 'lowpass', def.family === 'perc' || def.family === 'foley' ? 16000 : velocityLowpassHz(p.vel), 0.5)
  let out: AudioNode = env
  source.connect(lp)
  lp.connect(env)
  if (p.pan && Math.abs(p.pan) > 0.01 && typeof StereoPannerNode !== 'undefined') {
    const panner = ctx.createStereoPanner()
    panner.pan.value = Math.max(-1, Math.min(1, p.pan))
    env.connect(panner)
    out = panner
  }
  out.connect(dest)

  // Start so that the sample's onset lands on `time` (the attack is kept, §5.3).
  let when = p.time - sample.onset / rate
  let offset = 0
  if (when < now) {
    offset = (now - when) * rate
    when = now
  }
  const t0 = Math.max(now, p.time)
  env.gain.setValueAtTime(0.0001, when)
  env.gain.linearRampToValueAtTime(gain, Math.max(when + 0.001, t0 + attackSec))
  if (def.family === 'wind' && p.phraseStart) {
    source.detune.setValueAtTime(-30, when)
    source.detune.linearRampToValueAtTime(0, t0 + 0.06)
  }
  const naturalEnd = looping ? Infinity : when + (buffer.duration - offset) / rate
  const noteEnd = p.time + p.dur
  let endsAt: number
  if (looping || def.family === 'wind') {
    endsAt = noteEnd + releaseSec
    env.gain.setValueAtTime(gain, Math.max(t0 + attackSec, noteEnd))
    env.gain.exponentialRampToValueAtTime(0.0001, endsAt)
  } else {
    // Plucks and hits ring; damp them after the note, or let the sample finish, whichever is first.
    const dampAt = noteEnd
    endsAt = Math.min(naturalEnd, dampAt + releaseSec)
    if (dampAt + releaseSec < naturalEnd) {
      env.gain.setValueAtTime(gain, Math.max(t0 + attackSec, dampAt))
      env.gain.exponentialRampToValueAtTime(0.0001, endsAt)
    }
  }
  source.start(when, offset)
  if (Number.isFinite(endsAt)) source.stop(endsAt + 0.05)
  const voice: Voice = {
    endsAt,
    out,
    source,
    rate: source.playbackRate,
    stopped: false,
    stop(at, release = 0.02) {
      if (voice.stopped) return
      voice.stopped = true
      const t = Math.max(ctx.currentTime, at)
      env.gain.cancelScheduledValues(t)
      env.gain.setValueAtTime(Math.max(0.0001, gain), t)
      env.gain.exponentialRampToValueAtTime(0.0001, t + release)
      try {
        source.stop(t + release + 0.02)
      } catch {
        /* already stopped */
      }
      voice.endsAt = t + release
    },
  }
  source.onended = () => {
    try {
      source.disconnect()
      lp.disconnect()
      env.disconnect()
      if (out !== env) out.disconnect()
    } catch {
      /* fine */
    }
  }
  if (p.grace?.length && !unpitched) {
    const graceTime = p.time - 0.035 * p.grace.length
    p.grace.forEach((g, i) => {
      playSample(ctx, bank, dest, { ...p, midi: g, grace: undefined, phraseStart: false, time: graceTime + i * 0.035, dur: 0.035, vel: p.vel * 0.8 })
    })
  }
  return voice
}
