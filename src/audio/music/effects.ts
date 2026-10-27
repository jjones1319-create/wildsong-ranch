/**
 * SOUND_UPGRADE §7.6: the musical effects (≤ 1.5 s). They play on the effects bus, over the music,
 * transposed into the playing song's key and mode: every pitched layer is a scale degree. They duck
 * nothing and never restart the music. S1 writes the eleven listed here; the rival calling cards (S2) and
 * the fusion and expedition cues (S3) come later. All original.
 */
import type { SfxDef, SfxLayer } from '../recipes/sfx.ts'

export const MUSICAL_EFFECT_IDS = ['coin', 'buy', 'mail', 'itemGet', 'sweet', 'learnTechnique', 'plannerStop', 'growUp', 'prime', 'weekStart', 'wrenReport'] as const
export type MusicalEffectId = (typeof MUSICAL_EFFECT_IDS)[number]

const harp = (degree: number, delay: number, dur = 0.4, vel = 0.5, gainDb = -8): SfxLayer => ({ kind: 'note', inst: 'harp', degree, octave: 5, dur, vel, gainDb, delay })
const glock = (degree: number, delay: number, dur = 0.5, vel = 0.3, gainDb = -14): SfxLayer => ({ kind: 'note', inst: 'glock', degree, octave: 6, dur, vel, gainDb, delay })
const kalimba = (degree: number, delay: number, dur = 0.35, vel = 0.45, gainDb = -10): SfxLayer => ({ kind: 'note', inst: 'kalimba', degree, octave: 5, dur, vel, gainDb, delay })
const ocarina = (degree: number, delay: number, dur: number, vel = 0.5, gainDb = -8): SfxLayer => ({ kind: 'note', inst: 'ocarina', art: 'sus', degree, octave: 5, dur, vel, gainDb, delay })

export const MUSICAL_EFFECTS: Record<MusicalEffectId, SfxDef> = {
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
