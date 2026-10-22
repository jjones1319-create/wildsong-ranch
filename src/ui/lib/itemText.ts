import { fill } from '../../data/text/format.ts'
import { STAT_NAMES } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import type { Item } from '../../data/types.ts'

const signed = (n: number) => (n > 0 ? `+${n}` : String(n))

/** One line that says what an item does (CONTENT §6), from its effect data. */
export function itemEffectText(item: Item): string {
  const t = UI_TEXT.shop.effects
  const e = item.effect
  switch (e.kind) {
    case 'fatigue':
      return fill(t.fatigue, { n: signed(e.amount) })
    case 'stress':
      return fill(t.stress, { n: signed(e.amount) })
    case 'stressHalve':
      return t.stressHalve
    case 'spoil':
      return fill(t.spoil, { n: signed(e.amount) })
    case 'fear':
      return fill(t.fear, { n: signed(e.amount) })
    case 'nature':
      return fill(t.nature, { n: signed(e.amount) })
    case 'form':
      return fill(t.form, { n: signed(e.amount) })
    case 'sweet':
      return e.stat === 'all' ? fill(t.sweetAll, { n: e.amount }) : fill(t.sweet, { stat: STAT_NAMES[e.stat], n: e.amount })
    case 'potentialGrade':
      return t.potentialGrade
    case 'tempoBell':
      return t.tempoBell
    case 'tonic':
      return fill(t.tonic, { stat: STAT_NAMES[e.stat] })
    case 'fruit':
      return fill(t.fruit, { n: e.weeks })
    case 'toy':
      return t.toy
    case 'charm':
      return e.slot === 'comfort' ? fill(t.charmComfort, { n: e.value }) : fill(t.charmBedding, { n: e.value })
    case 'catalyst':
      return e.lineageSeal ? t.lineageSeal : e.lifespan > 0 ? t.amber : t.catalyst
    case 'key':
      return t.key
    case 'sellable':
      return fill(t.sellable, { n: item.sell ?? 0 })
  }
}
