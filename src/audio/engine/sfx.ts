/**
 * SOUND_UPGRADE §10.1: the effect player. Performs recipe layers (noise, tones, samples, notes in the
 * playing key) with ±3% pitch and ±1.5 dB variation on noise and Foley, ±10 cents on pitched layers,
 * alternate takes, a minimum gap per id, 16 effect voices (4 for UI) with stealing, and panning from the
 * arena. Speed thinning is a pure rule the battle bridge asks about.
 */
import type { FxEventKind } from '../../fx/bus.ts'
import { INSTRUMENTS, type InstrumentId } from '../recipes/instruments.ts'
import type { SfxDef, SfxLayer, Strength } from '../recipes/sfx.ts'
import { MODE_STEPS, type Mode } from '../music/abc.ts'
import { colourChain, filterMakeupDb, noiseLoop } from './ambience.ts'
import type { Graph } from './context.ts'
import { dbToGain, makeFilter, makeGain, makeOscillator, rampTo } from './nodes.ts'
import { between, type Rng } from './rng.ts'
import type { SampleBank } from './samples.ts'
import { playSample, type NoteParams, type Voice } from './sampler.ts'
import { playSynth } from './synth.ts'
import { VoicePool } from './voices.ts'

export interface KeyContext {
  /** Tonic pitch class 0–11. */
  tonic: number
  mode: Mode
}

export const DEFAULT_KEY: KeyContext = { tonic: 2, mode: 'lydian' }

/** A 1-based scale degree (8 = the octave, 0 and below go down) to MIDI, in the key, around `octave`. */
export function degreeToMidi(degree: number, octave: number, key: KeyContext): number {
  const steps = MODE_STEPS[key.mode]
  const index = (((degree - 1) % 7) + 7) % 7
  const shift = Math.floor((degree - 1) / 7)
  return 12 * (octave + 1) + key.tonic + steps[index]! + 12 * shift
}

/** §10.1 speed: at ×2 drop travel and crowd reactions except KO; at ×4 only medium-or-heavier impacts and KOs. */
export function allowedAtSpeed(kind: FxEventKind | 'crowd', strength: Strength, speed: 1 | 2 | 4): boolean {
  if (speed === 1) return true
  if (kind === 'ko') return true
  if (speed === 2) return kind !== 'travel' && kind !== 'crowd'
  return (kind === 'hit' || kind === 'crit') && strength !== 'light'
}

export interface PlayOptions {
  pan?: number
  at?: number
  gainDb?: number
  key?: KeyContext
  /** The playback-rate sag for Slacked beds (1 = none). */
  rateScale?: number
}

export class SfxEngine {
  readonly ctx: BaseAudioContext
  readonly graph: Graph
  readonly bank: SampleBank
  readonly rng: Rng
  readonly pool = new VoicePool('sfx', 16)
  readonly uiPool = new VoicePool('ui', 4)
  key: KeyContext = DEFAULT_KEY
  /** Per-effect trims from calibration (dB). */
  trims: Record<string, number> = {}
  private lastPlayed = new Map<string, number>()
  private lastTake = new Map<string, number>()
  played = 0
  throttled = 0

  constructor(ctx: BaseAudioContext, graph: Graph, bank: SampleBank, rng: Rng) {
    this.ctx = ctx
    this.graph = graph
    this.bank = bank
    this.rng = rng
  }

  /** Plays an effect by id and recipe. False when its throttle refused it. */
  play(id: string, def: SfxDef, o: PlayOptions = {}): boolean {
    const now = this.ctx.currentTime
    const at = Math.max(now, o.at ?? now)
    const gap = (def.throttleMs ?? 50) / 1000
    const last = this.lastPlayed.get(id)
    if (last !== undefined && at - last < gap) {
      this.throttled++
      return false
    }
    this.lastPlayed.set(id, at)
    const bus = def.bus === 'ui' ? this.graph.ui : this.graph.sfx
    const pool = def.bus === 'ui' ? this.uiPool : this.pool
    const trim = (this.trims[id] ?? 0) + (def.trimDb ?? 0) + (o.gainDb ?? 0)
    let dest: AudioNode = bus
    if (o.pan && Math.abs(o.pan) > 0.01 && typeof StereoPannerNode !== 'undefined') {
      const p = this.ctx.createStereoPanner()
      p.pan.value = Math.max(-0.6, Math.min(0.6, o.pan))
      p.connect(bus)
      dest = p
    }
    const key = o.key ?? this.key
    for (const layer of def.layers) {
      pool.makeRoom(at)
      const voice = this.layer(layer, at + (layer.delay ?? 0), trim, dest, key, o.rateScale ?? 1)
      if (voice) pool.add({ voice, startedAt: at, level: Math.min(1, dbToGain((layer.gainDb ?? 0) + trim + 20)), silentLayer: false, owner: id })
    }
    this.played++
    return true
  }

  private envelope(g: GainNode, at: number, aMs: number, hMs: number, dMs: number, peak: number, reverse = false): number {
    const a = Math.max(0.002, aMs / 1000)
    const h = Math.max(0, hMs / 1000)
    const d = Math.max(0.01, dMs / 1000)
    g.gain.setValueAtTime(0.0001, at)
    if (reverse) {
      g.gain.exponentialRampToValueAtTime(peak, at + a)
      g.gain.setValueAtTime(peak, at + a + h)
      g.gain.exponentialRampToValueAtTime(0.0001, at + a + h + 0.012)
      return at + a + h + 0.012
    }
    g.gain.linearRampToValueAtTime(peak, at + a)
    g.gain.setValueAtTime(peak, at + a + h)
    g.gain.exponentialRampToValueAtTime(0.0001, at + a + h + d)
    return at + a + h + d
  }

  private track(g: GainNode, endsAt: number, sources: AudioScheduledSourceNode[]): Voice {
    const voice: Voice = {
      endsAt,
      out: g,
      source: null,
      rate: null,
      stopped: false,
      stop: (at, rel = 0.02) => {
        voice.stopped = true
        rampTo(g.gain, 0, at, rel)
        for (const s of sources) {
          try {
            s.stop(at + rel + 0.02)
          } catch {
            /* fine */
          }
        }
      },
    }
    const last = sources[sources.length - 1]
    if (last) {
      last.onended = () => {
        try {
          g.disconnect()
        } catch {
          /* fine */
        }
      }
    }
    return voice
  }

  private layer(l: SfxLayer, at: number, trim: number, dest: AudioNode, key: KeyContext, rateScale: number): Voice | null {
    const ctx = this.ctx
    const rng = this.rng
    switch (l.kind) {
      case 'noise': {
        const cents = between(rng, -50, 50)
        const db = (l.gainDb ?? 0) + trim + between(rng, -1.5, 1.5)
        const src = ctx.createBufferSource()
        src.buffer = noiseLoop(ctx, l.color)
        src.loop = true
        let node: AudioNode = src
        // Makeup so a layer's gainDb reads as roughly its RMS (the white loop sits at −5 dBFS).
        let makeupDb = 5
        const colour = colourChain(ctx, l.color)
        if (colour) {
          node.connect(colour.input)
          node = colour.output
        }
        if (l.filter) {
          const f = makeFilter(ctx, l.filter.type, l.filter.hz * Math.pow(2, cents / 1200), l.filter.q ?? 0.707, l.filter.gainDb ?? 0)
          if (l.sweepTo) f.frequency.exponentialRampToValueAtTime(Math.max(20, l.sweepTo * Math.pow(2, cents / 1200)), at + (l.a + (l.h ?? 0) + l.d) / 1000)
          node.connect(f)
          node = f
          makeupDb += filterMakeupDb(l.filter)
        }
        if (l.am) {
          const am = makeGain(ctx, 0.5)
          const lfo = makeOscillator(ctx, 'sine', l.am)
          const depth = makeGain(ctx, 0.5)
          lfo.connect(depth)
          depth.connect(am.gain)
          node.connect(am)
          node = am
          lfo.start(at)
          lfo.stop(at + (l.a + (l.h ?? 0) + l.d) / 1000 + 0.1)
        }
        if (l.lowpassHz) {
          const lp = makeFilter(ctx, 'lowpass', l.lowpassHz, 0.5)
          node.connect(lp)
          node = lp
        }
        const g = makeGain(ctx, 0)
        node.connect(g)
        g.connect(dest)
        const end = this.envelope(g, at, l.a, l.h ?? 0, l.d, dbToGain(db + makeupDb), l.reverse)
        src.start(at, between(rng, 0, 7))
        src.stop(end + 0.03)
        return this.track(g, end, [src])
      }
      case 'tone': {
        const cents = between(rng, -10, 10) + (l.detune ?? 0)
        const db = (l.gainDb ?? 0) + trim
        const osc = makeOscillator(ctx, l.wave, l.hz * Math.pow(2, cents / 1200) * rateScale)
        const total = (l.a + (l.h ?? 0) + l.d) / 1000
        if (l.to) osc.frequency.exponentialRampToValueAtTime(Math.max(20, l.to * Math.pow(2, cents / 1200) * rateScale), at + total)
        let node: AudioNode = osc
        if (l.lowpassHz) {
          const lp = makeFilter(ctx, 'lowpass', l.lowpassHz, 0.5)
          node.connect(lp)
          node = lp
        }
        const g = makeGain(ctx, 0)
        node.connect(g)
        g.connect(dest)
        const end = this.envelope(g, at, l.a, l.h ?? 0, l.d, dbToGain(db))
        osc.start(at)
        osc.stop(end + 0.03)
        return this.track(g, end, [osc])
      }
      case 'sample': {
        const def = INSTRUMENTS[l.inst]
        const art = l.art ?? def.arts[0]!
        const unpitched = def.melody === undefined
        const cents = (l.cents ?? 0) + (unpitched ? between(rng, -50, 50) : between(rng, -10, 10))
        const db = (l.gainDb ?? 0) + trim + (unpitched ? between(rng, -1.5, 1.5) : 0)
        let target: AudioNode = dest
        if (l.lowpassHz) {
          const lp = makeFilter(ctx, 'lowpass', l.lowpassHz, 0.5)
          lp.connect(dest)
          target = lp
        }
        const params: NoteParams = { inst: l.inst, art, midi: l.midi ?? 60, vel: l.vel ?? 0.6, time: at, dur: 0.4, gainDb: db, detuneCents: cents, rateScale }
        return playSample(ctx, this.bank, target, params) ?? (unpitched ? null : playSynth(ctx, target, def.fallback, params))
      }
      case 'note':
      case 'chord': {
        const def = INSTRUMENTS[l.inst]
        const art = l.art ?? def.arts[0]!
        const degrees = l.kind === 'note' ? [l.degree] : [...l.degrees]
        const octave = l.octave ?? 4
        const db = (l.gainDb ?? 0) + trim
        let first: Voice | null = null
        degrees.forEach((degree, i) => {
          const midi = this.clampToRange(l.inst, degreeToMidi(degree, octave, key))
          const t = at + (l.kind === 'chord' ? (i * (l.rollMs ?? 0)) / 1000 : 0)
          const params: NoteParams = { inst: l.inst, art, midi, vel: l.vel ?? 0.5, time: t, dur: l.dur, gainDb: db, detuneCents: between(rng, -10, 10) + (l.kind === 'note' ? (l.detune ?? 0) : 0), rateScale }
          const v = this.playNote(params, dest)
          if (v && l.kind === 'note' && l.rateRamp && v.rate) {
            v.rate.setValueAtTime(v.rate.value, t)
            v.rate.linearRampToValueAtTime(v.rate.value * l.rateRamp, t + l.dur)
          }
          first ??= v
        })
        return first
      }
    }
  }

  /** Keeps a note inside the instrument's playable register by octaves. */
  private clampToRange(inst: InstrumentId, midi: number): number {
    const m = INSTRUMENTS[inst].melody
    if (!m) return midi
    let x = midi
    while (x < m[0]) x += 12
    while (x > m[1]) x -= 12
    return x
  }

  /** A note through the sampler, or the fallback while its samples load. Patches (music box) are layered. */
  playNote(p: NoteParams, dest: AudioNode): Voice | null {
    const def = INSTRUMENTS[p.inst]
    if (def.patch) {
      let first: Voice | null = null
      for (const layer of def.patch.layers) {
        const sub = INSTRUMENTS[layer.inst]
        const v = this.playNote({ ...p, inst: layer.inst, art: sub.arts[0]!, midi: p.midi + layer.transpose, gainDb: (p.gainDb ?? 0) + layer.gainDb, dur: layer.decayCapSec ? Math.min(p.dur, layer.decayCapSec) : p.dur }, dest)
        first ??= v
      }
      return first
    }
    return playSample(this.ctx, this.bank, dest, p) ?? playSynth(this.ctx, dest, def.fallback, p)
  }

  voices(): number {
    return this.pool.count(this.ctx.currentTime) + this.uiPool.count(this.ctx.currentTime)
  }

  stopAll(): void {
    const now = this.ctx.currentTime
    this.pool.stopAll(now)
    this.uiPool.stopAll(now)
    this.lastTake.clear()
  }
}
