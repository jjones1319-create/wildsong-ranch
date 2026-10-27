import { describe, expect, it } from 'vitest'
import { ELEMENTS } from '../data/types.ts'
import { allowedAtSpeed, DEFAULT_KEY, degreeToMidi } from './engine/sfx.ts'
import { MUSICAL_EFFECTS } from './music/effects.ts'
import { INSTRUMENTS } from './recipes/instruments.ts'
import { battleSfx, strengthOf, UI_SFX, WORLD_SFX, type SfxDef } from './recipes/sfx.ts'

const KINDS = ['fire', 'travel', 'hit', 'crit', 'miss', 'ko', 'special', 'push', 'dash', 'distract', 'wither', 'heal'] as const

function checkDef(id: string, def: SfxDef): void {
  for (const l of def.layers) {
    if (l.kind === 'sample' || l.kind === 'note' || l.kind === 'chord') {
      const inst = INSTRUMENTS[l.inst]
      expect(inst, `${id}: ${l.inst}`).toBeTruthy()
      if (l.art) expect(inst.arts, `${id}: ${l.inst}/${l.art}`).toContain(l.art)
    }
    if (l.kind === 'noise' || l.kind === 'tone') {
      // Soft transients: attacks of at least 2 ms except deliberate impacts (1 ms).
      expect(l.a).toBeGreaterThanOrEqual(1)
      expect(l.d).toBeGreaterThan(0)
    }
    if (l.kind === 'tone') expect(['sine', 'triangle']).toContain(l.wave)
  }
}

describe('the effect recipes (§10)', () => {
  it('UI, world and musical effects name real instruments and articulations', () => {
    for (const [id, def] of Object.entries(UI_SFX)) {
      checkDef(id, def)
      expect(def.bus).toBe('ui')
      expect(def.throttleMs).toBe(60)
    }
    for (const [id, def] of Object.entries(WORLD_SFX)) checkDef(id, def)
    for (const [id, def] of Object.entries(MUSICAL_EFFECTS)) checkDef(id, def)
  })

  it('every battle kind has a recipe for every element and strength, with the §10.1 throttles', () => {
    for (const element of ELEMENTS) {
      for (const kind of KINDS) {
        for (const strength of ['light', 'medium', 'heavy'] as const) {
          const def = battleSfx(kind, element, strength)
          checkDef(`${kind}/${element}/${strength}`, def)
          if (kind !== 'travel' || element !== 'Lightning') expect(def.layers.length, `${kind}/${element}`).toBeGreaterThan(0)
          if (kind === 'hit') expect(def.throttleMs).toBe(50)
          if (kind === 'miss') expect(def.throttleMs).toBe(80)
        }
      }
    }
    // Lightning has no travel sound (§10.3).
    expect(battleSfx('travel', 'Lightning', 'medium').layers).toHaveLength(0)
    // Heavier hits are lower and louder; light ones higher and softer.
    const light = battleSfx('hit', 'Physical', 'light').layers[0] as { gainDb: number }
    const heavy = battleSfx('hit', 'Physical', 'heavy').layers[0] as { gainDb: number }
    expect(heavy.gainDb).toBeGreaterThan(light.gainDb)
  })

  it('strength bands, speed thinning and scale degrees', () => {
    expect(strengthOf(0.1)).toBe('light')
    expect(strengthOf(0.5)).toBe('medium')
    expect(strengthOf(0.9)).toBe('heavy')
    expect(allowedAtSpeed('travel', 'medium', 2)).toBe(false)
    expect(allowedAtSpeed('hit', 'light', 2)).toBe(true)
    expect(allowedAtSpeed('hit', 'light', 4)).toBe(false)
    expect(allowedAtSpeed('hit', 'heavy', 4)).toBe(true)
    expect(allowedAtSpeed('crowd', 'medium', 2)).toBe(false)
    expect(allowedAtSpeed('ko', 'light', 4)).toBe(true)
    // D Lydian: degrees 1, 4, 5, 8 around octave 4 → D4, G#4, A4, D5.
    expect(degreeToMidi(1, 4, DEFAULT_KEY)).toBe(62)
    expect(degreeToMidi(4, 4, DEFAULT_KEY)).toBe(68)
    expect(degreeToMidi(5, 4, DEFAULT_KEY)).toBe(69)
    expect(degreeToMidi(8, 4, DEFAULT_KEY)).toBe(74)
    expect(degreeToMidi(0, 4, DEFAULT_KEY)).toBe(61)
    expect(degreeToMidi(3, 5, { tonic: 7, mode: 'mixolydian' })).toBe(83)
  })

  it('the Echo Stones play four clearly different pitches and the clear phrase ends on the motif', () => {
    const notes = ['echo1', 'echo2', 'echo3', 'echo4'].map((id) => (WORLD_SFX[id as 'echo1'].layers[0] as { degree: number }).degree)
    expect(new Set(notes).size).toBe(4)
    const clear = WORLD_SFX.echoClear.layers.filter((l) => l.kind === 'note' && l.inst === 'harp').map((l) => degreeToMidi((l as { degree: number }).degree, 5, DEFAULT_KEY))
    expect(clear.slice(1).map((p, i) => p - clear[i]!)).toEqual([2, 5, -1, -2, -2])
  })
})
