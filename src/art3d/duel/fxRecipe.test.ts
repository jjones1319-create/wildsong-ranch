import { describe, expect, it } from 'vitest'
import { pathOf } from '../../data/paths.ts'
import { TECHNIQUES, TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { ELEMENTS, FAMILIES } from '../../data/types.ts'
import { ART } from '../../data/tuning.ts'
import { ELEMENT_STYLES } from '../../fx/elements.ts'
import { CELL, MOTIF_LOOKS, MOTIF_OF, attackFxFor, fxCount, fxQuality } from './fxRecipe.ts'

/** docs/BATTLE_3D.md §7: every technique looks like what it is. */
describe('attack effects: technique → recipe', () => {
  const tech = (id: string) => attackFxFor(TECHNIQUE_BY_ID[id]!)

  it('maps every technique, and every element in the data has its own look', () => {
    for (const t of TECHNIQUES) {
      const r = attackFxFor(t)
      expect(r.look).toBe(MOTIF_LOOKS[r.motif])
      expect(r.path).toBe(pathOf(t))
    }
    const used = new Set(TECHNIQUES.map((t) => t.element))
    for (const el of used) expect(ELEMENTS).toContain(el)
    expect(new Set(ELEMENTS.map((el) => MOTIF_OF[el])).size).toBe(ELEMENTS.length)
    for (const look of Object.values(MOTIF_LOOKS)) expect(Object.values(CELL)).toContain(look.cell)
  })

  it('takes its colours and projectile from the classic battle (src/fx/elements.ts), so 2-D and 3-D agree', () => {
    for (const t of TECHNIQUES.slice(0, 60)) {
      const r = attackFxFor(t)
      const s = ELEMENT_STYLES[t.element]
      expect([r.core, r.glow, r.smoke, r.projectile, r.ramp]).toEqual([s.core, s.glow, s.smoke, s.projectile, s.ramp])
      expect(r.look.inward).toBe(s.inward)
    }
  })

  it('reads the shape from the rules: sweeps, slashes, hits, knockback, drain, heal', () => {
    expect(tech('puddlepup.soggy-cloud')).toMatchObject({ path: 'sweep', drain: true, element: 'Water', motif: 'splash' })
    expect(tech('puddlepup.slipstream-spin')).toMatchObject({ slash: true, ranged: false })
    expect(tech('puddlepup.bubble-pop')).toMatchObject({ ranged: true, path: 'line', projectile: 'drop' })
    expect(tech('puddlepup.geyser-burst')).toMatchObject({ grand: true, signature: false, hits: 2 })
    expect(tech('puddlepup.puddle-party')).toMatchObject({ grand: true, signature: true, heal: true })
    expect(tech('moatshell.catapult-barrage')).toMatchObject({ hits: 3, path: 'sweep' })
    expect(tech('plumdrake.cloud-gust-blast')).toMatchObject({ shockwave: true, motif: 'gust' })
    expect(tech('wishlume.ember-siphon')).toMatchObject({ drain: true })
    expect(tech('tumblefox.fluffstorm')).toMatchObject({ stun: true })
    expect(tech('cobblemaw.gravel-swipe')).toMatchObject({ ranged: false, grand: false })
  })

  it('sizes by family: Basic small, Heavy big, Special and Signature grand, Signature the most', () => {
    const p = ART.duel.fx.familyPct
    for (const f of FAMILIES) expect(p[f]).toBeGreaterThan(0)
    expect(p.Basic).toBeLessThan(p.Hit)
    expect(p.Hit).toBeLessThan(p.Heavy)
    expect(p.Chain).toBeLessThan(p.Heavy)
    expect(p.Heavy).toBeLessThan(p.Special)
    expect(p.Special).toBeLessThan(p.Signature)
    const sig = TECHNIQUES.filter((t) => t.family === 'Signature').map(attackFxFor)
    expect(sig.every((r) => r.grand && r.signature)).toBe(true)
  })

  it('Lite and Reduce motion draw fewer particles and never flash; faster speeds shorten the effects', () => {
    const full = fxQuality({ lite: false, reduceMotion: false, speed: 1 })
    const lite = fxQuality({ lite: true, reduceMotion: false, speed: 1 })
    const calm = fxQuality({ lite: false, reduceMotion: true, speed: 1 })
    expect(full.flash).toBe(true)
    expect(lite.flash || calm.flash).toBe(false)
    const r = tech('puddlepup.belly-flop')
    expect(fxCount(14, r, lite)).toBeLessThan(fxCount(14, r, full))
    expect(fxCount(14, r, calm)).toBeLessThan(fxCount(14, r, full))
    expect(fxCount(1, tech('puddlepup.splash-nip'), lite)).toBe(1)
    expect(fxQuality({ lite: false, reduceMotion: false, speed: 4 }).life).toBeLessThan(full.life)
  })
})
