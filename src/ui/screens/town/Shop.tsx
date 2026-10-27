import { useEffect, useState } from 'preact/hooks'
import { inDebt, maxAffordable, sellableStock, SHOP_CATEGORIES, shopStock, type ShopEntry } from '../../../core/economy.ts'
import { foodRelation } from '../../../core/food.ts'
import { FOODS, FOOD_BY_ID } from '../../../data/foods.ts'
import { fill } from '../../../data/text/format.ts'
import { ITEM_CATEGORY_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import type { Item, ItemCategory } from '../../../data/types.ts'
import { Chips, TopBar } from '../../components/Controls.tsx'
import { QuantitySheet, SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { itemEffectText } from '../../lib/itemText.ts'
import { navigate } from '../../router.ts'
import { playSfx } from '../../../audio/player.ts'
import { showToast } from '../../store/appStore.ts'
import { buy, game, sell } from '../../store/gameStore.ts'

type Tab = ItemCategory | 'food' | 'sell'

/** §8 Basil's Shop: food for reference, care items, the Stat Sweets bakery counter, charms, toys, tonics; multi-buy. */
export function ShopScreen() {
  const g = game.value
  const t = UI_TEXT.shop
  const [tab, setTab] = useState<Tab>('sweet')
  const [buying, setBuying] = useState<ShopEntry | null>(null)
  const [selling, setSelling] = useState<{ item: Item; owned: number } | null>(null)
  useEffect(() => {
    if (!g) navigate('title')
  }, [g === null])
  if (!g) return null
  const stock = shopStock(g)
  const treasures = sellableStock(g)
  const tabs: { value: Tab; label: string }[] = [
    ...SHOP_CATEGORIES.filter((c) => stock.some((e) => e.item.category === c)).map((c) => ({ value: c as Tab, label: ITEM_CATEGORY_LABELS[c] })),
    { value: 'food', label: t.food },
    { value: 'sell', label: treasures.length ? `${UI_TEXT.sell.tab} (${treasures.length})` : UI_TEXT.sell.tab },
  ]
  const entries = stock.filter((e) => e.item.category === tab)
  const lastRumor = g.unlocks.rumorsHeard[g.unlocks.rumorsHeard.length - 1]
  const rumorLine = lastRumor ? fill(UI_TEXT.basilRumor, { rumor: UI_TEXT.rumors[lastRumor].heard }) : null

  const confirmSell = (n: number) => {
    if (!selling) return
    const r = sell(selling.item.id, n)
    setSelling(null)
    if (r.refused) showToast(UI_TEXT.sell.nothing)
    else {
      showToast(fill(UI_TEXT.sell.sold, { n, item: selling.item.name, gold: gold(r.gold) }))
      playSfx('buy')
    }
  }

  const gateText = (e: ShopEntry) => {
    if (e.blocked === 'rank') return fill(t.gates.rank, { n: e.item.gate?.rank ?? 0 })
    if (e.blocked === 'gradeC') return t.gates.gradeC
    if (e.blocked === 'debt') return t.gates.debt
    if (e.blocked === 'notSold') return t.gates.notSold
    if (g.money < (e.item.price ?? 0)) return t.gates.money
    return null
  }

  const confirm = (n: number) => {
    if (!buying) return
    const r = buy(buying.item.id, n)
    setBuying(null)
    if (r.refused) showToast(r.refused === 'money' ? t.gates.money : r.refused === 'debt' ? t.gates.debt : t.gates.notSold)
    else {
      showToast(fill(t.bought, { n, item: buying.item.name }))
      playSfx('buy')
    }
  }

  return (
    <main class="screen">
      <TopBar title={t.title} right={<span class="calstrip__money">{gold(g.money)}</span>} />
      <SpeakerCard speaker={UI_TEXT.basil} tone="muted">
        <p>{t.hello}</p>
        {rumorLine && <p class="muted small">{rumorLine}</p>}
      </SpeakerCard>
      {inDebt(g) && <p class="notice">{fill(t.debtNotice, { n: (-g.money).toLocaleString() })}</p>}
      <Chips options={tabs} value={tab} onChange={setTab} label={t.title} />

      {tab === 'sell' ? (
        <section class="card">
          {treasures.length === 0 && <p class="muted">{UI_TEXT.sell.nothing}</p>}
          {treasures.map((e) => (
            <div class="item" key={e.item.id}>
              <span class="item__body">
                <span class="item__name">
                  {e.item.name} <span class="muted small">{fill(t.owned, { n: e.owned })}</span>
                </span>
                <span class="item__meta">{fill(UI_TEXT.sell.sellsFor, { n: gold(e.item.sell ?? 0) })}</span>
              </span>
              <button type="button" class="btn btn--small btn--primary" onClick={() => setSelling(e)}>
                {UI_TEXT.sell.sell}
              </button>
            </div>
          ))}
        </section>
      ) : tab === 'food' ? (
        <section class="card">
          {g.monster && <p class="muted small">{fill(t.foodNote, { name: g.monster.name, food: FOOD_BY_ID[g.foodChoice].name })}</p>}
          {FOODS.map((f) => {
            const rel = g.monster ? foodRelation(g.monster, f.id) : 'neutral'
            return (
              <div class="item" key={f.id}>
                <span class="item__body">
                  <span class="item__name">
                    {f.name} {rel === 'liked' && <span class="food__tag">{UI_TEXT.food.liked}</span>}
                    {rel === 'disliked' && <span class="food__tag food__tag--bad">{UI_TEXT.food.disliked}</span>}
                  </span>
                </span>
                <span class="item__price">{gold(f.price)}</span>
              </div>
            )
          })}
        </section>
      ) : (
        <section class="card">
          {entries.length === 0 && <p class="muted">{UI_TEXT.library.nothing}</p>}
          {entries.map((e) => {
            const gate = gateText(e)
            const off = e.blocked !== null
            return (
              <div class={`item ${off ? 'item--off' : ''}`} key={e.item.id}>
                <span class="item__body">
                  <span class="item__name">
                    {e.item.name} {e.owned > 0 && <span class="muted small">{fill(t.owned, { n: e.owned })}</span>}
                  </span>
                  <span class="item__meta">{itemEffectText(e.item)}</span>
                  {gate && <span class="item__meta food__tag--bad">{gate}</span>}
                </span>
                <span class="item__price">{gold(e.item.price ?? 0)}</span>
                <button type="button" class="btn btn--small btn--primary" disabled={off || maxAffordable(g, e.item.id) < 1} onClick={() => setBuying(e)}>
                  {t.buy}
                </button>
              </div>
            )
          })}
        </section>
      )}
      <div class="spacer" />
      <QuantitySheet
        open={buying !== null}
        title={buying?.item.name ?? ''}
        hint={buying ? `${itemEffectText(buying.item)} · ${gold(buying.item.price ?? 0)}` : undefined}
        max={buying ? maxAffordable(g, buying.item.id) : 0}
        confirmLabel={(n) => `${t.buy} ×${n}`}
        totalFor={(n) => fill(t.total, { n: ((buying?.item.price ?? 0) * n).toLocaleString() })}
        onConfirm={confirm}
        onClose={() => setBuying(null)}
      />
      <QuantitySheet
        open={selling !== null}
        title={selling?.item.name ?? ''}
        hint={selling ? fill(UI_TEXT.sell.sellsFor, { n: gold(selling.item.sell ?? 0) }) : undefined}
        max={selling?.owned ?? 0}
        confirmLabel={(n) => `${UI_TEXT.sell.sell} ×${n}`}
        totalFor={(n) => fill(UI_TEXT.sell.total, { n: ((selling?.item.sell ?? 0) * n).toLocaleString() })}
        onConfirm={confirmSell}
        onClose={() => setSelling(null)}
      />
    </main>
  )
}
