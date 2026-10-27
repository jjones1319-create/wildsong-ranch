/**
 * SOUND_UPGRADE §9.1: the ambience engine. Only white-noise buffers are looped (8 s, seeded, with a crossfaded
 * seam); pink and brown are made from them with filters. Layers are shaped by biquads and moved slowly by
 * an LFO and a seeded random walk every 250 ms. Spawners fire one-shot events at a Poisson rate with random
 * pan, pitch and level. Every stereo bed uses two decorrelated sources. Beds crossfade over 2 s; weather
 * overlays add or remove layers; crowds are layers with reactions.
 */
import { AUDIO } from '../../data/tuning.ts'
import type { Weather } from '../../data/types.ts'
import { bedLayers, CROWD_PROFILES, CROWDS, WEATHER_OVERLAYS, type BedId, type BedLayer, type CrowdReaction, type CrowdSize, type NoiseColor, type SpawnEvent, type SpawnLayer } from '../recipes/ambience.ts'
import { dbToGain, makeFilter, makeGain, makeOscillator, rampTo } from './nodes.ts'
import { between, createRng, type Rng } from './rng.ts'
import type { SampleBank } from './samples.ts'
import { VoicePool } from './voices.ts'
import type { Voice } from './sampler.ts'

const LOOP_SEC = 8
const SEAM_SEC = 0.1
const WALK_SEC = 0.25

const noiseCache = new WeakMap<BaseAudioContext, Map<string, AudioBuffer>>()

/**
 * The 8 s noise loop of a colour (white, pink or brown) with its seam crossfaded in, one per colour per context.
 * Every layer and effect plays the same loop from its own offset; two sources half a loop apart are as
 * uncorrelated as two different loops would be, and three loops a session cost a few milliseconds once.
 */
export function noiseLoop(ctx: BaseAudioContext, color: NoiseColor = 'white'): AudioBuffer {
  let perCtx = noiseCache.get(ctx)
  if (!perCtx) {
    perCtx = new Map()
    noiseCache.set(ctx, perCtx)
  }
  const cached = perCtx.get(color)
  if (cached) return cached
  const sr = ctx.sampleRate
  const n = Math.round(LOOP_SEC * sr)
  const buffer = ctx.createBuffer(1, n, sr)
  const d = buffer.getChannelData(0)
  const rng = createRng(0x5eed + (color === 'pink' ? 1 : color === 'brown' ? 2 : 0))
  for (let i = 0; i < n; i++) d[i] = rng() * 2 - 1
  const seam = Math.round(SEAM_SEC * sr)
  for (let i = 0; i < seam; i++) {
    const w = i / seam
    const a = Math.cos((w * Math.PI) / 2)
    const b = Math.sin((w * Math.PI) / 2)
    d[n - seam + i] = a * d[n - seam + i]! + b * d[i]!
  }
  colourInPlace(d, color, sr)
  perCtx.set(color, buffer)
  return buffer
}

/**
 * Pink or brown from the white loop, filtered here in JS with the same coefficients an IIRFilterNode would
 * use (a 3rd-order pink approximation; a leaky integrator for brown). Creating an IIRFilterNode costs Chrome
 * about 400 ms, which froze the page for seconds on every bed switch and for half a second on every fire or
 * earth effect; a few milliseconds of arithmetic here replaces it. The filter warms up over the last second
 * of the loop first so the seam stays continuous.
 */
function colourInPlace(d: Float32Array, color: NoiseColor, sr: number): void {
  if (color === 'white') return
  const n = d.length
  const x = Float32Array.from(d)
  const warm = Math.min(n, Math.round(sr))
  if (color === 'brown') {
    let y1 = 0
    for (let i = n - warm; i < n; i++) y1 = 0.02 * x[i]! + 0.98 * y1
    for (let i = 0; i < n; i++) {
      y1 = 0.02 * x[i]! + 0.98 * y1
      d[i] = y1
    }
    return
  }
  // Pink: b = [0.049922035, −0.095993537, 0.050612699, −0.004408786], a = [1, −2.494956002, 2.017265875, −0.5221894].
  let x1 = 0
  let x2 = 0
  let x3 = 0
  let y1 = 0
  let y2 = 0
  let y3 = 0
  const step = (x0: number): number => {
    const y = 0.049922035 * x0 - 0.095993537 * x1 + 0.050612699 * x2 - 0.004408786 * x3 + 2.494956002 * y1 - 2.017265875 * y2 + 0.5221894 * y3
    x3 = x2
    x2 = x1
    x1 = x0
    y3 = y2
    y2 = y1
    y1 = y
    return y
  }
  for (let i = n - warm; i < n; i++) step(x[i]!)
  for (let i = 0; i < n; i++) d[i] = step(x[i]!)
}

/**
 * The colour is baked into the loop (`noiseLoop(ctx, seed, color)`); this is the makeup gain that follows it so
 * each colour sits near the white loop's RMS (−5 dBFS). A recipe's `levelDb` then reads as roughly the layer's RMS.
 */
export const COLOUR_MAKEUP_DB: Record<NoiseColor, number> = { white: 0, pink: 20, brown: 14 }

export function colourChain(ctx: BaseAudioContext, color: NoiseColor): { input: AudioNode; output: AudioNode } | null {
  if (color === 'white') return null
  const makeup = makeGain(ctx, dbToGain(COLOUR_MAKEUP_DB[color]))
  return { input: makeup, output: makeup }
}

/** The white loop's RMS is about −5 dBFS; this lifts a layer so `levelDb` reads as its RMS. */
const WHITE_RMS_MAKEUP_DB = 5

/** The RMS a biquad takes out of broadband noise, roughly, so a recipe's level survives its filters. */
export function filterMakeupDb(f: { type: BiquadFilterType; q?: number }): number {
  switch (f.type) {
    case 'bandpass':
      return 6 + ((f.q ?? 0.707) > 1 ? 4 : 0)
    case 'lowpass':
    case 'highpass':
      return 2
    default:
      return 0
  }
}

interface LiveNoise {
  kind: 'noise'
  id: string
  gain: GainNode
  baseDb: number
  /** The colour and filter makeup folded into the gain, dB. */
  makeupDb: number
  firstFilter: BiquadFilterNode | null
  baseHz: number
  walk: { db: number; hz: number } | null
  walkDb: number
  walkHz: number
  sources: AudioScheduledSourceNode[]
}

interface LiveSpawn {
  kind: 'spawn'
  id: string
  gain: GainNode
  baseDb: number
  layer: SpawnLayer
  /** Multiplier on the rate (weather scales birds). */
  rateScale: number
}

interface LiveTone {
  kind: 'tone'
  id: string
  gain: GainNode
  baseDb: number
  sources: AudioScheduledSourceNode[]
}

type Live = LiveNoise | LiveSpawn | LiveTone

export interface BedInstance {
  id: BedId | 'crowd'
  out: GainNode
  layers: Live[]
  muffle: BiquadFilterNode
  stop(at: number, fadeSec: number): void
}

export class Ambience {
  readonly ctx: BaseAudioContext
  readonly dest: AudioNode
  readonly reverbSend: AudioNode
  readonly bank: SampleBank
  readonly rng: Rng
  readonly pool = new VoicePool('ambience', 16)
  current: BedInstance | null = null
  crowd: BedInstance | null = null
  bedId: BedId | null = null
  weather: Weather = 'Sunny'
  crowdSize: CrowdSize = 'none'
  /** Per-layer trims from the Sound Lab (dB), this session only. */
  trims = new Map<string, number>()
  /** Per-bed trims from calibration (dB, levels.json). */
  bedTrims: Record<string, number> = {}
  private fading: BedInstance[] = []
  private nextWalk = 0
  private reactionUntil = 0

  constructor(ctx: BaseAudioContext, dest: AudioNode, reverbSend: AudioNode, bank: SampleBank, rng: Rng) {
    this.ctx = ctx
    this.dest = dest
    this.reverbSend = reverbSend
    this.bank = bank
    this.rng = rng
  }

  private levelOf(layerId: string, baseDb: number, bedId: string): number {
    const trim = this.trims.get(`${bedId}/${layerId}`) ?? 0
    let db = baseDb + trim + (this.bedTrims[bedId] ?? 0)
    const w = WEATHER_OVERLAYS[this.weather]
    if (/wind|breeze|gust/.test(layerId)) db += w.windDb
    if (w.muffle) db += w.muffle.db
    return db
  }

  private buildNoise(layer: Extract<BedLayer, { kind: 'noise' }>, out: AudioNode, bedId: string): LiveNoise {
    const ctx = this.ctx
    const makeupDb = WHITE_RMS_MAKEUP_DB + (layer.filters ?? []).reduce((s, f) => s + filterMakeupDb(f), 0)
    const gain = makeGain(ctx, dbToGain(this.levelOf(layer.id, layer.levelDb, bedId) + makeupDb))
    gain.connect(out)
    const stereo = layer.stereo !== false
    const sources: AudioScheduledSourceNode[] = []
    let firstFilter: BiquadFilterNode | null = null
    const chains = stereo ? [-0.7, 0.7] : [layer.pan ?? 0]
    chains.forEach((pan, i) => {
      const src = ctx.createBufferSource()
      src.buffer = noiseLoop(ctx, layer.color)
      src.loop = true
      let node: AudioNode = src
      const colour = colourChain(ctx, layer.color)
      if (colour) {
        node.connect(colour.input)
        node = colour.output
      }
      for (const f of layer.filters ?? []) {
        const bq = makeFilter(ctx, f.type, f.hz, f.q ?? 0.707, f.gainDb ?? 0)
        node.connect(bq)
        node = bq
        if (!firstFilter) firstFilter = bq
      }
      if (layer.am) {
        const am = makeGain(ctx, 1 - layer.am.depth)
        const lfo = makeOscillator(ctx, 'sine', typeof layer.am.rateHz === 'number' ? layer.am.rateHz : between(this.rng, layer.am.rateHz[0], layer.am.rateHz[1]))
        const depth = makeGain(ctx, layer.am.depth)
        lfo.connect(depth)
        depth.connect(am.gain)
        node.connect(am)
        node = am
        lfo.start()
        sources.push(lfo)
      }
      if (Math.abs(pan) > 0.01 && typeof StereoPannerNode !== 'undefined') {
        const p = ctx.createStereoPanner()
        p.pan.value = pan
        node.connect(p)
        node = p
      }
      node.connect(gain)
      // The two channels start half a loop apart so they never line up.
      src.start(ctx.currentTime, (between(this.rng, 0, LOOP_SEC) + (i * LOOP_SEC) / chains.length) % LOOP_SEC)
      sources.push(src)
    })
    if (layer.lfo) {
      const rate = typeof layer.lfo.rateHz === 'number' ? layer.lfo.rateHz : between(this.rng, layer.lfo.rateHz[0], layer.lfo.rateHz[1])
      const lfo = makeOscillator(ctx, 'sine', rate)
      const depth = makeGain(ctx, gain.gain.value * (dbToGain(layer.lfo.depthDb) - 1) * 0.5)
      lfo.connect(depth)
      depth.connect(gain.gain)
      lfo.start()
      sources.push(lfo)
    }
    return { kind: 'noise', id: layer.id, gain, baseDb: layer.levelDb, makeupDb, firstFilter, baseHz: layer.filters?.[0]?.hz ?? 0, walk: layer.walk ? { db: layer.walk.db ?? 0, hz: layer.walk.hz ?? 0 } : null, walkDb: 0, walkHz: 0, sources }
  }

  private buildTone(layer: Extract<BedLayer, { kind: 'tone' }>, out: AudioNode, bedId: string): LiveTone {
    const ctx = this.ctx
    const gain = makeGain(ctx, dbToGain(this.levelOf(layer.id, layer.levelDb, bedId)))
    const lp = makeFilter(ctx, 'lowpass', layer.lowpassHz ?? 4000, 0.5)
    lp.connect(gain)
    gain.connect(out)
    const sources: AudioScheduledSourceNode[] = []
    layer.hz.forEach((hz, i) => {
      const osc = makeOscillator(ctx, 'sine', hz + (layer.beatHz ? (i % 2 ? layer.beatHz : 0) : 0))
      const g = makeGain(ctx, 1 / layer.hz.length)
      osc.connect(g)
      g.connect(lp)
      osc.start()
      sources.push(osc)
    })
    return { kind: 'tone', id: layer.id, gain, baseDb: layer.levelDb, sources }
  }

  private build(id: BedId | 'crowd', layers: readonly BedLayer[]): BedInstance {
    const ctx = this.ctx
    const out = makeGain(ctx, 0)
    const muffle = makeFilter(ctx, 'lowpass', WEATHER_OVERLAYS[this.weather].muffle?.lowpassHz ?? 20000, 0.5)
    out.connect(muffle)
    muffle.connect(this.dest)
    const send = makeGain(ctx, 0.25)
    muffle.connect(send)
    send.connect(this.reverbSend)
    const live: Live[] = []
    layers.forEach((layer) => {
      if (layer.kind === 'noise') live.push(this.buildNoise(layer, out, id))
      else if (layer.kind === 'tone') live.push(this.buildTone(layer, out, id))
      else {
        const gain = makeGain(ctx, dbToGain(this.levelOf(layer.id, layer.levelDb, id)))
        gain.connect(out)
        live.push({ kind: 'spawn', id: layer.id, gain, baseDb: layer.levelDb, layer, rateScale: /bird/.test(layer.id) ? WEATHER_OVERLAYS[this.weather].birds : 1 })
      }
    })
    const inst: BedInstance = {
      id,
      out,
      layers: live,
      muffle,
      stop: (at, fadeSec) => {
        rampTo(out.gain, 0, at, fadeSec)
        const end = at + fadeSec + 0.1
        for (const l of live) {
          if (l.kind === 'spawn') continue
          for (const s of l.sources) {
            try {
              s.stop(end)
            } catch {
              /* already stopped */
            }
          }
        }
      },
    }
    return inst
  }

  /** Crossfades to a bed (null = silence) over `fadeSec`. */
  setBed(id: BedId | null, fadeSec = 2): void {
    if (id === this.bedId) return
    const now = this.ctx.currentTime
    if (this.current) {
      const old = this.current
      old.stop(now, fadeSec)
      this.fading.push(old)
      this.current = null
    }
    this.bedId = id
    if (!id) return
    const w = WEATHER_OVERLAYS[this.weather]
    const layers = [...bedLayers(id), ...(w.add ?? [])]
    const inst = this.build(id, layers)
    this.current = inst
    rampTo(inst.out.gain, dbToGain(AUDIO.ambienceMakeupDb), now, fadeSec)
  }

  setWeather(weather: Weather): void {
    if (weather === this.weather) return
    this.weather = weather
    // Rebuild the bed with the new overlay (the crossfade hides it).
    const id = this.bedId
    this.bedId = null
    this.setBed(id, 2)
  }

  setCrowd(size: CrowdSize): void {
    if (size === this.crowdSize) return
    this.crowdSize = size
    const now = this.ctx.currentTime
    if (this.crowd) {
      this.crowd.stop(now, 1.5)
      this.fading.push(this.crowd)
      this.crowd = null
    }
    if (size === 'none') return
    const inst = this.build('crowd', CROWDS[size])
    this.crowd = inst
    rampTo(inst.out.gain, dbToGain(AUDIO.ambienceMakeupDb), now, 1.5)
  }

  /** A crowd reaction: a swell of the crowd layers, darker for an "ooh", sized by the crowd (§9.4). A polite crowd only applauds. */
  react(kind: CrowdReaction, at: number = this.ctx.currentTime): void {
    if (!this.crowd || this.crowdSize === 'none') return
    const profile = CROWD_PROFILES[this.crowdSize]
    if (profile.polite) {
      if (kind !== 'applause' && kind !== 'ko') return
      const t = Math.max(this.ctx.currentTime, at)
      if (t < this.reactionUntil) return
      this.reactionUntil = t + profile.applause.seconds
      this.applause(t, profile.applause.seconds)
      return
    }
    const t = Math.max(this.ctx.currentTime, at)
    if (t < this.reactionUntil && kind !== 'ko') return
    const big = kind === 'ko' ? 2 : kind === 'applause' ? profile.applause.seconds : kind === 'cheer' ? 0.6 : 0.5
    const up = (kind === 'ko' ? 9 : kind === 'applause' ? 6 : kind === 'cheer' ? 5 : kind === 'ooh' ? 3 : 2) * profile.react
    this.reactionUntil = t + big
    for (const l of this.crowd.layers) {
      if (l.kind !== 'noise') continue
      const base = l.gain.gain.value
      l.gain.gain.cancelScheduledValues(t)
      l.gain.gain.setValueAtTime(base, t)
      l.gain.gain.linearRampToValueAtTime(base * dbToGain(up), t + 0.15)
      l.gain.gain.linearRampToValueAtTime(base, t + big)
      if (kind === 'ooh' && l.firstFilter) {
        const hz = l.firstFilter.frequency.value
        l.firstFilter.frequency.setValueAtTime(hz, t)
        l.firstFilter.frequency.linearRampToValueAtTime(hz * 0.6, t + 0.2)
        l.firstFilter.frequency.linearRampToValueAtTime(hz, t + big)
      }
    }
    if (kind === 'applause' || kind === 'ko') this.applause(t, big)
    if (kind === 'clap') this.clapOnce(t)
  }

  private applause(t: number, seconds: number): void {
    // Many soft claps: short filtered bursts, as many and as loud as the crowd is big.
    const a = CROWD_PROFILES[this.crowdSize].applause
    const n = Math.round(seconds * a.rate)
    for (let i = 0; i < n; i++) {
      const at = t + (i / n) * seconds + between(this.rng, 0, 0.05)
      const env = 1 - i / n
      this.burst(at, 'white', { type: 'bandpass', hz: 1800, q: 1 }, 0.02 + 0.02 * this.rng(), a.levelDb + 6 * env, between(this.rng, -0.6, 0.6), 3500, this.crowd?.out ?? this.dest)
    }
  }

  /** The crowd claps on the beat at `at` (the last 10 s, §9.4): a handful of hands, a few ms apart. */
  clapAlong(at: number): void {
    if (!this.crowd || this.crowdSize === 'none') return
    const c = CROWD_PROFILES[this.crowdSize].clap
    for (let i = 0; i < c.voices; i++) {
      const t = Math.max(this.ctx.currentTime, at + between(this.rng, -0.012, 0.012))
      this.burst(t, 'white', { type: 'bandpass', hz: between(this.rng, 1400, 2200), q: 1.1 }, 0.018 + 0.012 * this.rng(), c.levelDb + between(this.rng, -3, 1), between(this.rng, -0.6, 0.6), 3500, this.crowd.out)
    }
  }

  /** A chanting crowd claps on two and four only. */
  crowdBackbeat(): boolean {
    return CROWD_PROFILES[this.crowdSize].clap.backbeat
  }

  private clapOnce(t: number): void {
    const pick = this.bank.take('claps', 'hit')
    if (!pick) return
    this.playSampleAt(pick.buffer, pick.rate, t, -30, between(this.rng, -0.3, 0.3), this.crowd?.out ?? this.dest, 3500)
  }

  /** The tick: random walks every 250 ms and Poisson spawns. Called from the scheduler's filler with the horizon. */
  tick(now: number, until: number): void {
    this.fading = this.fading.filter((b) => b.out.gain.value > 0.001 || now < this.ctx.currentTime + 3)
    if (now >= this.nextWalk) {
      this.nextWalk = now + WALK_SEC
      for (const bed of [this.current, this.crowd]) {
        if (!bed) continue
        for (const l of bed.layers) {
          if (l.kind !== 'noise' || !l.walk) continue
          l.walkDb = Math.max(-l.walk.db, Math.min(l.walk.db, l.walkDb + (this.rng() - 0.5) * l.walk.db))
          const target = dbToGain(this.levelOf(l.id, l.baseDb, bed.id) + l.makeupDb + l.walkDb)
          l.gain.gain.setTargetAtTime(target, now, WALK_SEC)
          if (l.firstFilter && l.walk.hz) {
            l.walkHz = Math.max(-l.walk.hz, Math.min(l.walk.hz, l.walkHz + (this.rng() - 0.5) * l.walk.hz))
            l.firstFilter.frequency.setTargetAtTime(Math.max(30, l.baseHz + l.walkHz), now, WALK_SEC)
          }
        }
      }
    }
    const dt = Math.max(0, until - now)
    for (const bed of [this.current, this.crowd]) {
      if (!bed) continue
      for (const l of bed.layers) {
        if (l.kind !== 'spawn') continue
        const rate = l.layer.rate * l.rateScale
        if (rate <= 0) continue
        // Poisson in the window: expected count rate·dt, at most one phrase per tick.
        if (this.rng() < rate * dt * 0.0625) this.spawnPhrase(l, now + this.rng() * dt)
      }
    }
  }

  private spawnPhrase(l: LiveSpawn, at: number): void {
    const count = l.layer.burst ? Math.round(between(this.rng, l.layer.burst.count[0], l.layer.burst.count[1])) : 1
    let t = at
    for (let i = 0; i < count; i++) {
      this.spawnOne(l, t)
      if (l.layer.burst) t += between(this.rng, l.layer.burst.gapMs[0], l.layer.burst.gapMs[1]) / 1000
    }
  }

  private panOf(l: SpawnLayer): number {
    if (typeof l.pan === 'number') return l.pan
    if (l.pan === 'wide') return between(this.rng, -0.8, 0.8)
    if (l.pan === 'random') return between(this.rng, -0.5, 0.5)
    return 0
  }

  private spawnOne(l: LiveSpawn, at: number): void {
    if (this.pool.count(at) >= this.pool.limit) this.pool.makeRoom(at)
    const e: SpawnEvent = l.layer.event
    const pan = this.panOf(l.layer)
    const db = (l.layer.levelJitterDb ? between(this.rng, -l.layer.levelJitterDb, l.layer.levelJitterDb) : 0)
    const cents = l.layer.pitchCents ? between(this.rng, -l.layer.pitchCents, l.layer.pitchCents) : 0
    const lowpass = l.layer.lowpassHz
    const target = l.gain
    switch (e.kind) {
      case 'chirp': {
        const hz = between(this.rng, e.hz[0], e.hz[1]) * Math.pow(2, cents / 1200)
        const ms = between(this.rng, e.ms[0], e.ms[1])
        this.tone(at, hz, hz * (1 + (e.sweep ?? 0) * (this.rng() - 0.5)), ms / 1000, db, pan, target, lowpass, e.fm)
        break
      }
      case 'click':
        this.burst(at, 'white', { type: 'bandpass', hz: 2500, q: 2 }, (e.ms ?? 4) / 1000, db, pan, lowpass, target)
        break
      case 'drip':
        this.tone(at, e.from * Math.pow(2, cents / 1200), e.to * Math.pow(2, cents / 1200), e.ms / 1000, db, pan, target, lowpass)
        break
      case 'bubble':
        this.tone(at, e.from * Math.pow(2, cents / 1200), e.to * Math.pow(2, cents / 1200), e.ms / 1000, db, pan, target, lowpass)
        break
      case 'crackle':
        this.burst(at, 'white', { type: 'highpass', hz: 1200, q: 0.7 }, between(this.rng, e.ms[0], e.ms[1]) / 1000, db, pan, lowpass ?? 4000, target)
        break
      case 'creak':
        this.tone(at, 180 * Math.pow(2, cents / 1200), 260, between(this.rng, e.ms[0], e.ms[1]) / 1000, db - 6, pan, target, lowpass ?? 2500, 8)
        break
      case 'noiseBurst':
        this.burst(at, e.color, e.filter ?? null, between(this.rng, e.ms[0], e.ms[1]) / 1000, db, pan, e.lowpassHz ?? lowpass, target)
        break
      case 'thunder': {
        // A brown burst with a lowpass falling 200→60 Hz over 3–6 s; never close.
        const seconds = between(this.rng, 3, 6)
        this.burst(at, 'brown', { type: 'lowpass', hz: 200, q: 0.6 }, seconds, db, pan, undefined, target, 60)
        break
      }
      case 'crickets': {
        for (let p = 0; p < e.pulses; p++) this.tone(at + p / e.pulseHz, e.hz * Math.pow(2, cents / 1200), e.hz, 0.5 / e.pulseHz, db, pan, target, lowpass ?? 6000)
        break
      }
      case 'sample': {
        const pick = e.midi !== undefined ? this.bank.pick(e.inst, e.art, e.midi) : this.bank.take(e.inst, e.art)
        if (!pick) return
        this.playSampleAt(pick.buffer, pick.rate * Math.pow(2, cents / 1200), at, db, pan, target, lowpass)
        break
      }
    }
  }

  private tone(at: number, fromHz: number, toHz: number, seconds: number, db: number, pan: number, out: AudioNode, lowpassHz?: number, fmHz?: number): void {
    const ctx = this.ctx
    const osc = makeOscillator(ctx, 'sine', fromHz)
    if (toHz !== fromHz) osc.frequency.exponentialRampToValueAtTime(Math.max(20, toHz), at + seconds)
    const g = makeGain(ctx, 0)
    let node: AudioNode = osc
    if (fmHz) {
      const mod = makeOscillator(ctx, 'sine', fmHz)
      const depth = makeGain(ctx, fromHz * 0.02)
      mod.connect(depth)
      depth.connect(osc.frequency)
      mod.start(at)
      mod.stop(at + seconds + 0.05)
    }
    if (lowpassHz) {
      const lp = makeFilter(ctx, 'lowpass', lowpassHz, 0.5)
      node.connect(lp)
      node = lp
    }
    node.connect(g)
    this.connectPanned(g, pan, out)
    const a = Math.min(0.01, seconds * 0.3)
    g.gain.setValueAtTime(0.0001, at)
    g.gain.linearRampToValueAtTime(dbToGain(db), at + a)
    g.gain.exponentialRampToValueAtTime(0.0001, at + seconds)
    osc.start(at)
    osc.stop(at + seconds + 0.02)
    this.track(g, at + seconds, osc)
  }

  private burst(at: number, color: NoiseColor, filter: { type: BiquadFilterType; hz: number; q?: number } | null, seconds: number, db: number, pan: number, lowpassHz: number | undefined, out: AudioNode, sweepTo?: number): void {
    const ctx = this.ctx
    const src = ctx.createBufferSource()
    src.buffer = noiseLoop(ctx, color)
    src.loop = true
    let node: AudioNode = src
    const colour = colourChain(ctx, color)
    if (colour) {
      node.connect(colour.input)
      node = colour.output
    }
    let makeupDb = WHITE_RMS_MAKEUP_DB
    if (filter) {
      const f = makeFilter(ctx, filter.type, filter.hz, filter.q ?? 0.707)
      if (sweepTo) f.frequency.exponentialRampToValueAtTime(sweepTo, at + seconds)
      node.connect(f)
      node = f
      makeupDb += filterMakeupDb(filter)
    }
    if (lowpassHz) {
      const lp = makeFilter(ctx, 'lowpass', lowpassHz, 0.5)
      node.connect(lp)
      node = lp
    }
    const g = makeGain(ctx, 0)
    node.connect(g)
    this.connectPanned(g, pan, out)
    const a = Math.min(0.02, seconds * 0.25)
    g.gain.setValueAtTime(0.0001, at)
    g.gain.linearRampToValueAtTime(dbToGain(db + makeupDb), at + a)
    g.gain.exponentialRampToValueAtTime(0.0001, at + seconds)
    src.start(at, between(this.rng, 0, LOOP_SEC))
    src.stop(at + seconds + 0.02)
    this.track(g, at + seconds, src)
  }

  private playSampleAt(buffer: AudioBuffer, rate: number, at: number, db: number, pan: number, out: AudioNode, lowpassHz?: number): void {
    const ctx = this.ctx
    const src = ctx.createBufferSource()
    src.buffer = buffer
    src.playbackRate.value = rate
    let node: AudioNode = src
    if (lowpassHz) {
      const lp = makeFilter(ctx, 'lowpass', lowpassHz, 0.5)
      node.connect(lp)
      node = lp
    }
    const g = makeGain(ctx, dbToGain(db))
    node.connect(g)
    this.connectPanned(g, pan, out)
    src.start(at)
    const end = at + buffer.duration / rate
    this.track(g, end, src)
  }

  private connectPanned(node: AudioNode, pan: number, out: AudioNode): void {
    if (Math.abs(pan) > 0.01 && typeof StereoPannerNode !== 'undefined') {
      const p = this.ctx.createStereoPanner()
      p.pan.value = Math.max(-1, Math.min(1, pan))
      node.connect(p)
      p.connect(out)
    } else node.connect(out)
  }

  private track(g: GainNode, endsAt: number, src: AudioScheduledSourceNode): void {
    const voice: Voice = {
      endsAt,
      out: g,
      source: null,
      rate: null,
      stopped: false,
      stop: (at, rel = 0.02) => {
        voice.stopped = true
        rampTo(g.gain, 0, at, rel)
        try {
          src.stop(at + rel + 0.02)
        } catch {
          /* fine */
        }
      },
    }
    this.pool.add({ voice, startedAt: this.ctx.currentTime, level: 0.3, silentLayer: false, owner: 'ambience' })
    src.onended = () => {
      try {
        g.disconnect()
      } catch {
        /* fine */
      }
    }
  }

  /** A session-only trim for one layer (the Sound Lab's sliders). */
  setLayerTrim(bedId: string, layerId: string, db: number): void {
    this.trims.set(`${bedId}/${layerId}`, db)
    for (const bed of [this.current, this.crowd]) {
      if (!bed || bed.id !== bedId) continue
      for (const l of bed.layers) if (l.id === layerId) l.gain.gain.setTargetAtTime(dbToGain(this.levelOf(l.id, l.baseDb, bed.id) + (l.kind === 'noise' ? l.makeupDb : 0)), this.ctx.currentTime, 0.05)
    }
  }

  stopAll(fadeSec = 0.3): void {
    const now = this.ctx.currentTime
    this.current?.stop(now, fadeSec)
    this.crowd?.stop(now, fadeSec)
    this.current = null
    this.crowd = null
    this.bedId = null
    this.crowdSize = 'none'
    this.pool.stopAll(now)
  }

  voices(): number {
    return this.pool.count(this.ctx.currentTime)
  }
}
