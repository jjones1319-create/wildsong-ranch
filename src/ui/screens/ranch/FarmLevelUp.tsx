import { useState } from 'preact/hooks'
import { levelBrings } from '../../../core/farm.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { speedFactor } from '../../store/appStore.ts'

const t = HERD_TEXT.farm

/**
 * §9.1 the week summary's small celebration when the farm reaches a new level: a pop, three sparkles and what the
 * level brings (its perks, a pen to build). It never blocks the summary; a tap (or instant animations, or Reduce
 * motion) skips the sparkles.
 */
export function FarmLevelUp({ level }: { level: number }) {
  const [done, setDone] = useState(() => speedFactor() === 0)
  const brings = levelBrings(level)
  const list = [...brings.perks.map((p) => p.name), ...(brings.pens.length > 0 ? [t.newPen] : [])]
  return (
    <section class={`card farmup ${done ? 'farmup--done' : ''}`} role="status" onClick={() => setDone(true)}>
      <span class="farmup__spark" aria-hidden="true">
        ✨
      </span>
      <span class="farmup__spark" aria-hidden="true">
        🌾
      </span>
      <span class="farmup__spark" aria-hidden="true">
        ✨
      </span>
      <p class="farmup__title">🎉 {fill(t.levelUp, { n: level })}</p>
      {list.length > 0 && <p class="small">{fill(t.brings, { list: list.join(' · ') })}</p>}
    </section>
  )
}
