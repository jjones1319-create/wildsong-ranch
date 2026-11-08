import { describe, expect, it } from 'vitest'
import { ULTRA_IDS, ULTRA_LOOKS, ultraHeightPct, type UltraLook } from '../../art/ultraLooks.ts'
import { ART } from '../../data/tuning.ts'
import { duelFighters, duelLoads } from './fighters.ts'

/** A registry with a second breed and a grown form, as the batches ship them. */
const P = ULTRA_LOOKS.puddlepup!
const LOOKS: Record<string, UltraLook> = {
  puddlepup: P,
  tumblefox: { ...P, id: 'tumblefox', breed: 'tumblefox', glb: 'models/monsters-ultra/tumblefox.glb', meta: 'models/monsters-ultra/tumblefox.json', heightUnits: 135, variants: ['town-crier-tumblefox'] },
  'hearthwing-grown': { ...P, id: 'hearthwing-grown', breed: 'hearthwing', stage: 'grown', glb: 'models/monsters-ultra/hearthwing-grown.glb', meta: 'models/monsters-ultra/hearthwing-grown.json', heightUnits: 300, variants: [] },
}

describe('Battle 3D fighters (docs/BATTLE_3D.md §8)', () => {
  it('two different breeds: each at its true height beside Puddlepup, two downloads', () => {
    const f = duelFighters({ looks: ['puddlepup', 'tumblefox'], variants: [null, 'town-crier-tumblefox'] }, LOOKS)
    expect(f.map((x) => x.breed)).toEqual(['puddlepup', 'tumblefox'])
    expect(f[0].heightM).toBe(ART.duel.monsterHeightM)
    expect(f[1].heightM).toBeCloseTo(ART.duel.monsterHeightM * 0.9, 6)
    expect(f[1].variant).toBe('town-crier-tumblefox')
    expect(duelLoads(f)).toEqual(['puddlepup', 'tumblefox'])
  })

  it('a grown form is its own look: its breed fights, at the grown height', () => {
    const f = duelFighters({ looks: ['hearthwing-grown', 'puddlepup'], variants: [null, null] }, LOOKS)
    expect(f[0].look).toBe('hearthwing-grown')
    expect(f[0].breed).toBe('hearthwing')
    expect(f[0].heightM).toBeCloseTo(ART.duel.monsterHeightM * 2, 6)
  })

  it('the same look on both sides shares one download; a variant its file lacks shows the usual look', () => {
    const f = duelFighters({ looks: ['tumblefox', 'tumblefox'], variants: ['songheart-puddlepup', 'town-crier-tumblefox'] }, LOOKS)
    expect(f[0].variant).toBeNull()
    expect(f[1].variant).toBe('town-crier-tumblefox')
    expect(duelLoads(f)).toEqual(['tumblefox'])
  })

  it('a look outside the registry, or none, fights as Puddlepup', () => {
    const f = duelFighters({ looks: ['cobblemaw', 'tumblefox'], variants: [null, null] }, { puddlepup: P })
    expect(f.map((x) => x.look)).toEqual(['puddlepup', 'puddlepup'])
    const d = duelFighters({ variants: [null, 'songheart-puddlepup'] })
    expect(d[0].breed).toBe('puddlepup')
    expect(d[1].variant).toBe('songheart-puddlepup')
  })

  it('every pair of the real registry loads its looks once each, at their own heights', () => {
    for (const a of ULTRA_IDS) {
      for (const b of ULTRA_IDS) {
        const f = duelFighters({ looks: [a, b], variants: [null, null] })
        expect(f.map((x) => x.look)).toEqual([a, b])
        expect(duelLoads(f)).toEqual(a === b ? [a] : [a, b])
        expect(f[1].heightM).toBeCloseTo((ART.duel.monsterHeightM * ultraHeightPct(ULTRA_LOOKS[b]!)) / 100, 6)
      }
    }
  })
})
