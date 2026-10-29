import { useEffect, useRef, useState } from 'preact/hooks'
import { hasModel, lookFor, MODEL_LOOKS, type LookId } from '../../../art/models.ts'
import type { StageHandle } from '../../../art3d/art3d.ts'
import { FACES, STAR_CLIPS, type ClipName, type FaceName } from '../../../art3d/types.ts'
import { BREED_BY_ID, BREEDS } from '../../../data/breeds.ts'
import { SECRETS } from '../../../data/secrets.ts'
import { FX_QUALITY_LABELS, STAGE_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { fill } from '../../../data/text/format.ts'
import { ART } from '../../../data/tuning.ts'
import type { BreedId } from '../../../data/types.ts'
import { Chips, Segmented, Toggle, TopBar } from '../../components/Controls.tsx'
import { Monster3D } from '../../components/Monster3D.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { settings } from '../../store/appStore.ts'
import { art3dStats, art3dUnavailable } from '../../store/artStore.ts'
import { currentTier, reduceMotionNow } from '../../store/fxStore.ts'

const t = UI_TEXT.modelsLab
const SIZE = 300
/** The review scripts lose and restore the WebGL context through this (kept, because a lost context returns no extensions). */
let loseExt: WEBGL_lose_context | null = null

interface ViewState {
  breed: BreedId
  variant: string | null
  stage: number
  face: FaceName
  clip: ClipName
  yaw: number
}

interface SnapshotReq {
  look?: LookId
  breed?: BreedId
  variant?: string | null
  stage?: number
  face?: FaceName
  clip?: ClipName
  yaw?: number
  size?: number
}

interface Art3dWindow extends Window {
  __art3d?: {
    ready: boolean
    set: (s: Partial<ViewState>) => void
    snapshot: (req: SnapshotReq) => Promise<string | null>
    step: (ms: number) => void
    loseContext: () => void
    restoreContext: () => void
    stats: () => unknown
    /** What the live actor really shows right now (the scripts wait for it to match before a capture). */
    state: () => { variant: string | null; clip: string | null; stage: number; face: string } | null
  }
}

/**
 * Monster Lab → Models (ART_2_PLAN §8 P1): any breed, variant, stage, face and clip; drag to turn it; an fps
 * counter. Breeds without a model show their Classic drawing and say so. Playwright drives it through
 * `window.__art3d` for the review sheets and the build-time portraits (`?artmanual=1` gives a manual clock).
 */
export function LabModelsScreen() {
  const [v, setV] = useState<ViewState>({ breed: 'puddlepup', variant: null, stage: 5, face: 'neutral', clip: 'idle', yaw: 0 })
  const [autoTurn, setAutoTurn] = useState(false)
  const handleRef = useRef<StageHandle | null>(null)
  const vRef = useRef(v)
  vRef.current = v
  const manual = typeof location !== 'undefined' && location.search.includes('artmanual')
  const stats = art3dStats.value
  const look = lookFor(v.breed, v.variant, v.stage)
  const modelled = hasModel(v.breed)
  const variants = SECRETS.filter((s) => s.breed === v.breed)
  const drag = useRef<{ x: number; yaw: number } | null>(null)

  const playClip = (clip: ClipName) => {
    const h = handleRef.current
    if (!h) return
    const a = h.actor('m')
    const meta = a?.asset.meta.clips[clip]
    const again = () => {
      if (handleRef.current === h && vRef.current.clip === clip) setTimeout(() => h.play('m', clip, { restart: true, onFinish: again }), meta?.hold ? 900 : 250)
    }
    h.play('m', clip, { restart: true, onFinish: meta?.loop === false ? again : undefined })
  }

  useEffect(() => {
    if (handleRef.current) playClip(v.clip)
  }, [v.clip, v.breed, v.variant])

  useEffect(() => {
    if (!autoTurn || reduceMotionNow()) return
    const id = setInterval(() => setV((s) => ({ ...s, yaw: (s.yaw + 0.9) % 360 })), 16)
    return () => clearInterval(id)
  }, [autoTurn])

  // Playwright and the dev console drive the viewer through window.__art3d.
  useEffect(() => {
    const w = window as Art3dWindow
    w.__art3d = {
      ready: false,
      set: (s) => setV((prev) => ({ ...prev, ...s })),
      snapshot: async (req) => {
        const { Stage3D } = await import('../../../art3d/art3d.ts')
        const cur = vRef.current
        const ref = req.look ? { look: req.look, variant: req.variant ?? null } : lookFor(req.breed ?? cur.breed, req.variant === undefined ? cur.variant : req.variant, req.stage ?? cur.stage)
        if (!ref) return null
        const blob = await Stage3D.get().renderPortrait({ look: ref.look, variant: ref.variant, stage: req.stage ?? cur.stage, face: req.face ?? cur.face, size: req.size ?? 256, yawDeg: req.yaw ?? ART.portrait.yawDeg, clip: req.clip ?? cur.clip })
        if (!blob) return null
        return await new Promise<string>((resolve) => {
          const r = new FileReader()
          r.onload = () => resolve(String(r.result))
          r.readAsDataURL(blob)
        })
      },
      step: (ms) => handleRef.current?.step(ms),
      loseContext: () => {
        const c = document.querySelector('canvas.art3d-canvas') as HTMLCanvasElement | null
        const gl = c?.getContext('webgl2') as WebGL2RenderingContext | null
        // a lost context returns no extensions, so the handle is kept for the restore
        loseExt = gl?.getExtension('WEBGL_lose_context') ?? null
        loseExt?.loseContext()
      },
      restoreContext: () => {
        loseExt?.restoreContext()
      },
      stats: () => handleRef.current?.stats() ?? null,
      state: () => {
        const a = handleRef.current?.actor('m')
        return a ? { variant: a.variant, clip: a.clipName, stage: a.stage, face: a.baseFace } : null
      },
    }
    return () => {
      delete w.__art3d
    }
  }, [])

  const onPointerDown = (e: PointerEvent) => {
    drag.current = { x: e.clientX, yaw: vRef.current.yaw }
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: PointerEvent) => {
    const d = drag.current
    if (!d) return
    setV((s) => ({ ...s, yaw: d.yaw + (e.clientX - d.x) * 0.6 }))
  }
  const onPointerUp = () => {
    drag.current = null
  }

  const breedOptions = BREEDS.map((b) => ({ value: b.id, label: `${hasModel(b.id) ? '◆ ' : ''}${b.name}` }))
  const s = settings.value

  return (
    <main class="screen modelslab">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.pell} tone="muted">
        <p>{art3dUnavailable.value ? t.noWebgl : s.monsters !== '3d' ? t.classicOn : modelled ? t.hint : fill(t.noModel, { name: BREED_BY_ID[v.breed].name })}</p>
      </SpeakerCard>
      <div class="modelslab__stage" onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} data-breed={v.breed} data-face={v.face} data-clip={v.clip}>
        {modelled && look && !art3dUnavailable.value ? (
          <Monster3D
            look={look.look}
            variant={look.variant}
            stage={v.stage}
            face={v.face}
            size={SIZE}
            clip={v.clip}
            yaw={v.yaw}
            label={BREED_BY_ID[v.breed].name}
            manualClock={manual}
            fallback={<MonsterPortrait breed={v.breed} stage={v.stage} size={SIZE} animate={false} />}
            onHandle={(h) => {
              handleRef.current = h
              const w = window as Art3dWindow
              if (w.__art3d) w.__art3d.ready = h !== null
              if (h) playClip(vRef.current.clip)
            }}
          />
        ) : (
          <MonsterPortrait breed={v.breed} stage={v.stage} size={SIZE} />
        )}
      </div>
      <p class="modelslab__stats muted small" aria-live="polite" data-fps={stats?.fps ?? ''}>
        {stats ? `${stats.fps} ${t.fps} · ${stats.tris} ${t.tris} · ${stats.drawCalls} ${t.calls} · ${FX_QUALITY_LABELS[currentTier()].name}` : t.turnHint}
      </p>
      <Toggle label={t.autoTurn} checked={autoTurn} onChange={setAutoTurn} />
      <p class="field__label small">{t.breed}</p>
      <Chips options={breedOptions} value={v.breed} onChange={(b) => setV((st) => ({ ...st, breed: b, variant: null }))} label={t.breed} />
      {variants.length > 0 && (
        <>
          <p class="field__label small">{t.variant}</p>
          <Segmented options={[{ value: '', label: t.base }, ...variants.map((x) => ({ value: x.id, label: `${x.adjective}${MODEL_LOOKS[(lookFor(v.breed, null, v.stage)?.look ?? 'puddlepup') as LookId]?.variants.includes(x.id) ? '' : ' (Classic)'}` }))]} value={v.variant ?? ''} onChange={(id) => setV((st) => ({ ...st, variant: id || null }))} label={t.variant} />
        </>
      )}
      <p class="field__label small">{t.stage}</p>
      <Chips options={STAGE_NAMES.map((n, i) => ({ value: String(i + 1), label: `${i + 1} ${n}` }))} value={String(v.stage)} onChange={(x) => setV((st) => ({ ...st, stage: Number(x) }))} label={t.stage} />
      <p class="field__label small">{t.face}</p>
      <Chips options={FACES.map((f) => ({ value: f, label: f }))} value={v.face} onChange={(f) => setV((st) => ({ ...st, face: f }))} label={t.face} />
      <p class="field__label small">{t.clip}</p>
      <Chips options={STAR_CLIPS.map((c) => ({ value: c, label: c }))} value={v.clip} onChange={(c) => setV((st) => ({ ...st, clip: c }))} label={t.clip} />
    </main>
  )
}
