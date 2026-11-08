import { ART } from '../../data/tuning.ts'
import type { Level, PerfView } from './view.ts'

/**
 * Dynamic resolution and quality (ART_2_DETAIL §3.6), shared by Battle 3D and the 3D Gallery: hold the frame rate by
 * lowering the render resolution first, then the effects one level at a time; climb back when calm. The monsters'
 * detail never changes. Lite starts (and stays) at 'no-msaa'.
 */
export interface DynRes {
  /** Device pixels per CSS pixel the view renders at now. */
  dpr(): number
  level(): Level
  /** Count one frame (its length in ms); steps once a second. */
  frame(frameMs: number): void
  /** Don't judge the frames for a while (a model just loaded: its uploads and shader compiles aren't the phone's pace). */
  pause(ms: number): void
}

export interface DynResOptions {
  lite: boolean
  /** Where to start, and the most it may climb to. */
  dprStart: number
  dprMax: number
  /** The canvas's CSS size now. */
  size: () => { w: number; h: number }
  /** When more than missShare of a second's frames are late, step down stepMul× as far (a slow phone recovers fast). */
  fastDrop: { missShare: number; stepMul: number }
}

export function createDynRes(view: PerfView, o: DynResOptions): DynRes {
  const S = ART.ultra.scaling
  const L = ART.ultra.levels
  const floor = o.lite ? L.indexOf('no-msaa') : 0
  let dpr = Math.min(o.dprStart, o.dprMax)
  let levelIndex = floor
  let missSecond = 0
  let framesSecond = 0
  let secondStart = performance.now()
  let calmSince = performance.now()
  let pausedUntil = 0
  return {
    dpr: () => dpr,
    level: () => L[levelIndex]!,
    pause(ms) {
      pausedUntil = Math.max(pausedUntil, performance.now() + ms)
      missSecond = 0
      framesSecond = 0
      secondStart = Math.min(pausedUntil, performance.now() + 1e9)
    },
    frame(frameMs) {
      if (performance.now() < pausedUntil) return
      const budget = 1000 / S.targetFps
      framesSecond++
      if (frameMs > budget * S.missFactor) missSecond++
      const t = performance.now()
      if (t - secondStart < 1000) return
      const miss = missSecond / Math.max(1, framesSecond)
      secondStart = t
      missSecond = 0
      framesSecond = 0
      const { w, h } = o.size()
      if (miss > S.missShareDown) {
        // most frames late (a slower phone at the start): take bigger steps so it recovers in a second or two
        const step = miss > o.fastDrop.missShare ? S.dprStepDown * o.fastDrop.stepMul : S.dprStepDown
        if (dpr - S.dprStepDown >= S.dprMin - 1e-6) {
          dpr = Math.max(S.dprMin, Math.round((dpr - step) * 100) / 100)
          view.setSize(w, h, dpr)
        } else if (levelIndex < L.length - 1) view.setLevel(L[++levelIndex]!)
        calmSince = t
      } else if (miss <= S.calmMissShare && t - calmSince > S.calmMsUp) {
        if (levelIndex > floor) view.setLevel(L[--levelIndex]!)
        else if (dpr + S.dprStepUp <= o.dprMax + 1e-6) {
          dpr = Math.round((dpr + S.dprStepUp) * 100) / 100
          view.setSize(w, h, dpr)
        }
        calmSince = t
      }
    },
  }
}
