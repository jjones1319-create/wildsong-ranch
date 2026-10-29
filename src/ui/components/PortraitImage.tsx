import type { ComponentChildren } from 'preact'
import { useEffect, useState } from 'preact/hooks'
import { lookKey, type LookId } from '../../art/models.ts'
import { ART } from '../../data/tuning.ts'
import { idbStore } from '../../save/db.ts'
import { isBasePortrait, PortraitCache, type PortraitJob } from '../../save/portraitCache.ts'
import { art3dUnavailable } from '../store/artStore.ts'

export interface PortraitImageProps {
  look: LookId
  variant: string | null
  stage: number
  face: string
  size: number
  mirror?: boolean
  label?: string
  fallback: ComponentChildren
  class?: string
}

let cache: PortraitCache | null = null

/** Draws a missing picture through the shared stage (the 3D code loads lazily). */
async function draw(job: PortraitJob): Promise<Blob | null> {
  if (art3dUnavailable.value) return null
  const { Stage3D } = await import('../../art3d/art3d.ts')
  return Stage3D.get().renderPortrait({ look: job.look, variant: job.variant, stage: job.drawStage, face: job.face as never, size: ART.portrait.px })
}

export function portraitCache(): PortraitCache {
  return (cache ??= new PortraitCache(idbStore(), draw))
}

/**
 * A picture of a 3D monster for lists and pickers (ART_2_PLAN §3.3): the precached base picture when it fits,
 * otherwise the on-phone cache; the Classic drawing shows until a picture is ready or if none can be made.
 */
export function PortraitImage(p: PortraitImageProps) {
  const req = { look: p.look, variant: p.variant, stage: p.stage, face: p.face }
  const base = isBasePortrait(req)
  const baseUrl = `${import.meta.env.BASE_URL}portraits/${lookKey({ look: p.look, variant: p.variant })}.webp`
  const [url, setUrl] = useState<string | null>(() => (base ? baseUrl : portraitCache().peek(req)))
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    if (base) {
      setUrl(baseUrl)
      return
    }
    const hit = portraitCache().peek(req)
    setUrl(hit)
    if (!hit) {
      void portraitCache()
        .get(req)
        .then((u) => {
          if (alive) setUrl(u)
        })
    }
    return () => {
      alive = false
    }
  }, [p.look, p.variant, p.stage, p.face])

  if (!url || failed === url) return <>{p.fallback}</>
  return (
    <div class={`portrait portrait--img ${p.class ?? ''}`} style={{ width: p.size, height: p.size }}>
      <img src={url} alt={p.label ?? ''} width={p.size} height={p.size} draggable={false} style={p.mirror ? { transform: 'scaleX(-1)' } : undefined} onError={() => setFailed(url)} />
    </div>
  )
}
