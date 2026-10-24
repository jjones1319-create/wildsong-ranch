import { signal } from '@preact/signals'
import type { FxStats } from '../../fx/FxLayer.ts'
import { budgetFor, FrameSampler, initialTier, intensityProfile, tierAfterSample, type DeviceHints, type IntensityProfile, type QualityBudget, type QualityTier } from '../../fx/quality.ts'
import { settings, updateSettings } from './appStore.ts'

/**
 * V1 effects settings → the numbers the layer needs (VISUAL_V1_EFFECTS §6). Quality "Auto" starts from device
 * hints, measures the first battle's frames once, and remembers the tier in settings. Reduced motion (the toggle
 * or the OS) forces Cozy. The Effects Lab reads the live stats from here.
 */
export const fxStats = signal<FxStats | null>(null)
/** True when WebGL could not start: the arena shows the plain hits and the Lab says so. */
export const fxUnavailable = signal(false)

export function osReducedMotion(): boolean {
  try {
    return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

export function reduceMotionNow(): boolean {
  return settings.value.reduceMotion || osReducedMotion()
}

export function deviceHints(): DeviceHints {
  const h: DeviceHints = {}
  try {
    const nav = navigator as Navigator & { deviceMemory?: number }
    if (nav.deviceMemory !== undefined) h.deviceMemoryGb = nav.deviceMemory
    if (nav.hardwareConcurrency !== undefined) h.cores = nav.hardwareConcurrency
    h.reducedData = !!window.matchMedia?.('(prefers-reduced-data: reduce)').matches
  } catch {
    /* no navigator (tests) */
  }
  return h
}

/** The tier in force: the override, or Auto's remembered / initial pick. */
export function currentTier(): QualityTier {
  const s = settings.value
  if (s.fxQuality !== 'auto') return s.fxQuality
  return s.fxAutoTier ?? initialTier(deviceHints())
}

export function currentBudget(): QualityBudget {
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
  return budgetFor(currentTier(), dpr)
}

export function currentProfile(): IntensityProfile {
  return intensityProfile(settings.value.fxIntensity, reduceMotionNow())
}

/** Auto still has to measure: the first battle's frames decide, once. */
export function autoNeedsSample(): boolean {
  const s = settings.value
  return s.fxQuality === 'auto' && s.fxAutoTier === null
}

/** Returns an onFrame callback that settles Auto's tier after the sample, or undefined when nothing is pending. */
export function makeAutoSampler(onSettled: (tier: QualityTier) => void): ((frameMs: number) => void) | undefined {
  if (!autoNeedsSample()) return undefined
  const sampler = new FrameSampler()
  const start = currentTier()
  return (frameMs) => {
    const avg = sampler.push(frameMs)
    if (avg === null) return
    const tier = tierAfterSample(start, avg)
    void updateSettings({ fxAutoTier: tier })
    onSettled(tier)
  }
}

/** Changing Quality back to Auto forgets the measured tier so the next battle measures again. */
export function setFxQuality(q: typeof settings.value.fxQuality): void {
  void updateSettings(q === 'auto' ? { fxQuality: q, fxAutoTier: null } : { fxQuality: q })
}

export function setFxIntensity(i: typeof settings.value.fxIntensity): void {
  void updateSettings({ fxIntensity: i })
}
