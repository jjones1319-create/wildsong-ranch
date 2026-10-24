import { FX } from '../data/tuning.ts'

/**
 * VISUAL_V1_EFFECTS §6: the Quality tiers (what the phone can draw) and the Intensity levels (how loud the
 * effects feel), plus the photosensitivity gate. Pure, so every rule is unit-tested without a GPU.
 */

export type QualityTier = (typeof FX.quality.tiers)[number]
export type QualitySetting = 'auto' | QualityTier
export type Intensity = keyof typeof FX.intensity
export type FilterLevel = 'all' | 'some' | 'none'

export interface QualityBudget {
  tier: QualityTier
  maxParticles: number
  filters: FilterLevel
  /** The canvas resolution for a given devicePixelRatio. */
  resolution: number
  lightningPasses: number
}

export interface IntensityProfile {
  intensity: Intensity
  shakePx: number
  hitstopMs: number
  impactFrames: 'off' | 'crits' | 'heavy'
  flashAlpha: number
  bloom: 'off' | 'low' | 'high'
  particles: number
  /** True when reduced motion forced Cozy. */
  reduced: boolean
}

export interface DeviceHints {
  deviceMemoryGb?: number
  cores?: number
  reducedData?: boolean
}

export function budgetFor(tier: QualityTier, devicePixelRatio = 1): QualityBudget {
  const b = FX.quality.budgets[tier]
  return { tier, maxParticles: b.maxParticles, filters: b.filters as FilterLevel, resolution: Math.min(Math.max(1, devicePixelRatio), b.resolutionCap), lightningPasses: b.lightningPasses }
}

/** Auto's starting tier before any frame has been measured. */
export function initialTier(h: DeviceHints): QualityTier {
  if (h.reducedData) return 'lite'
  if ((h.deviceMemoryGb !== undefined && h.deviceMemoryGb < FX.quality.highBelowMemoryGb) || (h.cores !== undefined && h.cores < FX.quality.highBelowCores)) return 'high'
  return 'ultra'
}

/** Auto after the sample: the average frame time drops the tier by one or two steps. */
export function tierAfterSample(start: QualityTier, avgFrameMs: number): QualityTier {
  const tiers = FX.quality.tiers
  const i = tiers.indexOf(start)
  const drop = avgFrameMs > FX.quality.dropTwoMs ? 2 : avgFrameMs > FX.quality.dropOneMs ? 1 : 0
  return tiers[Math.min(tiers.length - 1, i + drop)]!
}

/** Collects frame times and reports the average once `FX.quality.sampleFrames` are in. */
export class FrameSampler {
  private total = 0
  private n = 0
  done = false
  push(frameMs: number): number | null {
    if (this.done) return null
    // A frame that waited for a tab switch is not the phone's fault.
    if (frameMs <= 0 || frameMs > FX.maxFrameMs) return null
    this.total += frameMs
    this.n += 1
    if (this.n < FX.quality.sampleFrames) return null
    this.done = true
    return this.total / this.n
  }
}

export function intensityProfile(setting: Intensity, reduceMotion: boolean): IntensityProfile {
  const key: Intensity = reduceMotion ? 'cozy' : setting
  const p = FX.intensity[key]
  return {
    intensity: key,
    shakePx: reduceMotion ? 0 : p.shakePx,
    hitstopMs: p.hitstopMs,
    impactFrames: reduceMotion ? 'off' : (p.impactFrames as IntensityProfile['impactFrames']),
    flashAlpha: reduceMotion ? 0 : Math.min(FX.flash.maxAlpha, p.flashAlpha),
    bloom: p.bloom as IntensityProfile['bloom'],
    particles: p.particles,
    reduced: reduceMotion,
  }
}

/** How many particles an effect may spawn: its wish × the intensity multiplier, inside the tier's cap and the pool. */
export function particleAllowance(wish: number, profile: IntensityProfile, budget: QualityBudget, live: number): number {
  const want = Math.round(wish * profile.particles)
  return Math.max(0, Math.min(want, budget.maxParticles - live))
}

/** §24: no more than FX.flash.maxPerSecond flashes in any rolling second, anywhere. */
export class FlashGate {
  private readonly times: number[] = []
  allow(nowMs: number): boolean {
    while (this.times.length > 0 && nowMs - this.times[0]! >= 1000) this.times.shift()
    if (this.times.length >= FX.flash.maxPerSecond) return false
    this.times.push(nowMs)
    return true
  }
  /** The brightest a flash may ever be. */
  static clampAlpha(alpha: number): number {
    return Math.max(0, Math.min(FX.flash.maxAlpha, alpha))
  }
}

/** Shake: a decaying offset, deterministic in time so it can be tested and replayed. */
export function shakeOffset(elapsedMs: number, amplitudePx: number, durationMs: number = FX.shake.durationMs, hz: number = FX.shake.hz): { dx: number; dy: number } {
  if (amplitudePx <= 0 || elapsedMs < 0 || elapsedMs >= durationMs) return { dx: 0, dy: 0 }
  const decay = 1 - elapsedMs / durationMs
  const t = (elapsedMs / 1000) * hz * Math.PI * 2
  return { dx: Math.sin(t) * amplitudePx * decay, dy: Math.cos(t * 1.3) * amplitudePx * decay * 0.6 }
}
