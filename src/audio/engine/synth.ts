/**
 * SOUND_UPGRADE §4.5: the fallback voices that play while a pack loads or if it fails. All band-limited:
 * wind = a sine with its 2nd harmonic at −30 dB, a breath puff at onset and a delayed 5 Hz vibrato;
 * pad = three detuned triangles into a 1.2 kHz lowpass with a slow attack; pluck = Karplus-Strong rendered
 * once per pitch into cached buffers; mallet = three or four modal partials with exponential decays.
 * Percussion, Foley, glass and drones stay silent until their samples are in.
 */
import { INSTRUMENTS, type FallbackVoice } from '../recipes/instruments.ts'
import { dbToGain, makeFilter, makeGain, makeOscillator, makePeriodicWave } from './nodes.ts'
import { createRng } from './rng.ts'
import { velocityDb, type NoteParams, type Voice } from './sampler.ts'

export function midiToHz(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12)
}

let windWave: { ctx: BaseAudioContext; wave: PeriodicWave } | null = null
let noiseBuffer: { ctx: BaseAudioContext; buffer: AudioBuffer } | null = null
const pluckCache = new Map<string, AudioBuffer>()

function breathNoise(ctx: BaseAudioContext): AudioBuffer {
  if (noiseBuffer && noiseBuffer.ctx === ctx) return noiseBuffer.buffer
  const n = Math.round(ctx.sampleRate * 0.5)
  const b = ctx.createBuffer(1, n, ctx.sampleRate)
  const d = b.getChannelData(0)
  const rng = createRng(0xb4ea7)
  for (let i = 0; i < n; i++) d[i] = rng() * 2 - 1
  noiseBuffer = { ctx, buffer: b }
  return b
}

/** Karplus-Strong string, rendered once per pitch and sample rate. */
function pluckBuffer(ctx: BaseAudioContext, midi: number): AudioBuffer {
  const key = `${ctx.sampleRate}:${midi}`
  const cached = pluckCache.get(key)
  if (cached) return cached
  const sr = ctx.sampleRate
  const hz = midiToHz(midi)
  const period = Math.max(2, Math.round(sr / hz))
  const seconds = 2
  const n = Math.round(sr * seconds)
  const buffer = ctx.createBuffer(1, n, sr)
  const out = buffer.getChannelData(0)
  const line = new Float32Array(period)
  const rng = createRng(1000 + midi)
  for (let i = 0; i < period; i++) line[i] = rng() * 2 - 1
  // Brightness falls with pitch: a one-pole blend keeps high strings from fizzing.
  const decay = 0.994 + Math.min(0.0055, midi / 20000)
  let idx = 0
  let prev = 0
  for (let i = 0; i < n; i++) {
    const cur = line[idx]!
    const next = line[(idx + 1) % period]!
    const v = decay * 0.5 * (cur + next)
    out[i] = 0.5 * (v + prev)
    prev = v
    line[idx] = v
    idx = (idx + 1) % period
  }
  // Fade the last 50 ms so the buffer never clicks when it ends.
  const fade = Math.round(sr * 0.05)
  for (let i = 0; i < fade; i++) out[n - fade + i] = out[n - fade + i]! * (1 - i / fade)
  pluckCache.set(key, buffer)
  return buffer
}

/** Plays one fallback note; null for the silent families. */
export function playSynth(ctx: BaseAudioContext, dest: AudioNode, kind: FallbackVoice, p: NoteParams): Voice | null {
  if (kind === 'silent') return null
  const def = INSTRUMENTS[p.inst]
  const now = ctx.currentTime
  const t0 = Math.max(now, p.time)
  const hz = midiToHz(p.midi) * (p.rateScale ?? 1)
  const gainDb = velocityDb(p.vel) + (p.gainDb ?? 0) - 6
  const env = makeGain(ctx, 0)
  let out: AudioNode = env
  if (p.pan && Math.abs(p.pan) > 0.01 && typeof StereoPannerNode !== 'undefined') {
    const panner = ctx.createStereoPanner()
    panner.pan.value = Math.max(-1, Math.min(1, p.pan))
    env.connect(panner)
    out = panner
  }
  out.connect(dest)
  const sources: (OscillatorNode | AudioBufferSourceNode)[] = []
  const noteEnd = p.time + p.dur
  let endsAt = noteEnd
  const gain = dbToGain(gainDb)
  const attack = Math.max(0.003, def.attackMs / 1000)
  const release = Math.max(0.03, def.releaseMs / 1000)

  switch (kind) {
    case 'wind': {
      if (!windWave || windWave.ctx !== ctx) windWave = { ctx, wave: makePeriodicWave(ctx, [1, dbToGain(-30)]) }
      const osc = makeOscillator(ctx, 'custom', hz, windWave.wave)
      const dark = makeFilter(ctx, 'lowpass', Math.min(12000, Math.max(1200, hz * 6)), 0.5)
      osc.connect(dark)
      dark.connect(env)
      sources.push(osc)
      // Delayed vibrato: ±12 cents at 5 Hz after 300 ms.
      const lfo = makeOscillator(ctx, 'sine', 5)
      const depth = makeGain(ctx, 0)
      lfo.connect(depth)
      depth.connect(osc.detune)
      depth.gain.setValueAtTime(0, t0)
      depth.gain.linearRampToValueAtTime(12, t0 + 0.6)
      sources.push(lfo)
      if (p.phraseStart) {
        osc.detune.setValueAtTime(-30, t0)
        osc.detune.linearRampToValueAtTime(0, t0 + 0.06)
      }
      // The breath puff: band-passed noise at 1.5 kHz for 60 ms.
      const puff = ctx.createBufferSource()
      puff.buffer = breathNoise(ctx)
      const bp = makeFilter(ctx, 'bandpass', 1500, 1.2)
      const puffGain = makeGain(ctx, 0)
      puff.connect(bp)
      bp.connect(puffGain)
      puffGain.connect(dest)
      puffGain.gain.setValueAtTime(0, t0)
      puffGain.gain.linearRampToValueAtTime(gain * 0.25, t0 + 0.015)
      puffGain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.06)
      puff.start(t0)
      puff.stop(t0 + 0.08)
      env.gain.setValueAtTime(0.0001, t0)
      env.gain.linearRampToValueAtTime(gain, t0 + attack)
      env.gain.setValueAtTime(gain, Math.max(t0 + attack, noteEnd))
      endsAt = noteEnd + release
      env.gain.exponentialRampToValueAtTime(0.0001, endsAt)
      break
    }
    case 'pad': {
      const lp = makeFilter(ctx, 'lowpass', 1200, 0.7)
      lp.connect(env)
      for (const cents of [-7, 0, 7]) {
        const osc = makeOscillator(ctx, 'triangle', hz)
        osc.detune.value = cents
        osc.connect(lp)
        sources.push(osc)
      }
      const slow = Math.max(attack, 0.3)
      env.gain.setValueAtTime(0.0001, t0)
      env.gain.linearRampToValueAtTime(gain * 0.5, t0 + slow)
      env.gain.setValueAtTime(gain * 0.5, Math.max(t0 + slow, noteEnd))
      endsAt = noteEnd + Math.max(release, 0.4)
      env.gain.exponentialRampToValueAtTime(0.0001, endsAt)
      break
    }
    case 'pluck': {
      const src = ctx.createBufferSource()
      src.buffer = pluckBuffer(ctx, p.midi)
      src.playbackRate.value = p.rateScale ?? 1
      src.connect(env)
      sources.push(src)
      env.gain.setValueAtTime(gain, t0)
      endsAt = Math.min(t0 + 2, noteEnd + release)
      env.gain.setValueAtTime(gain, Math.max(t0, Math.min(noteEnd, endsAt - 0.03)))
      env.gain.exponentialRampToValueAtTime(0.0001, endsAt)
      break
    }
    case 'mallet': {
      const partials: [number, number, number][] = [
        [1, 1, 1.2],
        [3.0, 0.4, 0.5],
        [5.9, 0.2, 0.25],
        [8.9, 0.1, 0.12],
      ]
      for (const [ratio, amp, decay] of partials) {
        const f = hz * ratio
        if (f > ctx.sampleRate * 0.45) continue
        const osc = makeOscillator(ctx, 'sine', f)
        const g = makeGain(ctx, 0)
        osc.connect(g)
        g.connect(env)
        g.gain.setValueAtTime(0.0001, t0)
        g.gain.linearRampToValueAtTime(amp, t0 + 0.003)
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + decay * 1.5)
        sources.push(osc)
      }
      env.gain.setValueAtTime(gain, t0)
      endsAt = Math.min(t0 + 1.8, noteEnd + release)
      env.gain.setValueAtTime(gain, Math.max(t0, endsAt - release))
      env.gain.exponentialRampToValueAtTime(0.0001, endsAt)
      break
    }
  }
  for (const s of sources) {
    s.start(t0)
    s.stop(endsAt + 0.05)
  }
  const voice: Voice = {
    endsAt,
    out,
    source: null,
    rate: null,
    stopped: false,
    stop(at, rel = 0.02) {
      if (voice.stopped) return
      voice.stopped = true
      const t = Math.max(ctx.currentTime, at)
      env.gain.cancelScheduledValues(t)
      env.gain.setValueAtTime(Math.max(0.0001, env.gain.value), t)
      env.gain.exponentialRampToValueAtTime(0.0001, t + rel)
      for (const s of sources) {
        try {
          s.stop(t + rel + 0.02)
        } catch {
          /* already stopped */
        }
      }
      voice.endsAt = t + rel
    },
  }
  const last = sources[sources.length - 1]
  if (last) {
    last.onended = () => {
      try {
        env.disconnect()
        if (out !== env) out.disconnect()
      } catch {
        /* fine */
      }
    }
  }
  return voice
}
