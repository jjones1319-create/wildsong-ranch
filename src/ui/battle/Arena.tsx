import { useEffect, useMemo, useRef, useState, type MutableRef } from 'preact/hooks'
import type { ComponentChildren } from 'preact'
import { sceneBackground } from '../../art/backgrounds.ts'
import type { Expression } from '../../art/monster/expressions.ts'
import type { Monster } from '../../core/monster.ts'
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
import { currentBudget, currentProfile, fxStats, fxUnavailable, makeAutoSampler } from '../store/fxStore.ts'
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
function useArenaCamera(arenaRef: MutableRef<HTMLElement | null>, posRef: MutableRef<[number, number]>, layerRef: MutableRef<FxLayer | null>, live: boolean): void {
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

  useArenaCamera(arenaRef, posRef, layerRef, live)

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
          hitstop: (on) => setHitstop(on),
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
      const layer = layerRef.current
      if (!layer) return
      layer.fireAll(recipeFor(ev, currentProfile()))
    })
  }, [live])

  useEffect(() => {
    layerRef.current?.setTimeScale(p.speed ?? 1)
  }, [p.speed])
  useEffect(() => {
    layerRef.current?.setPaused(p.paused ?? false)
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
              <div class="fighter__art">
                <MonsterPortrait monster={f.monster} size={BATTLE_CAMERA.basePx} mirror={i === 1} expression={f.expression} />
                {f.hit && <span class="fighter__flash" aria-hidden="true" />}
              </div>
            </div>
          ))}
        </div>
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
