import { describe, expect, it } from 'vitest'
import { FX } from '../data/tuning.ts'
import { budgetFor, FlashGate, FrameSampler, initialTier, intensityProfile, particleAllowance, shakeOffset, tierAfterSample } from './quality.ts'

describe('Quality tiers (VISUAL_V1_EFFECTS §6)', () => {
  it('budgets match the table', () => {
    expect(budgetFor('ultra', 3)).toEqual({ tier: 'ultra', maxParticles: 2500, filters: 'all', resolution: 2, lightningPasses: 3 })
    expect(budgetFor('high', 3)).toEqual({ tier: 'high', maxParticles: 1200, filters: 'some', resolution: 1.5, lightningPasses: 2 })
    expect(budgetFor('lite', 3)).toEqual({ tier: 'lite', maxParticles: 400, filters: 'none', resolution: 1, lightningPasses: 1 })
    expect(budgetFor('ultra', 1.25).resolution).toBe(1.25)
    expect(budgetFor('high', 0.5).resolution).toBe(1)
  })

  it('Auto starts at Ultra, at High on small phones, at Lite under data saver', () => {
    expect(initialTier({})).toBe('ultra')
    expect(initialTier({ deviceMemoryGb: 8, cores: 8 })).toBe('ultra')
    expect(initialTier({ deviceMemoryGb: 3 })).toBe('high')
    expect(initialTier({ cores: 4 })).toBe('high')
    expect(initialTier({ reducedData: true, deviceMemoryGb: 16 })).toBe('lite')
  })

  it('the frame sample drops one tier above 18 ms and two above 28 ms', () => {
    expect(tierAfterSample('ultra', 12)).toBe('ultra')
    expect(tierAfterSample('ultra', 18)).toBe('ultra')
    expect(tierAfterSample('ultra', 19)).toBe('high')
    expect(tierAfterSample('ultra', 29)).toBe('lite')
    expect(tierAfterSample('high', 29)).toBe('lite')
    expect(tierAfterSample('lite', 40)).toBe('lite')
  })

  it('the sampler averages the first 90 frames and ignores tab-switch gaps', () => {
    const s = new FrameSampler()
    let avg: number | null = null
    expect(s.push(5000)).toBeNull()
    for (let i = 0; i < FX.quality.sampleFrames; i++) avg = s.push(i % 2 === 0 ? 10 : 30) ?? avg
    expect(avg).toBeCloseTo(20)
    expect(s.done).toBe(true)
    expect(s.push(10)).toBeNull()
  })
})

describe('Intensity (VISUAL_V1_EFFECTS §6)', () => {
  it('maps the table and reduced motion forces Cozy with no shake, flash or impact frames', () => {
    expect(intensityProfile('standard', false)).toMatchObject({ intensity: 'standard', shakePx: 4, hitstopMs: 60, impactFrames: 'crits', flashAlpha: 0.2, bloom: 'low', particles: 1, reduced: false })
    expect(intensityProfile('flashy', false)).toMatchObject({ shakePx: 8, hitstopMs: 120, impactFrames: 'heavy', flashAlpha: 0.3, bloom: 'high', particles: 1.4 })
    expect(intensityProfile('cozy', false)).toMatchObject({ shakePx: 0, hitstopMs: 0, impactFrames: 'off', flashAlpha: 0, bloom: 'off', particles: 0.6 })
    expect(intensityProfile('flashy', true)).toMatchObject({ intensity: 'cozy', shakePx: 0, flashAlpha: 0, impactFrames: 'off', reduced: true })
  })

  it('the particle allowance scales by intensity and stops at the tier cap', () => {
    const lite = budgetFor('lite')
    expect(particleAllowance(100, intensityProfile('flashy', false), lite, 0)).toBe(140)
    expect(particleAllowance(100, intensityProfile('cozy', false), lite, 0)).toBe(60)
    expect(particleAllowance(100, intensityProfile('standard', false), lite, 350)).toBe(50)
    expect(particleAllowance(100, intensityProfile('standard', false), lite, 400)).toBe(0)
  })
})

describe('Photosensitivity (§24)', () => {
  it('allows at most three flashes in any rolling second', () => {
    const g = new FlashGate()
    expect(g.allow(0)).toBe(true)
    expect(g.allow(100)).toBe(true)
    expect(g.allow(200)).toBe(true)
    expect(g.allow(300)).toBe(false)
    expect(g.allow(999)).toBe(false)
    expect(g.allow(1000)).toBe(true)
    expect(g.allow(1050)).toBe(false)
    expect(g.allow(1100)).toBe(true)
  })

  it('never lets a flash above the alpha cap', () => {
    expect(FlashGate.clampAlpha(0.9)).toBe(FX.flash.maxAlpha)
    expect(FlashGate.clampAlpha(0.1)).toBe(0.1)
    expect(FlashGate.clampAlpha(-1)).toBe(0)
    expect(FX.flash.maxAlpha).toBeLessThanOrEqual(0.3)
    expect(FX.flash.maxPerSecond).toBeLessThanOrEqual(3)
  })
})

describe('Shake', () => {
  it('decays to nothing and is zero with no amplitude', () => {
    expect(shakeOffset(10, 0)).toEqual({ dx: 0, dy: 0 })
    expect(shakeOffset(300, 8, 280)).toEqual({ dx: 0, dy: 0 })
    const early = shakeOffset(20, 8, 280)
    const late = shakeOffset(250, 8, 280)
    expect(Math.hypot(early.dx, early.dy)).toBeLessThanOrEqual(8)
    expect(Math.hypot(late.dx, late.dy)).toBeLessThan(Math.hypot(early.dx, early.dy) + 0.001)
    expect(shakeOffset(20, 8, 280)).toEqual(early)
  })
})
