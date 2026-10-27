/**
 * SOUND_UPGRADE §5.2: the instruments, their articulations, families, hand-set melodic ranges and fallback
 * voices. `range.playable` comes from the manifest at runtime (samples ±4 semitones, see `playableRange`);
 * `melody` is set here, inside it. Pure data; the checker, the generators, the sampler and the Sound Lab
 * all read it. Sounding MIDI throughout (C4 = 60).
 */

export const INSTRUMENT_IDS = [
  'ocarina',
  'recorder-alto',
  'recorder-tenor',
  'flute',
  'horn',
  'violins',
  'violas',
  'cellos',
  'contrabass',
  'harp',
  'strumstick',
  'kalimba',
  'marimba',
  'glock',
  'hand-chimes',
  'tubular-bells',
  'vibes',
  'music-box',
  'frame-drum',
  'shaker',
  'tambourine',
  'woodblock',
  'claves',
  'claps',
  'finger-cymbals',
  'triangle',
  'mark-trees',
  'sleigh-bells',
  'timpani',
  'bass-drum',
  'darbuka',
  'bongos',
  'cajon',
  'cymbal-swell',
  'foley',
] as const
export type InstrumentId = (typeof INSTRUMENT_IDS)[number]

export type Family = 'wind' | 'bowed' | 'pluck' | 'mallet' | 'perc' | 'foley' | 'patch'
export type FallbackVoice = 'wind' | 'pad' | 'pluck' | 'mallet' | 'silent'

export interface InstrumentDef {
  family: Family
  /** Articulations as named in the manifest; the first is the default. */
  arts: readonly string[]
  /** The articulation for notes of a beat or longer (vibrato), if the instrument has one. */
  longArt?: string
  /** Monophonic: a new note replaces the old one with a 20 ms crossfade (§4.5). */
  mono?: boolean
  /** Hand-set melodic range, sounding MIDI, inside the playable range. Absent for unpitched percussion. */
  melody?: readonly [number, number]
  /** §3.1 bright colour: it doubles or answers and never carries a line longer than 2 bars alone. */
  bright?: boolean
  fallback: FallbackVoice
  /** Attack and release in ms (§4.5). Plucks ring naturally and are damped `releaseMs` after the note ends. */
  attackMs: number
  releaseMs: number
  /** Rate-pitched percussion (timpani): `pitch: 'root' | 'fifth'` from the chord track. */
  pitchedPerc?: boolean
  /** A patch built from other instruments (music box). */
  patch?: { layers: readonly { inst: InstrumentId; transpose: number; gainDb: number; decayCapSec?: number }[]; minMidi: number }
}

export const INSTRUMENTS: Record<InstrumentId, InstrumentDef> = {
  ocarina: { family: 'wind', arts: ['sus', 'vib'], longArt: 'vib', mono: true, melody: [69, 85], fallback: 'wind', attackMs: 40, releaseMs: 110 },
  'recorder-alto': { family: 'wind', arts: ['sus', 'vib', 'stac'], longArt: 'vib', mono: true, melody: [65, 88], fallback: 'wind', attackMs: 30, releaseMs: 90 },
  'recorder-tenor': { family: 'wind', arts: ['sus', 'vib'], longArt: 'vib', mono: true, melody: [60, 84], fallback: 'wind', attackMs: 35, releaseMs: 100 },
  flute: { family: 'wind', arts: ['sus', 'vib', 'stac'], longArt: 'vib', mono: true, melody: [65, 93], fallback: 'wind', attackMs: 35, releaseMs: 100 },
  horn: { family: 'wind', arts: ['sus', 'stac'], mono: true, melody: [43, 64], fallback: 'wind', attackMs: 60, releaseMs: 150 },
  violins: { family: 'bowed', arts: ['vib', 'spic', 'pizz', 'trem'], longArt: 'vib', melody: [55, 86], fallback: 'pad', attackMs: 80, releaseMs: 400 },
  violas: { family: 'bowed', arts: ['vib', 'pizz'], longArt: 'vib', melody: [48, 79], fallback: 'pad', attackMs: 80, releaseMs: 450 },
  cellos: { family: 'bowed', arts: ['vib', 'pizz', 'spic', 'trem'], longArt: 'vib', melody: [36, 69], fallback: 'pad', attackMs: 80, releaseMs: 500 },
  contrabass: { family: 'bowed', arts: ['pizz', 'sus'], melody: [28, 55], fallback: 'pad', attackMs: 60, releaseMs: 500 },
  harp: { family: 'pluck', arts: ['pluck'], melody: [48, 91], fallback: 'pluck', attackMs: 3, releaseMs: 900 },
  strumstick: { family: 'pluck', arts: ['pluck'], melody: [50, 81], fallback: 'pluck', attackMs: 3, releaseMs: 500 },
  kalimba: { family: 'pluck', arts: ['pluck'], melody: [55, 91], fallback: 'pluck', attackMs: 3, releaseMs: 600 },
  marimba: { family: 'mallet', arts: ['hit'], melody: [48, 86], fallback: 'mallet', attackMs: 3, releaseMs: 400 },
  glock: { family: 'mallet', arts: ['hit'], melody: [79, 103], bright: true, fallback: 'mallet', attackMs: 3, releaseMs: 1200 },
  'hand-chimes': { family: 'mallet', arts: ['hit'], melody: [60, 96], bright: true, fallback: 'mallet', attackMs: 3, releaseMs: 1500 },
  'tubular-bells': { family: 'mallet', arts: ['hit'], melody: [60, 76], bright: true, fallback: 'mallet', attackMs: 3, releaseMs: 1500 },
  vibes: { family: 'mallet', arts: ['hit', 'bowed'], melody: [53, 88], fallback: 'mallet', attackMs: 3, releaseMs: 1200 },
  'music-box': {
    family: 'patch',
    arts: ['pluck'],
    melody: [72, 96],
    bright: true,
    fallback: 'pluck',
    attackMs: 3,
    releaseMs: 500,
    patch: {
      layers: [
        { inst: 'kalimba', transpose: 0, gainDb: 0, decayCapSec: 0.8 },
        { inst: 'glock', transpose: 12, gainDb: -12 },
      ],
      minMidi: 72,
    },
  },
  'frame-drum': { family: 'perc', arts: ['hit', 'muted'], fallback: 'silent', attackMs: 2, releaseMs: 200 },
  shaker: { family: 'perc', arts: ['hit', 'up'], fallback: 'silent', attackMs: 2, releaseMs: 120 },
  tambourine: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 250 },
  woodblock: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 120 },
  claves: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 120 },
  claps: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 150 },
  'finger-cymbals': { family: 'perc', arts: ['hit'], bright: true, fallback: 'silent', attackMs: 2, releaseMs: 1500 },
  triangle: { family: 'perc', arts: ['hit'], bright: true, fallback: 'silent', attackMs: 2, releaseMs: 1500 },
  'mark-trees': { family: 'perc', arts: ['hit'], bright: true, fallback: 'silent', attackMs: 2, releaseMs: 2000 },
  'sleigh-bells': { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 500 },
  timpani: { family: 'perc', arts: ['hit', 'roll'], pitchedPerc: true, fallback: 'silent', attackMs: 2, releaseMs: 800 },
  'bass-drum': { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 500 },
  darbuka: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 200 },
  bongos: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 200 },
  cajon: { family: 'perc', arts: ['hit'], fallback: 'silent', attackMs: 2, releaseMs: 250 },
  'cymbal-swell': { family: 'perc', arts: ['swell'], fallback: 'silent', attackMs: 2, releaseMs: 1500 },
  foley: { family: 'foley', arts: ['footstep_grass', 'footstep_wood', 'footstep_concrete', 'impactWood_light', 'impactWood_heavy', 'impactSoft_heavy', 'impactSoft_medium', 'impactPlank_medium', 'impactMining', 'impactPunch_medium', 'cloth', 'creak', 'handleCoins', 'bookFlip'], fallback: 'silent', attackMs: 2, releaseMs: 200 },
}

/** §3.1 names that must never appear as an instrument (they are not ids, so a typo cannot summon them). */
export const BANNED_INSTRUMENT_WORDS = ['square', 'saw', 'sawtooth', 'pulse', 'synth', 'electric', 'trumpet', 'drum-machine', 'bitcrush', 'distortion'] as const

export function isInstrumentId(id: string): id is InstrumentId {
  return (INSTRUMENT_IDS as readonly string[]).includes(id)
}

/** True for instruments that carry melodic lines (anything with a melody range). */
export function isPitched(id: InstrumentId): boolean {
  return INSTRUMENTS[id].melody !== undefined
}

/** Resolves an articulation request: the instrument's default when none or an unknown one is asked for. */
export function articulationOf(id: InstrumentId, art?: string): string {
  const def = INSTRUMENTS[id]
  return art && def.arts.includes(art) ? art : def.arts[0]!
}

/** Which samples a (pitched) instrument has at each articulation, by root MIDI, from the manifest. */
export interface SampleRoots {
  [inst: string]: { [art: string]: readonly number[] }
}

/** The playable range: the samples' roots ±4 semitones (§5.2). Null when the manifest has no such articulation. */
export function playableRange(roots: SampleRoots, inst: InstrumentId, art?: string): readonly [number, number] | null {
  const def = INSTRUMENTS[inst]
  if (def.patch) return [def.patch.minMidi, def.melody?.[1] ?? 108]
  const a = articulationOf(inst, art)
  const list = roots[inst]?.[a]
  if (!list || list.length === 0) return null
  return [Math.min(...list) - 4, Math.max(...list) + 4]
}

/** The nearest sample root to `midi` within ±4 semitones, preferring the one just below (§4.5). */
export function nearestRoot(list: readonly number[], midi: number): number | null {
  let best: number | null = null
  let bestScore = Infinity
  for (const r of list) {
    const d = midi - r
    if (Math.abs(d) > 4) continue
    // Below is better than above at the same distance; nearer is better than farther.
    const score = Math.abs(d) * 2 + (d < 0 ? 1 : 0)
    if (score < bestScore) {
      bestScore = score
      best = r
    }
  }
  return best
}
