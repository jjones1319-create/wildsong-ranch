import type { ComponentChildren } from 'preact'
import { useEffect, useRef, useState } from 'preact/hooks'
import type { UltraId } from '../../art/ultraLooks.ts'
import type { LightPreset } from '../../art3d/materials.ts'
import type { UltraPortraitHandle, UltraPortraitSpec } from '../../art3d/ultra/portraitStage.ts'
import { ART } from '../../data/tuning.ts'
import { art3dLost, art3dUnavailable } from '../store/artStore.ts'
import { currentTier, reduceMotionNow } from '../store/fxStore.ts'
import { lite } from '../store/perf.ts'

export interface MonsterUltraProps {
  look: UltraId
  variant: string | null
  /** The loop it rests in (idle, or the mood's). */
  clip: string
  size: number
  mirror?: boolean
  label?: string
  light?: LightPreset
  /** The ranch: now and then it looks around, hops or celebrates; a look that flies takes a lap now and then. */
  idleActs?: boolean
  /** Reduce motion: one still frame. */
  still: boolean
  /** What shows until the model is ready, and if it can't be (the Classic drawing). */
  fallback: ComponentChildren
  class?: string
  seed?: number
}

/** What the review scripts and the e2e checks read (dev and test only). */
declare global {
  interface Window {
    __ultraPortrait?: { stats(): ReturnType<UltraPortraitHandle['stats']> | null; flyLap(): boolean; act(clip: string): boolean; light(preset: LightPreset): void }
  }
}

/**
 * A live Ultra monster in a square box (Art 2.1 on the ranch, the owner's option A, Nov 12): mounts the shared
 * portrait stage (src/art3d/ultra/portraitStage.ts) into its box, keeps the Classic drawing underneath until the model
 * is ready, then fades it out; falls back to it when 3D is lost or unavailable. Draws only while the box is on screen.
 * The 3D code loads lazily, so the main chunk never imports three.
 */
export function MonsterUltra(p: MonsterUltraProps) {
  const host = useRef<HTMLDivElement>(null)
  const handleRef = useRef<UltraPortraitHandle | null>(null)
  const [ready, setReady] = useState(false)
  const [gone, setGone] = useState(false)
  const unavailable = art3dUnavailable.value
  const lost = art3dLost.value
  const liteTier = lite.value || currentTier() === 'lite'
  const yawDeg = (p.mirror ? -1 : 1) * ART.portrait.yawDeg

  const spec = (): UltraPortraitSpec => ({ look: p.look, variant: p.variant, clip: p.clip, yawDeg, light: p.light ?? 'day' })

  useEffect(() => {
    const el = host.current
    if (!el || unavailable) return
    let alive = true
    const timers: ReturnType<typeof setTimeout>[] = []
    let io: IntersectionObserver | null = null
    setReady(false)
    setGone(false)
    void import('../../art3d/ultra/portraitStage.ts').then(({ UltraPortraitStage, seededRandom }) => {
      if (!alive) return
      const h = UltraPortraitStage.get().mount(el, {
        lite: liteTier,
        still: p.still,
        onReady: () => alive && setReady(true),
        onFailed: () => alive && setGone(true),
        onLost: () => alive && setReady(false),
        onRestored: () => alive && setReady(true),
        onEvicted: () => alive && setGone(true),
      })
      if (!h) {
        art3dUnavailable.value = true
        return
      }
      handleRef.current = h
      h.show(spec())
      // draw only while the box is on screen
      if ('IntersectionObserver' in window) {
        io = new IntersectionObserver((es) => h.setVisible(es.some((e) => e.isIntersecting)))
        io.observe(el)
      }
      if (import.meta.env.DEV || navigator.webdriver) {
        window.__ultraPortrait = { stats: () => (h.live ? h.stats() : null), flyLap: () => h.flyLap(), act: (c) => h.play(c), light: (l) => h.setLight(l) }
      }
      if (!p.idleActs || p.still) return
      const rng = seededRandom(p.seed ?? 11)
      void import('../../art3d/art3d.ts').then(({ ranchActionFor }) => {
        // now and then a ranch act (look round, hop, celebrate), as the Art 2.0 portrait did
        const act = () => {
          timers.push(
            setTimeout(() => {
              if (!alive) return
              if (!h.busy()) h.play(ranchActionFor(rng()))
              act()
            }, ART.anim.idleActMinMs + rng() * (ART.anim.idleActMaxMs - ART.anim.idleActMinMs)),
          )
        }
        act()
      })
      // a look that flies: a lap about once a minute while it is shown (never with Reduce motion)
      void import('../../art3d/ultra/flight.ts').then(({ lapAllowed, lapDelayMs }) => {
        const lap = () => {
          timers.push(
            setTimeout(() => {
              if (!alive) return
              if (lapAllowed({ flies: h.flies(), reduceMotion: reduceMotionNow(), hidden: document.hidden, busy: h.busy() })) h.flyLap()
              lap()
            }, lapDelayMs(rng())),
          )
        }
        lap()
      })
    })
    return () => {
      alive = false
      for (const t of timers) clearTimeout(t)
      io?.disconnect()
      handleRef.current?.release()
      handleRef.current = null
      if (window.__ultraPortrait) delete window.__ultraPortrait
    }
  }, [p.look, liteTier, unavailable, p.idleActs, p.still, p.seed])

  // keep the monster in step with the props (its colours, mood loop, turn and light)
  useEffect(() => {
    handleRef.current?.show(spec())
  }, [p.variant, p.clip, yawDeg, p.light])

  const showFallback = !ready || gone || lost || unavailable
  return (
    <div ref={host} class={`portrait portrait--3d ${showFallback ? '' : 'portrait--3d-ready'} ${p.class ?? ''}`} style={{ width: p.size, height: p.size }} role="img" aria-label={p.label} data-ultra={p.look}>
      <div class="portrait__fallback" aria-hidden={!showFallback}>
        {p.fallback}
      </div>
    </div>
  )
}
