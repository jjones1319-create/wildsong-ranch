import { useEffect, useMemo, useRef } from 'preact/hooks'
import type { Expression } from '../../art/monster/expressions.ts'
import { renderMonsterSvg, specForBreed, specFromMonster, type RenderSpec } from '../../art/monster/render.ts'
import { lookFor } from '../../art/models.ts'
import type { ClipName, FaceName } from '../../art3d/types.ts'
import type { LightPreset } from '../../art3d/materials.ts'
import type { Monster } from '../../core/monster.ts'
import { UI } from '../../data/tuning.ts'
import type { BreedId } from '../../data/types.ts'
import { settings } from '../store/appStore.ts'
import { art3dUnavailable, portraitMode } from '../store/artStore.ts'
import { reduceMotionNow } from '../store/fxStore.ts'
import { lite } from '../store/perf.ts'
import { Monster3D } from './Monster3D.tsx'
import { PortraitImage } from './PortraitImage.tsx'

export interface PortraitProps {
  monster?: Monster
  breed?: BreedId
  size?: number
  expression?: Expression
  sparkle?: boolean
  mischief?: boolean
  stage?: number
  mirror?: boolean
  class?: string
  label?: string
  /** False for lists and thumbnails, so a hundred cards don't each run idle animations. */
  animate?: boolean
  /** Art 2.0: the monster is the subject of this screen, so a breed with a model shows it live in 3D. */
  live?: boolean
  /** Live 3D only: the loop to play, the light preset and whether to do ranch things now and then. */
  clip?: ClipName
  light?: LightPreset
  idleActs?: boolean
}

/** The 3D face for a Classic spec: the eight expressions map one to one; a sparkle reads as happy. */
function faceOf(spec: RenderSpec): FaceName {
  if (spec.expression === 'neutral' && spec.sparkle) return 'happy'
  return spec.expression
}

/**
 * The monster's portrait. Classic is the procedural SVG (pure and memoised on its inputs); a breed with a
 * Blender model shows it live where it is the subject of the screen, or as a cached picture in lists
 * (ART_2_PLAN §3.3). Animated Classic portraits also glance toward where the player taps (§22 polish).
 */
export function MonsterPortrait(p: PortraitProps) {
  const animate = (p.animate ?? true) && !settings.value.reduceMotion
  const liteMode = lite.value
  const spec: RenderSpec | null = p.monster
    ? specFromMonster(p.monster, { expression: p.expression, sparkle: p.sparkle, mischief: p.mischief, stage: p.stage, animate, lite: liteMode })
    : p.breed
      ? specForBreed(p.breed, { expression: p.expression, sparkle: p.sparkle, mischief: p.mischief, stage: p.stage, animate, lite: liteMode })
      : null
  const key = spec ? JSON.stringify([spec, p.size, p.mirror, p.label]) : ''
  const svg = useMemo(() => (spec ? renderMonsterSvg(spec, { size: p.size ?? 128, mirror: p.mirror, label: p.label ?? p.monster?.name }) : ''), [key])
  const ref = useRef<HTMLDivElement>(null)
  const look = spec ? lookFor(spec.mainBreed, p.monster?.variantId ?? null, spec.stage) : null
  const mode = portraitMode(!!look, settings.value.monsters, art3dUnavailable.value, reduceMotionNow(), !!p.live)

  useEffect(() => {
    if (!animate || mode !== 'classic') return
    let timer: ReturnType<typeof setTimeout> | null = null
    const onTap = (e: PointerEvent) => {
      const box = ref.current
      if (!box) return
      const r = box.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height / 2
      const dx = e.clientX - cx
      const dy = e.clientY - cy
      const len = Math.hypot(dx, dy) || 1
      const reach = Math.min(1, len / (r.width * 1.5))
      box.style.setProperty('--ws-look-x', `${((dx / len) * UI.glance.maxPx * reach).toFixed(2)}px`)
      box.style.setProperty('--ws-look-y', `${((dy / len) * UI.glance.maxPx * reach).toFixed(2)}px`)
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        box.style.setProperty('--ws-look-x', '0px')
        box.style.setProperty('--ws-look-y', '0px')
      }, UI.glance.holdMs)
    }
    document.addEventListener('pointerdown', onTap)
    return () => {
      document.removeEventListener('pointerdown', onTap)
      if (timer) clearTimeout(timer)
    }
  }, [animate, mode])

  if (!svg || !spec) return null
  const size = p.size ?? 128
  const classic = <div ref={ref} class={`portrait ${p.class ?? ''}`} style={{ width: size, height: size }} dangerouslySetInnerHTML={{ __html: svg }} />
  if (mode === 'live' && look) {
    return (
      <Monster3D look={look.look} variant={look.variant} stage={spec.stage} face={faceOf(spec)} sick={spec.expression === 'sick' ? 1 : 0} size={size} mirror={p.mirror} label={p.label ?? p.monster?.name} clip={p.clip} light={p.light} idleActs={p.idleActs} fallback={classic} class={p.class} />
    )
  }
  if (mode === 'image' && look) {
    return <PortraitImage look={look.look} variant={look.variant} stage={spec.stage} face={faceOf(spec)} size={size} mirror={p.mirror} label={p.label ?? p.monster?.name} fallback={classic} class={p.class} />
  }
  return classic
}
