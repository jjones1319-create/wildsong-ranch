import { describe, expect, it } from 'vitest'
import { BREED_IDS } from '../data/types.ts'
import { portraitMode } from '../ui/store/artStore.ts'
import { hasModel, lookFor, lookKey, MODEL_LOOKS, MODELS } from './models.ts'

describe('the look registry (ART_2_PLAN §3.3)', () => {
  it('Puddlepup has a model at every stage; every other breed shows Classic', () => {
    for (let stage = 1; stage <= 10; stage++) expect(lookFor('puddlepup', null, stage)).toEqual({ look: 'puddlepup', variant: null })
    for (const b of BREED_IDS) {
      if (b === 'puddlepup') continue
      expect(lookFor(b, null, 5)).toBeNull()
      expect(hasModel(b)).toBe(false)
    }
  })

  it('a secret variant shows only when its texture set is in the file', () => {
    expect(lookFor('puddlepup', 'songheart-puddlepup', 3)).toEqual({ look: 'puddlepup', variant: 'songheart-puddlepup' })
    expect(lookFor('puddlepup', 'glitch-tumblefox', 3)).toBeNull()
    expect(lookKey({ look: 'puddlepup', variant: 'songheart-puddlepup' })).toBe('puddlepup.songheart-puddlepup')
    expect(lookKey({ look: 'puddlepup', variant: null })).toBe('puddlepup')
  })

  it('every registered look is a real entry', () => {
    for (const m of Object.values(MODELS)) {
      expect(MODEL_LOOKS[m.young]).toBeDefined()
      if (m.grown) expect(MODEL_LOOKS[m.grown]).toBeDefined()
    }
  })
})

describe('portraitMode', () => {
  it('Classic without a model or with the setting off; live only on subject screens with WebGL and motion', () => {
    expect(portraitMode(false, '3d', false, false, true)).toBe('classic')
    expect(portraitMode(true, 'classic', false, false, true)).toBe('classic')
    expect(portraitMode(true, '3d', false, false, true)).toBe('live')
    expect(portraitMode(true, '3d', false, false, false)).toBe('image')
    expect(portraitMode(true, '3d', true, false, true)).toBe('image')
    expect(portraitMode(true, '3d', false, true, true)).toBe('image')
  })
})
