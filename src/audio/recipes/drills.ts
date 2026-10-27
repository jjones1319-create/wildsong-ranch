/**
 * SOUND_UPGRADE §8: the training soundscapes. A drill cue is the ambience of its place, Foley on its
 * timeline, a short music bed in its own mood (2–4 bars, looping) mixed under the ambience, and five outcome
 * stingers (1.2–2.5 s) in the cue's key and instruments. S1 writes Waterfall Stand in full as the pilot;
 * the other ten drills share a soft generic cue until S3. All original.
 */
import type { DrillId } from '../../data/types.ts'
import type { DrillOutcome } from '../../core/training.ts'
import { defineSong, type Song } from '../music/song.ts'
import type { ReverbPreset } from '../engine/reverb.ts'
import type { BedId } from './ambience.ts'
import type { SfxDef } from './sfx.ts'

export interface FoleyTimeline {
  /** A sound every so often, seconds (min, max), from the cue's start. */
  every: readonly [number, number]
  sfx: SfxDef
  /** V4 will pass markers by name; the default timing lives here. */
  marker: string
}

export interface DrillCueRecipe {
  id: DrillId | 'generic'
  bed: BedId | null
  /** The music bed's level against the ambience, dB. */
  musicGainDb: number
  reverb: ReverbPreset
  song: Song
  stingers: Record<DrillOutcome, Song>
  foley: readonly FoleyTimeline[]
  /** The Slacked stinger's playback-rate sag (§8.3). */
  sag: { rate: number; seconds: number }
  /** Soft breathing after the yawn (an effect). */
  breath: SfxDef | null
  status: 'S1' | 'TODO_S3'
}

const SOFT_BREATH: SfxDef = { bus: 'sfx', throttleMs: 500, layers: [{ kind: 'noise', color: 'pink', filter: { type: 'bandpass', hz: 900, q: 0.8 }, a: 500, h: 300, d: 700, gainDb: -30, lowpassHz: 3000 }] }

/* ---------- Waterfall Stand (DEF·LIF), the S1 pilot ---------- */

const waterfallBed = defineSong({
  id: 'drill-waterfall',
  kind: 'drill',
  brief: 'Bracing under the little waterfall: a cello drone and a slow ocarina line with harp, heard through the roar.',
  energy: 2,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=80
K:D dor
V:chords
[P:A] "Dm"z8 | "Dm"z8 | "C"z8 | "Dm"z8 |
V:lead
[P:A] !mp! d4 e2 f2 | a4- a2 z2 | g2 e2 c2 d2 | d6 z2 |
`,
  parts: { lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0 } },
  accomp: {
    drone: { inst: 'cellos', art: 'vib', role: 'bass', pattern: 'drone', layers: ['main'], octave: 2, gain: -8 },
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9, spread: 'close' },
  },
  order: ['A'],
  loopFrom: 0,
})

const wf = (id: string, brief: string, abc: string, parts: Parameters<typeof defineSong>[0]['parts'], accomp?: Parameters<typeof defineSong>[0]['accomp']) =>
  defineSong({ id, kind: 'stinger', brief, energy: 2, musicSend: 0.3, abc, parts, accomp, order: ['A'], loopFrom: 0 })

const WATERFALL_STINGERS: Record<DrillOutcome, Song> = {
  Great: wf(
    'drill-waterfall-great',
    'Great: a harp glissando rises and a high ocarina note rings out through the roar.',
    `
X:1
M:3/4
L:1/8
Q:1/4=90
K:D dor
V:chords
[P:A] "Dm"z6 |
V:harp
[P:A] D/2 F/2 A/2 c/2 d4 |
V:lead
[P:A] z2 a4 |
`,
    { harp: { inst: 'harp', role: 'accomp', layers: ['main'], gain: -4 }, lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0 } },
  ),
  Success: wf(
    'drill-waterfall-success',
    'Success: a warm ♭VII–I cadence, three ocarina notes settling on the tonic over harp.',
    `
X:1
M:3/4
L:1/8
Q:1/4=90
K:D dor
V:chords
[P:A] "C"z3 "Dm"z3 |
V:lead
[P:A] e2 c2 d2 |
`,
    { lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0 } },
    { harp: { inst: 'harp', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -8 } },
  ),
  Cheat: wf(
    'drill-waterfall-cheat',
    'Cheat: a sly chromatic slide up the ocarina and one cello pizzicato plink.',
    `
X:1
M:3/4
L:1/8
Q:1/4=90
K:D dor
V:chords
[P:A] "Dm"z6 |
V:lead
[P:A] f ^f g a3 |
`,
    { lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: -1 } },
    { pizz: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -7 } },
  ),
  Fail: wf(
    'drill-waterfall-fail',
    'Fail: a soft falling third on the ocarina, lower down, left hanging. Sympathetic, never a buzzer.',
    `
X:1
M:3/4
L:1/8
Q:1/4=90
K:D dor
V:chords
[P:A] "F"z6 |
V:lead
[P:A] !p! c4 A2 |
`,
    { lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0 } },
    { pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -12 } },
  ),
  Slacked: wf(
    'drill-waterfall-slacked',
    'Slacked: the bed sags down a step, then a sleepy two-note yawn on the tenor recorder and soft breathing.',
    `
X:1
M:3/4
L:1/8
Q:1/4=90
K:D dor
V:chords
[P:A] "C"z6 |
V:lead
[P:A] !p! E4 C2 |
`,
    { lead: { inst: 'recorder-tenor', role: 'lead', layers: ['main'], gain: 2 } },
  ),
}

/* ---------- the generic cue (the other ten drills until S3) ---------- */

const genericBed = defineSong({
  id: 'drill-generic',
  kind: 'drill',
  brief: 'A soft training bed: harp arpeggio and a two-bar alto recorder phrase in G, unhurried.',
  energy: 2,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=84
K:G
V:chords
[P:A] "G"z8 | "Am"z4 "D"z4 |
V:lead
[P:A] !mp! d2 B2 G4 | A2 c2 d4 |
`,
  parts: { lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: -2 } },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -8 },
    pizz: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -10 },
  },
  order: ['A'],
  loopFrom: 0,
})

const gn = (id: string, brief: string, abc: string, parts: Parameters<typeof defineSong>[0]['parts'], accomp?: Parameters<typeof defineSong>[0]['accomp']) =>
  defineSong({ id, kind: 'stinger', brief, energy: 2, musicSend: 0.3, abc, parts, accomp, order: ['A'], loopFrom: 0 })

const GENERIC_STINGERS: Record<DrillOutcome, Song> = {
  Great: gn(
    'drill-generic-great',
    'Great: a harp run up to the octave with a high recorder note and a glock double.',
    `
X:1
M:3/4
L:1/8
Q:1/4=96
K:G
V:chords
[P:A] "G"z6 |
V:harp
[P:A] G/2 B/2 d/2 g/2 g4 |
V:lead
[P:A] z2 g4 |
V:glock
[P:A] z2 !p! g'4 |
`,
    { harp: { inst: 'harp', role: 'accomp', layers: ['main'], gain: -4 }, lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: -1 }, glock: { inst: 'glock', role: 'colour', layers: ['main'], gain: -14 } },
  ),
  Success: gn(
    'drill-generic-success',
    'Success: a warm IV–I cadence, three recorder notes over harp.',
    `
X:1
M:3/4
L:1/8
Q:1/4=96
K:G
V:chords
[P:A] "C"z3 "G"z3 |
V:lead
[P:A] e2 d2 d2 |
`,
    { lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: -1 } },
    { harp: { inst: 'harp', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -8 } },
  ),
  Cheat: gn(
    'drill-generic-cheat',
    'Cheat: a sly chromatic slide on the recorder and a woodblock plink.',
    `
X:1
M:3/4
L:1/8
Q:1/4=96
K:G
V:chords
[P:A] "G"z6 |
V:lead
[P:A] d ^d e g3 |
`,
    { lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: -1 } },
    undefined,
  ),
  Fail: gn(
    'drill-generic-fail',
    'Fail: a soft falling third on the recorder, lower down, unresolved.',
    `
X:1
M:3/4
L:1/8
Q:1/4=96
K:G
V:chords
[P:A] "Em"z6 |
V:lead
[P:A] !p! B4 G2 |
`,
    { lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: 0 } },
    { pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -11 } },
  ),
  Slacked: gn(
    'drill-generic-slacked',
    'Slacked: the bed sags, then a sleepy two-note yawn on the tenor recorder and soft breathing.',
    `
X:1
M:3/4
L:1/8
Q:1/4=96
K:G
V:chords
[P:A] "C"z6 |
V:lead
[P:A] !p! G4 E2 |
`,
    { lead: { inst: 'recorder-tenor', role: 'lead', layers: ['main'], gain: 1 } },
  ),
}

const SPLASH: SfxDef = { bus: 'sfx', throttleMs: 300, layers: [{ kind: 'noise', color: 'white', filter: { type: 'highpass', hz: 900, q: 0.6 }, a: 8, h: 40, d: 110, gainDb: -18 }, { kind: 'noise', color: 'pink', filter: { type: 'lowpass', hz: 1200, q: 0.5 }, a: 5, d: 90, gainDb: -22 }] }
const WOODBLOCK_PLINK: SfxDef = { bus: 'sfx', throttleMs: 100, layers: [{ kind: 'sample', inst: 'woodblock', vel: 0.5, gainDb: -10 }] }

export const DRILL_CUES: { 'waterfall-stand': DrillCueRecipe; generic: DrillCueRecipe } = {
  'waterfall-stand': {
    id: 'waterfall-stand',
    bed: 'waterfall-near',
    musicGainDb: -6,
    reverb: 'outdoor',
    song: waterfallBed,
    stingers: WATERFALL_STINGERS,
    foley: [{ every: [1.0, 1.4], sfx: SPLASH, marker: 'surge' }],
    sag: { rate: 0.85, seconds: 0.8 },
    breath: SOFT_BREATH,
    status: 'S1',
  },
  generic: {
    id: 'generic',
    bed: 'meadow',
    musicGainDb: 2,
    reverb: 'outdoor',
    song: genericBed,
    stingers: GENERIC_STINGERS,
    foley: [],
    sag: { rate: 0.85, seconds: 0.8 },
    breath: SOFT_BREATH,
    status: 'TODO_S3',
  },
}

/** The cheat plink for the generic cue (a woodblock) and the waterfall cue (a pizz, written into its stinger). */
export const CHEAT_PLINK: SfxDef = WOODBLOCK_PLINK

export function cueFor(drill: DrillId): DrillCueRecipe {
  return drill === 'waterfall-stand' ? DRILL_CUES['waterfall-stand'] : DRILL_CUES.generic
}
