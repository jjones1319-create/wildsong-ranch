import { useEffect, useMemo, useRef } from 'preact/hooks'
import type { Expression } from '../../art/monster/expressions.ts'
import { renderMonsterSvg, specForBreed, specFromMonster, type RenderSpec } from '../../art/monster/render.ts'
import type { Monster } from '../../core/monster.ts'
import { UI } from '../../data/tuning.ts'
import type { BreedId } from '../../data/types.ts'
import { settings } from '../store/appStore.ts'
import { lite } from '../store/perf.ts'

export interface PortraitProps {
  monster?: Monster
  breed?: BreedId
  sub?: BreedId
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
}

/**
 * The procedural SVG portrait. The string renderer is pure, so it is memoised on its inputs.
 * Animated portraits also glance toward where the player taps (§22 polish).
 */
export function MonsterPortrait(p: PortraitProps) {
  const animate = (p.animate ?? true) && !settings.value.reduceMotion
  const liteMode = lite.value
  const spec: RenderSpec | null = p.monster
    ? specFromMonster(p.monster, { expression: p.expression, sparkle: p.sparkle, mischief: p.mischief, stage: p.stage, animate, lite: liteMode })
    : p.breed
      ? specForBreed(p.breed, { sub: p.sub, expression: p.expression, sparkle: p.sparkle, mischief: p.mischief, stage: p.stage, animate, lite: liteMode })
      : null
  const key = spec ? JSON.stringify([spec, p.size, p.mirror, p.label]) : ''
  const svg = useMemo(() => (spec ? renderMonsterSvg(spec, { size: p.size ?? 128, mirror: p.mirror, label: p.label ?? p.monster?.name }) : ''), [key])
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!animate) return
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
  }, [animate])

  if (!svg) return null
  return <div ref={ref} class={`portrait ${p.class ?? ''}`} style={{ width: p.size ?? 128, height: p.size ?? 128 }} dangerouslySetInnerHTML={{ __html: svg }} />
}
