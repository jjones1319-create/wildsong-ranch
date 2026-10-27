/**
 * SOUND_UPGRADE §5.2–5.3: where every sample comes from. One rule per instrument × articulation: the library,
 * the folder inside it, an optional filter on the file name, which dynamic or velocity layer is the main take
 * and which (if any) gives the alternate, the sample class (sets the length cap and bitrate) and how its pitch
 * is found. The libraries name their files differently (`StdOcarina_SusVib_A4`, `EWHarp_Normal_A#1_v2_RR1`,
 * `Marimba_hit_Outrigger_B2_soft_01`, `susvib_A2_v1_1`), so a generic name parser pulls the note, dynamic,
 * velocity layer and round-robin out of any of them, and the rule says what to prefer.
 *
 * Note names are the library's own; VCSL calls middle C "C3". The build measures every pitch and learns each
 * library's octave convention from its harmonic instruments (§5.3 step 2).
 */

export type Lib = 'vcsl' | 'vsco' | 'kenney-impact' | 'kenney-rpg'
export type SampleClass = 'sustain' | 'pluck' | 'drum' | 'ringing' | 'foley'
/** named: a chromatic instrument whose measured pitch must agree with its name · inharmonic: trust the name's pitch class · measure: a single-pitch drum (timpani) whose fundamental is stored · none: unpitched. */
export type PitchMode = 'named' | 'inharmonic' | 'measure' | 'none'

export interface SourceRule {
  inst: string
  art: string
  lib: Lib
  /** Folder prefix inside the library (Kenney: ignored; the filter matches the whole zip). */
  dir: string
  /** Extra filter on the base file name. */
  filter?: RegExp
  /** Preference order for the main take, per parsed field. The first value that exists for a note wins. */
  prefer?: Partial<Record<'dyn' | 'vel', readonly string[]>>
  /** The layer that gives the alternate take (same note), if any. */
  alt?: Partial<Record<'dyn' | 'vel' | 'rr', readonly string[]>>
  cls: SampleClass
  pitch: PitchMode
  /** Useful register as the library names it (MIDI of the name, C4 = 60), inclusive. */
  range?: readonly [number, number]
  /** Samples per articulation cap (default 14). */
  max?: number
  /** Lowest fundamental to look for (Hz), for the pitch detector. */
  minHz?: number
  /** Unpitched takes to keep (default 2 for drums, 4 for Foley). */
  takes?: number
  /** Length cap in seconds, overriding the class default (§5.3 step 3). */
  capSec?: number
}

export const LIBRARIES: Record<Lib, { url: string; pin: string; kind: 'git' | 'zip'; license: string; name: string }> = {
  vcsl: { name: 'Versilian Community Sample Library (VCSL)', url: 'https://github.com/sgossner/VCSL', pin: 'c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e', kind: 'git', license: 'CC0 1.0' },
  vsco: { name: 'Versilian Studios Chamber Orchestra 2 Community Edition (VSCO 2 CE)', url: 'https://github.com/sgossner/VSCO-2-CE', pin: '440300901dfe9275fd84e0b7763af1f8443ae62e', kind: 'git', license: 'CC0 1.0' },
  'kenney-impact': { name: 'Kenney Impact Sounds', url: 'https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip', pin: '', kind: 'zip', license: 'CC0 1.0' },
  'kenney-rpg': { name: 'Kenney RPG Audio', url: 'https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip', pin: '', kind: 'zip', license: 'CC0 1.0' },
}

const V = 'Aerophones/Edge-blown Aerophones/'
const VI = 'Idiophones/Struck Idiophones/'
const VM = 'Membranophones/Struck Membranophones/'

const NOTE = (lo: string, hi: string): readonly [number, number] => [noteNameToMidi(lo), noteNameToMidi(hi)]

/** `A#3` / `Db4` / `C-1` → MIDI with C4 = 60 (the library's own convention, before any octave shift). */
export function noteNameToMidi(name: string): number {
  const m = /^([A-Ga-g])(#|b)?(-?\d)$/.exec(name.trim())
  if (!m) throw new Error(`bad note name ${name}`)
  const base: Record<string, number> = { c: 0, d: 2, e: 4, f: 5, g: 7, a: 9, b: 11 }
  return 12 * (Number(m[3]) + 1) + base[m[1]!.toLowerCase()]! + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0)
}

export interface ParsedName {
  note: string | null
  dyn: string | null
  vel: string | null
  rr: string | null
}

/** Pulls the note, dynamic, velocity layer and round-robin out of a sample file name. */
export function parseSampleName(base: string): ParsedName {
  const stem = base.replace(/\.(wav|ogg|flac|aif+)$/i, '')
  const parts = stem.split(/[_\-\s]+/)
  let note: string | null = null
  let dyn: string | null = null
  let vel: string | null = null
  let rr: string | null = null
  for (const p of parts) {
    if (note === null && /^[A-G]#?-?\d$/.test(p)) note = p
    else if (rr === null && /^rr\d+$/i.test(p)) rr = p.toLowerCase().replace('rr', '')
    else if (vel === null && /^v(l)?\d+$/i.test(p)) vel = p.toLowerCase()
    else if (dyn === null && /^(ppp|pp|p|mp|mf|f|ff|fff|soft|med|medium|loud|quiet|hard)$/i.test(p)) dyn = p.toLowerCase()
  }
  return { note, dyn, vel, rr }
}

/** The S1 instrument set. Later stages add rules here and re-run `npm run audio:samples`. */
export const SOURCE_RULES: readonly SourceRule[] = [
  // ---- calm leads
  { inst: 'ocarina', art: 'sus', lib: 'vcsl', dir: `${V}Ocarina, Typical/Sustains/Sus/`, cls: 'sustain', pitch: 'named', minHz: 150 },
  { inst: 'ocarina', art: 'vib', lib: 'vcsl', dir: `${V}Ocarina, Typical/Sustains/SusVib/`, cls: 'sustain', pitch: 'named', minHz: 150 },
  { inst: 'recorder-alto', art: 'sus', lib: 'vcsl', dir: `${V}Baroque Alto Recorder/Sustain/`, cls: 'sustain', pitch: 'named', minHz: 150 },
  { inst: 'recorder-alto', art: 'vib', lib: 'vcsl', dir: `${V}Baroque Alto Recorder/SusVib/`, cls: 'sustain', pitch: 'named', minHz: 150 },
  { inst: 'recorder-alto', art: 'stac', lib: 'vcsl', dir: `${V}Baroque Alto Recorder/Staccato/`, cls: 'pluck', pitch: 'named', minHz: 150 },
  { inst: 'recorder-tenor', art: 'sus', lib: 'vcsl', dir: `${V}Baroque Tenor Recorder/Sustain/`, cls: 'sustain', pitch: 'named', minHz: 100 },
  { inst: 'recorder-tenor', art: 'vib', lib: 'vcsl', dir: `${V}Baroque Tenor Recorder/SusVib/`, cls: 'sustain', pitch: 'named', minHz: 100 },
  { inst: 'flute', art: 'vib', lib: 'vsco', dir: 'Woodwinds/Flute/susvib/', prefer: { vel: ['v1'] }, cls: 'sustain', pitch: 'named', minHz: 150 },
  { inst: 'flute', art: 'sus', lib: 'vsco', dir: 'Woodwinds/Flute/susNV/', prefer: { vel: ['v1', 'v3'] }, cls: 'sustain', pitch: 'named', minHz: 150 },
  { inst: 'flute', art: 'stac', lib: 'vsco', dir: 'Woodwinds/Flute/stac/', prefer: { vel: ['v1', 'v2'] }, cls: 'pluck', pitch: 'named', minHz: 150 },
  // ---- noble
  { inst: 'horn', art: 'sus', lib: 'vsco', dir: 'Brass/F Horn/sus/', prefer: { vel: ['v2', 'v1', 'v3'] }, cls: 'sustain', pitch: 'named', minHz: 50, range: NOTE('C1', 'C4') },
  { inst: 'horn', art: 'stac', lib: 'vsco', dir: 'Brass/F Horn/stac/', prefer: { vel: ['v2', 'v1'] }, cls: 'pluck', pitch: 'named', minHz: 50, range: NOTE('C1', 'C4') },
  { inst: 'violins', art: 'vib', lib: 'vsco', dir: 'Strings/Violin Section/susVib/', prefer: { vel: ['v1', 'v2'] }, cls: 'sustain', pitch: 'named', minHz: 150, range: NOTE('G2', 'C6') },
  { inst: 'violins', art: 'spic', lib: 'vsco', dir: 'Strings/Violin Section/Spic/', prefer: { vel: ['v1', 'v2'] }, cls: 'pluck', pitch: 'named', minHz: 150, range: NOTE('G2', 'C6') },
  { inst: 'violins', art: 'pizz', lib: 'vsco', dir: 'Strings/Violin Section/Pizz/', prefer: { vel: ['v1', 'v2'] }, cls: 'pluck', pitch: 'named', minHz: 150, range: NOTE('G2', 'C6'), capSec: 1.5 },
  { inst: 'violins', art: 'trem', lib: 'vsco', dir: 'Strings/Violin Section/Trem/', prefer: { vel: ['v1', 'v2'] }, cls: 'sustain', pitch: 'named', minHz: 150, range: NOTE('G2', 'C6') },
  { inst: 'violas', art: 'vib', lib: 'vsco', dir: 'Strings/Viola Section/susvib/', prefer: { vel: ['v1', 'v2'] }, cls: 'sustain', pitch: 'named', minHz: 100, range: NOTE('C2', 'C5') },
  { inst: 'violas', art: 'pizz', lib: 'vsco', dir: 'Strings/Viola Section/pizz/', prefer: { vel: ['v1', 'v2'] }, cls: 'pluck', pitch: 'named', minHz: 100, range: NOTE('C2', 'C5'), capSec: 1.5 },
  { inst: 'cellos', art: 'vib', lib: 'vsco', dir: 'Strings/Cello Section/susvib/', prefer: { vel: ['v1', 'v3'] }, cls: 'sustain', pitch: 'named', minHz: 50, range: NOTE('C1', 'C4') },
  { inst: 'cellos', art: 'pizz', lib: 'vsco', dir: 'Strings/Cello Section/pizzT/', prefer: { vel: ['v1', 'v2'] }, cls: 'pluck', pitch: 'named', minHz: 50, range: NOTE('C1', 'C4'), capSec: 1.5 },
  { inst: 'cellos', art: 'spic', lib: 'vsco', dir: 'Strings/Cello Section/spic/', prefer: { vel: ['v1', 'v2'] }, cls: 'pluck', pitch: 'named', minHz: 50, range: NOTE('C1', 'C4') },
  { inst: 'cellos', art: 'trem', lib: 'vsco', dir: 'Strings/Cello Section/trem/', prefer: { vel: ['v1', 'v2'] }, cls: 'sustain', pitch: 'named', minHz: 50, range: NOTE('C1', 'C4') },
  { inst: 'contrabass', art: 'pizz', lib: 'vsco', dir: 'Strings/Solo Contrabass/Pizz/', prefer: { vel: ['v1', 'v3'] }, cls: 'pluck', pitch: 'named', minHz: 35, range: NOTE('E0', 'C3'), capSec: 1.5 },
  { inst: 'contrabass', art: 'sus', lib: 'vsco', dir: 'Strings/Solo Contrabass/SusNV/', prefer: { vel: ['v1', 'v3'] }, cls: 'sustain', pitch: 'named', minHz: 35, range: NOTE('E0', 'C3') },
  // ---- plucked and struck
  { inst: 'harp', art: 'pluck', lib: 'vcsl', dir: 'Chordophones/Composite Chordophones/Folk Harp/', prefer: { vel: ['v2'] }, cls: 'pluck', pitch: 'named', minHz: 50, range: NOTE('C2', 'C6'), capSec: 3 },
  { inst: 'strumstick', art: 'pluck', lib: 'vcsl', dir: 'Chordophones/Composite Chordophones/Strumstick/Finger/', filter: /_Main_/, prefer: { vel: ['vl2', 'vl1'] }, cls: 'pluck', pitch: 'named', minHz: 60, capSec: 1.6 },
  { inst: 'kalimba', art: 'pluck', lib: 'vcsl', dir: 'Idiophones/Plucked Idiophones/Kalimba, Tanzania/', filter: /_Main_/, cls: 'pluck', pitch: 'inharmonic', minHz: 100 },
  { inst: 'marimba', art: 'hit', lib: 'vcsl', dir: `${VI}Marimba/`, prefer: { dyn: ['soft'] }, alt: { dyn: ['med'] }, cls: 'pluck', pitch: 'named', minHz: 50, range: NOTE('C1', 'C5'), capSec: 1.5 },
  { inst: 'glock', art: 'hit', lib: 'vcsl', dir: `${VI}Glockenspiel/`, prefer: { dyn: ['soft', 'med', 'medium', 'loud'] }, cls: 'pluck', pitch: 'inharmonic', minHz: 300, capSec: 2 },
  { inst: 'hand-chimes', art: 'hit', lib: 'vcsl', dir: `${VI}Hand Chimes/`, filter: /^sus_/, cls: 'pluck', pitch: 'inharmonic', minHz: 150, capSec: 2 },
  { inst: 'tubular-bells', art: 'hit', lib: 'vcsl', dir: `${VI}Tubular Bells 1/`, prefer: { dyn: ['f', 'pp', 'ff'] }, cls: 'pluck', pitch: 'inharmonic', minHz: 100, max: 8, capSec: 2.5 },
  { inst: 'vibes', art: 'hit', lib: 'vcsl', dir: `${VI}Vibraphone/Soft Mallets/`, prefer: { vel: ['v1'] }, cls: 'pluck', pitch: 'inharmonic', minHz: 100, capSec: 2 },
  { inst: 'vibes', art: 'bowed', lib: 'vcsl', dir: `${VI}Vibraphone/Bowed/`, cls: 'sustain', pitch: 'inharmonic', minHz: 100 },
  // ---- percussion (unpitched unless said)
  { inst: 'frame-drum', art: 'hit', lib: 'vcsl', dir: `${VM}Frame Drum/`, filter: /HDrumL_Hit_/, prefer: { vel: ['v2', 'v1'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none' },
  { inst: 'frame-drum', art: 'muted', lib: 'vcsl', dir: `${VM}Frame Drum/`, filter: /HDrumL_HitMuted_/, prefer: { vel: ['v2', 'v1'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none' },
  { inst: 'shaker', art: 'hit', lib: 'vcsl', dir: `${VI}Shaker, Small/`, filter: /ShakerDouble_Down/, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none' },
  { inst: 'shaker', art: 'up', lib: 'vcsl', dir: `${VI}Shaker, Small/`, filter: /ShakerDouble_Up/, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none' },
  { inst: 'tambourine', art: 'hit', lib: 'vcsl', dir: `${VI}Tambourine 1/`, filter: /Tamb1_Hit_/, prefer: { vel: ['v1'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none' },
  { inst: 'woodblock', art: 'hit', lib: 'vcsl', dir: `${VI}Woodblock/`, filter: /wood_click/, prefer: { dyn: ['mf', 'mp', 'f'] }, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'claves', art: 'hit', lib: 'vcsl', dir: `${VI}Claves/`, filter: /^(?!.*Legacy)/, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'claps', art: 'hit', lib: 'vcsl', dir: `${VI}Claps/`, filter: /^Clap_rr/, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'finger-cymbals', art: 'hit', lib: 'vcsl', dir: `${VI}Finger Cymbals/`, cls: 'ringing', pitch: 'none', takes: 1 },
  { inst: 'triangle', art: 'hit', lib: 'vcsl', dir: `${VI}Triangles/`, filter: /^Triangle1_Hit/, cls: 'ringing', pitch: 'none', takes: 2 },
  { inst: 'mark-trees', art: 'hit', lib: 'vcsl', dir: `${VI}Mark Trees/Legacy/`, filter: /^windchimes_(asc1|slowAsc1)\.wav$/, cls: 'ringing', pitch: 'none', takes: 2 },
  { inst: 'sleigh-bells', art: 'hit', lib: 'vcsl', dir: `${VI}Sleigh Bells/`, filter: /Sleighbells_Hit_/, alt: { rr: ['2'] }, cls: 'ringing', pitch: 'none', takes: 2 },
  { inst: 'timpani', art: 'hit', lib: 'vcsl', dir: `${VM}Timpani 1/Hit/`, prefer: { vel: ['v2', 'v1'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'measure', minHz: 50, takes: 2 },
  { inst: 'timpani', art: 'roll', lib: 'vcsl', dir: `${VM}Timpani 1/Roll/`, prefer: { vel: ['v2', 'v3', 'v1'] }, cls: 'ringing', pitch: 'measure', minHz: 50, takes: 1 },
  { inst: 'bass-drum', art: 'hit', lib: 'vcsl', dir: `${VM}Bass Drum 1/`, prefer: { vel: ['v1', 'v2'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'darbuka', art: 'hit', lib: 'vcsl', dir: `${VM}Darbuka/`, filter: /Darbuka_1_hit/, prefer: { vel: ['vl1', 'vl2'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'bongos', art: 'hit', lib: 'vcsl', dir: `${VM}Bongos/`, filter: /Bongo[HL]_Hit1_/, prefer: { vel: ['v1'] }, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'cajon', art: 'hit', lib: 'vcsl', dir: `${VI}Cajon/`, filter: /Cajon_hit1_/, prefer: { dyn: ['f', 'mf', 'ff'] }, alt: { rr: ['2'] }, cls: 'drum', pitch: 'none', takes: 2 },
  { inst: 'cymbal-swell', art: 'swell', lib: 'vcsl', dir: `${VI}Suspended Cymbal 1/`, filter: /roll_\w+_nloop/i, cls: 'ringing', pitch: 'none', takes: 2 },
  // ---- Foley (Kenney): the name prefix is the articulation
  ...(['footstep_grass', 'footstep_wood', 'footstep_concrete', 'impactWood_light', 'impactWood_heavy', 'impactSoft_heavy', 'impactSoft_medium', 'impactPlank_medium', 'impactMining', 'impactPunch_medium'] as const).map(
    (p): SourceRule => ({ inst: 'foley', art: p, lib: 'kenney-impact', dir: '', filter: new RegExp(`^${p}_\\d+\\.(ogg|wav)$`), cls: 'foley', pitch: 'none', takes: 4 }),
  ),
  ...(['cloth', 'creak', 'handleCoins', 'bookFlip'] as const).map((p): SourceRule => ({ inst: 'foley', art: p, lib: 'kenney-rpg', dir: '', filter: new RegExp(`^${p}\\d*\\.(ogg|wav)$`), cls: 'foley', pitch: 'none', takes: 4 })),
]
