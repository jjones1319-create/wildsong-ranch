import { useEffect, useMemo, useRef, useState, type MutableRef } from 'preact/hooks'
import type { ComponentChildren } from 'preact'
import { sceneBackground } from '../../art/backgrounds.ts'
import { lookFor } from '../../art/models.ts'
import type { Expression } from '../../art/monster/expressions.ts'
import type { Arena3DLayer } from '../../art3d/arena3d.ts'
import { stageOf, type Monster } from '../../core/monster.ts'
import { BAND_LABELS } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { BATTLE, BATTLE_CAMERA } from '../../data/tuning.ts'
import type { PlanMode, Season, Weather } from '../../data/types.ts'
import { subscribeFx } from '../../fx/bus.ts'
import type { FxLayer } from '../../fx/FxLayer.ts'
import { recipeFor } from '../../fx/recipes.ts'
import { MonsterPortrait } from '../components/MonsterPortrait.tsx'
import { settings } from '../store/appStore.ts'
import type { FloatEffect } from '../store/battleStore.ts'
import { art3dUnavailable, lightPreset } from '../store/artStore.ts'
import { currentBudget, currentProfile, currentTier, fxStats, fxUnavailable, makeAutoSampler, reduceMotionNow } from '../store/fxStore.ts'
import { lite } from '../store/perf.ts'
import { frameCamera, spriteScale, stepCamera, type Camera } from './camera.ts'

/** The floor line sits this many CSS px above the arena's bottom edge (battle.css `.fighter { bottom }`). */
export const FLOOR_PX = 40

export interface ArenaFighter {
  monster: Monster
  /** Arena units. */
  x: number
  expression?: Expression
  plan?: PlanMode | null
  busy?: boolean
  dawdling?: boolean
  stunned?: boolean
  lunge?: boolean
  hit?: boolean
  ko?: boolean
  win?: boolean
}

export interface ArenaProps {
  fighters: [ArenaFighter, ArenaFighter]
  floats?: readonly FloatEffect[]
  showThinking?: boolean
  /** The range ruler: the current band and gap. Omitted in the Lab. */
  ruler?: { band: number; gap: number }
  season: Season
  weather: Weather
  /** Playback speed and pause, forwarded to the effects clock. */
  speed?: number
  paused?: boolean
  /** Drives the camera and effects while true. */
  live?: boolean
  /** The fx layer runs without its own frames; `step(ms)` drives it (Playwright). */
  manualClock?: boolean
  /** The effects layer once it is ready (the Lab fires primitives straight at it), and null when it is torn down. */
  onLayer?: (layer: FxLayer | null) => void
  children?: ComponentChildren
}

const t = UI_TEXT.battle

/** The two fence posts that mark the walls (§12.11): an original rope fence, drawn in world units at basePx scale. */
function Wall({ side }: { side: -1 | 1 }) {
  return (
    <span class={`wall ${side === 1 ? 'wall--right' : ''}`} style={{ '--wx': side * BATTLE.arena.halfWidth }} aria-hidden="true">
      <svg viewBox="0 0 48 120" width="48" height="120">
        <path d="M24 112 C 34 104, 44 96, 48 84" fill="none" stroke="#b08a5a" stroke-width="3" stroke-linecap="round" />
        <path d="M24 70 C 34 64, 44 58, 48 48" fill="none" stroke="#b08a5a" stroke-width="3" stroke-linecap="round" />
        <rect x="18" y="14" width="12" height="104" rx="3" fill="#7a5436" />
        <rect x="20" y="16" width="4" height="100" rx="2" fill="#9a6f48" />
        <path d="M14 14 L24 4 L34 14 Z" fill="#5f3f29" />
        <circle cx="24" cy="70" r="3.5" fill="#d6b27a" />
        <circle cx="24" cy="112" r="3.5" fill="#d6b27a" />
      </svg>
    </span>
  )
}

/**
 * Runs the arena camera (M10): one requestAnimationFrame loop, writing three CSS variables on the arena element
 * (the world and the floats layers both read them) and handing the same numbers to the effects layer. No Preact
 * render happens per frame.
 */
function useArenaCamera(
  arenaRef: MutableRef<HTMLElement | null>,
  posRef: MutableRef<[number, number]>,
  layerRef: MutableRef<FxLayer | null>,
  live: boolean,
  layer3dRef: MutableRef<Arena3DLayer | null>,
  fightersRef: MutableRef<[ArenaFighter, ArenaFighter]>,
): void {
  useEffect(() => {
    if (!live || typeof requestAnimationFrame !== 'function') return
    let raf = 0
    let last = 0
    let cam: Camera | null = null
    let written = ''
    const tick = (time: number) => {
      raf = 0
      const arena = arenaRef.current
      if (!arena) return
      const dt = last ? Math.min(100, time - last) : 0
      last = time
      const width = arena.clientWidth
      const height = arena.clientHeight
      const [xA, xB] = posRef.current
      const target = frameCamera({ xA, xB, width, height })
      cam = stepCamera(cam, target, dt, settings.value.reduceMotion)
      const next = `${cam.centre.toFixed(2)}|${cam.pxPerUnit.toFixed(4)}|${width}|${height}`
      if (next !== written) {
        written = next
        arena.style.setProperty('--cam-x', cam.centre.toFixed(2))
        arena.style.setProperty('--cam-px', cam.pxPerUnit.toFixed(4))
        arena.style.setProperty('--cam-s', spriteScale(cam).toFixed(4))
        layerRef.current?.setCamera({ centre: cam.centre, pxPerUnit: cam.pxPerUnit, width, height, floorPx: FLOOR_PX })
        layer3dRef.current?.setCamera({ centre: cam.centre, pxPerUnit: cam.pxPerUnit, width, height, floorPx: FLOOR_PX })
      }
      // The 3D monsters share this frame: positions and flags in, then one render.
      const l3 = layer3dRef.current
      if (l3) {
        l3.update(fightersRef.current, dt)
        l3.frame(time)
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => {
      if (raf) cancelAnimationFrame(raf)
    }
  }, [live])
}

/**
 * The arena (§12.11 middle band): backdrop, floor, the world layer with the walls and the two monsters, the
 * effects canvas (V1), the floats layer and the range ruler. Owns the camera loop and the effects layer's life.
 */
export function Arena(p: ArenaProps) {
  const arenaRef = useRef<HTMLElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const fxHostRef = useRef<HTMLDivElement>(null)
  const layerRef = useRef<FxLayer | null>(null)
  const posRef = useRef<[number, number]>([p.fighters[0].x, p.fighters[1].x])
  posRef.current = [p.fighters[0].x, p.fighters[1].x]
  const [hitstop, setHitstop] = useState(false)
  const [impact, setImpact] = useState<string | null>(null)
  const liteMode = lite.value
  const live = p.live ?? true
  const backdrop = useMemo(() => sceneBackground({ scene: 'arena', season: p.season, weather: p.weather, lite: liteMode, seed: 3 }), [p.season, p.weather, liteMode])
  const fxQuality = settings.value.fxQuality
  const fxIntensity = settings.value.fxIntensity
  const reduceMotion = settings.value.reduceMotion

  // Art 2.0: fighters whose breed has a model are drawn by the 3D layer; the others stay Classic in the world layer.
  const host3dRef = useRef<HTMLDivElement>(null)
  const layer3dRef = useRef<Arena3DLayer | null>(null)
  const fightersRef = useRef<[ArenaFighter, ArenaFighter]>(p.fighters)
  fightersRef.current = p.fighters
  const [ready3d, setReady3d] = useState<[boolean, boolean]>([false, false])
  const has3d = p.fighters.map((f) => !!lookFor(f.monster.mainBreed, f.monster.variantId, stageOf(f.monster)))
  const use3d = settings.value.monsters === '3d' && !art3dUnavailable.value && !reduceMotionNow() && has3d.some(Boolean)

  useArenaCamera(arenaRef, posRef, layerRef, live, layer3dRef, fightersRef)

  useEffect(() => {
    const host = host3dRef.current
    if (!use3d || !host || typeof window === 'undefined') return
    let alive = true
    let layer: Arena3DLayer | null = null
    void import('../../art3d/art3d.ts').then(({ Stage3D, Arena3DLayer: Layer }) => {
      if (!alive) return
      const h = Stage3D.get().mount(host, {
        quality: lite.value ? 'lite' : currentTier(),
        manualClock: p.manualClock,
        seed: 3,
        onReady: (id) => {
          if (alive) setReady3d((r) => (id === 'a' ? [true, r[1]] : [r[0], true]))
        },
        onLost: () => {
          if (alive) setReady3d([false, false])
        },
        onRestored: () => {
          if (alive) setReady3d([true, true])
        },
        onEvicted: () => {
          if (alive) setReady3d([false, false])
        },
      })
      if (!h) return
      layer = new Layer(h)
      layer3dRef.current = layer
      h.setLight(lightPreset(p.season, p.weather))
      const arena = arenaRef.current
      if (arena) layer.setCamera({ centre: Number(arena.style.getPropertyValue('--cam-x')) || 0, pxPerUnit: Number(arena.style.getPropertyValue('--cam-px')) || 0.4865, width: arena.clientWidth, height: arena.clientHeight, floorPx: FLOOR_PX })
      layer.update(fightersRef.current, 0)
      if (!live) h.start()
    })
    return () => {
      alive = false
      layer3dRef.current = null
      layer?.release()
      setReady3d([false, false])
    }
  }, [use3d, live])

  useEffect(() => {
    layer3dRef.current?.handle.setLight(lightPreset(p.season, p.weather))
  }, [p.season, p.weather])

  // The effects layer: created once per mount, destroyed on unmount. Loads the fx chunk lazily.
  useEffect(() => {
    const host = fxHostRef.current
    if (!host || typeof window === 'undefined') return
    let alive = true
    let layer: FxLayer | null = null
    let statsTimer: ReturnType<typeof setInterval> | null = null
    void import('../../fx/index.ts').then(async ({ createFxLayer }) => {
      if (!alive) return
      const created = await createFxLayer({
        host,
        budget: currentBudget(),
        profile: currentProfile(),
        manualClock: p.manualClock,
        seed: 7,
        onFrame: makeAutoSampler((tier) => {
          layerRef.current?.setQuality(currentBudget())
          if (import.meta.env.DEV) console.info('[fx] Auto quality settled on', tier)
        }),
        hooks: {
          shake: (dx, dy) => {
            const s = stageRef.current
            if (s) s.style.transform = dx === 0 && dy === 0 ? '' : `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px)`
          },
          hitstop: (on) => {
            setHitstop(on)
            layer3dRef.current?.setHitstop(on)
          },
          impactFrame: (on, color) => setImpact(on ? color : null),
        },
      })
      if (!alive) {
        created?.destroy()
        return
      }
      if (!created) {
        fxUnavailable.value = true
        p.onLayer?.(null)
        return
      }
      layer = created
      layerRef.current = created
      const arena = arenaRef.current
      if (arena) created.setCamera({ centre: 0, pxPerUnit: Number(arena.style.getPropertyValue('--cam-px')) || 0.4865, width: arena.clientWidth, height: arena.clientHeight, floorPx: FLOOR_PX })
      statsTimer = setInterval(() => {
        if (layerRef.current) fxStats.value = layerRef.current.stats()
      }, 250)
      p.onLayer?.(created)
    })
    return () => {
      alive = false
      if (statsTimer) clearInterval(statsTimer)
      layerRef.current = null
      layer?.destroy()
      p.onLayer?.(null)
      fxStats.value = null
    }
  }, [])

  // Battle events → default recipes → the layer.
  useEffect(() => {
    if (!live) return
    return subscribeFx((ev) => {
      layer3dRef.current?.onEvent(ev)
      const layer = layerRef.current
      if (!layer) return
      layer.fireAll(recipeFor(ev, currentProfile()))
    })
  }, [live])

  useEffect(() => {
    layerRef.current?.setTimeScale(p.speed ?? 1)
    layer3dRef.current?.setTimeScale(p.speed ?? 1)
  }, [p.speed])
  useEffect(() => {
    layerRef.current?.setPaused(p.paused ?? false)
    layer3dRef.current?.setPaused(p.paused ?? false)
  }, [p.paused])
  useEffect(() => {
    const layer = layerRef.current
    if (!layer) return
    layer.setQuality(currentBudget())
    layer.setIntensity(currentProfile())
  }, [fxQuality, fxIntensity, reduceMotion, settings.value.fxAutoTier])

  const floats = p.floats ?? []
  const bandAt = (gap: number) => Math.min(100, (Math.max(0, gap) / BATTLE.bandEnds[3]!) * 100)

  return (
    <section ref={arenaRef} class={`arena ${hitstop ? 'arena--hitstop' : ''}`} aria-label={t.title}>
      <div ref={stageRef} class="arena__stage">
        <div class="arena__bg" dangerouslySetInnerHTML={{ __html: backdrop }} />
        <div class="arena__floor" />
        <div class="arena__world">
          <Wall side={-1} />
          <Wall side={1} />
          {p.fighters.map((f, i) => (
            <div key={i} class={`fighter ${i === 1 ? 'fighter--b' : ''} ${f.busy ? 'fighter--busy' : ''} ${f.dawdling ? 'fighter--dawdle' : ''} ${f.stunned ? 'fighter--stun' : ''} ${f.lunge ? 'fighter--lunge' : ''} ${f.hit ? 'fighter--hit' : ''} ${f.ko ? 'fighter--ko' : ''} ${f.win ? 'fighter--win' : ''}`} style={{ '--wx': f.x }}>
              {p.showThinking && f.plan && (
                <span class="fighter__plan" role="img" aria-label={t.thinking[f.plan].label}>
                  {t.thinking[f.plan].icon}
                </span>
              )}
              <div class={`fighter__art ${use3d && has3d[i] && ready3d[i] ? 'fighter__art--3d' : ''}`}>
                <MonsterPortrait monster={f.monster} size={BATTLE_CAMERA.basePx} mirror={i === 1} expression={f.expression} />
                {f.hit && !(use3d && has3d[i] && ready3d[i]) && <span class="fighter__flash" aria-hidden="true" />}
              </div>
            </div>
          ))}
        </div>
        <div ref={host3dRef} class="arena__3d" aria-hidden="true" />
        <div ref={fxHostRef} class="arena__fx" aria-hidden="true" />
        <div class="arena__floats" aria-hidden="true">
          {floats.map((e, k) => (
            <span key={e.id} class={`afloat float--${e.tone}`} style={{ '--wx': p.fighters[e.side].x, '--stack': floats.slice(0, k).filter((o) => o.side === e.side).length }}>
              {e.text}
            </span>
          ))}
        </div>
        {impact && <div class="arena__impact" style={{ '--impact-color': impact }} aria-hidden="true" />}
      </div>
      {p.ruler && (
        <div class="ruler" role="img" aria-label={BAND_LABELS[p.ruler.band as 1 | 2 | 3 | 4 | 5]}>
          {[1, 2, 3, 4].map((band) => (
            <span key={band} class={`ruler__band ruler__band--${band} ${p.ruler!.band === band ? 'ruler__band--on' : ''}`}>
              {BAND_LABELS[band as 1 | 2 | 3 | 4]}
            </span>
          ))}
          <span class="ruler__marker" style={{ left: `${bandAt(p.ruler.gap)}%` }} />
        </div>
      )}
      {p.children}
    </section>
  )
}
