/**
 * SOUND_UPGRADE §10: the sound-effect recipes. Natural sources only: samples, Foley, filtered noise, sine
 * and triangle. Soft transients, every sound fades out. An effect is a list of layers; pitched layers that
 * follow the playing song's key use scale degrees. The engine (`engine/sfx.ts`) performs them with ±3%
 * pitch and ±1.5 dB variation on noise and Foley, ±10 cents on pitched layers, alternate takes, throttles
 * per id and a 16-voice pool. Pure data.
 */
import type { Element } from '../../data/types.ts'
import type { FxEventKind } from '../../fx/bus.ts'
import type { FilterSpec, NoiseColor } from './ambience.ts'
import type { InstrumentId } from './instruments.ts'

export type SfxBus = 'sfx' | 'ui'

export type SfxLayer =
  | { kind: 'noise'; color: NoiseColor; filter?: FilterSpec; sweepTo?: number; a: number; h?: number; d: number; gainDb?: number; delay?: number; lowpassHz?: number; am?: number; reverse?: boolean }
  | { kind: 'tone'; wave: 'sine' | 'triangle'; hz: number; to?: number; a: number; h?: number; d: number; gainDb?: number; delay?: number; detune?: number; lowpassHz?: number }
  | { kind: 'sample'; inst: InstrumentId; art?: string; midi?: number; vel?: number; gainDb?: number; delay?: number; cents?: number; lowpassHz?: number }
  | { kind: 'note'; inst: InstrumentId; art?: string; degree: number; octave?: number; dur: number; vel?: number; gainDb?: number; delay?: number; detune?: number; rateRamp?: number; semis?: number }
  | { kind: 'chord'; inst: InstrumentId; art?: string; degrees: readonly number[]; octave?: number; dur: number; vel?: number; gainDb?: number; delay?: number; rollMs?: number }

export interface SfxDef {
  bus: SfxBus
  layers: readonly SfxLayer[]
  /** Minimum gap between two plays of this id, ms (§10.1 throttles). */
  throttleMs?: number
  /** True peak ceiling hint: the engine scales the whole effect by this trim, dB. */
  trimDb?: number
}

const ms = (n: number) => n

/* ---------- UI (§10.2) ---------- */

export const UI_SFX_IDS = ['tap', 'select', 'back', 'toggleOn', 'toggleOff', 'deny', 'sheetOpen', 'sheetClose', 'tab'] as const
export type UiSfxId = (typeof UI_SFX_IDS)[number]

export const UI_SFX: Record<UiSfxId, SfxDef> = {
  tap: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'sample', inst: 'marimba', midi: 72, vel: 0.25, lowpassHz: 2500, gainDb: -6 }] },
  select: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'sample', inst: 'kalimba', midi: 79, vel: 0.28, lowpassHz: 3000, gainDb: -6 }] },
  back: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'sample', inst: 'marimba', midi: 65, vel: 0.25, lowpassHz: 2200, gainDb: -6 }] },
  toggleOn: {
    bus: 'ui',
    throttleMs: 60,
    layers: [
      { kind: 'sample', inst: 'marimba', midi: 67, vel: 0.25, lowpassHz: 2500, gainDb: -6 },
      { kind: 'sample', inst: 'marimba', midi: 74, vel: 0.25, lowpassHz: 2500, gainDb: -6, delay: 0.07 },
    ],
  },
  toggleOff: {
    bus: 'ui',
    throttleMs: 60,
    layers: [
      { kind: 'sample', inst: 'marimba', midi: 74, vel: 0.25, lowpassHz: 2500, gainDb: -6 },
      { kind: 'sample', inst: 'marimba', midi: 67, vel: 0.25, lowpassHz: 2500, gainDb: -6, delay: 0.07 },
    ],
  },
  deny: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'noise', color: 'brown', filter: { type: 'lowpass', hz: 250, q: 0.7 }, a: 3, d: ms(45), gainDb: -14 }] },
  sheetOpen: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'sample', inst: 'foley', art: 'cloth', vel: 0.6, gainDb: 8, lowpassHz: 5000 }] },
  sheetClose: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'sample', inst: 'foley', art: 'cloth', vel: 0.6, gainDb: 8, cents: -300, lowpassHz: 4000 }] },
  tab: { bus: 'ui', throttleMs: 60, layers: [{ kind: 'sample', inst: 'foley', art: 'bookFlip', vel: 0.6, gainDb: 12, lowpassHz: 5000 }] },
}

/* ---------- the world (§10.4) ---------- */

export const WORLD_SFX_IDS = ['stoneHum', 'echo1', 'echo2', 'echo3', 'echo4', 'echoClear', 'echoWrong', 'timerTick', 'stun', 'reflect', 'recoil', 'jackpotDouble', 'jackpotHeal', 'jackpotFizzle', 'traitDragonheart', 'pause'] as const
export type WorldSfxId = (typeof WORLD_SFX_IDS)[number]

const ECHO_DEGREES = [1, 3, 5, 7] as const

function echoNote(i: number): SfxDef {
  // The four stones: ocarina plus a hand chime, in the Wildsong key (D Lydian), four clearly different pitches.
  const degree = ECHO_DEGREES[i]!
  return {
    bus: 'sfx',
    throttleMs: 80,
    layers: [
      { kind: 'note', inst: 'ocarina', art: 'sus', degree, octave: 5, dur: 0.45, vel: 0.55, gainDb: -4 },
      { kind: 'note', inst: 'hand-chimes', degree, octave: 5, dur: 0.8, vel: 0.4, gainDb: -10 },
    ],
  }
}

export const WORLD_SFX: Record<WorldSfxId, SfxDef> = {
  stoneHum: {
    bus: 'sfx',
    throttleMs: 350,
    layers: [
      { kind: 'note', inst: 'vibes', art: 'bowed', degree: 1, octave: 3, dur: 1.6, vel: 0.5, gainDb: -6 },
      { kind: 'note', inst: 'vibes', art: 'bowed', degree: 5, octave: 3, dur: 1.6, vel: 0.45, gainDb: -8, delay: 0.1 },
      { kind: 'note', inst: 'hand-chimes', degree: 8, octave: 4, dur: 1.2, vel: 0.35, gainDb: -12, delay: 0.6 },
      { kind: 'note', inst: 'hand-chimes', degree: 12, octave: 4, dur: 1.2, vel: 0.3, gainDb: -14, delay: 0.9 },
    ],
  },
  echo1: echoNote(0),
  echo2: echoNote(1),
  echo3: echoNote(2),
  echo4: echoNote(3),
  echoClear: {
    bus: 'sfx',
    throttleMs: 200,
    // A harp phrase ending on the Wildsong motif (D E A G# F# E, as degrees of D Lydian: 1 2 5 4 3 2).
    layers: [
      { kind: 'note', inst: 'harp', degree: 1, octave: 5, dur: 0.3, vel: 0.5, gainDb: -6 },
      { kind: 'note', inst: 'harp', degree: 2, octave: 5, dur: 0.3, vel: 0.5, gainDb: -6, delay: 0.18 },
      { kind: 'note', inst: 'harp', degree: 5, octave: 5, dur: 0.4, vel: 0.55, gainDb: -6, delay: 0.36 },
      { kind: 'note', inst: 'harp', degree: 4, octave: 5, dur: 0.3, vel: 0.5, gainDb: -6, delay: 0.72 },
      { kind: 'note', inst: 'harp', degree: 3, octave: 5, dur: 0.3, vel: 0.5, gainDb: -6, delay: 0.9 },
      { kind: 'note', inst: 'harp', degree: 2, octave: 5, dur: 0.9, vel: 0.55, gainDb: -6, delay: 1.08 },
      { kind: 'note', inst: 'hand-chimes', degree: 2, octave: 5, dur: 0.9, vel: 0.35, gainDb: -12, delay: 1.08 },
    ],
  },
  echoWrong: { bus: 'sfx', throttleMs: 80, layers: [{ kind: 'noise', color: 'brown', filter: { type: 'lowpass', hz: 220, q: 0.7 }, a: 3, d: ms(70), gainDb: -12 }] },
  timerTick: { bus: 'sfx', throttleMs: 200, layers: [{ kind: 'sample', inst: 'woodblock', vel: 0.5, gainDb: 4, lowpassHz: 3000 }] },
  stun: {
    bus: 'sfx',
    throttleMs: 150,
    layers: [
      { kind: 'note', inst: 'harp', degree: 5, octave: 5, dur: 0.3, vel: 0.5, gainDb: -8, detune: 30 },
      { kind: 'note', inst: 'harp', degree: 4, octave: 5, dur: 0.3, vel: 0.5, gainDb: -8, detune: -35, delay: 0.12 },
      { kind: 'note', inst: 'harp', degree: 5, octave: 5, dur: 0.5, vel: 0.5, gainDb: -8, detune: 25, delay: 0.24 },
    ],
  },
  reflect: { bus: 'sfx', throttleMs: 100, layers: [{ kind: 'tone', wave: 'sine', hz: 2200, a: 3, d: ms(110), gainDb: -16, lowpassHz: 3000 }] },
  recoil: { bus: 'sfx', throttleMs: 100, layers: [{ kind: 'sample', inst: 'foley', art: 'impactSoft_medium', vel: 0.6, gainDb: 10, lowpassHz: 4000 }] },
  jackpotDouble: {
    bus: 'sfx',
    throttleMs: 200,
    layers: [1, 3, 5, 8].map((degree, i) => ({ kind: 'note' as const, inst: 'music-box' as const, degree, octave: 5, dur: 0.4, vel: 0.45, gainDb: -8, delay: i * 0.09 })),
  },
  jackpotHeal: {
    bus: 'sfx',
    throttleMs: 200,
    layers: [1, 5, 8].map((degree, i) => ({ kind: 'note' as const, inst: 'harp' as const, degree, octave: 4, dur: 0.5, vel: 0.5, gainDb: -6, delay: i * 0.1 })),
  },
  jackpotFizzle: { bus: 'sfx', throttleMs: 200, layers: [{ kind: 'note', inst: 'kalimba', degree: 5, octave: 5, dur: 0.5, vel: 0.45, gainDb: -8, rateRamp: 0.8 }] },
  traitDragonheart: { bus: 'sfx', throttleMs: 300, layers: [{ kind: 'note', inst: 'horn', art: 'sus', degree: 1, octave: 3, dur: 0.9, vel: 0.5, gainDb: -8 }] },
  pause: { bus: 'ui', throttleMs: 100, layers: [{ kind: 'sample', inst: 'marimba', midi: 60, vel: 0.22, lowpassHz: 2000, gainDb: -8 }] },
}

/* ---------- battle (§10.3) ---------- */

export type Strength = 'light' | 'medium' | 'heavy'

export function strengthOf(share: number): Strength {
  // `share` is the FxEvent strength (0..1, heavyHitPct ≈ 0.75); light < 8% ≈ 0.33, heavy > 18% ≈ 0.75.
  return share < 0.33 ? 'light' : share >= 0.75 ? 'heavy' : 'medium'
}

interface ElementSet {
  cast: SfxLayer[]
  travel: SfxLayer[]
  impact: SfxLayer[]
}

const noise = (color: NoiseColor, filter: FilterSpec | undefined, a: number, d: number, gainDb: number, extra: Partial<Extract<SfxLayer, { kind: 'noise' }>> = {}): SfxLayer => ({ kind: 'noise', color, filter, a, d, gainDb, ...extra })
const tone = (wave: 'sine' | 'triangle', hz: number, a: number, d: number, gainDb: number, extra: Partial<Extract<SfxLayer, { kind: 'tone' }>> = {}): SfxLayer => ({ kind: 'tone', wave, hz, a, d, gainDb, ...extra })
const sample = (inst: InstrumentId, art: string | undefined, gainDb: number, extra: Partial<Extract<SfxLayer, { kind: 'sample' }>> = {}): SfxLayer => ({ kind: 'sample', inst, art, gainDb, ...extra })
const note = (inst: InstrumentId, degree: number, octave: number, dur: number, gainDb: number, extra: Partial<Extract<SfxLayer, { kind: 'note' }>> = {}): SfxLayer => ({ kind: 'note', inst, degree, octave, dur, gainDb, ...extra })

const ELEMENT_SFX: Record<Element, ElementSet> = {
  Physical: {
    cast: [sample('foley', 'cloth', -14, { lowpassHz: 5000 }), sample('foley', 'footstep_grass', -16, { delay: 0.05, lowpassHz: 4000 })],
    travel: [noise('white', { type: 'bandpass', hz: 300, q: 1 }, 10, 120, -18, { sweepTo: 1200 })],
    impact: [tone('sine', 90, 2, 120, -8, { to: 55 }), sample('foley', 'impactPunch_medium', -10, { lowpassHz: 5000 })],
  },
  Fire: {
    cast: [noise('pink', { type: 'lowpass', hz: 400, q: 0.6 }, 40, 250, -14, { sweepTo: 2500 }), noise('white', { type: 'highpass', hz: 2000, q: 0.7 }, 2, 25, -22, { delay: 0.08 }), noise('white', { type: 'highpass', hz: 2200, q: 0.7 }, 2, 20, -24, { delay: 0.16 })],
    travel: [noise('pink', { type: 'lowpass', hz: 1500, q: 0.6 }, 30, 300, -16, { am: 25 })],
    impact: [noise('brown', { type: 'lowpass', hz: 900, q: 0.6 }, 3, 200, -8), noise('white', { type: 'highpass', hz: 2000, q: 0.7 }, 2, 30, -20, { delay: 0.12 }), noise('white', { type: 'highpass', hz: 2500, q: 0.7 }, 2, 20, -22, { delay: 0.22 })],
  },
  Water: {
    cast: [tone('sine', 500, 3, 25, -16, { to: 1400 }), tone('sine', 600, 3, 25, -17, { to: 1500, delay: 0.06 }), tone('sine', 450, 3, 25, -18, { to: 1300, delay: 0.13 })],
    travel: [noise('pink', { type: 'bandpass', hz: 800, q: 0.8 }, 30, 300, -16)],
    impact: [noise('white', { type: 'highpass', hz: 800, q: 0.7 }, 3, 150, -10), tone('sine', 1500, 3, 30, -18, { to: 900, delay: 0.1 }), tone('sine', 1300, 3, 30, -20, { to: 800, delay: 0.17 })],
  },
  Ice: {
    cast: [sample('hand-chimes', undefined, -18, { midi: 96, vel: 0.35 }), sample('hand-chimes', undefined, -20, { midi: 100, vel: 0.3, delay: 0.09 })],
    travel: [noise('white', { type: 'lowpass', hz: 4000, q: 0.5 }, 30, 250, -24)],
    impact: [tone('sine', 2100, 2, 120, -14, { lowpassHz: 6000 }), tone('sine', 3300, 2, 100, -16, { lowpassHz: 6000 }), tone('sine', 4700, 2, 80, -18, { lowpassHz: 6000 }), noise('white', { type: 'bandpass', hz: 1500, q: 1 }, 2, 60, -14)],
  },
  Lightning: {
    cast: [noise('white', { type: 'lowpass', hz: 3000, q: 0.5 }, 20, 150, -24)],
    travel: [],
    impact: [noise('white', { type: 'bandpass', hz: 1200, q: 1 }, 1, 45, -8), noise('brown', { type: 'lowpass', hz: 150, q: 0.6 }, 10, 420, -12, { delay: 0.03 })],
  },
  Wind: {
    cast: [noise('pink', { type: 'bandpass', hz: 500, q: 0.6 }, 200, 300, -16)],
    travel: [noise('pink', { type: 'bandpass', hz: 300, q: 0.7 }, 20, 250, -16, { sweepTo: 900 })],
    impact: [noise('brown', { type: 'lowpass', hz: 300, q: 0.6 }, 3, 150, -10), noise('white', { type: 'highpass', hz: 2500, q: 0.7 }, 3, 60, -20, { delay: 0.08 }), noise('white', { type: 'highpass', hz: 2500, q: 0.7 }, 3, 50, -22, { delay: 0.16 })],
  },
  Earth: {
    cast: [noise('brown', { type: 'lowpass', hz: 150, q: 0.6 }, 30, 300, -12)],
    travel: [sample('woodblock', undefined, -14, { cents: -700 }), sample('woodblock', undefined, -15, { cents: -600, delay: 0.09 }), sample('woodblock', undefined, -16, { cents: -800, delay: 0.19 })],
    impact: [sample('foley', 'impactMining', -8, { lowpassHz: 3500, cents: -300 }), noise('white', { type: 'lowpass', hz: 1500, q: 0.5 }, 2, 40, -22, { delay: 0.12 }), noise('white', { type: 'lowpass', hz: 1500, q: 0.5 }, 2, 35, -24, { delay: 0.2 })],
  },
  Nature: {
    cast: [noise('white', { type: 'highpass', hz: 2500, q: 0.7 }, 10, 150, -20), tone('triangle', 180, 60, 200, -22, { to: 260, lowpassHz: 2500 })],
    travel: [noise('white', { type: 'bandpass', hz: 600, q: 1 }, 10, 150, -18, { sweepTo: 1500 })],
    impact: [sample('foley', 'impactSoft_medium', -9, { lowpassHz: 4500 }), note('kalimba', 8, 5, 0.3, -18, { vel: 0.4, delay: 0.05 })],
  },
  Light: {
    cast: [note('harp', 1, 5, 0.3, -14, { vel: 0.4 }), note('harp', 3, 5, 0.3, -14, { vel: 0.4, delay: 0.05 }), note('harp', 5, 5, 0.3, -14, { vel: 0.4, delay: 0.1 }), note('harp', 8, 5, 0.4, -14, { vel: 0.4, delay: 0.15 })],
    travel: [noise('white', { type: 'bandpass', hz: 6000, q: 1 }, 120, 250, -26)],
    impact: [note('hand-chimes', 8, 5, 0.7, -12, { vel: 0.5 }), noise('white', { type: 'highpass', hz: 3000, q: 0.7 }, 2, 60, -16)],
  },
  Dark: {
    cast: [noise('pink', { type: 'lowpass', hz: 800, q: 0.6 }, 300, 50, -14, { reverse: true })],
    travel: [noise('brown', { type: 'bandpass', hz: 200, q: 0.8 }, 20, 250, -12)],
    impact: [noise('brown', { type: 'lowpass', hz: 300, q: 0.6 }, 3, 100, -8), tone('sine', 55, 20, 500, -18)],
  },
  Sound: {
    cast: [note('ocarina', 1, 5, 0.09, -10, { vel: 0.5 }), note('ocarina', 3, 5, 0.09, -10, { vel: 0.5, delay: 0.1 }), note('ocarina', 5, 5, 0.14, -10, { vel: 0.5, delay: 0.2 })],
    travel: [note('vibes', 5, 5, 0.3, -14, { vel: 0.45 })],
    impact: [{ kind: 'chord', inst: 'harp', degrees: [1, 3, 5, 8], octave: 4, dur: 0.5, vel: 0.5, gainDb: -10, rollMs: 18 }, note('hand-chimes', 8, 5, 0.6, -14, { vel: 0.4, delay: 0.05 })],
  },
}

function scaled(layers: readonly SfxLayer[], gainDb: number, cents: number, timeScale: number): SfxLayer[] {
  return layers.map((l) => {
    const g = (l.gainDb ?? 0) + gainDb
    switch (l.kind) {
      case 'noise':
        return { ...l, gainDb: g, d: l.d * timeScale, filter: l.filter ? { ...l.filter, hz: l.filter.hz * Math.pow(2, cents / 1200) } : undefined, sweepTo: l.sweepTo ? l.sweepTo * Math.pow(2, cents / 1200) : undefined }
      case 'tone':
        return { ...l, gainDb: g, d: l.d * timeScale, hz: l.hz * Math.pow(2, cents / 1200), to: l.to ? l.to * Math.pow(2, cents / 1200) : undefined }
      case 'sample':
        return { ...l, gainDb: g, cents: (l.cents ?? 0) + cents }
      case 'note':
        return { ...l, gainDb: g, dur: l.dur * timeScale }
      case 'chord':
        return { ...l, gainDb: g, dur: l.dur * timeScale }
    }
  })
}

/** The effect for a battle FxEvent kind, by element and strength (§10.3). */
export function battleSfx(kind: FxEventKind, element: Element, strength: Strength, crit = false): SfxDef {
  const set = ELEMENT_SFX[element]
  const byStrength = (layers: readonly SfxLayer[]) => (strength === 'light' ? scaled(layers, -3, 200, 0.75) : strength === 'heavy' ? scaled(layers, 2, -200, 1.3) : [...layers])
  switch (kind) {
    case 'fire':
      return { bus: 'sfx', throttleMs: 50, layers: set.cast }
    case 'travel':
      return { bus: 'sfx', throttleMs: 50, layers: set.travel }
    case 'hit':
      return { bus: 'sfx', throttleMs: 50, layers: byStrength(set.impact) }
    case 'crit':
      return {
        bus: 'sfx',
        throttleMs: 50,
        layers: [...scaled(set.impact, 2, -200, 1.3), noise('white', { type: 'lowpass', hz: 5000, q: 0.5 }, 1, 15, -6), tone('sine', 80, 2, 160, -8, { to: 45, delay: 0.01 })],
      }
    case 'miss':
      return { bus: 'sfx', throttleMs: 80, layers: [noise('white', { type: 'bandpass', hz: 1200, q: 1 }, 10, 90, -22, { sweepTo: 600 })] }
    case 'ko':
      return { bus: 'sfx', throttleMs: 50, layers: [tone('sine', 70, 3, 300, -4, { to: 40 }), noise('brown', { type: 'lowpass', hz: 200, q: 0.6 }, 3, 260, -8), sample('foley', 'impactSoft_heavy', -8, { lowpassHz: 3000 })] }
    case 'special':
      return { bus: 'sfx', throttleMs: 50, layers: [...scaled(set.cast, 2, 0, 2), noise('pink', { type: 'bandpass', hz: 400, q: 0.7 }, 150, 500, -14, { sweepTo: 1600 })] }
    case 'push':
      return { bus: 'sfx', throttleMs: 50, layers: [sample('foley', 'impactSoft_heavy', -10, { lowpassHz: 4000 }), noise('white', { type: 'bandpass', hz: 900, q: 1 }, 20, 150, -20, { delay: 0.04 })] }
    case 'dash':
      return { bus: 'sfx', throttleMs: 50, layers: [sample('foley', 'footstep_grass', -14), sample('foley', 'footstep_grass', -14, { delay: 0.09 }), sample('foley', 'footstep_grass', -15, { delay: 0.18 })] }
    case 'distract':
      return { bus: 'sfx', throttleMs: 50, layers: [note('kalimba', 5, 5, 0.25, -12, { vel: 0.45 }), note('kalimba', 6, 5, 0.35, -12, { vel: 0.45, delay: 0.16 })] }
    case 'wither':
      return { bus: 'sfx', throttleMs: 50, layers: [noise('pink', { type: 'bandpass', hz: 1200, q: 1 }, 30, 500, -18, { sweepTo: 300 }), tone('triangle', 110, 40, 500, -20, { detune: -20, lowpassHz: 800 })] }
    case 'heal':
      return { bus: 'sfx', throttleMs: 50, layers: [note('harp', 1, 4, 0.4, -12, { vel: 0.45 }), note('harp', 3, 4, 0.4, -12, { vel: 0.45, delay: 0.08 }), note('harp', 5, 4, 0.4, -12, { vel: 0.45, delay: 0.16 }), note('harp', 8, 4, 0.5, -12, { vel: 0.45, delay: 0.24 }), note('hand-chimes', 8, 5, 0.6, -16, { vel: 0.4, delay: 0.3 })] }
  }
  void crit
  return { bus: 'sfx', layers: [] }
}
