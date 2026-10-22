import { signal } from '@preact/signals'
import { UI } from '../../data/tuning.ts'

/**
 * GAME_DESIGN §22 performance budget: decide once per session whether portraits should run in
 * lite mode (no particles, no secondary motion). Device hints first; otherwise one short frame-rate
 * sample a moment after start-up.
 */

export const lite = signal(false)

let decided = false

export function detectPerformance(): void {
  if (decided || typeof window === 'undefined') return
  decided = true
  const nav = navigator as Navigator & { deviceMemory?: number }
  const memory = nav.deviceMemory
  const cores = nav.hardwareConcurrency
  if ((memory !== undefined && memory <= UI.perf.liteMemoryGb) || (cores !== undefined && cores <= UI.perf.liteCores)) {
    lite.value = true
    return
  }
  setTimeout(() => {
    if (document.visibilityState !== 'visible') return
    let frames = 0
    const start = performance.now()
    const tick = () => {
      frames += 1
      if (frames < UI.perf.sampleFrames) {
        requestAnimationFrame(tick)
        return
      }
      const seconds = (performance.now() - start) / 1000
      if (seconds > 0 && frames / seconds < UI.perf.minFps) lite.value = true
    }
    requestAnimationFrame(tick)
  }, UI.perf.sampleDelayMs)
}
