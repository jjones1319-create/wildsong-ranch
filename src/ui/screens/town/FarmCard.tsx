import { useState } from 'preact/hooks'
import { farmView, type PenRefusal } from '../../../core/farm.ts'
import type { GameState } from '../../../core/state.ts'
import { FARM_PENS } from '../../../data/farm.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { FARM } from '../../../data/tuning.ts'
import { Badge, Confirm } from '../../components/Controls.tsx'
import { gold } from '../../components/RanchBits.tsx'
import { showToast } from '../../store/appStore.ts'
import { buyPen } from '../../store/herdStore.ts'

const t = HERD_TEXT.farm

/**
 * GAME_DESIGN §9.1 the farm card at the top of Ranch Upgrades: the level and its XP bar, the pens built, the next pen
 * (its price and level, Build with a confirm, and the refusals said kindly), and the perks (✓, or 🔒 Lv N).
 */
export function FarmCard({ g }: { g: GameState }) {
  const [asking, setAsking] = useState(false)
  const v = farmView(g)
  const next = v.pens.next
  const span = v.levelTo === null ? 1 : v.levelTo - v.levelFrom
  const into = v.levelTo === null ? 1 : v.xp - v.levelFrom
  const refusal = (why: PenRefusal) => (why === 'level' && next ? fill(t.refused.level, { n: next.level }) : t.refused[why])
  const confirm = () => {
    setAsking(false)
    const why = buyPen()
    showToast(why ? refusal(why) : t.built)
  }
  return (
    <section class="card farmcard" aria-label={t.title}>
      <p class="field__label farmcard__head">
        <span>{t.title}</span>
        <Badge tone="pure">{fill(t.level, { n: v.level })}</Badge>
      </p>
      <p class="muted small">{t.intro}</p>
      <div class="bar bar--xp">
        <span class="bar__label">{t.xpLabel}</span>
        <span class="bar__track" role="img" aria-label={v.levelTo === null ? t.max : fill(t.xp, { xp: v.xp, next: v.levelTo })}>
          <span class="bar__fill" style={{ width: `${Math.min(100, Math.max(0, (into * 100) / span))}%` }} />
        </span>
        <span class="bar__word">{v.levelTo === null ? t.max : fill(t.xp, { xp: v.xp, next: v.levelTo })}</span>
      </div>
      <p class="small farmcard__pens">{fill(t.pensBuilt, { n: v.pens.capacity, max: FARM.basePens + FARM_PENS.length })}</p>
      {next ? (
        <>
          <p class="small">{fill(t.nextPen, { price: next.price.toLocaleString(), level: next.level })}</p>
          {v.pens.blocked && <p class="muted small food__tag--bad">{refusal(v.pens.blocked)}</p>}
          <button type="button" class="btn btn--primary farmcard__buy" disabled={!v.pens.canBuy} onClick={() => setAsking(true)}>
            {fill(t.buyPen, { price: gold(next.price) })}
          </button>
        </>
      ) : (
        <p class="muted small">{t.allBuilt}</p>
      )}
      <p class="field__label farmcard__perks">{t.perksTitle}</p>
      <ul class="farmcard__list">
        {v.perks.map(({ perk, unlocked }) => (
          <li key={perk.id} class={`farmcard__perk ${unlocked ? '' : 'farmcard__perk--locked'}`}>
            <span class="farmcard__mark">{unlocked ? '✓' : fill(t.locked, { n: perk.level })}</span>
            <span>
              <b>{perk.name}</b>
              <span class="muted small"> · {t.perks[perk.id]}</span>
            </span>
          </li>
        ))}
      </ul>
      <Confirm
        open={asking && next !== null}
        text={next ? fill(t.ask, { n: next.n + FARM.basePens, price: gold(next.price) }) : ''}
        confirmLabel={next ? fill(t.buyPen, { price: gold(next.price) }) : ''}
        onConfirm={confirm}
        onCancel={() => setAsking(false)}
      />
    </section>
  )
}
