/**
 * SOUND_UPGRADE §6.2: the ABC subset every song is written in. Headers X T M L Q K V P; notes C–B c–b with
 * , and ' octaves; accidentals ^ ^^ _ __ = lasting to the bar line; durations A2 A/2 A/ A3/2 and broken
 * rhythm A>B A<B; rests z x; ties -; chords [CEG]; triplets (3abc; grace notes {g}; chord symbols "Dm7" (in a
 * `V:chords` voice of rests); dynamics !pp!…!f! and !crescendo(! … !crescendo)!; bar lines | || |] [|; repeats
 * |: :| :: with endings [1 [2; inline [K:] [M:] [Q:] [P:]; comments %. Anything else throws with line:column.
 *
 * Output is in quarter-note beats from the start of each bar, per voice, per section ([P:name]). Pure.
 */

export type Mode = 'ionian' | 'dorian' | 'phrygian' | 'lydian' | 'mixolydian' | 'aeolian' | 'locrian'

export interface KeySig {
  /** Tonic pitch class 0–11 (C = 0). */
  tonic: number
  mode: Mode
  /** Accidental per letter A–G (−1, 0, 1), after the mode and any explicit accidentals. */
  accidentals: Record<string, number>
  /** The ABC text of the key, as written. */
  text: string
}

export interface NoteEvent {
  /** Start, in quarter-note beats from the bar's start. */
  t: number
  /** Length in quarter-note beats. */
  dur: number
  /** MIDI pitches; empty for a rest. */
  pitches: number[]
  /** Tied into the next event (same pitch). */
  tie: boolean
  /** Grace pitches played just before the note. */
  grace?: number[]
  /** 0..1 from the dynamics marks (mf = 0.6). */
  vel: number
  /** A chord symbol that starts here (chords voice). */
  chord?: string
}

export interface Bar {
  events: NoteEvent[]
  /** Length in quarter-note beats as written. */
  length: number
  /** The meter in force. */
  meter: [number, number]
}

export interface Section {
  name: string
  bars: Bar[]
}

export interface Voice {
  id: string
  sections: Section[]
}

export interface Tune {
  meter: [number, number]
  /** Quarter-note BPM (Q:3/8=60 → 90). */
  bpm: number
  /** The Q: header as written, e.g. "3/8=60". */
  tempoText: string
  key: KeySig
  voices: Voice[]
  /** Section names in the order they first appear. */
  sections: string[]
}

export class AbcError extends Error {
  line: number
  col: number
  constructor(message: string, line: number, col: number) {
    super(`${message} (line ${line}, col ${col})`)
    this.line = line
    this.col = col
  }
}

const LETTER_PC: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }
const MODE_NAMES: Record<string, Mode> = {
  '': 'ionian',
  maj: 'ionian',
  major: 'ionian',
  ion: 'ionian',
  ionian: 'ionian',
  dor: 'dorian',
  dorian: 'dorian',
  phr: 'phrygian',
  phrygian: 'phrygian',
  lyd: 'lydian',
  lydian: 'lydian',
  mix: 'mixolydian',
  mixolydian: 'mixolydian',
  aeo: 'aeolian',
  aeolian: 'aeolian',
  min: 'aeolian',
  minor: 'aeolian',
  m: 'aeolian',
  loc: 'locrian',
  locrian: 'locrian',
}
/** Semitone steps of each mode from its tonic. */
export const MODE_STEPS: Record<Mode, number[]> = {
  ionian: [0, 2, 4, 5, 7, 9, 11],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  phrygian: [0, 1, 3, 5, 7, 8, 10],
  lydian: [0, 2, 4, 6, 7, 9, 11],
  mixolydian: [0, 2, 4, 5, 7, 9, 10],
  aeolian: [0, 2, 3, 5, 7, 8, 10],
  locrian: [0, 1, 3, 5, 6, 8, 10],
}
const DYNAMICS: Record<string, number> = { ppp: 0.15, pp: 0.25, p: 0.38, mp: 0.5, mf: 0.62, f: 0.78, ff: 0.9, fff: 1 }

/** Parses "D lyd", "Am", "A phr ^c", "C min =b". */
export function parseKey(text: string): KeySig {
  const m = /^\s*([A-G])([#b]?)\s*([A-Za-z]*)\s*(.*)$/.exec(text)
  if (!m) throw new Error(`bad key ${text}`)
  const tonic = (LETTER_PC[m[1]!]! + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) + 12) % 12
  const modeWord = m[3]!.toLowerCase()
  const mode = MODE_NAMES[modeWord]
  if (mode === undefined) throw new Error(`unknown mode ${m[3]}`)
  // Key signature from the mode: which letters carry which accidental.
  const accidentals: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, E: 0, F: 0, G: 0 }
  const letters = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
  const tonicLetterIndex = letters.indexOf(m[1]!)
  const steps = MODE_STEPS[mode]
  for (let d = 0; d < 7; d++) {
    const letter = letters[(tonicLetterIndex + d) % 7]!
    const wantPc = (tonic + steps[d]!) % 12
    const naturalPc = LETTER_PC[letter]!
    let diff = ((wantPc - naturalPc + 18) % 12) - 6
    if (diff > 2 || diff < -2) throw new Error(`key ${text} needs a double accidental on ${letter}`)
    accidentals[letter] = diff
  }
  // Explicit accidentals, as in ABC 2.1 (K:A phr ^c).
  for (const tok of m[4]!.split(/\s+/).filter(Boolean)) {
    const am = /^(\^\^|\^|__|_|=)([A-Ga-g])$/.exec(tok)
    if (!am) throw new Error(`bad key accidental ${tok}`)
    accidentals[am[2]!.toUpperCase()] = am[1] === '^' ? 1 : am[1] === '^^' ? 2 : am[1] === '_' ? -1 : am[1] === '__' ? -2 : 0
  }
  return { tonic, mode, accidentals, text: text.trim() }
}

/** Scale degrees (0–6) → pitch classes of a key. */
export function scaleOf(key: KeySig): number[] {
  const letters = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
  const tonicLetter = letters.find((l) => (LETTER_PC[l]! + key.accidentals[l]! + 12) % 12 === key.tonic) ?? letters[0]!
  const start = letters.indexOf(tonicLetter)
  return Array.from({ length: 7 }, (_, d) => {
    const l = letters[(start + d) % 7]!
    return (LETTER_PC[l]! + key.accidentals[l]! + 12) % 12
  })
}

function parseFraction(text: string, what: string): [number, number] {
  const m = /^\s*(\d+)\s*\/\s*(\d+)\s*$/.exec(text)
  if (text.trim() === 'C') return [4, 4]
  if (text.trim() === 'C|') return [2, 2]
  if (!m) throw new Error(`bad ${what} ${text}`)
  return [Number(m[1]), Number(m[2])]
}

interface Cursor {
  src: string
  i: number
  line: number
  col: number
}

function err(c: Cursor, msg: string): AbcError {
  return new AbcError(msg, c.line, c.col)
}

function peek(c: Cursor, n = 0): string {
  return c.src[c.i + n] ?? ''
}

function advance(c: Cursor, n = 1): string {
  let out = ''
  for (let k = 0; k < n; k++) {
    const ch = c.src[c.i] ?? ''
    out += ch
    c.i++
    if (ch === '\n') {
      c.line++
      c.col = 1
    } else c.col++
  }
  return out
}

interface VoiceState {
  id: string
  sections: Section[]
  current: Section | null
  bar: Bar
  barIndex: number
  /** Accidentals set in this bar, keyed by letter+octave. */
  barAccidentals: Map<string, number>
  t: number
  vel: number
  cresc: { from: number; startIndex: number; events: NoteEvent[] } | null
  pendingChord: string | null
  pendingGrace: number[] | null
  tieNext: boolean
  broken: number
  tuplet: { n: number; left: number } | null
  /** For repeats: the bar index where the repeat body started, and where its first ending started. */
  repeatStart: number
  firstEndingStart: number | null
  meter: [number, number]
  unit: number
  key: KeySig
  bpm: number
  tempoText: string
}

/**
 * Parses one tune. Every voice must declare sections with [P:name] before its notes (a tune without any
 * [P:] gets one section named "A").
 */
export function parseAbc(src: string): Tune {
  const c: Cursor = { src, i: 0, line: 1, col: 1 }
  let meter: [number, number] = [4, 4]
  let unit = 1 / 8
  let bpm = 120
  let tempoText = '1/4=120'
  let key: KeySig = parseKey('C')
  let unitSet = false
  const voices = new Map<string, VoiceState>()
  let voice: VoiceState | null = null
  const sectionOrder: string[] = []

  const applyTempo = (text: string, at: Cursor) => {
    const m = /^\s*(\d+)\s*\/\s*(\d+)\s*=\s*(\d+)\s*$/.exec(text)
    if (!m) throw err(at, `bad tempo ${text}`)
    const beat = Number(m[1]) / Number(m[2])
    bpm = Number(m[3]) * (beat / 0.25)
    tempoText = text.trim()
  }

  const newBar = (v: VoiceState): Bar => ({ events: [], length: 0, meter: v.meter })

  const barBeats = (m: [number, number]) => (m[0] / m[1]) * 4

  const startSection = (v: VoiceState, name: string, at: Cursor) => {
    closeBar(v, at, true)
    if (v.sections.some((s) => s.name === name)) throw err(at, `section ${name} appears twice in voice ${v.id}`)
    const s: Section = { name, bars: [] }
    v.sections.push(s)
    v.current = s
    v.barIndex = 0
    v.repeatStart = 0
    v.firstEndingStart = null
    if (!sectionOrder.includes(name)) sectionOrder.push(name)
  }

  const closeBar = (v: VoiceState, at: Cursor, sectionEnd: boolean) => {
    if (v.bar.events.length === 0 && v.bar.length === 0) return
    if (!v.current) throw err(at, `notes before any [P:section] in voice ${v.id}`)
    const want = barBeats(v.bar.meter)
    const got = v.bar.length
    const isPickup = v.current.bars.length === 0 && got < want - 1e-6
    if (Math.abs(got - want) > 1e-6 && !isPickup) throw err(at, `bar ${v.current.bars.length + 1} of ${v.id}/${v.current.name} has ${got} beats, the meter wants ${want}`)
    v.current.bars.push(v.bar)
    v.bar = newBar(v)
    v.t = 0
    v.barAccidentals.clear()
    void sectionEnd
  }

  const pitchOf = (v: VoiceState, letter: string, acc: string | null, octaveMarks: string, at: Cursor): number => {
    const upper = letter.toUpperCase()
    let octave = letter === upper ? 4 : 5
    for (const ch of octaveMarks) octave += ch === "'" ? 1 : -1
    const keyOf = `${upper}${octave}`
    let alter: number
    if (acc !== null) {
      alter = acc === '^' ? 1 : acc === '^^' ? 2 : acc === '_' ? -1 : acc === '__' ? -2 : 0
      v.barAccidentals.set(keyOf, alter)
    } else if (v.barAccidentals.has(keyOf)) alter = v.barAccidentals.get(keyOf)!
    else alter = v.key.accidentals[upper] ?? 0
    const midi = 12 * (octave + 1) + LETTER_PC[upper]! + alter
    if (midi < 0 || midi > 127) throw err(at, `note out of range`)
    return midi
  }

  const readDuration = (v: VoiceState): number => {
    // numerator?
    let num = 1
    let den = 1
    let digits = ''
    while (/\d/.test(peek(c))) digits += advance(c)
    if (digits) num = Number(digits)
    if (peek(c) === '/') {
      advance(c)
      let d = ''
      while (/\d/.test(peek(c))) d += advance(c)
      if (d) den = Number(d)
      else {
        den = 2
        while (peek(c) === '/') {
          advance(c)
          den *= 2
        }
      }
    }
    let beats = (num / den) * v.unit * 4
    if (v.broken !== 0) {
      beats *= v.broken > 0 ? 1.5 : 0.5
      v.broken = 0
    }
    if (peek(c) === '>' || peek(c) === '<') {
      const ch = advance(c)
      beats *= ch === '>' ? 1.5 : 0.5
      v.broken = ch === '>' ? -1 : 1
    }
    if (v.tuplet) {
      beats *= 2 / v.tuplet.n
      v.tuplet.left--
      if (v.tuplet.left === 0) v.tuplet = null
    }
    return beats
  }

  const pushEvent = (v: VoiceState, pitches: number[], dur: number) => {
    const ev: NoteEvent = { t: v.t, dur, pitches, tie: false, vel: v.vel }
    if (v.pendingChord !== null) {
      ev.chord = v.pendingChord
      v.pendingChord = null
    }
    if (v.pendingGrace) {
      ev.grace = v.pendingGrace
      v.pendingGrace = null
    }
    if (v.tieNext) {
      const prev = lastEvent(v)
      if (prev) prev.tie = true
      v.tieNext = false
    }
    v.bar.events.push(ev)
    if (v.cresc) v.cresc.events.push(ev)
    v.t += dur
    v.bar.length += dur
  }

  const lastEvent = (v: VoiceState): NoteEvent | null => {
    if (v.bar.events.length) return v.bar.events[v.bar.events.length - 1]!
    const bars = v.current?.bars ?? []
    for (let b = bars.length - 1; b >= 0; b--) if (bars[b]!.events.length) return bars[b]!.events[bars[b]!.events.length - 1]!
    return null
  }

  const makeVoice = (id: string): VoiceState => ({
    id,
    sections: [],
    current: null,
    bar: { events: [], length: 0, meter },
    barIndex: 0,
    barAccidentals: new Map(),
    t: 0,
    vel: DYNAMICS.mf!,
    cresc: null,
    pendingChord: null,
    pendingGrace: null,
    tieNext: false,
    broken: 0,
    tuplet: null,
    repeatStart: 0,
    firstEndingStart: null,
    meter,
    unit,
    key,
    bpm,
    tempoText,
  })

  const headerLine = (name: string, value: string, at: Cursor) => {
    switch (name) {
      case 'X':
      case 'T':
        return
      case 'M':
        meter = parseFraction(value, 'meter')
        if (voice) voice.meter = meter
        if (!unitSet) unit = meter[0] / meter[1] < 0.75 ? 1 / 16 : 1 / 8
        return
      case 'L':
        unit = (() => {
          const [n, d] = parseFraction(value, 'unit length')
          return n / d
        })()
        unitSet = true
        if (voice) voice.unit = unit
        return
      case 'Q':
        applyTempo(value, at)
        if (voice) {
          voice.bpm = bpm
          voice.tempoText = tempoText
        }
        return
      case 'K':
        try {
          key = parseKey(value)
        } catch (e) {
          throw err(at, (e as Error).message)
        }
        if (voice) voice.key = key
        return
      case 'V': {
        const id = value.trim().split(/\s+/)[0]!
        if (!id) throw err(at, 'V: needs a name')
        if (voice) closeBar(voice, at, true)
        let v = voices.get(id)
        if (!v) {
          v = makeVoice(id)
          voices.set(id, v)
        }
        voice = v
        return
      }
      case 'P': {
        if (!voice) throw err(at, 'P: before any V: voice')
        startSection(voice, value.trim(), at)
        return
      }
      default:
        throw err(at, `unsupported header ${name}:`)
    }
  }

  while (c.i < src.length) {
    const ch = peek(c)
    // Line starts: headers and comments.
    if (c.col === 1) {
      if (ch === '%') {
        while (c.i < src.length && peek(c) !== '\n') advance(c)
        continue
      }
      const hm = /^([A-Za-z]):([^\n]*)/.exec(src.slice(c.i))
      if (hm && /^[XTMLQKVP]$/.test(hm[1]!)) {
        const at = { ...c }
        advance(c, hm[0].length)
        headerLine(hm[1]!, hm[2]!, at)
        continue
      }
    }
    if (ch === '\n' || ch === ' ' || ch === '\t' || ch === '\r') {
      advance(c)
      continue
    }
    if (ch === '%') {
      while (c.i < src.length && peek(c) !== '\n') advance(c)
      continue
    }
    if (!voice) throw err(c, 'music before any V: voice')
    const v: VoiceState = voice
    const at = { ...c }
    // Inline fields.
    if (ch === '[' && /^\[[KMQP]:/.test(src.slice(c.i, c.i + 3))) {
      const end = src.indexOf(']', c.i)
      if (end < 0) throw err(c, 'unclosed inline field')
      const inner = src.slice(c.i + 1, end)
      advance(c, end - c.i + 1)
      const name = inner[0]!
      const value = inner.slice(2)
      if (name === 'P') startSection(v, value.trim(), at)
      else if (name === 'K') {
        try {
          v.key = parseKey(value)
        } catch (e) {
          throw err(at, (e as Error).message)
        }
        key = v.key
      } else if (name === 'M') {
        v.meter = parseFraction(value, 'meter')
        if (v.bar.events.length === 0) v.bar.meter = v.meter
        else throw err(at, 'meter change inside a bar')
      } else {
        applyTempo(value, at)
        v.bpm = bpm
        v.tempoText = tempoText
      }
      continue
    }
    // Endings [1 [2
    if (ch === '[' && /^\[\d/.test(src.slice(c.i, c.i + 2))) {
      advance(c)
      const n = Number(advance(c))
      closeBar(v, at, false)
      if (n === 1) v.firstEndingStart = v.current?.bars.length ?? 0
      continue
    }
    // Bar lines and repeats.
    if (ch === '|' || ch === ':') {
      let tok = ''
      while (/[|:\]\[]/.test(peek(c)) && tok.length < 3) {
        if (peek(c) === '[' && /^\[[KMQP\d]/.test(src.slice(c.i, c.i + 2))) break
        tok += advance(c)
      }
      if (tok === '|' || tok === '||' || tok === '|]' || tok === '[|') {
        closeBar(v, at, false)
        continue
      }
      if (tok === '|:') {
        closeBar(v, at, false)
        v.repeatStart = v.current?.bars.length ?? 0
        v.firstEndingStart = null
        continue
      }
      if (tok === ':|' || tok === '::' || tok === ':|]') {
        closeBar(v, at, false)
        // Replay the repeat body (the bars before any first ending); the second ending then follows.
        const cur = v.current
        if (!cur) throw err(at, 'repeat before any section')
        const bodyEnd = v.firstEndingStart ?? cur.bars.length
        const body = cur.bars.slice(v.repeatStart, bodyEnd)
        for (const b of body) cur.bars.push(cloneBar(b))
        v.repeatStart = cur.bars.length
        v.firstEndingStart = null
        continue
      }
      throw err(at, `unsupported bar line ${tok}`)
    }
    // Chord symbol "Dm7"
    if (ch === '"') {
      advance(c)
      let s = ''
      while (c.i < src.length && peek(c) !== '"') s += advance(c)
      if (peek(c) !== '"') throw err(at, 'unclosed chord symbol')
      advance(c)
      v.pendingChord = s
      continue
    }
    // Dynamics and decorations
    if (ch === '!') {
      advance(c)
      let s = ''
      while (c.i < src.length && peek(c) !== '!') s += advance(c)
      if (peek(c) !== '!') throw err(at, 'unclosed ! decoration')
      advance(c)
      if (DYNAMICS[s] !== undefined) {
        if (v.cresc) {
          finishRamp(v, DYNAMICS[s]!)
        }
        v.vel = DYNAMICS[s]!
        continue
      }
      if (s === 'crescendo(' || s === 'diminuendo(') {
        v.cresc = { from: v.vel, startIndex: 0, events: [] }
        continue
      }
      if (s === 'crescendo)' || s === 'diminuendo)') {
        // The ramp ends at the next dynamic mark; until then it holds the events.
        if (!v.cresc) throw err(at, `${s} without a start`)
        v.cresc.startIndex = -1
        continue
      }
      throw err(at, `unsupported decoration !${s}!`)
    }
    // Grace notes {g}
    if (ch === '{') {
      advance(c)
      const grace: number[] = []
      while (c.i < src.length && peek(c) !== '}') {
        if (peek(c) === ' ') {
          advance(c)
          continue
        }
        const n = readNoteToken(c, v, at)
        if (!n) throw err(c, 'bad grace note')
        grace.push(n)
        while (/[\d/]/.test(peek(c))) advance(c)
      }
      if (peek(c) !== '}') throw err(at, 'unclosed grace group')
      advance(c)
      v.pendingGrace = grace
      continue
    }
    // Triplets (3
    if (ch === '(' && /^\(\d/.test(src.slice(c.i, c.i + 2))) {
      advance(c)
      const n = Number(advance(c))
      if (n !== 3) throw err(at, 'only (3 triplets are supported')
      v.tuplet = { n, left: n }
      continue
    }
    // Chord [CEG]
    if (ch === '[') {
      advance(c)
      const pitches: number[] = []
      while (c.i < src.length && peek(c) !== ']') {
        if (peek(c) === ' ') {
          advance(c)
          continue
        }
        const n = readNoteToken(c, v, at)
        if (n === null) throw err(c, 'bad note in chord')
        pitches.push(n)
        // Durations inside a chord are ignored; the chord's duration follows the bracket.
        while (/[\d/]/.test(peek(c))) advance(c)
      }
      if (peek(c) !== ']') throw err(at, 'unclosed chord')
      advance(c)
      const dur = readDuration(v)
      pushEvent(v, pitches, dur)
      continue
    }
    // Rests
    if (ch === 'z' || ch === 'x') {
      advance(c)
      const dur = readDuration(v)
      pushEvent(v, [], dur)
      continue
    }
    // Tie
    if (ch === '-') {
      advance(c)
      v.tieNext = true
      continue
    }
    // Notes
    const n = readNoteToken(c, v, at)
    if (n !== null) {
      const dur = readDuration(v)
      pushEvent(v, [n], dur)
      continue
    }
    throw err(at, `unsupported symbol '${ch}'`)
  }
  for (const v of voices.values()) closeBar(v, c, true)

  function readNoteToken(cur: Cursor, v: VoiceState, at: Cursor): number | null {
    let acc: string | null = null
    const two = src.slice(cur.i, cur.i + 2)
    if (two === '^^' || two === '__') acc = advance(cur, 2)
    else if (/^[\^_=]/.test(two)) acc = advance(cur)
    const letter = peek(cur)
    if (!/^[A-Ga-g]$/.test(letter)) {
      if (acc !== null) throw err(at, 'accidental without a note')
      return null
    }
    advance(cur)
    let marks = ''
    while (peek(cur) === "'" || peek(cur) === ',') marks += advance(cur)
    return pitchOf(v, letter, acc, marks, at)
  }

  function finishRamp(v: VoiceState, to: number) {
    const ramp = v.cresc!
    const n = ramp.events.length
    ramp.events.forEach((ev, i) => {
      ev.vel = ramp.from + ((to - ramp.from) * (i + 1)) / Math.max(1, n)
    })
    v.cresc = null
  }

  function cloneBar(b: Bar): Bar {
    return { events: b.events.map((e) => ({ ...e, pitches: [...e.pitches], grace: e.grace ? [...e.grace] : undefined })), length: b.length, meter: b.meter }
  }

  if (voices.size === 0) throw new AbcError('no voices', 1, 1)
  const out: Voice[] = []
  for (const v of voices.values()) {
    if (v.sections.length === 0) throw new AbcError(`voice ${v.id} has no [P:section]`, 1, 1)
    out.push({ id: v.id, sections: v.sections })
  }
  // Every voice has the same length in each section.
  for (const name of sectionOrder) {
    const lengths = new Map<string, number>()
    for (const v of out) {
      const s = v.sections.find((x) => x.name === name)
      if (!s) throw new AbcError(`voice ${v.id} has no section ${name}`, 1, 1)
      lengths.set(v.id, s.bars.reduce((sum, b) => sum + b.length, 0))
    }
    const vals = [...lengths.values()]
    if (vals.some((l) => Math.abs(l - vals[0]!) > 1e-6)) throw new AbcError(`section ${name}: voices differ in length (${[...lengths.entries()].map(([k, l]) => `${k}=${l}`).join(', ')})`, 1, 1)
  }
  return { meter, bpm, tempoText, key, voices: out, sections: sectionOrder }
}

/** Quarter-note beats per bar for a meter. */
export function beatsPerBar(meter: readonly [number, number]): number {
  return (meter[0] / meter[1]) * 4
}

/** True for compound meters (6/8, 9/8, 12/8): the beat is a dotted quarter. */
export function isCompound(meter: readonly [number, number]): boolean {
  return meter[1] === 8 && meter[0] % 3 === 0 && meter[0] >= 6
}

/** Strong beats of a bar in quarter-note beats (4/4: 0 and 2; 3/4: 0; 6/8: 0 and 1.5; 2/4: 0). */
export function strongBeats(meter: readonly [number, number]): number[] {
  if (isCompound(meter)) return Array.from({ length: meter[0] / 3 }, (_, i) => i * 1.5)
  if (meter[0] === 4 && meter[1] === 4) return [0, 2]
  if (meter[0] === 2 && meter[1] === 2) return [0, 2]
  return [0]
}

export function midiName(midi: number): string {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  return `${names[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`
}
