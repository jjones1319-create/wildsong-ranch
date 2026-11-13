import { describe, expect, it } from 'vitest'
import { BREED_IDS } from '../data/types.ts'
import { STAGES } from '../data/tuning.ts'
import { portraitMode, ultraPortraitMode } from '../ui/store/artStore.ts'
import { hasModel, lookFor, lookKey, MODEL_LOOKS, MODELS, ultraLookFor } from './models.ts'
import { ULTRA_LOOKS } from './ultraLooks.ts'

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

describe("the live Ultra portrait (the owner's option A, Nov 12)", () => {
  it('a live portrait of a breed with an Ultra look shows it, a still with Reduce motion; otherwise the old rules', () => {
    expect(ultraPortraitMode(true, '3d', false, false, true)).toBe('live')
    expect(ultraPortraitMode(true, '3d', false, true, true)).toBe('still')
    // lists, thumbnails, cards and cups (not live) keep the old rules
    expect(ultraPortraitMode(true, '3d', false, false, false)).toBeNull()
    // Settings → Monsters: Classic forces the drawings; no WebGL falls back as before
    expect(ultraPortraitMode(true, 'classic', false, false, true)).toBeNull()
    expect(ultraPortraitMode(true, '3d', true, false, true)).toBeNull()
    // a breed without an Ultra look: the old rules (Classic, or Art 2.0)
    expect(ultraPortraitMode(false, '3d', false, false, true)).toBeNull()
  })

  it('picks the look by breed and form, and the variant only where the look holds it', () => {
    expect(ultraLookFor('puddlepup', null, 1)).toEqual({ id: 'puddlepup', variant: null })
    expect(ultraLookFor('puddlepup', 'songheart-puddlepup', 3)).toEqual({ id: 'puddlepup', variant: 'songheart-puddlepup' })
    if (ULTRA_LOOKS['hearthwing-grown']) {
      expect(ultraLookFor('hearthwing', null, STAGES.prime[0]! - 1)?.id).toBe('hearthwing')
      expect(ultraLookFor('hearthwing', null, STAGES.prime[0]!)?.id).toBe('hearthwing-grown')
    }
    // a variant of another breed shows the look's own colours
    expect(ultraLookFor('hearthwing', 'songheart-puddlepup', 1)).toEqual({ id: 'hearthwing', variant: null })
    for (const b of BREED_IDS) if (!ULTRA_LOOKS[b]) expect(ultraLookFor(b, null, 5)).toBeNull()
  })
})
