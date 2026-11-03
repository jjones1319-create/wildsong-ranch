import { useState } from 'preact/hooks'
import { penCapacity } from '../../../core/farm.ts'
import type { GameState } from '../../../core/state.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { navigate } from '../../router.ts'
import { cardId } from '../../store/herdStore.ts'
import { HerdSheet } from './HerdSheet.tsx'
import { orderIcon, orderLabel, tileBadge } from './herdBits.ts'
import { PenSheet } from './PenSheet.tsx'

/**
 * §21 v16 the herd strip under the stage: a ⭐ tile for the star (its Monster Card), a tile per ranch-mate (its sheet:
 * orders, Card, Edit, Make star, the Freezer, Set free) with its order icon and a status or last-week badge, a "+" on
 * each empty pen (move a monster in from the Freezer), and the pens count. One compact row that scrolls sideways.
 */
export function HerdStrip({ g, disabled }: { g: GameState; disabled?: boolean }) {
  const [open, setOpen] = useState<string | null>(null)
  const [penOpen, setPenOpen] = useState(false)
  const t = HERD_TEXT.strip
  const capacity = penCapacity(g)
  const empty = Math.max(0, capacity - g.ranchmates.length)
  return (
    <section class="herd" aria-label={t.label}>
      <div class="herd__row">
        {g.monster && (
          <button
            type="button"
            class="herd__tile herd__tile--star"
            disabled={disabled}
            aria-label={fill(t.star, { name: g.monster.name })}
            onClick={() => {
              cardId.value = null
              navigate('ranchCard')
            }}
          >
            <span class="herd__pic">
              <MonsterPortrait monster={g.monster} size={44} animate={false} />
              <span class="herd__corner" aria-hidden="true">
                ⭐
              </span>
            </span>
          </button>
        )}
        {g.ranchmates.map((r) => {
          const badge = tileBadge(r.monster, r.last)
          return (
            <button
              key={r.monster.id}
              type="button"
              class="herd__tile"
              disabled={disabled}
              aria-label={fill(t.mate, { name: r.monster.name, order: orderLabel(r.order), status: badge.text })}
              onClick={() => setOpen(r.monster.id)}
            >
              <span class="herd__pic">
                <MonsterPortrait monster={r.monster} size={44} animate={false} />
                <span class="herd__corner" aria-hidden="true">
                  {orderIcon(r.order)}
                </span>
              </span>
              <span class="herd__text" aria-hidden="true">
                <span class="herd__name">{r.monster.name}</span>
                <span class={`herd__badge herd__badge--${badge.tone}`}>{badge.text}</span>
              </span>
            </button>
          )
        })}
        {Array.from({ length: empty }, (_, i) => (
          <button key={`empty-${i}`} type="button" class="herd__tile herd__tile--empty" disabled={disabled} aria-label={t.emptyPen} onClick={() => setPenOpen(true)}>
            <span aria-hidden="true">＋</span>
          </button>
        ))}
        <span class="herd__label">{fill(HERD_TEXT.farm.pens, { used: g.ranchmates.length, max: capacity })}</span>
      </div>
      <HerdSheet id={open} onClose={() => setOpen(null)} />
      <PenSheet open={penOpen} onClose={() => setPenOpen(false)} />
    </section>
  )
}
