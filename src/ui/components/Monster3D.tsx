import type { ComponentChildren } from 'preact'
import { useEffect, useRef, useState } from 'preact/hooks'
import { MODEL_LOOKS, type LookId } from '../../art/models.ts'
import type { ClipName, FaceName, StageHandle } from '../../art3d/art3d.ts'
import type { LightPreset } from '../../art3d/materials.ts'
import { ART } from '../../data/tuning.ts'
import { art3dLost, art3dUnavailable } from '../store/artStore.ts'
import { currentTier } from '../store/fxStore.ts'
import { lite } from '../store/perf.ts'

export interface Monster3DProps {
  look: LookId
  variant: string | null
  stage: number
  face: FaceName
  sick?: number
  size: number
  mirror?: boolean
  label?: string
  /** The loop to play (idle by default). */
  clip?: ClipName
  light?: LightPreset
  /** The ranch: now and then the monster looks around, hops or celebrates. */
  idleActs?: boolean
  /** Extra turn in degrees (the Lab's drag). */
  yaw?: number
  /** What shows until the model is ready (the Classic drawing). */
  fallback: ComponentChildren
  class?: string
  seed?: number
  /** The review scripts' manual clock: frames only advance through the handle's `step`. */
  manualClock?: boolean
  onHandle?: (h: StageHandle | null) => void
}

const ACTOR = 'm'

/**
 * A live 3D monster in a square box (ART_2_PLAN §3.2 `Monster3D`): mounts the shared stage into its box, keeps
 * the Classic drawing underneath until the model is ready, then fades it out. Taps anywhere make it glance.
 * The 3D code is loaded lazily, so the main chunk never imports three.
 */
export function Monster3D(p: Monster3DProps) {
  const host = useRef<HTMLDivElement>(null)
  const handleRef = useRef<StageHandle | null>(null)
  const [ready, setReady] = useState(false)
  const [gone, setGone] = useState(false)
  const unavailable = art3dUnavailable.value
  const lost = art3dLost.value
  const tier = lite.value ? 'lite' : currentTier()
  const yawBase = (p.mirror ? -1 : 1) * ART.portrait.yawDeg + (p.yaw ?? 0)

  const spec = () => ({
    id: ACTOR,
    look: p.look,
    variant: p.variant,
    stage: p.stage,
    face: p.face,
    x: 0,
    yawDeg: yawBase,
    clip: p.clip ?? 'idle',
    sick: p.sick ?? 0,
  })

  // Mount once per look and quality tier.
  useEffect(() => {
    const el = host.current
    if (!el || unavailable) return
    let alive = true
    let timer: ReturnType<typeof setTimeout> | null = null
    setReady(false)
    setGone(false)
    void import('../../art3d/art3d.ts').then(({ Stage3D, portraitCamera, ranchActionFor, seededRandom }) => {
      if (!alive) return
      const rng = seededRandom(p.seed ?? 11)
      const h = Stage3D.get().mount(el, {
        quality: tier,
        seed: p.seed ?? 11,
        manualClock: p.manualClock,
        onReady: () => {
          if (alive) setReady(true)
        },
        onLost: () => {
          if (alive) setReady(false)
        },
        onRestored: () => {
          if (alive) setReady(true)
        },
        onEvicted: () => {
          if (alive) setGone(true)
        },
      })
      if (!h) {
        art3dUnavailable.value = true
        return
      }
      handleRef.current = h
      p.onHandle?.(h)
      h.setLight(p.light ?? 'day')
      h.setCamera(portraitCamera(p.size, MODEL_LOOKS[p.look].unitsPerMetre))
      h.setActors([spec()])
      h.start()
      if (p.idleActs) {
        const schedule = () => {
          timer = setTimeout(() => {
            const hh = handleRef.current
            const a = hh?.actor(ACTOR)
            if (hh && a) {
              const act = ranchActionFor(rng())
              const base = p.clip ?? 'idle'
              const meta = a.asset.meta.clips[act]
              if (meta?.loop === false) hh.play(ACTOR, act, { onFinish: () => hh.play(ACTOR, base) })
              else {
                hh.play(ACTOR, act)
                setTimeout(() => {
                  if (handleRef.current === hh && a.clipName === act) hh.play(ACTOR, base)
                }, (meta?.seconds ?? 2) * 1000)
              }
            }
            schedule()
          }, ART.anim.idleActMinMs + rng() * (ART.anim.idleActMaxMs - ART.anim.idleActMinMs))
        }
        schedule()
      }
    })
    return () => {
      alive = false
      if (timer) clearTimeout(timer)
      handleRef.current?.release()
      handleRef.current = null
      p.onHandle?.(null)
    }
  }, [p.look, tier, unavailable, p.idleActs, p.seed])

  // Keep the actor in step with the props.
  useEffect(() => {
    const h = handleRef.current
    if (!h || !h.live) return
    h.setActors([spec()])
  }, [p.variant, p.stage, p.face, p.sick, p.clip, yawBase])

  useEffect(() => {
    const h = handleRef.current
    if (!h || !h.live) return
    void import('../../art3d/art3d.ts').then(({ portraitCamera }) => {
      if (handleRef.current === h && h.live) h.setCamera(portraitCamera(p.size, MODEL_LOOKS[p.look].unitsPerMetre))
    })
  }, [p.size])

  useEffect(() => {
    handleRef.current?.setLight(p.light ?? 'day')
  }, [p.light])

  // Glance toward taps anywhere on the page.
  useEffect(() => {
    const onTap = (e: PointerEvent) => {
      const el = host.current
      const h = handleRef.current
      if (!el || !h) return
      const r = el.getBoundingClientRect()
      const dx = e.clientX - (r.left + r.width / 2)
      const dy = e.clientY - (r.top + r.height / 2)
      const reach = Math.min(1, Math.hypot(dx, dy) / (r.width * 1.5))
      h.glance(dx * (p.mirror ? -1 : 1), dy, reach)
    }
    document.addEventListener('pointerdown', onTap)
    return () => document.removeEventListener('pointerdown', onTap)
  }, [p.mirror])

  const showFallback = !ready || gone || lost || unavailable
  return (
    <div ref={host} class={`portrait portrait--3d ${showFallback ? '' : 'portrait--3d-ready'} ${p.class ?? ''}`} style={{ width: p.size, height: p.size }} role="img" aria-label={p.label}>
      <div class="portrait__fallback" aria-hidden={!showFallback}>
        {p.fallback}
      </div>
    </div>
  )
}
