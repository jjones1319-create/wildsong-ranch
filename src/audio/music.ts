import { AUDIO } from '../data/tuning.ts'
import type { Season } from '../data/types.ts'

/**
 * GAME_DESIGN §23 music: nine short original loops written as step-sequencer patterns and rendered to
 * sample buffers by a tiny synth. Everything here is pure (no Web Audio), so the tracks are unit-tested
 * and rendered once, lazily, by the player. Sixteen steps make a bar; a token is a note name with its
 * octave (`c4`, `f#3`), `-` for a rest or `.` to hold the previous note.
 */

export const TRACK_IDS = ['ranchSpring', 'ranchSummer', 'ranchAutumn', 'ranchWinter', 'town', 'battle', 'victory', 'farewell', 'shrine'] as const
export type TrackId = (typeof TRACK_IDS)[number]

export type Wave = 'square' | 'triangle' | 'saw' | 'sine' | 'noise'

export interface Voice {
  wave: Wave
  /** 0–100. */
  volume: number
  /** Space-separated tokens, one per sixteenth step. */
  pattern: string
  /** Note release in steps: how much of each step the note sounds (1 = legato). */
  gate?: number
  /** Soft the attack (ms). */
  attackMs?: number
}

export interface Track {
  id: TrackId
  bpm: number
  loop: boolean
  voices: Voice[]
}

const NOTE_INDEX: Record<string, number> = { c: 0, d: 2, e: 4, f: 5, g: 7, a: 9, b: 11 }

/** `c4` → 60 (MIDI). Returns 0 for a rest, −1 for a hold. */
export function parseToken(token: string): number {
  if (token === '-') return 0
  if (token === '.') return -1
  const m = /^([a-g])(#|b)?(\d)$/.exec(token)
  if (!m) throw new Error(`bad note ${token}`)
  const semis = NOTE_INDEX[m[1]!]! + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0)
  return 12 * (Number(m[3]) + 1) + semis
}

export function parsePattern(pattern: string): number[] {
  return pattern.trim().split(/\s+/).map(parseToken)
}

export function midiToHz(midi: number): number {
  return 440 * 2 ** ((midi - 69) / 12)
}

/** Loop length in sixteenth steps: the longest voice (every voice repeats to fill it). */
export function stepsOf(track: Track): number {
  return Math.max(...track.voices.map((v) => parsePattern(v.pattern).length))
}

export function stepSeconds(bpm: number): number {
  return 60 / bpm / 4
}

/** Loop length in whole samples. */
export function sampleCount(track: Track, sampleRate: number = AUDIO.sampleRate): number {
  return Math.round(stepsOf(track) * stepSeconds(track.bpm) * sampleRate)
}

function osc(wave: Wave, phase: number, noise: () => number): number {
  const p = phase - Math.floor(phase)
  switch (wave) {
    case 'square':
      return p < 0.5 ? 1 : -1
    case 'triangle':
      return p < 0.5 ? 4 * p - 1 : 3 - 4 * p
    case 'saw':
      return 2 * p - 1
    case 'sine':
      return Math.sin(p * Math.PI * 2)
    case 'noise':
      return noise()
  }
}

/** A tiny seeded generator for the noise voice, so a render is identical every time. */
function lcg(seed: number): () => number {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 2147483648 - 1
  }
}

/**
 * Renders a whole loop to mono samples in [−1, 1]. Each voice is a simple oscillator with an attack,
 * a gate and a short release; voices are mixed and soft-clipped.
 */
export function renderTrack(track: Track, sampleRate: number = AUDIO.sampleRate): Float32Array {
  const steps = stepsOf(track)
  const stepLen = stepSeconds(track.bpm)
  const total = Math.round(steps * stepLen * sampleRate)
  const out = new Float32Array(total)
  const noise = lcg(7)
  for (const voice of track.voices) {
    const notes = parsePattern(voice.pattern)
    const gate = voice.gate ?? 0.85
    const attack = Math.max(1, Math.round(((voice.attackMs ?? 4) / 1000) * sampleRate))
    const release = Math.max(1, Math.round(0.03 * sampleRate))
    const gain = voice.volume / 100
    // Expand holds into (note, length) runs.
    const runs: { midi: number; start: number; len: number }[] = []
    for (let s = 0; s < steps; s++) {
      const n = notes[s % notes.length]!
      if (n === -1 && runs.length > 0 && runs[runs.length - 1]!.start + runs[runs.length - 1]!.len === s) {
        runs[runs.length - 1]!.len += 1
      } else if (n > 0) {
        runs.push({ midi: n, start: s, len: 1 })
      }
    }
    for (const run of runs) {
      const hz = midiToHz(run.midi)
      const from = Math.round(run.start * stepLen * sampleRate)
      const soundLen = Math.round(run.len * stepLen * sampleRate * gate)
      const to = Math.min(total, from + soundLen + release)
      let phase = 0
      for (let i = from; i < to; i++) {
        const t = i - from
        const env = t < attack ? t / attack : t < soundLen ? 1 : Math.max(0, 1 - (t - soundLen) / release)
        out[i] = out[i]! + osc(voice.wave, phase, noise) * env * gain
        phase += hz / sampleRate
      }
    }
  }
  for (let i = 0; i < total; i++) {
    const x = out[i]!
    out[i] = x / (1 + Math.abs(x) * 0.6)
  }
  return out
}

/* ---------- the tracks ---------- */

const rep = (s: string, n: number) => Array.from({ length: n }, () => s).join(' ')

export const TRACKS: Record<TrackId, Track> = {
  ranchSpring: {
    id: 'ranchSpring',
    bpm: 104,
    loop: true,
    voices: [
      {
        wave: 'square',
        volume: 22,
        pattern: ['c5 . e5 . g5 . e5 . a5 . g5 . e5 . d5 .', 'c5 . d5 . e5 . g5 . a5 . . . g5 . e5 .', 'd5 . e5 . g5 . a5 . c6 . a5 . g5 . e5 .', 'd5 . c5 . d5 . e5 . c5 . . . . . - -'].join(' '),
      },
      { wave: 'triangle', volume: 32, gate: 0.6, pattern: ['c3 - c3 - g3 - c3 - a2 - a2 - e3 - a2 -', 'f3 - f3 - c4 - f3 - g3 - g3 - d4 - g3 -'].join(' ') },
      { wave: 'noise', volume: 5, gate: 0.2, pattern: '- - c5 - - - c5 - - - c5 - - - c5 c5' },
    ],
  },
  ranchSummer: {
    id: 'ranchSummer',
    bpm: 118,
    loop: true,
    voices: [
      {
        wave: 'square',
        volume: 22,
        pattern: ['g5 . b5 . d6 . b5 . a5 . g5 . e5 . g5 .', 'a5 . b5 . a5 . g5 . e5 . . . d5 . e5 .', 'g5 . a5 . b5 . d6 . e6 . d6 . b5 . a5 .', 'g5 . a5 . g5 . e5 . d5 . . . . . - -'].join(' '),
      },
      { wave: 'triangle', volume: 32, gate: 0.55, pattern: ['g3 - d3 - g3 - d3 - e3 - b2 - e3 - b2 -', 'c3 - g3 - c3 - g3 - d3 - a3 - d3 - a3 -'].join(' ') },
      { wave: 'noise', volume: 6, gate: 0.2, pattern: 'c5 - - - c5 - c5 - c5 - - - c5 - c5 c5' },
    ],
  },
  ranchAutumn: {
    id: 'ranchAutumn',
    bpm: 92,
    loop: true,
    voices: [
      {
        wave: 'triangle',
        volume: 30,
        attackMs: 12,
        pattern: ['d5 . . . f5 . a5 . g5 . f5 . e5 . d5 .', 'c5 . . . e5 . g5 . f5 . e5 . d5 . c5 .', 'd5 . . . f5 . a5 . c6 . a5 . g5 . f5 .', 'e5 . . . d5 . c5 . d5 . . . . . - -'].join(' '),
      },
      { wave: 'square', volume: 14, gate: 0.9, pattern: ['a3 . . . . . . . f3 . . . . . . .', 'g3 . . . . . . . e3 . . . . . . .'].join(' ') },
      { wave: 'triangle', volume: 30, gate: 0.7, pattern: ['d3 - - - d3 - - - a2 - - - a2 - - -', 'c3 - - - c3 - - - g2 - - - g2 - - -'].join(' ') },
    ],
  },
  ranchWinter: {
    id: 'ranchWinter',
    bpm: 78,
    loop: true,
    voices: [
      {
        wave: 'sine',
        volume: 36,
        attackMs: 20,
        pattern: ['a5 . . . e5 . . . c5 . . . e5 . . .', 'b5 . . . e5 . . . d5 . . . e5 . . .', 'a5 . . . c6 . . . b5 . . . e5 . . .', 'd5 . . . c5 . . . b4 . . . . . . .'].join(' '),
      },
      { wave: 'triangle', volume: 26, gate: 0.95, attackMs: 30, pattern: ['a2 . . . . . . . . . . . . . . .', 'e2 . . . . . . . . . . . . . . .', 'a2 . . . . . . . . . . . . . . .', 'g2 . . . . . . . . . . . . . . .'].join(' ') },
      { wave: 'sine', volume: 12, gate: 0.3, pattern: ['- - - - - - - - a6 - - - - - - -', '- - - - e6 - - - - - - - - - - -'].join(' ') },
    ],
  },
  town: {
    id: 'town',
    bpm: 124,
    loop: true,
    voices: [
      {
        wave: 'square',
        volume: 20,
        pattern: ['f5 . a5 . c6 . a5 . g5 . f5 . e5 . f5 .', 'g5 . a5 . g5 . f5 . e5 . d5 . c5 . . .', 'f5 . a5 . c6 . d6 . c6 . a5 . g5 . a5 .', 'g5 . f5 . e5 . d5 . f5 . . . . . - -'].join(' '),
      },
      { wave: 'triangle', volume: 34, gate: 0.5, pattern: ['f3 - c4 - f3 - c4 - c3 - g3 - c3 - g3 -', 'b2 - f3 - b2 - f3 - c3 - g3 - c3 - g3 -'].join(' ') },
      { wave: 'square', volume: 8, gate: 0.4, pattern: ['- - a4 - - - a4 - - - g4 - - - g4 -', '- - f4 - - - f4 - - - g4 - - - g4 -'].join(' ') },
      { wave: 'noise', volume: 6, gate: 0.15, pattern: '- - c5 - - - c5 - - - c5 - - - c5 -' },
    ],
  },
  battle: {
    id: 'battle',
    bpm: 150,
    loop: true,
    voices: [
      {
        wave: 'saw',
        volume: 18,
        pattern: ['e5 . e5 . g5 . e5 . b5 . a5 . g5 . e5 .', 'd5 . d5 . f5 . d5 . a5 . g5 . f5 . d5 .', 'e5 . e5 . g5 . b5 . d6 . b5 . a5 . g5 .', 'f#5 . e5 . d5 . e5 . . . - - - - - -'].join(' '),
      },
      { wave: 'square', volume: 26, gate: 0.5, pattern: ['e2 e2 - e2 e2 - e2 e2 e2 e2 - e2 e2 - e2 e2', 'd2 d2 - d2 d2 - d2 d2 d2 d2 - d2 d2 - d2 d2', 'e2 e2 - e2 e2 - e2 e2 g2 g2 - g2 g2 - g2 g2', 'a2 a2 - a2 a2 - a2 a2 b2 b2 - b2 b2 - b2 b2'].join(' ') },
      { wave: 'noise', volume: 9, gate: 0.15, pattern: 'c5 - c6 - c5 - c6 - c5 - c6 - c5 - c6 c6' },
    ],
  },
  victory: {
    id: 'victory',
    bpm: 132,
    loop: false,
    voices: [
      { wave: 'square', volume: 24, pattern: 'g5 . c6 . e6 . g6 . . . e6 . g6 . . . . . . . - - - - - - - - - - - -' },
      { wave: 'triangle', volume: 30, gate: 0.9, pattern: 'c3 . . . c3 . . . g3 . . . c4 . . . . . . . - - - - - - - - - - - -' },
      { wave: 'sine', volume: 14, pattern: 'e5 . g5 . c6 . e6 . . . c6 . e6 . . . . . . . - - - - - - - - - - - -' },
    ],
  },
  farewell: {
    id: 'farewell',
    bpm: 70,
    loop: true,
    voices: [
      {
        wave: 'sine',
        volume: 38,
        attackMs: 40,
        pattern: ['e5 . . . . . . . d5 . . . c5 . . .', 'd5 . . . . . . . . . . . . . . .', 'c5 . . . . . . . d5 . . . e5 . . .', 'g4 . . . . . . . . . . . . . . .'].join(' '),
      },
      { wave: 'triangle', volume: 24, gate: 1, attackMs: 60, pattern: ['c3 . . . . . . . . . . . . . . .', 'g2 . . . . . . . . . . . . . . .', 'a2 . . . . . . . . . . . . . . .', 'f2 . . . . . . . . . . . . . . .'].join(' ') },
      { wave: 'triangle', volume: 12, gate: 1, attackMs: 60, pattern: ['e4 . . . . . . . . . . . . . . .', 'd4 . . . . . . . . . . . . . . .', 'c4 . . . . . . . . . . . . . . .', 'c4 . . . . . . . . . . . . . . .'].join(' ') },
    ],
  },
  shrine: {
    id: 'shrine',
    bpm: 60,
    loop: true,
    voices: [
      {
        wave: 'sine',
        volume: 34,
        attackMs: 80,
        pattern: ['d5 . . . . . f#5 . . . . . a5 . . .', 'g5 . . . . . . . . . . . . . . .', 'e5 . . . . . g5 . . . . . b5 . . .', 'a5 . . . . . . . . . . . . . . .'].join(' '),
      },
      { wave: 'triangle', volume: 22, gate: 1, attackMs: 120, pattern: ['d2 . . . . . . . . . . . . . . .', 'c2 . . . . . . . . . . . . . . .', 'e2 . . . . . . . . . . . . . . .', 'a1 . . . . . . . . . . . . . . .'].join(' ') },
      { wave: 'sine', volume: 10, gate: 0.4, pattern: ['- - - - - - - - - - - - a6 - - -', rep('-', 16), '- - - - - - - - - - - - b6 - - -', rep('-', 16)].join(' ') },
    ],
  },
}

export function ranchTrackFor(season: Season): TrackId {
  switch (season) {
    case 'Spring':
      return 'ranchSpring'
    case 'Summer':
      return 'ranchSummer'
    case 'Autumn':
      return 'ranchAutumn'
    case 'Winter':
      return 'ranchWinter'
  }
}
