import { describe, expect, it } from 'vitest'
import { ELEMENTS } from '../data/types.ts'
import type { FxEvent } from './bus.ts'
import { intensityProfile } from './quality.ts'
import { comboRecipe, MELEE_LAND_MS, recipeFor, travelMs } from './recipes.ts'

const from = { x: -230, y: -100 }
const to = { x: 230, y: -100 }
const standard = intensityProfile('standard', false)
const cozy = intensityProfile('cozy', false)
const flashy = intensityProfile('flashy', false)

describe('default recipes per element (VISUAL_V1_EFFECTS §5 payoff)', () => {
  it('every element gives a melee fire, a ranged fire and a hit something to draw, and the elements differ', () => {
    const seen = new Set<string>()
    for (const element of ELEMENTS) {
      const melee = recipeFor({ kind: 'fire', side: 0, element, from, to, strength: 0.5, ranged: false }, standard)
      const ranged = recipeFor({ kind: 'fire', side: 0, element, from, to, strength: 0.5, ranged: true }, standard)
      const hit = recipeFor({ kind: 'hit', side: 1, element, from, to, strength: 0.5, techId: 'puddlepup.splash-nip' }, standard)
      expect(melee.length).toBeGreaterThan(0)
      expect(ranged.some((c) => c.name === 'projectile')).toBe(true)
      expect(hit.some((c) => c.name === 'impact')).toBe(true)
      seen.add(hit.map((c) => c.name).join(','))
    }
    expect(seen.size).toBeGreaterThanOrEqual(6)
  })

  it('hits wait for the attack to land: melee a little, ranged the projectile time', () => {
    const melee = recipeFor({ kind: 'hit', side: 1, element: 'Fire', from, to, strength: 0.5, techId: 'cinderlynx.ember-swipe' }, standard)
    expect(melee.find((c) => c.name === 'impact')!.delayMs).toBe(MELEE_LAND_MS)
    const ranged = recipeFor({ kind: 'hit', side: 1, element: 'Fire', from, to, strength: 0.5, techId: 'hearthwing.hearthfire-torrent' }, standard)
    expect(ranged.find((c) => c.name === 'impact')!.delayMs).toBe(travelMs(from.x, to.x))
    expect(travelMs(0, 0)).toBeGreaterThan(0)
    expect(travelMs(-600, 600)).toBeGreaterThan(travelMs(-100, 100))
  })

  it('Cozy never shakes, flashes, stops time or inverts; Flashy does on heavy hits; Standard only inverts on crits', () => {
    const heavy: FxEvent = { kind: 'hit', side: 1, element: 'Lightning', from, to, strength: 1 }
    const crit: FxEvent = { kind: 'crit', side: 1, element: 'Earth', from, to, strength: 1, crit: true }
    const names = (calls: ReturnType<typeof recipeFor>) => calls.map((c) => c.name)
    for (const ev of [heavy, crit]) {
      const n = names(recipeFor(ev, cozy))
      expect(n).not.toContain('shake')
      expect(n).not.toContain('flash')
      expect(n).not.toContain('hitstop')
      expect(n).not.toContain('impactFrame')
    }
    expect(names(recipeFor(heavy, flashy))).toEqual(expect.arrayContaining(['shake', 'hitstop', 'impactFrame', 'flash', 'lightning']))
    expect(names(recipeFor(heavy, standard))).not.toContain('impactFrame')
    expect(names(recipeFor(crit, standard))).toEqual(expect.arrayContaining(['impactFrame', 'ring', 'debris', 'shake']))
  })

  it('reduced motion is Cozy whatever the setting', () => {
    const reduced = intensityProfile('flashy', true)
    const n = recipeFor({ kind: 'crit', side: 1, element: 'Fire', from, to, strength: 1, crit: true }, reduced).map((c) => c.name)
    expect(n).not.toContain('shake')
    expect(n).not.toContain('flash')
    expect(n).not.toContain('impactFrame')
  })

  it('the other moments have recipes (ko, special, push, dash, heal, wither, miss) and distract has none', () => {
    const ev = (kind: FxEvent['kind']): FxEvent => ({ kind, side: 0, element: 'Physical', from, to, strength: 0.5 })
    expect(recipeFor(ev('ko'), standard).map((c) => c.name)).toEqual(expect.arrayContaining(['debris', 'ring']))
    expect(recipeFor(ev('special'), standard).map((c) => c.name)).toContain('glow')
    expect(recipeFor(ev('push'), standard).map((c) => c.name)).toContain('ring')
    expect(recipeFor(ev('dash'), standard).map((c) => c.name)).toContain('trail')
    expect(recipeFor(ev('heal'), standard).map((c) => c.name)).toContain('burst')
    expect(recipeFor(ev('wither'), standard).map((c) => c.name)).toContain('glow')
    expect(recipeFor(ev('miss'), standard).map((c) => c.name)).toContain('mist')
    expect(recipeFor(ev('distract'), standard)).toEqual([])
  })

  it('the Lab combo is fire cone → impact → shake (and nothing jarring under Cozy)', () => {
    expect(comboRecipe(-200, 1, standard).map((c) => c.name)).toEqual(expect.arrayContaining(['cone', 'impact', 'shake', 'hitstop']))
    const cozyCombo = comboRecipe(-200, 1, cozy).map((c) => c.name)
    expect(cozyCombo).not.toContain('hitstop')
    expect(cozyCombo).not.toContain('impactFrame')
  })
})
