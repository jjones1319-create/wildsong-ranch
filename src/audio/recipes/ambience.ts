/**
 * SOUND_UPGRADE §9.2–9.4: the ambience recipes. A bed is a named set of layers: shaped noise with slow
 * movement, spawners of one-shot events (synth chirps, clicks, drips, creaks, bubbles, or samples), and
 * steady tones. Levels are starting points in dBFS for each layer alone; calibration (§14.3) sets each
 * bed's overall trim and keeps the balance. Weather overlays add, remove or scale layers; crowds are
 * layers of their own. Pure data; `engine/ambience.ts` performs it.
 */
import type { Weather } from '../../data/types.ts'
import type { InstrumentId } from './instruments.ts'
import type { ReverbPreset } from '../engine/reverb.ts'

export type NoiseColor = 'white' | 'pink' | 'brown'

export interface FilterSpec {
  type: BiquadFilterType
  hz: number
  q?: number
  gainDb?: number
}

export interface NoiseLayer {
  kind: 'noise'
  id: string
  color: NoiseColor
  filters?: readonly FilterSpec[]
  levelDb: number
  /** A slow gain LFO: ±depthDb at rateHz (or a range picked per instance). */
  lfo?: { rateHz: number | readonly [number, number]; depthDb: number }
  /** A seeded random walk every 250 ms: ±db on the gain, ±hz on the first filter. */
  walk?: { db?: number; hz?: number }
  /** Amplitude modulation (bees, syllable swells). */
  am?: { rateHz: number | readonly [number, number]; depth: number }
  /** Two decorrelated sources panned left and right (default true). */
  stereo?: boolean
  /** A fixed pan for a mono layer. */
  pan?: number
}

export type SpawnEvent =
  | { kind: 'chirp'; hz: readonly [number, number]; ms: readonly [number, number]; sweep?: number; fm?: number }
  | { kind: 'click'; ms?: number }
  | { kind: 'drip'; from: number; to: number; ms: number }
  | { kind: 'crackle'; ms: readonly [number, number] }
  | { kind: 'creak'; ms: readonly [number, number] }
  | { kind: 'bubble'; from: number; to: number; ms: number }
  | { kind: 'sample'; inst: InstrumentId; art: string; vel?: number; midi?: number }
  | { kind: 'noiseBurst'; color: NoiseColor; filter?: FilterSpec; ms: readonly [number, number]; lowpassHz?: number }
  | { kind: 'thunder' }
  | { kind: 'crickets'; hz: number; pulseHz: number; pulses: number }

export interface SpawnLayer {
  kind: 'spawn'
  id: string
  levelDb: number
  /** Events (or phrases) per second, Poisson. */
  rate: number
  /** A phrase of several events. */
  burst?: { count: readonly [number, number]; gapMs: readonly [number, number] }
  event: SpawnEvent
  pan?: 'wide' | 'random' | number
  /** ±cents of pitch variation. */
  pitchCents?: number
  levelJitterDb?: number
  lowpassHz?: number
}

export interface ToneLayer {
  kind: 'tone'
  id: string
  hz: readonly number[]
  levelDb: number
  /** Slow beating between the tones. */
  beatHz?: number
  lowpassHz?: number
}

export type BedLayer = NoiseLayer | SpawnLayer | ToneLayer

export const BED_IDS = [
  'meadow',
  'summer-field',
  'autumn-wind',
  'winter-yard',
  'brook',
  'waterfall-near',
  'town',
  'market',
  'shop',
  'guild',
  'library',
  'arena-out',
  'arena',
] as const
export type BedId = (typeof BED_IDS)[number]

export interface BedRecipe {
  id: BedId
  layers: readonly BedLayer[]
  reverb: ReverbPreset
  /** Beds this one extends (their layers come first). */
  extends?: BedId
}

const breeze = (id: string, levelDb: number, hz = 500, q = 0.5): NoiseLayer => ({ kind: 'noise', id, color: 'pink', filters: [{ type: 'bandpass', hz, q }], levelDb, lfo: { rateHz: [0.1, 0.3], depthDb: 4 }, walk: { db: 1.5, hz: 60 } })

const birds = (id: string, levelDb: number, ratePerSec: number): SpawnLayer => ({
  kind: 'spawn',
  id,
  levelDb,
  rate: ratePerSec,
  burst: { count: [3, 6], gapMs: [110, 260] },
  event: { kind: 'chirp', hz: [2000, 4000], ms: [45, 130], sweep: 0.3, fm: 40 },
  pan: 'wide',
  pitchCents: 200,
  levelJitterDb: 3,
  lowpassHz: 6000,
})

const BROOK: BedLayer[] = [
  { kind: 'noise', id: 'brook', color: 'pink', filters: [{ type: 'bandpass', hz: 900, q: 0.6 }, { type: 'highpass', hz: 200, q: 0.7 }], levelDb: -40, lfo: { rateHz: [0.8, 2], depthDb: 3 } },
  { kind: 'spawn', id: 'bubbles', levelDb: -40, rate: 9, event: { kind: 'bubble', from: 500, to: 1400, ms: 25 }, pan: 'random', pitchCents: 150, levelJitterDb: 4 },
]

export const BEDS: Record<BedId, BedRecipe> = {
  meadow: {
    id: 'meadow',
    reverb: 'outdoor',
    layers: [breeze('breeze', -38), birds('birds', -36, 1 / 6), { kind: 'noise', id: 'far-brook', color: 'pink', filters: [{ type: 'bandpass', hz: 900, q: 0.6 }], levelDb: -52, lfo: { rateHz: 1.2, depthDb: 2 } }],
  },
  'summer-field': {
    id: 'summer-field',
    reverb: 'outdoor',
    layers: [
      breeze('breeze', -36, 400, 0.6),
      birds('birds', -36, 1 / 11),
      { kind: 'noise', id: 'bees', color: 'white', filters: [{ type: 'bandpass', hz: 250, q: 3 }], levelDb: -48, am: { rateHz: [45, 70], depth: 0.6 }, lfo: { rateHz: [0.05, 0.1], depthDb: 5 }, stereo: false, pan: 0.3 },
    ],
  },
  'autumn-wind': {
    id: 'autumn-wind',
    reverb: 'outdoor',
    layers: [
      { kind: 'noise', id: 'wind', color: 'pink', filters: [{ type: 'bandpass', hz: 450, q: 0.4 }], levelDb: -36, lfo: { rateHz: [0.08, 0.2], depthDb: 6 }, walk: { db: 2, hz: 120 } },
      { kind: 'spawn', id: 'leaves', levelDb: -44, rate: 0.6, burst: { count: [2, 5], gapMs: [60, 180] }, event: { kind: 'noiseBurst', color: 'white', filter: { type: 'highpass', hz: 2500, q: 0.7 }, ms: [40, 120], lowpassHz: 7000 }, pan: 'random', levelJitterDb: 4 },
    ],
  },
  'winter-yard': {
    id: 'winter-yard',
    reverb: 'outdoor',
    layers: [
      { kind: 'noise', id: 'wind', color: 'pink', filters: [{ type: 'lowpass', hz: 600, q: 0.5 }], levelDb: -34, lfo: { rateHz: [0.06, 0.15], depthDb: 4 } },
      { kind: 'spawn', id: 'hearth', levelDb: -44, rate: 6, event: { kind: 'crackle', ms: [8, 30] }, pan: -0.5, levelJitterDb: 5, lowpassHz: 3000 },
    ],
  },
  brook: { id: 'brook', reverb: 'outdoor', layers: BROOK },
  'waterfall-near': {
    id: 'waterfall-near',
    reverb: 'outdoor',
    layers: [
      { kind: 'noise', id: 'roar', color: 'pink', filters: [{ type: 'lowpass', hz: 2200, q: 0.5 }, { type: 'highpass', hz: 80, q: 0.7 }], levelDb: -24, walk: { db: 3 }, lfo: { rateHz: [0.3, 0.6], depthDb: 2 } },
      { kind: 'noise', id: 'rumble', color: 'brown', filters: [{ type: 'lowpass', hz: 250, q: 0.6 }], levelDb: -28, lfo: { rateHz: [0.2, 0.4], depthDb: 2 } },
      { kind: 'noise', id: 'spray', color: 'white', filters: [{ type: 'bandpass', hz: 4500, q: 0.7 }, { type: 'lowpass', hz: 8000, q: 0.5 }], levelDb: -44, lfo: { rateHz: [0.4, 0.7], depthDb: 3 } },
      { kind: 'spawn', id: 'splashes', levelDb: -34, rate: 3, event: { kind: 'noiseBurst', color: 'white', filter: { type: 'highpass', hz: 900, q: 0.6 }, ms: [60, 150] }, pan: 'random', levelJitterDb: 4 },
    ],
  },
  town: {
    id: 'town',
    reverb: 'outdoor',
    layers: [
      { kind: 'noise', id: 'murmur-low', color: 'pink', filters: [{ type: 'bandpass', hz: 300, q: 1.5 }], levelDb: -35, am: { rateHz: [3, 6], depth: 0.5 }, lfo: { rateHz: [0.1, 0.2], depthDb: 3 } },
      { kind: 'noise', id: 'murmur-mid', color: 'pink', filters: [{ type: 'bandpass', hz: 800, q: 1.5 }], levelDb: -37, am: { rateHz: [3, 6], depth: 0.5 }, lfo: { rateHz: [0.1, 0.25], depthDb: 3 } },
      { kind: 'noise', id: 'murmur-high', color: 'pink', filters: [{ type: 'bandpass', hz: 1600, q: 1.5 }], levelDb: -42, am: { rateHz: [3, 6], depth: 0.5 }, lfo: { rateHz: [0.1, 0.3], depthDb: 3 } },
      { kind: 'spawn', id: 'cart', levelDb: -40, rate: 1 / 40, event: { kind: 'noiseBurst', color: 'brown', filter: { type: 'lowpass', hz: 180, q: 0.5 }, ms: [1800, 3200] }, pan: 'random' },
      { kind: 'spawn', id: 'footsteps', levelDb: -34, rate: 1 / 7, burst: { count: [3, 6], gapMs: [420, 560] }, event: { kind: 'sample', inst: 'foley', art: 'footstep_concrete' }, pan: 'random', pitchCents: 80, levelJitterDb: 3, lowpassHz: 4000 },
      { kind: 'spawn', id: 'far-bell', levelDb: -40, rate: 1 / 180, event: { kind: 'sample', inst: 'tubular-bells', art: 'hit', midi: 67 }, pan: 0.4, lowpassHz: 2500 },
      birds('birds', -42, 1 / 15),
    ],
  },
  market: {
    id: 'market',
    reverb: 'outdoor',
    extends: 'town',
    layers: [
      { kind: 'spawn', id: 'coins', levelDb: -40, rate: 1 / 9, event: { kind: 'sample', inst: 'foley', art: 'handleCoins' }, pan: 'random', pitchCents: 60, levelJitterDb: 3 },
      { kind: 'spawn', id: 'crates', levelDb: -40, rate: 1 / 12, event: { kind: 'sample', inst: 'foley', art: 'impactWood_light' }, pan: 'random', pitchCents: 100, levelJitterDb: 3, lowpassHz: 3500 },
    ],
  },
  shop: {
    id: 'shop',
    reverb: 'room',
    layers: [
      { kind: 'noise', id: 'room', color: 'brown', filters: [{ type: 'lowpass', hz: 300, q: 0.5 }], levelDb: -29 },
      { kind: 'spawn', id: 'clock', levelDb: -29, rate: 1, event: { kind: 'click' }, pan: -0.6 },
    ],
  },
  guild: {
    id: 'guild',
    reverb: 'room',
    layers: [
      { kind: 'noise', id: 'room', color: 'brown', filters: [{ type: 'lowpass', hz: 350, q: 0.5 }], levelDb: -38 },
      { kind: 'noise', id: 'far-crowd', color: 'pink', filters: [{ type: 'bandpass', hz: 500, q: 1.2 }, { type: 'lowpass', hz: 1000, q: 0.5 }], levelDb: -37, am: { rateHz: [3, 5], depth: 0.4 }, lfo: { rateHz: [0.05, 0.12], depthDb: 4 } },
    ],
  },
  library: {
    id: 'library',
    reverb: 'room',
    layers: [
      { kind: 'noise', id: 'room', color: 'brown', filters: [{ type: 'lowpass', hz: 250, q: 0.5 }], levelDb: -29 },
      { kind: 'spawn', id: 'pages', levelDb: -27, rate: 1 / 17, event: { kind: 'sample', inst: 'foley', art: 'bookFlip' }, pan: 'random', pitchCents: 60 },
    ],
  },
  'arena-out': {
    id: 'arena-out',
    reverb: 'outdoor',
    layers: [
      { kind: 'noise', id: 'far-crowd', color: 'pink', filters: [{ type: 'bandpass', hz: 500, q: 1 }, { type: 'lowpass', hz: 1000, q: 0.5 }], levelDb: -38, am: { rateHz: [3, 5], depth: 0.4 }, lfo: { rateHz: [0.05, 0.15], depthDb: 4 } },
      breeze('wind', -42),
      { kind: 'spawn', id: 'flags', levelDb: -46, rate: 0.8, event: { kind: 'noiseBurst', color: 'white', filter: { type: 'bandpass', hz: 1200, q: 0.8 }, ms: [80, 200], lowpassHz: 5000 }, pan: 'random', levelJitterDb: 4 },
    ],
  },
  arena: {
    id: 'arena',
    reverb: 'outdoor',
    layers: [breeze('wind', -36)],
  },
}

/** The crowd layers by size (§9.4). Every crowd sound is lowpassed at 4 kHz or below; no whistles, no voices. */
export const CROWD_SIZES = ['none', 'small', 'medium', 'large', 'large+', 'huge', 'hushed', 'chanting'] as const
export type CrowdSize = (typeof CROWD_SIZES)[number]

interface CrowdShape {
  levelDb: number
  hz: number
  /** A low body band (bigger crowds), dB under the main band; null for none. */
  low?: number
  /** A far band with a slower swell (the biggest crowds), dB under the main band. */
  far?: number
  /** Syllable-rate swell depth (a hushed room barely moves). */
  amDepth?: number
  q?: number
}

function crowdLayers(c: CrowdShape): BedLayer[] {
  const am = c.amDepth ?? 0.35
  const out: BedLayer[] = [
    { kind: 'noise', id: 'crowd', color: 'pink', filters: [{ type: 'bandpass', hz: c.hz, q: c.q ?? 1 }, { type: 'lowpass', hz: 2500, q: 0.5 }], levelDb: c.levelDb, am: { rateHz: [3, 5], depth: am }, lfo: { rateHz: [0.05, 0.15], depthDb: 3 } },
    { kind: 'noise', id: 'crowd-air', color: 'pink', filters: [{ type: 'bandpass', hz: c.hz * 2.5, q: 1.2 }, { type: 'lowpass', hz: 4000, q: 0.5 }], levelDb: c.levelDb - 10, am: { rateHz: [4, 7], depth: am + 0.05 } },
  ]
  if (c.low !== undefined) out.push({ kind: 'noise', id: 'crowd-low', color: 'pink', filters: [{ type: 'bandpass', hz: c.hz * 0.5, q: 0.8 }, { type: 'lowpass', hz: 1200, q: 0.5 }], levelDb: c.levelDb - c.low, am: { rateHz: [2, 3.5], depth: am * 0.8 }, lfo: { rateHz: [0.04, 0.1], depthDb: 3 } })
  if (c.far !== undefined) out.push({ kind: 'noise', id: 'crowd-far', color: 'pink', filters: [{ type: 'bandpass', hz: c.hz * 1.8, q: 0.9 }, { type: 'lowpass', hz: 3000, q: 0.5 }], levelDb: c.levelDb - c.far, am: { rateHz: [1.5, 2.5], depth: am }, lfo: { rateHz: [0.03, 0.08], depthDb: 4 } })
  return out
}

/**
 * §9.4 each crowd size has its own sound and manners: how loud and wide its murmur is, how big its swells
 * are, how it applauds and how many hands clap along in the last ten seconds. The Masquerade's crowd is
 * hushed and polite (applause only); the Summit's chants, clapping on two and four.
 */
export interface CrowdProfile {
  layers: readonly BedLayer[]
  /** Multiplies every reaction's swell. */
  react: number
  /** Polite only: no cheers, gasps or murmurs; a KO gets applause. */
  polite: boolean
  applause: { rate: number; levelDb: number; seconds: number }
  clap: { voices: number; levelDb: number; backbeat: boolean }
}

export const CROWD_PROFILES: Record<CrowdSize, CrowdProfile> = {
  none: { layers: [], react: 0, polite: true, applause: { rate: 0, levelDb: -60, seconds: 0 }, clap: { voices: 0, levelDb: -60, backbeat: false } },
  small: { layers: crowdLayers({ levelDb: -46, hz: 500 }), react: 0.6, polite: false, applause: { rate: 8, levelDb: -42, seconds: 1.2 }, clap: { voices: 3, levelDb: -40, backbeat: false } },
  medium: { layers: crowdLayers({ levelDb: -42, hz: 500, low: 8 }), react: 0.8, polite: false, applause: { rate: 12, levelDb: -40, seconds: 1.4 }, clap: { voices: 5, levelDb: -38, backbeat: false } },
  large: { layers: crowdLayers({ levelDb: -38, hz: 450, low: 7 }), react: 1, polite: false, applause: { rate: 16, levelDb: -38, seconds: 1.6 }, clap: { voices: 7, levelDb: -36, backbeat: false } },
  'large+': { layers: crowdLayers({ levelDb: -36, hz: 450, low: 6, far: 8 }), react: 1.1, polite: false, applause: { rate: 20, levelDb: -37, seconds: 1.8 }, clap: { voices: 9, levelDb: -35, backbeat: false } },
  huge: { layers: crowdLayers({ levelDb: -33, hz: 400, low: 6, far: 8 }), react: 1.25, polite: false, applause: { rate: 26, levelDb: -35, seconds: 2.2 }, clap: { voices: 12, levelDb: -34, backbeat: false } },
  hushed: { layers: crowdLayers({ levelDb: -54, hz: 650, q: 1.6, amDepth: 0.12 }), react: 0, polite: true, applause: { rate: 6, levelDb: -46, seconds: 1 }, clap: { voices: 0, levelDb: -60, backbeat: false } },
  chanting: { layers: crowdLayers({ levelDb: -38, hz: 450, low: 7 }), react: 1, polite: false, applause: { rate: 16, levelDb: -38, seconds: 1.6 }, clap: { voices: 8, levelDb: -35, backbeat: true } },
}

/** The crowd layers by size (the usage graph and the Sound Lab read these). */
export const CROWDS: Record<CrowdSize, readonly BedLayer[]> = Object.fromEntries(Object.entries(CROWD_PROFILES).map(([k, p]) => [k, p.layers])) as Record<CrowdSize, readonly BedLayer[]>

export type CrowdReaction = 'cheer' | 'ooh' | 'murmur' | 'ko' | 'applause' | 'clap'

/** Weather overlays (§9.3). */
export interface WeatherOverlay {
  /** Multiplies the bird layers' rate (0 = none). */
  birds: number
  /** Added to the wind and breeze layers, dB. */
  windDb: number
  add?: readonly BedLayer[]
  /** Everything lowpassed and turned down (snow). */
  muffle?: { lowpassHz: number; db: number }
}

export const WEATHER_OVERLAYS: Record<Weather, WeatherOverlay> = {
  Sunny: { birds: 1.3, windDb: 0 },
  Cloudy: { birds: 0.6, windDb: 3 },
  Rain: {
    birds: 0,
    windDb: 0,
    add: [
      { kind: 'noise', id: 'rain', color: 'pink', filters: [{ type: 'highpass', hz: 400, q: 0.7 }, { type: 'lowpass', hz: 8000, q: 0.5 }], levelDb: -34, lfo: { rateHz: [0.1, 0.2], depthDb: 2 } },
      { kind: 'spawn', id: 'drips', levelDb: -40, rate: 5, event: { kind: 'drip', from: 1500, to: 900, ms: 18 }, pan: 'random', pitchCents: 300, levelJitterDb: 5 },
    ],
  },
  Storm: {
    birds: 0,
    windDb: 4,
    add: [
      { kind: 'noise', id: 'rain', color: 'pink', filters: [{ type: 'highpass', hz: 300, q: 0.7 }, { type: 'lowpass', hz: 8000, q: 0.5 }], levelDb: -30, lfo: { rateHz: [0.1, 0.3], depthDb: 3 } },
      { kind: 'noise', id: 'gusts', color: 'pink', filters: [{ type: 'bandpass', hz: 350, q: 0.5 }], levelDb: -36, lfo: { rateHz: [0.15, 0.35], depthDb: 8 }, walk: { db: 3, hz: 100 } },
      { kind: 'spawn', id: 'thunder', levelDb: -30, rate: 1 / 40, event: { kind: 'thunder' }, pan: 'random' },
    ],
  },
  Snow: { birds: 0, windDb: -2, muffle: { lowpassHz: 3000, db: -3 } },
}

/** The bed's layers with any base bed's first. */
export function bedLayers(id: BedId): BedLayer[] {
  const r = BEDS[id]
  return [...(r.extends ? bedLayers(r.extends) : []), ...r.layers]
}

export function isBedId(id: string): id is BedId {
  return (BED_IDS as readonly string[]).includes(id)
}
