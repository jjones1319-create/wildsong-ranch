import { useMemo } from 'preact/hooks'
import type { Expression } from '../../art/monster/expressions.ts'
import { renderMonsterSvg, specForBreed, specFromMonster, type RenderSpec } from '../../art/monster/render.ts'
import type { Monster } from '../../core/monster.ts'
import type { BreedId } from '../../data/types.ts'
import { settings } from '../store/appStore.ts'

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

/** The procedural SVG portrait. The string renderer is pure, so it is memoised on its inputs. */
export function MonsterPortrait(p: PortraitProps) {
  const animate = (p.animate ?? true) && !settings.value.reduceMotion
  const spec: RenderSpec | null = p.monster
    ? specFromMonster(p.monster, { expression: p.expression, sparkle: p.sparkle, mischief: p.mischief, stage: p.stage, animate })
    : p.breed
      ? specForBreed(p.breed, { sub: p.sub, expression: p.expression, sparkle: p.sparkle, mischief: p.mischief, stage: p.stage, animate })
      : null
  const key = spec ? JSON.stringify([spec, p.size, p.mirror, p.label]) : ''
  const svg = useMemo(() => (spec ? renderMonsterSvg(spec, { size: p.size ?? 128, mirror: p.mirror, label: p.label ?? p.monster?.name }) : ''), [key])
  if (!svg) return null
  return <div class={`portrait ${p.class ?? ''}`} style={{ width: p.size ?? 128, height: p.size ?? 128 }} dangerouslySetInnerHTML={{ __html: svg }} />
}
