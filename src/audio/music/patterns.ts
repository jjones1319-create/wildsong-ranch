/**
 * SOUND_UPGRADE §6.3: the accompaniment generators. Input: the chord track, the meter, the instrument's
 * range, a pattern name and its parameters. Output: note events per bar. The voicing moves as little as
 * possible from chord to chord, stays inside the range and keeps the root (or the slash bass) at the bottom.
 * Pure and deterministic; the only randomness (strum timing jitter) comes from the caller's audio RNG.
 */
import { beatsPerBar, isCompound } from './abc.ts'
import { chordAt, voiceChord, type Chord, type ChordAt } from './chords.ts'

export const PATTERN_IDS = ['harpArp', 'waltz', 'strum', 'pizzWalk', 'kalimbaOstinato', 'padSustain', 'pulse', 'tremolo', 'bassRoot', 'drone', 'flourish'] as const
export type PatternId = (typeof PATTERN_IDS)[number]

export interface PatternParams {
  /** The octave number of the voicing's floor (3 → C3 = 48). */
  octave?: number
  density?: 'sparse' | 'normal' | 'busy'
  spread?: 'close' | 'open'
  /** The instrument's playable range, sounding MIDI. */
  range: readonly [number, number]
  /** Voices in a chord voicing (bass included). */
  size?: number
  /** bassRoot: alternate the root with its octave. */
  octaveJumps?: boolean
}

export interface GenEvent {
  bar: number
  /** Beats from the bar start. */
  t: number
  dur: number
  pitches: number[]
  vel: number
  /** Tied into the next event of the same line. */
  tie?: boolean
  /** Milliseconds between the strings of a strummed chord. */
  strumMs?: number
}

const DEFAULT_VEL = 0.5

function floorOf(params: PatternParams): number {
  const octave = params.octave ?? 3
  return Math.max(params.range[0], 12 * (octave + 1))
}

function clampRange(midi: number, range: readonly [number, number]): number {
  let m = midi
  while (m < range[0]) m += 12
  while (m > range[1]) m -= 12
  return m
}

/** Chord tones as an ascending ladder above the bass, up to `top` (default two octaves above the bass). */
function ladder(chord: Chord, bass: number, count: number, top = bass + 24): number[] {
  const pcs = chord.intervals.map((i) => (chord.root + i) % 12)
  const out: number[] = []
  let m = bass
  while (out.length < count) {
    m++
    if (m > top) break
    if (pcs.includes(((m % 12) + 12) % 12)) out.push(m)
  }
  return out
}

/** Four rising tones above the bass for an arpeggio, reusing tones when the chord has few inside the span. */
function fourUp(tones: readonly number[], open: boolean): [number, number, number, number] {
  const pool = open && tones.length >= 5 ? [tones[1]!, tones[2]!, tones[3]!, tones[4]!] : tones.length >= 4 ? [tones[0]!, tones[1]!, tones[2]!, tones[3]!] : tones
  const out: number[] = []
  for (let i = 0; out.length < 4 && pool.length > 0; i++) out.push(pool[i % pool.length]!)
  while (out.length < 4) out.push(out[out.length - 1] ?? 60)
  return [out[0]!, out[1]!, out[2]!, out[3]!]
}

function chordsInBar(track: readonly ChordAt[], bar: number, beats: number): { beat: number; chord: Chord; until: number }[] {
  const starts = track.filter((c) => c.bar === bar).map((c) => c.beat)
  const first = chordAt(track, bar, 0)
  if (!first) return []
  const points = [...new Set([0, ...starts])].sort((a, b) => a - b)
  return points.map((beat, i) => ({ beat, chord: chordAt(track, bar, beat) ?? first, until: points[i + 1] ?? beats }))
}

/** Generates the events of one pattern over `bars` bars. */
export function generate(pattern: PatternId, track: readonly ChordAt[], bars: number, meter: readonly [number, number], params: PatternParams): GenEvent[] {
  const beats = beatsPerBar(meter)
  const compound = isCompound(meter)
  const floor = floorOf(params)
  const ceiling = params.range[1]
  const size = params.size ?? 3
  const out: GenEvent[] = []
  let previous: number[] | null = null
  const voicing = (chord: Chord): number[] => {
    const v = voiceChord(chord, floor, Math.min(ceiling, floor + 24), previous, size)
    previous = v
    return v
  }
  const push = (e: GenEvent) => {
    if (e.pitches.every((p) => p >= params.range[0] && p <= params.range[1])) out.push(e)
    else out.push({ ...e, pitches: e.pitches.map((p) => clampRange(p, params.range)) })
  }

  for (let bar = 0; bar < bars; bar++) {
    const segments = chordsInBar(track, bar, beats)
    if (segments.length === 0) continue
    switch (pattern) {
      case 'harpArp': {
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const bass = v[0]!
          // The arpeggio stays within two octaves above the pattern's floor, so a high bass note does not push it up.
          const tones = ladder(seg.chord, bass, 6, floor + 24)
          const [u0, u1, u2, u3] = fourUp(tones, params.spread !== 'close')
          // 1-5-8-10 rising then falling (open) or 1-3-5-8 (close), in eighths.
          const open = [bass, u0, u1, u2, u3, u2, u1, u0]
          const len = seg.until - seg.beat
          const eighth = 0.5
          const n = Math.round(len / eighth)
          const shape = compound || n === 6 ? [bass, u0, u1, u2, u1, u0] : open
          for (let i = 0; i < n; i++) {
            const t = seg.beat + i * eighth
            const strong = i === 0
            push({ bar, t, dur: eighth * 0.95, pitches: [shape[i % shape.length]!], vel: strong ? DEFAULT_VEL + 0.1 : DEFAULT_VEL - (i % 2 ? 0.08 : 0) })
          }
        }
        break
      }
      case 'waltz': {
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const len = seg.until - seg.beat
          const perBeat = compound ? 1.5 : 1
          const n = Math.round(len / perBeat)
          for (let i = 0; i < n; i++) {
            const t = seg.beat + i * perBeat
            const isBass = i === 0 || (meter[0] === 4 && i === 2)
            if (isBass) push({ bar, t, dur: perBeat * 0.9, pitches: [v[0]!], vel: DEFAULT_VEL + 0.1 })
            else push({ bar, t, dur: perBeat * 0.6, pitches: v.slice(1), vel: DEFAULT_VEL - 0.05 })
          }
        }
        break
      }
      case 'strum': {
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const len = seg.until - seg.beat
          const slots: { at: number; up: boolean }[] = []
          if (compound) for (let b = 0; b < len; b += 1.5) slots.push({ at: b, up: false }, { at: b + 1, up: true })
          else {
            for (let b = 0; b < len; b += 1) {
              slots.push({ at: b, up: false })
              if (params.density === 'busy') slots.push({ at: b + 0.5, up: true })
              else if (params.density !== 'sparse' && b % 2 === 1) slots.push({ at: b + 0.5, up: true })
            }
          }
          for (const s of slots) {
            if (s.at >= len) continue
            const pitches = s.up ? [...v].reverse() : [...v]
            push({ bar, t: seg.beat + s.at, dur: Math.min(0.9, len - s.at), pitches, vel: s.up ? DEFAULT_VEL - 0.12 : s.at === 0 ? DEFAULT_VEL + 0.08 : DEFAULT_VEL, strumMs: 15 })
          }
        }
        break
      }
      case 'pizzWalk': {
        const perBeat = compound ? 1.5 : 1
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const root = v[0]!
          const tones = ladder(seg.chord, root, 4)
          const fifth = tones.find((m) => (m - root) % 12 === 7) ?? tones[1]!
          const third = tones[0]!
          const sixth = root + 9
          const len = seg.until - seg.beat
          const n = Math.max(1, Math.round(len / perBeat))
          const shape = bar % 2 === 0 ? [root, fifth, sixth, fifth] : [root, third, fifth, sixth]
          for (let i = 0; i < n; i++) {
            let pitch = shape[i % shape.length]!
            // Approach note into the next chord on the last beat of the bar.
            if (i === n - 1 && seg.until >= beats - 1e-6) {
              const next = chordAt(track, bar + 1, 0)
              if (next && next.bass !== seg.chord.bass) {
                const nextBass = clampRange(floor + (((next.bass - floor) % 12) + 12) % 12, params.range)
                pitch = nextBass - 1 > root ? nextBass - 1 : nextBass + 2
              }
            }
            push({ bar, t: seg.beat + i * perBeat, dur: perBeat * 0.8, pitches: [pitch], vel: i === 0 ? DEFAULT_VEL + 0.1 : DEFAULT_VEL })
          }
        }
        break
      }
      case 'kalimbaOstinato': {
        // Chord tones in syncopated sixteenths, 3+3+2 per half bar.
        const sixteenth = 0.25
        const hits = [0, 3, 6, 8, 11, 14]
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const tones = [v[0]!, ...ladder(seg.chord, v[0]!, 4)]
          const cycle = [tones[0]!, tones[2]!, tones[1]!, tones[3]!, tones[2]!, tones[1]!]
          const len = seg.until - seg.beat
          const grid = Math.round(len / sixteenth)
          let k = 0
          for (const h of hits) {
            if (h >= grid) break
            push({ bar, t: seg.beat + h * sixteenth, dur: sixteenth * 2, pitches: [cycle[k % cycle.length]!], vel: h === 0 || h === 8 ? DEFAULT_VEL + 0.08 : DEFAULT_VEL - 0.05 })
            k++
          }
        }
        break
      }
      case 'padSustain':
      case 'tremolo': {
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const next = chordAt(track, bar + 1, 0)
          const holds = seg.until >= beats - 1e-6 && next !== null && next.text === seg.chord.text && bar + 1 < bars
          push({ bar, t: seg.beat, dur: seg.until - seg.beat, pitches: v, vel: DEFAULT_VEL - 0.1, tie: holds })
        }
        break
      }
      case 'pulse': {
        const eighth = 0.5
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const n = Math.round((seg.until - seg.beat) / eighth)
          for (let i = 0; i < n; i++) {
            const pitches = i % 2 === 0 ? [v[0]!] : v.slice(1, 3)
            push({ bar, t: seg.beat + i * eighth, dur: eighth * 0.6, pitches, vel: i % 4 === 0 ? DEFAULT_VEL + 0.15 : DEFAULT_VEL })
          }
        }
        break
      }
      case 'bassRoot': {
        for (const seg of segments) {
          const v = voicing(seg.chord)
          const root = v[0]!
          const len = seg.until - seg.beat
          const slots = compound ? [0] : meter[0] === 4 && len >= 4 ? [0, 2] : [0]
          slots.forEach((s, i) => {
            const pitch = params.octaveJumps && i % 2 === 1 ? root + 12 : root
            push({ bar, t: seg.beat + s, dur: Math.min(len, 2) * 0.9, pitches: [clampRange(pitch, params.range)], vel: i === 0 ? DEFAULT_VEL + 0.1 : DEFAULT_VEL })
          })
        }
        break
      }
      case 'drone': {
        const first = segments[0]!.chord
        const tonic = clampRange(floor + (((first.root - floor) % 12) + 12) % 12, params.range)
        push({ bar, t: 0, dur: beats, pitches: [tonic, tonic + 7], vel: DEFAULT_VEL - 0.15, tie: bar + 1 < bars })
        break
      }
      case 'flourish': {
        if (bar !== bars - 1) break
        const seg = segments[segments.length - 1]!
        const v = voicing(seg.chord)
        const tones = [v[0]!, ...ladder(seg.chord, v[0]!, 5)]
        const sixteenth = 0.25
        const start = beats - 1
        // Bright colours stay at p or softer (§3.2), so the rise may touch the top octave.
        tones.slice(0, 4).forEach((p, i) => push({ bar, t: start + i * sixteenth, dur: i === 3 ? 1 : sixteenth, pitches: [p], vel: 0.25 + i * 0.03 }))
        break
      }
    }
  }
  return out
}
