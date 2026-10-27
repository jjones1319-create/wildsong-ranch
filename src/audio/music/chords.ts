/**
 * SOUND_UPGRADE §6.3: chord symbols from the `V:chords` voice ("Dm7", "G/B", "Csus2", "Fadd9") turned into
 * pitch classes, plus the chord track (which chord sounds at each beat of each bar) that the accompaniment
 * generators and the pitched percussion read. Pure.
 */
import type { Section } from './abc.ts'

export interface Chord {
  text: string
  /** Pitch class of the root, 0–11. */
  root: number
  /** Pitch class of the bass (the slash note, or the root). */
  bass: number
  /** Intervals above the root, in semitones, ascending. */
  intervals: number[]
}

const PC: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }

const QUALITIES: Record<string, number[]> = {
  '': [0, 4, 7],
  maj: [0, 4, 7],
  M: [0, 4, 7],
  m: [0, 3, 7],
  min: [0, 3, 7],
  dim: [0, 3, 6],
  aug: [0, 4, 8],
  '5': [0, 7],
  sus2: [0, 2, 7],
  sus4: [0, 5, 7],
  sus: [0, 5, 7],
  '6': [0, 4, 7, 9],
  m6: [0, 3, 7, 9],
  '7': [0, 4, 7, 10],
  maj7: [0, 4, 7, 11],
  M7: [0, 4, 7, 11],
  m7: [0, 3, 7, 10],
  min7: [0, 3, 7, 10],
  dim7: [0, 3, 6, 9],
  m7b5: [0, 3, 6, 10],
  '9': [0, 4, 7, 10, 14],
  maj9: [0, 4, 7, 11, 14],
  m9: [0, 3, 7, 10, 14],
  add9: [0, 4, 7, 14],
  madd9: [0, 3, 7, 14],
  '7sus4': [0, 5, 7, 10],
  '6/9': [0, 4, 7, 9, 14],
}

function pcOf(text: string): number {
  const m = /^([A-G])([#b]?)$/.exec(text)
  if (!m) throw new Error(`bad note ${text}`)
  return (PC[m[1]!]! + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) + 12) % 12
}

export function parseChord(text: string): Chord {
  const m = /^([A-G][#b]?)([^/]*)(?:\/([A-G][#b]?))?$/.exec(text.trim())
  if (!m) throw new Error(`bad chord symbol "${text}"`)
  const root = pcOf(m[1]!)
  const quality = m[2]!.trim()
  const intervals = QUALITIES[quality]
  if (!intervals) throw new Error(`unknown chord quality "${quality}" in "${text}"`)
  const bass = m[3] ? pcOf(m[3]) : root
  return { text: text.trim(), root, bass, intervals: [...intervals] }
}

export interface ChordAt {
  bar: number
  /** Quarter-note beats from the bar start. */
  beat: number
  chord: Chord
}

/** The chord track of a section: every chord symbol with its bar and beat, carrying the last chord forward. */
export function chordTrack(chords: Section, previous: Chord | null = null): { track: ChordAt[]; last: Chord | null } {
  const track: ChordAt[] = []
  let last = previous
  chords.bars.forEach((bar, b) => {
    let first = true
    for (const ev of bar.events) {
      if (ev.chord !== undefined) {
        last = parseChord(ev.chord)
        track.push({ bar: b, beat: ev.t, chord: last })
        first = false
      } else if (first && last && ev.t === 0) {
        // The bar carries the previous chord from its first beat.
        track.push({ bar: b, beat: 0, chord: last })
        first = false
      }
    }
    if (first && last) track.push({ bar: b, beat: 0, chord: last })
  })
  return { track, last }
}

/** The chord sounding at a bar and beat. */
export function chordAt(track: readonly ChordAt[], bar: number, beat: number): Chord | null {
  let best: ChordAt | null = null
  for (const c of track) {
    if (c.bar < bar || (c.bar === bar && c.beat <= beat + 1e-6)) best = c
    else if (c.bar > bar) break
  }
  return best?.chord ?? null
}

/** The chord's pitch classes. */
export function chordPcs(chord: Chord): number[] {
  return chord.intervals.map((i) => (chord.root + i) % 12)
}

export function isChordTone(chord: Chord, midi: number): boolean {
  return chordPcs(chord).includes(((midi % 12) + 12) % 12)
}

/**
 * Voices a chord inside [low, high] with the bass pitch class at the bottom and the other tones above it,
 * moving as little as possible from the previous voicing (by the sum of absolute moves).
 */
export function voiceChord(chord: Chord, low: number, high: number, previous: readonly number[] | null, size = 3): number[] {
  const pcs = chordPcs(chord).filter((pc) => pc !== chord.bass)
  // The bass: the lowest instance of the bass pitch class at or above `low`.
  let bass = low + (((chord.bass - low) % 12) + 12) % 12
  if (bass > high) bass = high
  const upper: number[] = []
  const wanted = pcs.slice(0, Math.max(0, size - 1))
  if (wanted.length === 0) return [bass]
  // Candidate voicings: every assignment of each wanted pitch class to an octave above the bass and ≤ high.
  const options = wanted.map((pc) => {
    const list: number[] = []
    for (let m = bass + 1; m <= high; m++) if (((m % 12) + 12) % 12 === pc) list.push(m)
    return list.length ? list : [bass + (((pc - bass) % 12) + 12) % 12]
  })
  let best: number[] | null = null
  let bestCost = Infinity
  const walk = (i: number, acc: number[]) => {
    if (i === options.length) {
      const sorted = [...acc].sort((a, b) => a - b)
      let cost = 0
      if (previous && previous.length > 1) {
        const prevUpper = previous.slice(1)
        for (let k = 0; k < sorted.length; k++) cost += Math.abs(sorted[k]! - (prevUpper[Math.min(k, prevUpper.length - 1)] ?? sorted[k]!))
      } else {
        // No history: keep the voicing close and low.
        cost = sorted[sorted.length - 1]! - bass
      }
      // Spread: never two upper voices on the same pitch.
      if (new Set(sorted).size !== sorted.length) cost += 100
      if (cost < bestCost) {
        bestCost = cost
        best = sorted
      }
      return
    }
    for (const m of options[i]!) walk(i + 1, [...acc, m])
  }
  walk(0, upper)
  return [bass, ...(best ?? [])]
}
