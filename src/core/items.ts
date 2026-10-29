import { ITEM_BY_ID } from '../data/items.ts'
import { ITEMS, LIFESPAN, RANGES } from '../data/tuning.ts'
import { STAT_KEYS, type Item, type StatKey } from '../data/types.ts'
import { clamp } from './mathx.ts'
import { addCondition, addForm, addNature, addStat, stepGrade, type Monster } from './monster.ts'

/**
 * GAME_DESIGN §8: the Bag. Unlimited quantities, unlimited use, no diminishing returns. The only limits are
 * the two life fruits (once per monster each) and the optional one-item-per-week setting passed in by the caller.
 */

/** Item id → quantity. Toys are counted in uses (one toy = 5 uses). */
export type Inventory = Record<string, number>

export function countOf(inv: Inventory, itemId: string): number {
  return inv[itemId] ?? 0
}

export function addItems(inv: Inventory, itemId: string, qty: number): Inventory {
  const next = { ...inv }
  const item = ITEM_BY_ID[itemId]
  const units = item?.category === 'toy' ? qty * ITEMS.toyUses : qty
  next[itemId] = countOf(next, itemId) + units
  return next
}

export type UseRefusal = 'unknownItem' | 'notOwned' | 'onePerWeek' | 'fruitAlreadyUsed' | 'passive' | 'notUsable' | 'needsStat' | 'alreadyMaxed'

export interface UseItemOptions {
  /** Target stat for the Potential Pearl. */
  stat?: StatKey
  /** The optional Classic rule: at most one item per week. */
  onePerWeek?: boolean
  usedThisWeek?: number
}

export interface UseItemResult {
  monster: Monster
  inventory: Inventory
  /** How many units were actually used. */
  used: number
  refused: UseRefusal | null
  /** Lifespan weeks spent (tonics) or gained (fruits), as a signed total. */
  lifespanChange: number
}

/** Use `qty` of an item. Pure: returns a new monster and inventory. */
export function useItem(input: Monster, inventory: Inventory, itemId: string, qty: number, opts: UseItemOptions = {}): UseItemResult {
  const fail = (refused: UseRefusal): UseItemResult => ({ monster: input, inventory, used: 0, refused, lifespanChange: 0 })
  const item = ITEM_BY_ID[itemId]
  if (!item) return fail('unknownItem')
  const owned = countOf(inventory, itemId)
  if (owned <= 0 || qty <= 0) return fail('notOwned')
  if (opts.onePerWeek && (opts.usedThisWeek ?? 0) >= 1) return fail('onePerWeek')
  let wanted = Math.min(qty, owned)
  if (opts.onePerWeek) wanted = 1

  const m = structuredClone(input)
  let used = 0
  let lifespanChange = 0
  const e = item.effect

  switch (e.kind) {
    case 'fatigue':
      m.fatigue = addCondition(m.fatigue, e.amount * wanted)
      used = wanted
      break
    case 'stress':
      m.stress = addCondition(m.stress, e.amount * wanted)
      used = wanted
      break
    case 'stressHalve':
      for (let i = 0; i < wanted; i++) m.stress = Math.floor(m.stress / 2)
      used = wanted
      break
    case 'spoil':
      m.spoil = addCondition(m.spoil, e.amount * wanted)
      used = wanted
      break
    case 'fear':
      m.fear = addCondition(m.fear, e.amount * wanted)
      used = wanted
      break
    case 'nature':
      m.nature = addNature(m.nature, e.amount * wanted)
      used = wanted
      break
    case 'form':
      m.form = addForm(m.form, e.amount * wanted)
      used = wanted
      break
    case 'sweet': {
      // Sweets go past the grade caps (v1.11); only the 9,999 save bound stops them, and then they aren't eaten.
      const stats = e.stat === 'all' ? STAT_KEYS : [e.stat]
      for (let i = 0; i < wanted; i++) {
        if (stats.every((k) => m.stats[k] >= RANGES.stat.max)) break
        for (const k of stats) {
          const before = m.stats[k]
          m.stats[k] = addStat(before, e.amount)
          m.records.fromSweets[k] += m.stats[k] - before
        }
        used++
      }
      if (used === 0) return fail('alreadyMaxed')
      break
    }
    case 'potentialGrade': {
      if (!opts.stat) return fail('needsStat')
      for (let i = 0; i < wanted; i++) {
        if (m.grades[opts.stat] === ITEMS.pearlMaxGrade) break
        m.grades[opts.stat] = stepGrade(m.grades[opts.stat], 1)
        used++
      }
      if (used === 0) return fail('alreadyMaxed')
      break
    }
    case 'tempoBell': {
      for (let i = 0; i < wanted; i++) {
        if (m.gutsRate <= ITEMS.tempoBellMin) break
        m.gutsRate -= 1
        used++
      }
      if (used === 0) return fail('alreadyMaxed')
      break
    }
    case 'tonic': {
      for (let i = 0; i < wanted; i++) {
        m.status.tonics[e.stat] = ITEMS.tonicWeeks
        m.lifespanTotal = clamp(m.lifespanTotal - LIFESPAN.tonicCost, RANGES.lifespan.min, RANGES.lifespan.max)
        lifespanChange -= LIFESPAN.tonicCost
      }
      used = wanted
      break
    }
    case 'fruit': {
      if (m.status[e.flag]) return fail('fruitAlreadyUsed')
      m.status[e.flag] = true
      m.lifespanTotal = clamp(m.lifespanTotal + e.weeks, RANGES.lifespan.min, RANGES.lifespan.max)
      lifespanChange += e.weeks
      used = 1
      break
    }
    case 'toy': {
      const favorite = m.likes.toy === itemId
      for (let i = 0; i < wanted; i++) {
        if (favorite) {
          m.stress = addCondition(m.stress, ITEMS.toy.favoriteStress)
          m.spoil = addCondition(m.spoil, ITEMS.toy.favoriteSpoil)
        } else {
          m.stress = addCondition(m.stress, ITEMS.toy.otherStress)
        }
      }
      used = wanted
      break
    }
    case 'charm':
      return fail('passive')
    case 'catalyst':
    case 'key':
    case 'sellable':
      return fail('notUsable')
  }

  const next = { ...inventory }
  const left = owned - used
  if (left > 0) next[itemId] = left
  else delete next[itemId]
  return { monster: m, inventory: next, used, refused: null, lifespanChange }
}

/** The best owned charm of a slot (only the best one applies, §8). */
export function bestCharm(inv: Inventory, slot: 'comfort' | 'bedding'): Item | null {
  let best: Item | null = null
  for (const id of Object.keys(inv)) {
    if (countOf(inv, id) <= 0) continue
    const item = ITEM_BY_ID[id]
    if (!item || item.effect.kind !== 'charm' || item.effect.slot !== slot) continue
    if (!best || (best.effect.kind === 'charm' && item.effect.tier > best.effect.tier)) best = item
  }
  return best
}

export function charmValue(inv: Inventory, slot: 'comfort' | 'bedding'): number {
  const c = bestCharm(inv, slot)
  return c && c.effect.kind === 'charm' ? c.effect.value : 0
}
