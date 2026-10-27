/**
 * SOUND_UPGRADE §7.6: the musical effects (≤ 1.5 s). They play on the effects bus, over the music,
 * transposed into the playing song's key and mode: every pitched layer is a scale degree. They duck
 * nothing and never restart the music. S1 wrote the eleven everyday ones; S2 adds the rival calling cards
 * (§3.6), one 3–5 note phrase per named rival on their own instrument, played over the cup lobby when the
 * round preview shows them; the fusion and expedition cues (S3) come later. All original.
 */
import type { SfxDef, SfxLayer } from '../recipes/sfx.ts'

export const MUSICAL_EFFECT_IDS = ['coin', 'buy', 'mail', 'itemGet', 'sweet', 'learnTechnique', 'plannerStop', 'growUp', 'prime', 'weekStart', 'wrenReport'] as const
export const CALLING_CARD_IDS = ['card-corin-hale', 'card-marigold-finch', 'card-brannock-steele', 'card-wisteria-vane', 'card-juno-quell', 'card-old-man-garrow', 'card-captain-saltmarsh', 'card-ember-rook', 'card-masked-breeder'] as const
export type CallingCardId = (typeof CALLING_CARD_IDS)[number]

export type MusicalEffectId = (typeof MUSICAL_EFFECT_IDS)[number] | CallingCardId

const harp = (degree: number, delay: number, dur = 0.4, vel = 0.5, gainDb = -8): SfxLayer => ({ kind: 'note', inst: 'harp', degree, octave: 5, dur, vel, gainDb, delay })
const glock = (degree: number, delay: number, dur = 0.5, vel = 0.3, gainDb = -14): SfxLayer => ({ kind: 'note', inst: 'glock', degree, octave: 6, dur, vel, gainDb, delay })
const kalimba = (degree: number, delay: number, dur = 0.35, vel = 0.45, gainDb = -10): SfxLayer => ({ kind: 'note', inst: 'kalimba', degree, octave: 5, dur, vel, gainDb, delay })
const ocarina = (degree: number, delay: number, dur: number, vel = 0.5, gainDb = -8): SfxLayer => ({ kind: 'note', inst: 'ocarina', art: 'sus', degree, octave: 5, dur, vel, gainDb, delay })

export const MUSICAL_EFFECTS: Record<(typeof MUSICAL_EFFECT_IDS)[number], SfxDef> = {
  coin: { bus: 'sfx', throttleMs: 60, layers: [glock(5, 0, 0.4, 0.3), { kind: 'sample', inst: 'foley', art: 'handleCoins', gainDb: -16, lowpassHz: 5000 }] },
  buy: { bus: 'sfx', throttleMs: 60, layers: [glock(1, 0, 0.5, 0.3), glock(5, 0.1, 0.5, 0.28), { kind: 'sample', inst: 'foley', art: 'handleCoins', gainDb: -16, lowpassHz: 5000, delay: 0.05 }] },
  mail: { bus: 'sfx', throttleMs: 200, layers: [{ kind: 'sample', inst: 'mark-trees', gainDb: -18, lowpassHz: 7000 }, { kind: 'note', inst: 'hand-chimes', degree: 5, octave: 5, dur: 0.9, vel: 0.4, gainDb: -12, delay: 0.25 }] },
  itemGet: { bus: 'sfx', throttleMs: 100, layers: [harp(1, 0), harp(3, 0.07), harp(5, 0.14), harp(8, 0.21, 0.6), glock(8, 0.21, 0.6, 0.3)] },
  sweet: { bus: 'sfx', throttleMs: 100, layers: [kalimba(3, 0), kalimba(5, 0.1), kalimba(8, 0.2, 0.5)] },
  learnTechnique: {
    bus: 'sfx',
    throttleMs: 300,
    layers: [{ kind: 'chord', inst: 'harp', degrees: [1, 3, 5], octave: 4, dur: 1.4, vel: 0.45, gainDb: -10, rollMs: 20 }, ocarina(3, 0.1, 0.22), ocarina(5, 0.34, 0.22), ocarina(6, 0.58, 0.22), ocarina(8, 0.82, 0.6)],
  },
  plannerStop: { bus: 'sfx', throttleMs: 200, layers: [harp(5, 0, 0.4, 0.45), harp(1, 0.22, 0.6, 0.45)] },
  growUp: {
    bus: 'sfx',
    throttleMs: 300,
    layers: [harp(1, 0, 0.4, 0.5), harp(3, 0.1, 0.4, 0.5), harp(5, 0.2, 0.5, 0.5), { kind: 'note', inst: 'horn', art: 'sus', degree: 1, octave: 3, dur: 0.5, vel: 0.5, gainDb: -10, delay: 0.1 }, { kind: 'note', inst: 'horn', art: 'sus', degree: 5, octave: 3, dur: 0.8, vel: 0.55, gainDb: -9, delay: 0.55 }],
  },
  prime: {
    bus: 'sfx',
    throttleMs: 300,
    layers: [{ kind: 'chord', inst: 'harp', degrees: [1, 5, 8, 10], octave: 4, dur: 1.3, vel: 0.5, gainDb: -9, rollMs: 25 }, { kind: 'chord', inst: 'violas', art: 'vib', degrees: [1, 5], octave: 3, dur: 1.2, vel: 0.4, gainDb: -14, delay: 0.05 }],
  },
  weekStart: { bus: 'sfx', throttleMs: 300, layers: [{ kind: 'tone', wave: 'sine', hz: 2600, to: 3400, a: 5, d: 90, gainDb: -26, lowpassHz: 6000 }, { kind: 'tone', wave: 'sine', hz: 3100, to: 2700, a: 5, d: 70, gainDb: -27, lowpassHz: 6000, delay: 0.14 }, { kind: 'chord', inst: 'harp', degrees: [1, 5, 10], octave: 4, dur: 1.2, vel: 0.4, gainDb: -12, rollMs: 22, delay: 0.1 }] },
  wrenReport: { bus: 'sfx', throttleMs: 200, layers: [kalimba(5, 0, 0.3, 0.4), kalimba(3, 0.16, 0.4, 0.4)] },
}

/** A short phrase of notes on one instrument: [degree, seconds after the start, length], with optional semitone bends. */
function phrase(inst: Extract<SfxLayer, { kind: 'note' }>['inst'], octave: number, notes: readonly (readonly [number, number, number, number?])[], o: { art?: string; vel?: number; gainDb?: number } = {}): SfxLayer[] {
  return notes.map(([degree, delay, dur, semis]) => note(inst, degree, octave, delay, dur, o, semis))
}

function note(inst: Extract<SfxLayer, { kind: 'note' }>['inst'], degree: number, octave: number, delay: number, dur: number, o: { art?: string; vel?: number; gainDb?: number }, semis?: number): SfxLayer {
  const l: Extract<SfxLayer, { kind: 'note' }> = { kind: 'note', inst, degree, octave, dur, vel: o.vel ?? 0.5, gainDb: o.gainDb ?? -8, delay }
  if (o.art) l.art = o.art
  if (semis) l.semis = semis
  return l
}

/**
 * The rival calling cards (§3.6). Corin climbs his own cocky motif (1–3–5–8); the Masked Breeder turns the
 * masked chromatic figure on a harpsichord; the others each have their instrument and a shape that fits them.
 */
export const CALLING_CARDS: Record<CallingCardId, SfxDef> = {
  'card-corin-hale': {
    bus: 'sfx',
    throttleMs: 400,
    layers: [
      ...phrase('strumstick', 4, [[1, 0, 0.14], [3, 0.11, 0.14], [5, 0.22, 0.14], [8, 0.33, 0.6]], { vel: 0.55, gainDb: -7 }),
      note('violins', 1, 4, 0, 0.2, { art: 'pizz', vel: 0.45, gainDb: -13 }),
      note('violins', 8, 4, 0.33, 0.4, { art: 'pizz', vel: 0.45, gainDb: -13 }),
    ],
  },
  'card-marigold-finch': { bus: 'sfx', throttleMs: 400, layers: phrase('flute', 5, [[5, 0, 0.22], [6, 0.2, 0.22], [5, 0.4, 0.22], [3, 0.6, 0.6]], { art: 'sus', vel: 0.5, gainDb: -2 }) },
  'card-brannock-steele': { bus: 'sfx', throttleMs: 400, layers: phrase('cellos', 3, [[1, 0, 0.15], [1, 0.18, 0.15], [-3, 0.36, 0.15], [1, 0.54, 0.45]], { art: 'spic', vel: 0.6, gainDb: -6 }) },
  'card-wisteria-vane': { bus: 'sfx', throttleMs: 400, layers: phrase('vibes', 5, [[8, 0, 0.3], [5, 0.25, 0.3], [3, 0.5, 0.8]], { vel: 0.45, gainDb: -8 }) },
  'card-juno-quell': { bus: 'sfx', throttleMs: 400, layers: phrase('clarinet', 4, [[5, 0, 0.14], [4, 0.15, 0.14, 1], [5, 0.3, 0.18], [3, 0.5, 0.6]], { art: 'sus', vel: 0.5, gainDb: -2 }) },
  'card-old-man-garrow': { bus: 'sfx', throttleMs: 400, layers: phrase('recorder-tenor', 4, [[1, 0, 0.42], [2, 0.4, 0.42], [3, 0.8, 0.65]], { art: 'sus', vel: 0.42, gainDb: -8 }) },
  'card-captain-saltmarsh': { bus: 'sfx', throttleMs: 400, layers: phrase('horn', 3, [[1, 0, 0.25], [5, 0.25, 0.25], [8, 0.5, 0.7]], { art: 'sus', vel: 0.5, gainDb: -8 }) },
  'card-ember-rook': { bus: 'sfx', throttleMs: 400, layers: phrase('kalimba', 5, [[1, 0, 0.1], [2, 0.08, 0.1], [3, 0.16, 0.1], [5, 0.24, 0.5]], { vel: 0.5, gainDb: -5 }) },
  'card-masked-breeder': { bus: 'sfx', throttleMs: 400, layers: phrase('harpsichord', 4, [[1, 0, 0.12], [1, 0.12, 0.12, 1], [1, 0.24, 0.12], [1, 0.36, 0.12, -1], [1, 0.48, 0.5]], { vel: 0.5, gainDb: -8 }) },
}

/** The calling card for a rival id, if they have one. */
export function callingCardFor(rivalId: string | null | undefined): CallingCardId | null {
  if (!rivalId) return null
  const id = `card-${rivalId}` as CallingCardId
  return (CALLING_CARD_IDS as readonly string[]).includes(id) ? id : null
}

/** Any musical effect by id: the everyday ones and the calling cards. */
export function musicalEffectDef(id: string): SfxDef | null {
  if (id in MUSICAL_EFFECTS) return MUSICAL_EFFECTS[id as keyof typeof MUSICAL_EFFECTS]
  if (id in CALLING_CARDS) return CALLING_CARDS[id as CallingCardId]
  return null
}
