import { useState } from 'preact/hooks'
import { dateOf } from '../../../core/calendar.ts'
import { foodRelation, isBoredOf, monthlyFoodEffect } from '../../../core/food.ts'
import { monthlyFoodCost } from '../../../core/herd.ts'
import { tipText } from '../../../core/onboarding.ts'
import { FOODS, FOOD_BY_ID } from '../../../data/foods.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { MONTH_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import type { FoodId } from '../../../data/types.ts'
import { Sheet } from '../../components/Controls.tsx'
import { TipCard, gold } from '../../components/RanchBits.tsx'
import { settings } from '../../store/appStore.ts'
import { dismissTip, game, pickFood, tipFor } from '../../store/gameStore.ts'

const signed = (n: number) => (n > 0 ? `+${n}` : String(n))

/**
 * §8: week 1 of each month. The choice defaults to last month's; liked and disliked foods are marked. v16: the whole
 * ranch eats the same food, so with ranch-mates the prompt says how many it feeds and the month's total.
 */
export function FoodPrompt({ open }: { open: boolean }) {
  const g = game.value
  const t = UI_TEXT.food
  const [picked, setPicked] = useState<FoodId | null>(null)
  if (!open || !g || !g.monster) return null
  const m = g.monster
  const choice = picked ?? g.foodChoice
  const mode = settings.value.transparency
  const tip = tipFor({ screen: 'food' })
  const bill = monthlyFoodCost(g, choice)
  const price = bill.total
  return (
    <Sheet open title={t.title} onClose={() => undefined}>
      <p class="muted small">{fill(t.hint, { month: MONTH_NAMES[dateOf(g.week).month - 1] })}</p>
      {tip && <TipCard text={tipText(g, tip)} onDismiss={() => dismissTip(tip)} />}
      <div class="list">
        {FOODS.map((f) => {
          const rel = foodRelation(m, f.id)
          const bored = isBoredOf(m, f.id)
          const e = monthlyFoodEffect(m, f.id)
          return (
            <button key={f.id} type="button" class={`food ${choice === f.id ? 'food--on' : ''}`} aria-pressed={choice === f.id} onClick={() => setPicked(f.id)}>
              <span class="food__body">
                <span class="item__name">{f.name}</span>
                <span class="item__meta">
                  {rel === 'liked' && <span class="food__tag">{t.liked} · </span>}
                  {rel === 'disliked' && <span class="food__tag food__tag--bad">{t.disliked} · </span>}
                  {bored && <span class="food__tag food__tag--bad">{t.bored} · </span>}
                  {mode !== 'classic' && (
                    <>
                      {fill(t.effect, { stress: signed(e.stress ?? 0), form: signed(e.form ?? 0) })}
                      {e.life ? t.effectLife : ''}
                    </>
                  )}
                </span>
              </span>
              <span class="item__price">{gold(f.price)}</span>
            </button>
          )
        })}
      </div>
      {bill.mouths > 1 && <p class="field__label">{fill(HERD_TEXT.food.feeds, { n: bill.mouths, total: bill.total.toLocaleString('en-US') })}</p>}
      {g.money < price && <p class="notice">{t.loanNote}</p>}
      <div class="sheet__actions">
        <button type="button" class="btn btn--primary" onClick={() => pickFood(choice)}>
          {fill(t.serve, { food: FOOD_BY_ID[choice].name, price })}
        </button>
      </div>
    </Sheet>
  )
}
