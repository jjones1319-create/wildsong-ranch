import { useEffect, useState } from 'preact/hooks'
import { countOf, type UseRefusal } from '../../../core/items.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { fill } from '../../../data/text/format.ts'
import { ITEM_CATEGORY_LABELS, STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { ITEMS as ITEM_RULES, LIFESPAN } from '../../../data/tuning.ts'
import { ITEM_CATEGORIES, STAT_KEYS, type Grade, type Item, type StatKey } from '../../../data/types.ts'
import { stepGrade } from '../../../core/monster.ts'
import { Select, TopBar } from '../../components/Controls.tsx'
import { QuantitySheet } from '../../components/RanchBits.tsx'
import { itemEffectText } from '../../lib/itemText.ts'
import { navigate } from '../../router.ts'
import { showToast } from '../../store/appStore.ts'
import { playSfx } from '../../../audio/player.ts'
import { game, useItems } from '../../store/gameStore.ts'

const USABLE = new Set(['recovery', 'mood', 'form', 'sweet', 'potential', 'tonic', 'fruit', 'toy'])

function refusalText(r: UseRefusal, name: string): string {
  const t = UI_TEXT.bag
  switch (r) {
    case 'onePerWeek':
      return t.onePerWeek
    case 'fruitAlreadyUsed':
      return fill(t.fruitUsed, { name })
    case 'alreadyMaxed':
      return t.maxed
    case 'needsStat':
      return t.needsStat
    case 'passive':
      return t.passive
    default:
      return fill(t.notUsable, { name })
  }
}

/** §8 the Bag: every owned item by category, Use ×1 / ×5 / ×10 / Max, with the Pearl's stat picker and warnings. */
export function BagScreen() {
  const g = game.value
  const t = UI_TEXT.bag
  const [using, setUsing] = useState<Item | null>(null)
  const [stat, setStat] = useState<StatKey>('POW')
  useEffect(() => {
    if (!g || !g.monster) navigate('ranch')
  }, [g === null])
  if (!g || !g.monster) return null
  const m = g.monster
  const owned = Object.keys(g.inventory)
    .filter((id) => countOf(g.inventory, id) > 0 && ITEM_BY_ID[id])
    .map((id) => ITEM_BY_ID[id]!)
  const groups = ITEM_CATEGORIES.map((c) => ({ c, items: owned.filter((i) => i.category === c) })).filter((grp) => grp.items.length > 0)

  const confirm = (n: number) => {
    if (!using) return
    const r = useItems(using.id, n, using.effect.kind === 'potentialGrade' ? stat : undefined)
    setUsing(null)
    if (r.used === 0) {
      showToast(r.result?.refused ? refusalText(r.result.refused, m.name) : t.notNow)
      return
    }
    const parts = [fill(t.used, { name: m.name, n: r.used, item: using.name })]
    // Sound 2.0 §7.6: a kalimba lift for a Stat Sweet, a harp-and-glock arpeggio for anything else.
    playSfx(using.category === 'sweet' ? 'sweet' : 'itemGet')
    if (using.category === 'sweet') parts.push(fill(WREN.ateSweet, { name: m.name }))
    const life = r.result?.lifespanChange ?? 0
    if (life < 0) parts.push(fill(t.lifespanDown, { n: -life }))
    if (life > 0) parts.push(fill(t.lifespanUp, { n: life }))
    showToast(parts.join(' '))
  }

  const maxFor = (item: Item) => {
    const have = countOf(g.inventory, item.id)
    if (g.settings.onePerWeek || item.category === 'fruit') return Math.min(1, have)
    return have
  }

  return (
    <main class="screen">
      <TopBar title={t.title} />
      {groups.length === 0 && <p class="empty">{t.empty}</p>}
      {groups.map(({ c, items }) => (
        <section class="card" key={c}>
          <p class="field__label">{ITEM_CATEGORY_LABELS[c]}</p>
          {items.map((item) => {
            const n = countOf(g.inventory, item.id)
            const usable = USABLE.has(item.category)
            return (
              <div class="item" key={item.id}>
                <span class="item__body">
                  <span class="item__name">
                    {item.name} <span class="muted">{item.category === 'toy' ? fill(t.uses, { n }) : fill(t.owned, { n })}</span>
                  </span>
                  <span class="item__meta">{usable ? itemEffectText(item) : item.category === 'charm' ? `${itemEffectText(item)} · ${t.passive}` : itemEffectText(item)}</span>
                </span>
                {usable && (
                  <button type="button" class="btn btn--small btn--primary" onClick={() => setUsing(item)}>
                    {UI_TEXT.card.useItem}
                  </button>
                )}
              </div>
            )
          })}
        </section>
      ))}
      <div class="spacer" />
      <QuantitySheet
        open={using !== null}
        title={using?.name ?? ''}
        hint={using ? itemEffectText(using) : undefined}
        max={using ? maxFor(using) : 0}
        confirmLabel={(n) => fill(t.use, { n })}
        onConfirm={confirm}
        onClose={() => setUsing(null)}
      >
        {using?.effect.kind === 'tonic' && <p class="notice">{fill(t.tonicWarn, { n: LIFESPAN.tonicCost })}</p>}
        {using?.effect.kind === 'fruit' && <p class="notice notice--ok">{fill(t.fruitWarn, { n: using.effect.weeks })}</p>}
        {using?.effect.kind === 'potentialGrade' && (
          <Select label={t.pearlStat} value={stat} options={STAT_KEYS.map((k) => ({ value: k, label: `${k} · ${STAT_NAMES[k]} (${m.grades[k]}${m.grades[k] === ITEM_RULES.pearlMaxGrade ? '' : ' → ' + nextGrade(m.grades[k])})` }))} onChange={setStat} />
        )}
      </QuantitySheet>
    </main>
  )
}

function nextGrade(g: Grade): Grade {
  return stepGrade(g, 1)
}
