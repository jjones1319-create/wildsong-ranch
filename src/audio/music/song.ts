/**
 * SOUND_UPGRADE §6.1, §6.5: the song model. A song file holds its ABC (the only source of tempo, meter and
 * key), its parts (ABC voices), accompaniment lines (generators over the chord track), percussion lines
 * (step strings), its form (order, loop point, breath), its weather rules, stems and arrangements.
 * `defineSong` parses and compiles everything once into plain events per section per line, which the
 * scheduler, the checker, the analyser and the Sound Lab all read. Pure.
 */
import { articulationOf, INSTRUMENTS, isInstrumentId, type InstrumentId } from '../recipes/instruments.ts'
import { KITS, type KitId, type PercRole } from '../recipes/kits.ts'
import { beatsPerBar, parseAbc, type Tune } from './abc.ts'
import { chordAt, chordTrack, type Chord, type ChordAt } from './chords.ts'
import { generate, type GenEvent, type PatternId } from './patterns.ts'
import { defaultGrid, percEvents } from './perc.ts'

export const SONG_KINDS = ['place', 'ranch', 'town', 'battle', 'drill', 'stinger', 'effect', 'drone', 'minigame'] as const
export type SongKind = (typeof SONG_KINDS)[number]

export const ROLES = ['lead', 'counter', 'accomp', 'bass', 'perc', 'colour'] as const
export type Role = (typeof ROLES)[number]

export interface PartDef {
  inst: InstrumentId
  art?: string
  role: Role
  layers: readonly string[]
  /** dB. */
  gain?: number
  /** −1…1. */
  pan?: number
  /** The ABC voice that holds the notes (default: the part's id). */
  voice?: string
}

export interface AccompDef {
  inst: InstrumentId
  art?: string
  role: Role
  pattern: PatternId
  layers: readonly string[]
  octave?: number
  density?: 'sparse' | 'normal' | 'busy'
  spread?: 'close' | 'open'
  size?: number
  octaveJumps?: boolean
  gain?: number
  pan?: number
}

export interface PercLineDef {
  inst?: InstrumentId
  /** A kit role instead of an instrument (battle songs). */
  role?: PercRole
  art?: string
  layers: readonly string[]
  steps: string
  gain?: number
  pan?: number
  /** Pitched percussion follows the chord track. */
  pitch?: 'root' | 'fifth'
}

export interface PercDef {
  grid?: number
  lines: Record<string, PercLineDef>
}

export interface WeatherRule {
  gainDb?: number
  mute?: readonly string[]
  add?: readonly string[]
  swap?: Partial<Record<string, InstrumentId>>
  /** These lines play only bars 1–2 of every 4. */
  fragments?: readonly string[]
  breath?: readonly [number, number]
}

export interface Arrangement {
  /** Only these lines sound (default: all). */
  lines?: readonly string[]
  order?: readonly string[]
  loopFrom?: number
  kit?: KitId
  /** Swap the instrument of these lines. */
  swap?: Partial<Record<string, InstrumentId>>
  transpose?: number
  /** Quarter-note BPM added to the song's tempo. */
  tempoNudge?: number
  gainDb?: number
  musicSend?: number
  /** The last section's final chord is held (credits). */
  heldEnding?: boolean
  /** Half-time feel: percussion off, long notes only (a lobby). */
  halfTime?: boolean
}

export interface SongDef {
  id: string
  kind: SongKind
  brief: string
  /** §3.3 energy 1–5. */
  energy: number
  /** Reverb send 0–1. */
  musicSend: number
  /** 8th-note swing ratio 0.5 (straight) to 0.62. */
  swing?: number
  abc: string
  parts: Record<string, PartDef>
  accomp?: Record<string, AccompDef>
  perc?: PercDef
  order: readonly string[]
  loopFrom: number
  /** Ranch songs: the breath between passes, seconds. */
  breath?: readonly [number, number]
  weather?: Partial<Record<'cloudy' | 'rain' | 'storm' | 'snow', WeatherRule>>
  stems?: Record<string, readonly string[]>
  arrangements?: Record<string, Arrangement>
  derivedFrom?: string
  /** The kit for role-based percussion lines. */
  kit?: KitId
  /** Where the Wildsong motif is quoted, for the checker. */
  motifQuote?: { part: string; section: string }
}

export interface LineEvent {
  bar: number
  /** Beats from the bar's start. */
  t: number
  /** Beats; may cross bar lines after tie merging. */
  dur: number
  pitches: number[]
  vel: number
  grace?: number[]
  strumMs?: number
  /** First note after a rest (winds scoop, phrase shaping). */
  phraseStart?: boolean
}

export interface Line {
  id: string
  kind: 'part' | 'accomp' | 'perc'
  inst: InstrumentId
  art: string
  role: Role
  layers: readonly string[]
  gain: number
  pan: number
  pitchedPerc?: 'root' | 'fifth'
}

export interface SectionData {
  name: string
  bars: number
  /** Beats in the section (sum of bar lengths; a pickup bar counts as written). */
  beats: number
  chordTrack: ChordAt[]
  /** Events per line id. */
  events: Record<string, LineEvent[]>
  /** Lead-bar pitch lists per part voice (for the checker's repetition rule), before tie merging. */
  voiceBars: Record<string, number[][]>
}

export interface Song extends SongDef {
  tune: Tune
  lines: Line[]
  sections: Record<string, SectionData>
  /** Quarter-note BPM. */
  bpm: number
  meter: readonly [number, number]
}

export const BREATH = 'breath'

function requireInstrument(id: string, where: string): InstrumentId {
  if (!isInstrumentId(id)) throw new Error(`${where}: unknown instrument "${id}"`)
  return id
}

/** Merges tied events (same single pitch, back to back) into one longer event and marks phrase starts. */
function compilePart(bars: readonly { events: readonly { t: number; dur: number; pitches: number[]; tie: boolean; grace?: number[]; vel: number }[]; length: number }[]): LineEvent[] {
  const out: LineEvent[] = []
  let open: LineEvent | null = null
  let openTie = false
  let afterRest = true
  bars.forEach((bar, b) => {
    for (const ev of bar.events) {
      if (ev.pitches.length === 0) {
        afterRest = true
        open = null
        openTie = false
        continue
      }
      if (open && openTie && open.pitches.length === 1 && ev.pitches.length === 1 && open.pitches[0] === ev.pitches[0]) {
        open.dur += ev.dur
        openTie = ev.tie
        continue
      }
      const e: LineEvent = { bar: b, t: ev.t, dur: ev.dur, pitches: [...ev.pitches], vel: ev.vel }
      if (ev.grace) e.grace = [...ev.grace]
      if (afterRest) e.phraseStart = true
      afterRest = false
      out.push(e)
      open = e
      openTie = ev.tie
    }
  })
  return out
}

function fromGen(events: readonly GenEvent[]): LineEvent[] {
  const out: LineEvent[] = []
  let open: LineEvent | null = null
  let openTie = false
  for (const g of events) {
    if (open && openTie && open.pitches.join(',') === g.pitches.join(',')) {
      open.dur += g.dur
      openTie = g.tie ?? false
      continue
    }
    const e: LineEvent = { bar: g.bar, t: g.t, dur: g.dur, pitches: [...g.pitches], vel: g.vel }
    if (g.strumMs) e.strumMs = g.strumMs
    out.push(e)
    open = e
    openTie = g.tie ?? false
  }
  return out
}

/** The playable range used by generators when no manifest is at hand: the instrument's melody range widened. */
function generatorRange(inst: InstrumentId): readonly [number, number] {
  const m = INSTRUMENTS[inst].melody
  return m ? [m[0], m[1]] : [36, 84]
}

export function defineSong(def: SongDef): Song {
  const tune = parseAbc(def.abc)
  const chordsVoice = tune.voices.find((v) => v.id === 'chords')
  const lines: Line[] = []
  for (const [id, p] of Object.entries(def.parts)) {
    const inst = requireInstrument(p.inst, `${def.id}/${id}`)
    const voice = tune.voices.find((v) => v.id === (p.voice ?? id))
    if (!voice) throw new Error(`${def.id}: part ${id} has no ABC voice "${p.voice ?? id}"`)
    lines.push({ id, kind: 'part', inst, art: articulationOf(inst, p.art), role: p.role, layers: p.layers, gain: p.gain ?? 0, pan: p.pan ?? 0 })
  }
  for (const [id, a] of Object.entries(def.accomp ?? {})) {
    if (def.parts[id]) throw new Error(`${def.id}: line id ${id} is both a part and an accompaniment`)
    const inst = requireInstrument(a.inst, `${def.id}/${id}`)
    lines.push({ id, kind: 'accomp', inst, art: articulationOf(inst, a.art), role: a.role, layers: a.layers, gain: a.gain ?? 0, pan: a.pan ?? 0 })
  }
  const kit = def.kit ? KITS[def.kit] : null
  for (const [id, p] of Object.entries(def.perc?.lines ?? {})) {
    if (def.parts[id] || def.accomp?.[id]) throw new Error(`${def.id}: line id ${id} is used twice`)
    let inst: InstrumentId | null = null
    if (p.inst) inst = requireInstrument(p.inst, `${def.id}/${id}`)
    else if (p.role) {
      if (!kit) throw new Error(`${def.id}: perc line ${id} uses a role but the song names no kit`)
      inst = kit[p.role]
    } else throw new Error(`${def.id}: perc line ${id} needs an instrument or a role`)
    if (inst === null) continue
    const line: Line = { id, kind: 'perc', inst, art: articulationOf(inst, p.art), role: 'perc', layers: p.layers, gain: p.gain ?? 0, pan: p.pan ?? 0 }
    if (p.pitch) line.pitchedPerc = p.pitch
    lines.push(line)
  }

  const grid = def.perc?.grid ?? defaultGrid(tune.meter)
  const sections: Record<string, SectionData> = {}
  let lastChord: Chord | null = null
  for (const name of tune.sections) {
    const anyVoice = tune.voices[0]!.sections.find((s) => s.name === name)!
    const bars = anyVoice.bars.length
    const beats = anyVoice.bars.reduce((s, b) => s + b.length, 0)
    const meter = anyVoice.bars[0]?.meter ?? tune.meter
    let track: ChordAt[] = []
    if (chordsVoice) {
      const cs = chordsVoice.sections.find((s) => s.name === name)!
      const r = chordTrack(cs, lastChord)
      track = r.track
      lastChord = r.last
    }
    const events: Record<string, LineEvent[]> = {}
    const voiceBars: Record<string, number[][]> = {}
    for (const line of lines) {
      if (line.kind === 'part') {
        const p = def.parts[line.id]!
        const voice = tune.voices.find((v) => v.id === (p.voice ?? line.id))!
        const sec = voice.sections.find((s) => s.name === name)!
        events[line.id] = compilePart(sec.bars)
        voiceBars[line.id] = sec.bars.map((b) => b.events.flatMap((e) => (e.pitches.length ? [e.pitches[0]!] : [-1])))
      } else if (line.kind === 'accomp') {
        const a = def.accomp![line.id]!
        if (track.length === 0) throw new Error(`${def.id}: accompaniment ${line.id} needs a V:chords voice`)
        events[line.id] = fromGen(generate(a.pattern, track, bars, meter, { octave: a.octave, density: a.density, spread: a.spread, size: a.size, octaveJumps: a.octaveJumps, range: generatorRange(line.inst) }))
      } else {
        const p = def.perc!.lines[line.id]!
        const evs = percEvents(p.steps, grid, bars, meter)
        if (line.pitchedPerc) {
          for (const e of evs) {
            const c = chordAt(track, e.bar, e.t)
            if (c) {
              const pc = line.pitchedPerc === 'fifth' ? (c.root + 7) % 12 : c.bass
              // Timpani sit around C2–A3.
              let m = 36 + (((pc - 36) % 12) + 12) % 12
              if (m > 57) m -= 12
              e.pitches = [m]
            }
          }
        }
        events[line.id] = fromGen(evs)
      }
    }
    sections[name] = { name, bars, beats, chordTrack: track, events, voiceBars }
  }
  for (const name of def.order) if (name !== BREATH && !sections[name]) throw new Error(`${def.id}: order names unknown section "${name}"`)
  if (def.breath && def.kind !== 'ranch') throw new Error(`${def.id}: only ranch songs breathe`)
  if (def.order.includes(BREATH) && !def.breath) throw new Error(`${def.id}: a breath in the order needs breath: [min, max]`)
  for (const [stem, ids] of Object.entries(def.stems ?? {})) for (const id of ids) if (!lines.some((l) => l.id === id)) throw new Error(`${def.id}: stem ${stem} names unknown line ${id}`)
  return { ...def, tune, lines, sections, bpm: tune.bpm, meter: tune.meter }
}

export interface SoundingOptions {
  stem?: string | null
  layers: ReadonlySet<string>
  weather?: WeatherRule | null
  arrangement?: Arrangement | null
}

/** §6.5 which lines sound: in the active stem (or no stem), at least one layer on, and not muted by weather. */
export function sounding(song: Song, o: SoundingOptions): Set<string> {
  const out = new Set<string>()
  const stem = o.stem ? song.stems?.[o.stem] : null
  for (const line of song.lines) {
    if (stem && !stem.includes(line.id)) continue
    if (o.arrangement?.lines && !o.arrangement.lines.includes(line.id)) continue
    if (o.arrangement?.halfTime && line.kind === 'perc') continue
    const added = o.weather?.add?.includes(line.id) ?? false
    const layerOn = line.layers.some((l) => o.layers.has(l))
    if (!layerOn && !added) continue
    if (o.weather?.mute?.includes(line.id)) continue
    out.add(line.id)
  }
  return out
}

/** The instrument a line plays after weather swaps and arrangement swaps. */
export function instrumentFor(song: Song, lineId: string, o: { weather?: WeatherRule | null; arrangement?: Arrangement | null }): InstrumentId {
  const line = song.lines.find((l) => l.id === lineId)
  if (!line) throw new Error(`${song.id}: no line ${lineId}`)
  return o.weather?.swap?.[lineId] ?? o.arrangement?.swap?.[lineId] ?? line.inst
}

/** The breath between passes, in seconds, drawn from the song's (or the weather's) range. */
export function breathSeconds(song: Song, rng: () => number, weather?: WeatherRule | null): number {
  const range = weather?.breath ?? song.breath
  if (!range) return 0
  return range[0] + (range[1] - range[0]) * rng()
}

/** The play order of an arrangement (or the song's own). */
export function orderOf(song: Song, arrangement?: Arrangement | null): readonly string[] {
  return arrangement?.order ?? song.order
}

export function loopFromOf(song: Song, arrangement?: Arrangement | null): number {
  return arrangement?.loopFrom ?? song.loopFrom
}

/** Seconds of music in one pass of the order (breaths excluded). */
export function passSeconds(song: Song, arrangement?: Arrangement | null): number {
  const bpm = song.bpm + (arrangement?.tempoNudge ?? 0)
  let beats = 0
  for (const name of orderOf(song, arrangement)) if (name !== BREATH) beats += song.sections[name]!.beats
  return (beats * 60) / bpm
}

/** Seconds of one section. */
export function sectionSeconds(song: Song, name: string, arrangement?: Arrangement | null): number {
  const bpm = song.bpm + (arrangement?.tempoNudge ?? 0)
  return (song.sections[name]!.beats * 60) / bpm
}

/** Bars per section, beats per bar. */
export function barBeats(song: Song): number {
  return beatsPerBar(song.meter)
}
