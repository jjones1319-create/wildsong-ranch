import { useEffect, useRef, useState } from 'preact/hooks'
import { isUltraId, ULTRA_IDS, ULTRA_LOOKS, ultraVariant, type UltraId } from '../../../art/ultraLooks.ts'
import type { Gallery3D, GalleryStats } from '../../../art3d/gallery/gallery3d.ts'
import { GALLERY_CLIPS, GALLERY_LOOPS, type GalleryClip } from '../../../art3d/ultra/clips.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { SECRETS } from '../../../data/secrets.ts'
import { GALLERY3D_TEXT as T } from '../../../data/text/gallery3d.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { ART } from '../../../data/tuning.ts'
import { Chips, Segmented, Toggle, TopBar } from '../../components/Controls.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { currentTier, reduceMotionNow } from '../../store/fxStore.ts'

const G = ART.gallery3d

/** What the review tools and the e2e test drive (e2e/gallery3d.spec.ts). */
interface GalleryHook {
  ready: boolean
  phase: Phase
  /** A look id: a breed, or a grown form (`hearthwing-grown`). */
  show(look: string, variant?: string | null, compare?: boolean): void
  play(clip: GalleryClip): void
  /** Review only: hold a move at a share of its length; null plays on. */
  pose(clip: GalleryClip | null, t?: number): void
  turn(yawDeg: number, pitchDeg?: number): void
  zoom(k: number): void
  stats(): GalleryStats | null
  snapshot(): string | null
  /** Dev builds only: the 3D scene and camera, for review scripts. */
  inspect?(): unknown
}

declare global {
  interface Window {
    __gallery3d?: GalleryHook
  }
}

type Phase = 'starting' | 'loading' | 'ready' | 'failed' | 'error'

/** Remembered while the app is open, so coming back shows the same monster. */
let lastShown: { look: UltraId; variant: string | null; compare: boolean } = { look: 'puddlepup', variant: null, compare: false }

/** A look's name for the chips and the stage: the breed's, "(grown)" for a grown form. */
function lookName(id: UltraId): string {
  const look = ULTRA_LOOKS[id] ?? ULTRA_LOOKS.puddlepup!
  return T.lookName(BREED_BY_ID[look.breed].name, look.stage === 'grown')
}

/**
 * Lab → 3D Gallery (docs/ART_2_DETAIL.md §9.3): every finished Ultra breed (src/art/ultraLooks.ts) in the film look,
 * drag to turn, pinch or the buttons to zoom, its moves, its variants, and Puddlepup beside it at true scale. The 3D
 * code loads with the screen (a lazy chunk); Lite effects show the lighter models.
 */
export function LabGallery3DScreen() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const gallery = useRef<Gallery3D | null>(null)
  const [phase, setPhase] = useState<Phase>('starting')
  const [sel, setSel] = useState(lastShown)
  const [held, setHeld] = useState<string[]>([])
  const [clip, setClip] = useState<GalleryClip>('idle')
  const [stats, setStats] = useState<GalleryStats | null>(null)
  // a failed load is tried again from the stage's note
  const [retry, setRetry] = useState(0)
  const lite = currentTier() === 'lite'
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const pinch = useRef<number | null>(null)

  // the stage: created once for the screen
  useEffect(() => {
    let alive = true
    // review and test runs: ?backend=webgl picks the renderer, ?fixed=1 holds full quality
    const q = new URLSearchParams(location.search)
    const backend = q.get('backend') === 'webgl' ? 'webgl' : 'webgpu'
    const fixedQuality = q.get('fixed') === '1'
    void (async () => {
      try {
        const m = await import('../../../art3d/gallery/gallery3d.ts')
        if (!alive || !canvas.current) return
        const g = await m.createGallery3D({ canvas: canvas.current, lite, reduceMotion: reduceMotionNow(), backend, fixedQuality })
        if (!alive) {
          g.dispose()
          return
        }
        gallery.current = g
        setPhase('loading')
      } catch (err) {
        console.error(err)
        if (alive) setPhase('error')
      }
    })()
    const timer = setInterval(() => {
      const g = gallery.current
      if (!g) return
      const s = g.stats()
      setStats(s)
      // a move that settled back into idle on its own: the Idle button lights again
      if (s.clip && /idle/.test(s.clip)) setClip((c) => (GALLERY_LOOPS.has(c) ? c : 'idle'))
    }, 500)
    return () => {
      alive = false
      clearInterval(timer)
      gallery.current?.dispose()
      gallery.current = null
    }
  }, [])

  // what stands there: loads on a change of breed, look or the Puddlepup beside it
  useEffect(() => {
    const g = gallery.current
    if (!g || phase === 'starting' || phase === 'error') return
    let alive = true
    lastShown = sel
    setPhase('loading')
    g.show(sel).then(
      () => {
        if (!alive) return
        setHeld(g.variants())
        setClip('idle')
        setPhase('ready')
      },
      (err: unknown) => {
        console.error(err)
        if (alive) setPhase('failed')
      },
    )
    return () => {
      alive = false
    }
  }, [sel.look, sel.variant, sel.compare, retry, phase === 'starting' || phase === 'error'])

  const play = (c: GalleryClip) => {
    gallery.current?.play(c)
    if (c !== 'blink') setClip(c)
  }

  useEffect(() => {
    window.__gallery3d = {
      get ready() {
        return phase === 'ready'
      },
      get phase() {
        return phase
      },
      show: (id, variant = null, compare = false) => {
        const look = isUltraId(id) ? id : 'puddlepup'
        setSel({ look, variant: ultraVariant(look, variant), compare })
      },
      play,
      pose: (c, t) => gallery.current?.pose(c, t),
      turn: (y, p = 0) => gallery.current?.turn(y, p),
      zoom: (k) => gallery.current?.zoom(k),
      stats: () => gallery.current?.stats() ?? null,
      snapshot: () => gallery.current?.snapshot() ?? null,
      ...(import.meta.env.DEV ? { inspect: () => gallery.current?.inspect() } : {}),
    }
    return () => {
      delete window.__gallery3d
    }
  }, [phase])

  // drag turns the turntable, two fingers pinch the zoom, the wheel zooms on a computer
  const onPointerDown = (e: PointerEvent) => {
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    pinch.current = null
  }
  const onPointerMove = (e: PointerEvent) => {
    const p = pointers.current.get(e.pointerId)
    if (!p) return
    const g = gallery.current
    if (pointers.current.size >= 2) {
      p.x = e.clientX
      p.y = e.clientY
      const [a, b] = [...pointers.current.values()] as [{ x: number; y: number }, { x: number; y: number }]
      const d = Math.hypot(a.x - b.x, a.y - b.y)
      if (pinch.current && d > 0) g?.zoom(d / pinch.current)
      pinch.current = d
      return
    }
    g?.turn((e.clientX - p.x) * G.turnDegPerPx, (e.clientY - p.y) * G.pitchDegPerPx)
    p.x = e.clientX
    p.y = e.clientY
  }
  const onPointerUp = (e: PointerEvent) => {
    pointers.current.delete(e.pointerId)
    pinch.current = null
  }
  const onWheel = (e: WheelEvent) => {
    e.preventDefault()
    gallery.current?.zoom(e.deltaY < 0 ? G.zoomStep : 1 / G.zoomStep)
  }

  // a look that left the registry since (the remembered one) shows Puddlepup
  const name = lookName(sel.look)
  const look = ULTRA_LOOKS[sel.look]
  const variants = (look?.variants ?? []).filter((id) => held.includes(id))
  const busy = phase !== 'ready'

  return (
    <main class="screen gallery3d">
      <TopBar title={T.title} />
      <SpeakerCard speaker={UI_TEXT.wren} tone="muted">
        <p>{phase === 'error' ? T.noWebgl : T.hint}</p>
        {lite && phase !== 'error' && <p class="small muted">{T.lite}</p>}
      </SpeakerCard>
      <div
        class="gallery3d__stage"
        role="img"
        aria-label={T.stageLabel(name)}
        data-look={sel.look}
        data-phase={phase}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
      >
        <canvas ref={canvas} class="gallery3d__canvas" />
        {(phase === 'starting' || phase === 'loading') && <p class="gallery3d__note">{T.loading}</p>}
        {phase === 'failed' && (
          <button type="button" class="gallery3d__note gallery3d__retry" onPointerDown={(e) => e.stopPropagation()} onClick={() => setRetry((n) => n + 1)}>
            {T.failed}
          </button>
        )}
        {phase !== 'error' && (
          <div class="gallery3d__zoom">
            <button type="button" class="btn" aria-label={T.zoomIn} onPointerDown={(e) => e.stopPropagation()} onClick={() => gallery.current?.zoom(G.zoomStep)}>
              ＋
            </button>
            <button type="button" class="btn" aria-label={T.zoomOut} onPointerDown={(e) => e.stopPropagation()} onClick={() => gallery.current?.zoom(1 / G.zoomStep)}>
              －
            </button>
            <button type="button" class="btn" aria-label={T.zoomReset} onPointerDown={(e) => e.stopPropagation()} onClick={() => gallery.current?.zoom(0)}>
              ⤢
            </button>
          </div>
        )}
      </div>
      <p class="gallery3d__stats muted small" aria-hidden="true">
        {stats && stats.triangles > 0 ? T.stats(stats.fps, stats.triangles, stats.dpr, stats.backend, stats.level) : ' '}
      </p>
      {phase !== 'error' && (
        <>
          <p class="field__label small">{T.moves}</p>
          <div class="chips gallery3d__moves" role="group" aria-label={T.moves}>
            {GALLERY_CLIPS.map((c) => (
              <button key={c} type="button" data-clip={c} aria-pressed={c !== 'blink' && c === clip} class={`chip ${c !== 'blink' && c === clip ? 'chip--on' : ''}`} disabled={busy} onClick={() => play(c)}>
                {T.clips[c]}
              </button>
            ))}
          </div>
          <p class="field__label small">{T.breed}</p>
          <Chips
            options={ULTRA_IDS.map((id) => ({ value: id, label: lookName(id) }))}
            value={sel.look}
            onChange={(id) => setSel((s) => ({ look: id, variant: null, compare: id === 'puddlepup' ? false : s.compare }))}
            label={T.breed}
          />
          {ULTRA_IDS.length < 2 && <p class="small muted">{T.more}</p>}
          {variants.length > 0 && (
            <>
              <p class="field__label small">{T.look}</p>
              <Segmented
                options={[{ value: '', label: T.usual }, ...variants.map((id) => ({ value: id, label: SECRETS.find((x) => x.id === id)?.adjective ?? id }))]}
                value={sel.variant ?? ''}
                onChange={(id) => setSel((s) => ({ ...s, variant: id || null }))}
                label={T.look}
              />
            </>
          )}
          {sel.look !== 'puddlepup' && <Toggle label={T.beside} hint={T.besideHint} checked={sel.compare} onChange={(on) => setSel((s) => ({ ...s, compare: on }))} />}
        </>
      )}
    </main>
  )
}
