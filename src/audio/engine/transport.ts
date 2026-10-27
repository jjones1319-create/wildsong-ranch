/**
 * SOUND_UPGRADE §4.4, §6.5, §6.6, §4.7: the music player. One transport per song, every part of the playing
 * song scheduled bar by bar ahead of the look-ahead (parts in silent layers at zero gain, so a layer can fade
 * in at any bar with its held notes already sounding), stems and weather rules applied at the next bar,
 * breaths drawn from the audio RNG, loops from `loopFrom`, 1.5 s crossfades between songs, interrupting
 * stingers that fade the area music out over 150 ms and restart it at the next section, and the performance:
 * humanising, swing, phrase shaping, vibrato by note length, scoops, mono crossfades, rolled chords.
 */
import { AUDIO } from '../../data/tuning.ts'
import type { Weather } from '../../data/types.ts'
import { INSTRUMENTS, type InstrumentId } from '../recipes/instruments.ts'
import { KITS } from '../recipes/kits.ts'
import { beatsPerBar, type Mode } from '../music/abc.ts'
import { BREATH, breathSeconds, instrumentFor, loopFromOf, orderOf, sounding, type Arrangement, type LineEvent, type Song, type WeatherRule } from '../music/song.ts'
import type { Graph } from './context.ts'
import { dbToGain, makeGain, rampTo } from './nodes.ts'
import { between, jitter, type Rng } from './rng.ts'
import type { SampleBank } from './samples.ts'
import { playSample, type NoteParams, type Voice } from './sampler.ts'
import { beatToTime, type Scheduler, type Transport } from './scheduler.ts'
import type { KeyContext } from './sfx.ts'
import { playSynth } from './synth.ts'
import { VoicePool } from './voices.ts'

export interface PlayOptions {
  arrangement?: Arrangement | null
  layers?: Iterable<string>
  stem?: string | null
  weather?: Weather | null
  fadeInSec?: number
  fadeOutSec?: number
  /** Start at this order index (default 0). */
  startIndex?: number
  /** Semitones (stingers are written in C and transposed to the area key). */
  transpose?: number
  /** Loop (songs) or play once (stingers). */
  once?: boolean
  onEnd?: () => void
  /** Quantise the start to the previous song's beat when keys and tempos match. */
  onBeatOf?: Playback | null
}

export interface Playback {
  song: Song
  arrangement: Arrangement | null
  transport: Transport
  tag: string
  out: GainNode
  send: GainNode
  lines: Map<string, { gain: GainNode; sounding: GainNode; on: boolean }>
  layers: Set<string>
  stem: string | null
  weather: Weather | null
  rule: WeatherRule | null
  /** Beats from the transport start at which the current section began. */
  sectionStartBeat: number
  orderIndex: number
  /** Bars scheduled so far in the current section. */
  bar: number
  /** Absolute bar count since the start (for fragments). */
  barCount: number
  once: boolean
  ended: boolean
  stopping: boolean
  transpose: number
  mono: Map<string, Voice>
  onEnd?: () => void
  pendingBreathBeats: number | null
}

const CROSSFADE_SEC = 1.5
const LAYER_FADE_BARS = 1

export class MusicPlayer {
  readonly ctx: BaseAudioContext
  readonly graph: Graph
  readonly bank: SampleBank
  readonly scheduler: Scheduler
  readonly rng: Rng
  readonly pool = new VoicePool('music', 32)
  current: Playback | null = null
  /** The area song interrupted by a stinger, to be restarted at its next section. */
  interrupted: { playback: Playback; nextIndex: number } | null = null
  private fading: Playback[] = []
  private counter = 0
  /** Per-song trims from calibration (dB). */
  trims: Record<string, number> = {}
  /** For the drill cue timing error and the debug view. */
  lastSectionStartedAt = 0
  onSection: ((playback: Playback, section: string) => void) | null = null

  constructor(ctx: BaseAudioContext, graph: Graph, bank: SampleBank, scheduler: Scheduler, rng: Rng) {
    this.ctx = ctx
    this.graph = graph
    this.bank = bank
    this.scheduler = scheduler
    this.rng = rng
    scheduler.addFiller((until) => this.fill(until))
  }

  /** The key the playing song is in (for musical effects), with its transposition. */
  key(): KeyContext | null {
    const p = this.current
    if (!p) return null
    return { tonic: (((p.song.tune.key.tonic + p.transpose) % 12) + 12) % 12, mode: p.song.tune.key.mode as Mode }
  }

  play(song: Song, o: PlayOptions = {}): Playback {
    const now = this.ctx.currentTime
    const fadeIn = o.fadeInSec ?? CROSSFADE_SEC
    const fadeOut = o.fadeOutSec ?? CROSSFADE_SEC
    if (this.current && !this.current.stopping) this.stopPlayback(this.current, now, fadeOut)
    const arrangement = o.arrangement ?? null
    const bpm = song.bpm + (arrangement?.tempoNudge ?? 0)
    let startTime = now + 0.05
    if (o.onBeatOf && !o.onBeatOf.ended) {
      const t = o.onBeatOf.transport
      const beat = Math.floor(((now - t.startTime) * t.bpm) / 60 + 1e-6) + 1
      startTime = beatToTime(t, beat)
    }
    const transport: Transport = { startTime, bpm, beatsPerBar: beatsPerBar(song.meter) }
    const tag = `song-${++this.counter}`
    const out = makeGain(this.ctx, 0)
    const send = makeGain(this.ctx, (arrangement?.musicSend ?? song.musicSend) * 0.8)
    out.connect(this.graph.music)
    out.connect(send)
    send.connect(this.graph.reverbMusic.input)
    const lines = new Map<string, { gain: GainNode; sounding: GainNode; on: boolean }>()
    for (const line of song.lines) {
      const gain = makeGain(this.ctx, dbToGain(line.gain))
      const s = makeGain(this.ctx, 0)
      gain.connect(s)
      s.connect(out)
      lines.set(line.id, { gain, sounding: s, on: false })
    }
    const weatherName = o.weather ?? null
    const rule = weatherName ? ruleFor(song, weatherName) : null
    const playback: Playback = {
      song,
      arrangement,
      transport,
      tag,
      out,
      send,
      lines,
      layers: new Set(o.layers ?? ['main']),
      stem: o.stem ?? null,
      weather: weatherName,
      rule,
      sectionStartBeat: 0,
      orderIndex: o.startIndex ?? 0,
      bar: 0,
      barCount: 0,
      once: o.once ?? false,
      ended: false,
      stopping: false,
      transpose: o.transpose ?? 0,
      mono: new Map(),
      onEnd: o.onEnd,
      pendingBreathBeats: null,
    }
    this.applySounding(playback, startTime, 0.02)
    const trim = dbToGain(AUDIO.musicMakeupDb + (this.trims[song.id] ?? 0) + (arrangement?.gainDb ?? 0) + (rule?.gainDb ?? 0))
    out.gain.setValueAtTime(0.0001, now)
    out.gain.linearRampToValueAtTime(trim, startTime + fadeIn)
    this.current = playback
    // Fill now rather than at the next tick: a song started from inside a scheduler callback (a drill cue, a
    // stinger's end) would otherwise get its first bar scheduled late.
    this.fill(this.scheduler.horizon())
    this.graph.reverbMusic.setPreset(song.kind === 'battle' ? 'room' : 'hall')
    this.lastSectionStartedAt = startTime
    this.onSection?.(playback, orderOf(song, arrangement)[playback.orderIndex] ?? '')
    return playback
  }

  private stopPlayback(p: Playback, at: number, fadeSec: number): void {
    if (p.stopping) return
    p.stopping = true
    rampTo(p.out.gain, 0, at, Math.max(0.05, fadeSec))
    this.scheduler.cancel(p.tag)
    this.fading.push(p)
    const end = at + fadeSec + 0.1
    this.scheduler.add(end, () => {
      p.ended = true
      this.pool.stopOwner(p.tag, end, 0.1)
      try {
        p.out.disconnect()
        p.send.disconnect()
      } catch {
        /* fine */
      }
      this.fading = this.fading.filter((x) => x !== p)
    })
    if (this.current === p) this.current = null
  }

  stop(fadeSec = CROSSFADE_SEC): void {
    if (this.current) this.stopPlayback(this.current, this.ctx.currentTime, fadeSec)
  }

  /** Cuts the music fast (a KO: 150 ms). */
  cut(fadeSec = 0.15): void {
    this.stop(fadeSec)
  }

  /** Which lines sound now, applied as fades on the per-line gains. */
  private applySounding(p: Playback, at: number, fadeSec: number): void {
    const on = sounding(p.song, { stem: p.stem, layers: p.layers, weather: p.rule, arrangement: p.arrangement })
    for (const [id, l] of p.lines) {
      const want = on.has(id)
      if (want === l.on) continue
      l.on = want
      rampTo(l.sounding.gain, want ? 1 : 0, at, fadeSec)
      this.pool.setSilent(`${p.tag}/${id}`, !want)
    }
  }

  /** A layer change lands at the next bar and fades over one bar. */
  setLayers(layers: Iterable<string>): void {
    const p = this.current
    if (!p) return
    const next = new Set(layers)
    if (sameSet(next, p.layers)) return
    p.layers = next
    const at = this.nextBarTime(p)
    this.applySounding(p, at, (LAYER_FADE_BARS * p.transport.beatsPerBar * 60) / p.transport.bpm)
  }

  setStem(stem: string | null): void {
    const p = this.current
    if (!p || p.stem === stem) return
    p.stem = stem
    const at = this.nextBarTime(p)
    this.applySounding(p, at, (p.transport.beatsPerBar * 60) / p.transport.bpm)
  }

  /** Weather takes effect at the next phrase (bar). */
  setWeather(weather: Weather | null): void {
    const p = this.current
    if (!p || p.weather === weather) return
    p.weather = weather
    p.rule = weather ? ruleFor(p.song, weather) : null
    const at = this.nextBarTime(p)
    this.applySounding(p, at, (p.transport.beatsPerBar * 60) / p.transport.bpm)
    rampTo(p.out.gain, dbToGain(AUDIO.musicMakeupDb + (this.trims[p.song.id] ?? 0) + (p.arrangement?.gainDb ?? 0) + (p.rule?.gainDb ?? 0)), at, 1)
  }

  private nextBarTime(p: Playback): number {
    const now = this.ctx.currentTime
    const t = p.transport
    const beat = ((now - t.startTime) * t.bpm) / 60
    const bar = Math.floor(beat / t.beatsPerBar + 1e-6) + 1
    return beatToTime(t, bar * t.beatsPerBar)
  }

  /** Jumps to the next section at its boundary (the Sound Lab's button): the current section ends early at the next bar. */
  nextSection(): void {
    const p = this.current
    if (!p) return
    const sec = p.song.sections[orderOf(p.song, p.arrangement)[p.orderIndex]!]
    if (!sec) return
    // Let the scheduled bars play out; move the cursor to the end of the section so the filler advances.
    this.scheduler.cancel(p.tag)
    const beatsDone = p.bar * p.transport.beatsPerBar
    p.sectionStartBeat += beatsDone
    p.bar = sec.bars
    this.advanceSection(p, p.sectionStartBeat)
  }

  /** Remembers the area song and fades it out, so `resumeArea` can restart it at the section after the one it left. */
  suspendArea(fadeSec: number): void {
    const area = this.current
    if (!area || area.stopping || area.once) return
    const order = orderOf(area.song, area.arrangement)
    let next = area.orderIndex + 1
    if (next >= order.length) next = loopFromOf(area.song, area.arrangement)
    if (order[next] === BREATH) next = (next + 1) % order.length
    this.interrupted = { playback: area, nextIndex: next }
    this.stopPlayback(area, this.ctx.currentTime, fadeSec)
  }

  /** Restarts the suspended area song at its next section with a fade-in. */
  resumeArea(fadeInSec: number): Playback | null {
    const it = this.interrupted
    this.interrupted = null
    if (!it) return null
    return this.restart(it.playback, it.nextIndex, fadeInSec)
  }

  /** An interrupting stinger: the area music fades over 150 ms, the stinger plays, then the area music restarts at the section after the one it interrupted. */
  interrupt(stinger: Song, o: { transpose?: number; fadeInAfterSec?: number; gainDb?: number; onDone?: () => void } = {}): Playback {
    this.suspendArea(0.15)
    const fadeIn = o.fadeInAfterSec ?? 1
    const p = this.play(stinger, {
      transpose: o.transpose ?? 0,
      once: true,
      fadeInSec: 0.02,
      fadeOutSec: 0.15,
      arrangement: o.gainDb ? { gainDb: o.gainDb } : null,
      onEnd: () => {
        this.resumeArea(fadeIn)
        o.onDone?.()
      },
    })
    return p
  }

  /** §8.3 Slacked: every voice of the playing bed ramps its playback rate down (the pitch sags too). */
  sag(rate: number, seconds: number): void {
    const now = this.ctx.currentTime
    const p = this.current
    if (!p) return
    for (const v of this.pool.voicesOf(`${p.tag}/`)) {
      if (!v.rate) continue
      v.rate.cancelScheduledValues(now)
      v.rate.setValueAtTime(v.rate.value, now)
      v.rate.linearRampToValueAtTime(v.rate.value * rate, now + seconds)
    }
  }

  /** Restarts a song at an order index with a fade-in (after a stinger or a drill cue). */
  restart(old: Playback, index: number, fadeInSec: number): Playback {
    return this.play(old.song, { arrangement: old.arrangement, layers: old.layers, stem: old.stem, weather: old.weather, fadeInSec, fadeOutSec: 0.1, startIndex: index, transpose: old.transpose })
  }

  state(): { song: string; section: string; bar: number; layers: string[]; stem: string | null; weather: Weather | null; bpm: number } | null {
    const p = this.current
    if (!p) return null
    return { song: p.song.id, section: orderOf(p.song, p.arrangement)[p.orderIndex] ?? '', bar: p.bar, layers: [...p.layers], stem: p.stem, weather: p.weather, bpm: p.transport.bpm }
  }

  voices(): number {
    return this.pool.count(this.ctx.currentTime)
  }

  /** The scheduler's filler: schedules whole bars until the horizon. */
  private fill(until: number): void {
    const p = this.current
    if (!p || p.ended || p.stopping) return
    let guard = 0
    while (guard++ < 64) {
      const order = orderOf(p.song, p.arrangement)
      const name = order[p.orderIndex]
      if (name === undefined) {
        this.finish(p)
        return
      }
      if (name === BREATH) {
        if (p.pendingBreathBeats === null) p.pendingBreathBeats = (breathSeconds(p.song, this.rng, p.rule) * p.transport.bpm) / 60
        const endBeat = p.sectionStartBeat + p.pendingBreathBeats
        if (beatToTime(p.transport, endBeat) > until) return
        p.pendingBreathBeats = null
        this.advanceSection(p, endBeat)
        continue
      }
      const sec = p.song.sections[name]!
      if (p.bar >= sec.bars) {
        this.advanceSection(p, p.sectionStartBeat + sec.beats)
        continue
      }
      const barStartBeat = p.sectionStartBeat + p.bar * p.transport.beatsPerBar
      const barTime = beatToTime(p.transport, barStartBeat)
      if (barTime > until) return
      this.scheduleBar(p, name, p.bar, barStartBeat)
      p.bar++
      p.barCount++
    }
  }

  private advanceSection(p: Playback, atBeat: number): void {
    const order = orderOf(p.song, p.arrangement)
    p.sectionStartBeat = atBeat
    p.bar = 0
    p.orderIndex++
    if (p.orderIndex >= order.length) {
      if (p.once) {
        p.orderIndex = order.length
        return
      }
      p.orderIndex = loopFromOf(p.song, p.arrangement)
    }
    const name = order[p.orderIndex]
    const t = beatToTime(p.transport, atBeat)
    this.scheduler.add(t, () => {
      this.lastSectionStartedAt = t
      if (name) this.onSection?.(p, name)
    }, p.tag)
  }

  private finish(p: Playback): void {
    // A once-only song (a stinger) ends after its last note's release.
    const endBeat = p.sectionStartBeat
    const at = beatToTime(p.transport, endBeat) + 0.3
    if (p.stopping) return
    p.stopping = true
    this.scheduler.add(at, () => {
      p.ended = true
      rampTo(p.out.gain, 0, at, 0.5)
      this.pool.stopOwner(p.tag, at + 0.5, 0.4)
      if (this.current === p) this.current = null
      p.onEnd?.()
    })
  }

  private scheduleBar(p: Playback, section: string, bar: number, barStartBeat: number): void {
    const sec = p.song.sections[section]!
    const t = p.transport
    const spb = 60 / t.bpm
    const stem = p.stem ? p.song.stems?.[p.stem] : null
    const swing = p.song.swing ?? 0.5
    const kit = p.arrangement?.kit
    for (const line of p.song.lines) {
      if (stem && !stem.includes(line.id)) continue
      if (p.arrangement?.lines && !p.arrangement.lines.includes(line.id)) continue
      if (p.arrangement?.halfTime && line.kind === 'perc') continue
      const fragments = p.rule?.fragments?.includes(line.id) ?? false
      if (fragments && p.barCount % 4 >= 2) continue
      const events = sec.events[line.id] ?? []
      const lg = p.lines.get(line.id)!
      let inst: InstrumentId = instrumentFor(p.song, line.id, { weather: p.rule, arrangement: p.arrangement })
      if (kit && line.kind === 'perc' && p.song.kit) {
        const role = p.song.perc?.lines[line.id]?.role
        if (role) {
          const swapped = KITS[kit][role]
          if (swapped === null) continue
          inst = swapped
        }
      }
      const def = INSTRUMENTS[inst]
      const phrase = events.filter((e) => e.bar === bar)
      for (const e of phrase) {
        let beat = barStartBeat + e.t
        if (swing > 0.5 && t.beatsPerBar === 4 && Math.abs(e.t - Math.floor(e.t) - 0.5) < 1e-6) beat += swing - 0.5
        const human = (def.family === 'perc' ? 0.003 : 0.006) * jitter(this.rng)
        const time = beatToTime(t, beat) + human
        const dur = e.dur * spb
        const vel = Math.max(0.05, Math.min(1, e.vel * (1 + 0.06 * jitter(this.rng)) * phraseShape(e, phrase)))
        const pitches = e.pitches.map((m) => m + p.transpose)
        const art = e.dur >= 1 && def.longArt && line.art === def.arts[0] ? def.longArt : line.art
        this.scheduler.add(
          time - 0.05,
          () => {
            if (p.ended) return
            if (def.mono) {
              const prev = p.mono.get(line.id)
              if (prev && !prev.stopped && prev.endsAt > time) prev.stop(time, 0.02)
            }
            const roll = (e.strumMs ?? (pitches.length > 1 && def.family === 'pluck' ? between(this.rng, 10, 25) : 0)) / 1000
            pitches.forEach((midi, i) => {
              const params: NoteParams = { inst, art, midi, vel, time: time + i * roll, dur, pan: line.pan, grace: e.grace?.map((g) => g + p.transpose), phraseStart: e.phraseStart }
              this.pool.makeRoom(time)
              const v = this.note(params, lg.gain)
              if (!v) return
              this.pool.add({ voice: v, startedAt: time, level: lg.on ? vel : 0, silentLayer: !lg.on, owner: `${p.tag}/${line.id}` })
              if (def.mono) p.mono.set(line.id, v)
            })
          },
          p.tag,
        )
      }
    }
  }

  /** A sampled note, or its fallback while the pack loads; patches layer their instruments. */
  note(params: NoteParams, dest: AudioNode): Voice | null {
    const def = INSTRUMENTS[params.inst]
    if (def.patch) {
      let first: Voice | null = null
      for (const layer of def.patch.layers) {
        const sub = INSTRUMENTS[layer.inst]
        const v = this.note({ ...params, inst: layer.inst, art: sub.arts[0]!, midi: params.midi + layer.transpose, gainDb: (params.gainDb ?? 0) + layer.gainDb, dur: layer.decayCapSec ? Math.min(params.dur, layer.decayCapSec) : params.dur }, dest)
        first ??= v
      }
      return first
    }
    if (def.melody === undefined && !def.pitchedPerc) {
      const v = playSample(this.ctx, this.bank, dest, params)
      return v
    }
    return playSample(this.ctx, this.bank, dest, params) ?? playSynth(this.ctx, dest, def.fallback, params)
  }

  stopAll(): void {
    const now = this.ctx.currentTime
    if (this.current) this.stopPlayback(this.current, now, 0.2)
    this.interrupted = null
    this.pool.stopAll(now)
  }
}

function sameSet(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false
  for (const x of a) if (!b.has(x)) return false
  return true
}

function ruleFor(song: Song, weather: Weather): WeatherRule | null {
  const key = weather.toLowerCase() as 'cloudy' | 'rain' | 'storm' | 'snow' | 'sunny'
  if (key === 'sunny') return null
  return song.weather?.[key] ?? null
}

/** §6.6 phrase shaping: a gentle rise to the phrase's middle and an easing at its end (±6%). */
function phraseShape(e: LineEvent, phrase: readonly LineEvent[]): number {
  const i = phrase.indexOf(e)
  if (i < 0 || phrase.length < 3) return 1
  const x = i / (phrase.length - 1)
  return 1 + 0.06 * Math.sin(Math.PI * x) - 0.03 * x
}

