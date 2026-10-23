import { ITEM_BY_ID, ITEMS } from '../data/items.ts'
import { ECONOMY, SHOP } from '../data/tuning.ts'
import { TOURNAMENT_GRADES, type Item, type ItemCategory } from '../data/types.ts'
import { addItems } from './items.ts'
import type { GameState } from './state.ts'

/**
 * GAME_DESIGN §9: money is the only limit on items. Shop stock never runs out; prices are content.
 * The Guild Loan covers fees and food that money can't: the shortfall costs a 10% fee, and while in
 * debt only food and Recovery items can be bought. Everything here is pure.
 */

/** Pays `amount`. A shortfall is borrowed from the Guild with its fee (§9). */
export function charge(money: number, amount: number): number {
  if (amount <= 0) return money
  const after = money - amount
  if (after >= 0) return after
  const borrowed = money > 0 ? -after : amount
  const fee = Math.ceil((borrowed * ECONOMY.loanFeePct) / 100)
  return after - fee
}

export function inDebt(state: GameState): boolean {
  return state.money < 0
}

export type StockRefusal = 'notSold' | 'rank' | 'gradeC'
export type BuyRefusal = 'unknownItem' | StockRefusal | 'debt' | 'money' | 'quantity'

/** The highest tournament grade this save has seen (the active monster's current or best). */
function bestGradeIndex(state: GameState): number {
  const m = state.monster
  if (!m) return 0
  return Math.max(TOURNAMENT_GRADES.indexOf(m.grade), TOURNAMENT_GRADES.indexOf(m.records.highestGrade))
}

/** Is this item on the shelf at all (price and gates), regardless of money? */
export function stockStatus(state: GameState, item: Item): { ok: true } | { ok: false; reason: StockRefusal } {
  if (item.price === null) return { ok: false, reason: 'notSold' }
  if (item.gate?.rank !== undefined && state.breeder.rank < item.gate.rank) return { ok: false, reason: 'rank' }
  if (item.gate?.needsGradeC && bestGradeIndex(state) < TOURNAMENT_GRADES.indexOf('C')) return { ok: false, reason: 'gradeC' }
  return { ok: true }
}

/** §9: while in debt only food (bought monthly) and Recovery items can be bought. */
export function categoryAllowedInDebt(category: ItemCategory): boolean {
  return category === 'recovery'
}

export function canBuy(state: GameState, itemId: string, qty: number): { ok: true; cost: number } | { ok: false; reason: BuyRefusal } {
  const item = ITEM_BY_ID[itemId]
  if (!item) return { ok: false, reason: 'unknownItem' }
  const stock = stockStatus(state, item)
  if (!stock.ok) return stock
  if (!Number.isInteger(qty) || qty < 1 || qty > SHOP.maxPerPurchase) return { ok: false, reason: 'quantity' }
  if (inDebt(state) && !categoryAllowedInDebt(item.category)) return { ok: false, reason: 'debt' }
  const cost = item.price! * qty
  if (state.money < cost) return { ok: false, reason: 'money' }
  return { ok: true, cost }
}

/** How many of an item the player could buy right now (0 when it is gated or unaffordable). */
export function maxAffordable(state: GameState, itemId: string): number {
  const item = ITEM_BY_ID[itemId]
  if (!item || !stockStatus(state, item).ok || item.price === null) return 0
  if (inDebt(state) && !categoryAllowedInDebt(item.category)) return 0
  if (state.money <= 0) return 0
  return Math.min(SHOP.maxPerPurchase, Math.floor(state.money / item.price))
}

export interface BuyResult {
  state: GameState
  cost: number
  refused: BuyRefusal | null
}

/** Buys `qty` of an item. Pure: returns a new state, or the same state with a refusal. */
export function buyItem(input: GameState, itemId: string, qty: number): BuyResult {
  const check = canBuy(input, itemId, qty)
  if (!check.ok) return { state: input, cost: 0, refused: check.reason }
  const state = structuredClone(input)
  state.money -= check.cost
  state.inventory = addItems(state.inventory, itemId, qty)
  return { state, cost: check.cost, refused: null }
}

export interface ShopEntry {
  item: Item
  /** Why it can't be bought right now, if it can't. */
  blocked: StockRefusal | 'debt' | null
  owned: number
}

/** Every item with a price, with its gate status, for the Shop screen. */
export function shopStock(state: GameState): ShopEntry[] {
  const out: ShopEntry[] = []
  for (const item of ITEMS) {
    if (item.price === null) continue
    const stock = stockStatus(state, item)
    const blocked: ShopEntry['blocked'] = !stock.ok ? stock.reason : inDebt(state) && !categoryAllowedInDebt(item.category) ? 'debt' : null
    out.push({ item, blocked, owned: state.inventory[item.id] ?? 0 })
  }
  return out
}

export type SellRefusal = 'unknownItem' | 'notSellable' | 'notOwned' | 'quantity'

/** Expedition treasures (CONTENT §6 sellables) sold to Basil at their listed value. Pure. */
export function sellItem(input: GameState, itemId: string, qty: number): { state: GameState; gold: number; refused: SellRefusal | null } {
  const item = ITEM_BY_ID[itemId]
  if (!item) return { state: input, gold: 0, refused: 'unknownItem' }
  if (item.sell === null) return { state: input, gold: 0, refused: 'notSellable' }
  const owned = input.inventory[itemId] ?? 0
  if (owned <= 0) return { state: input, gold: 0, refused: 'notOwned' }
  if (!Number.isInteger(qty) || qty < 1) return { state: input, gold: 0, refused: 'quantity' }
  const n = Math.min(qty, owned)
  const state = structuredClone(input)
  const gold = item.sell * n
  state.money += gold
  if (owned - n > 0) state.inventory[itemId] = owned - n
  else delete state.inventory[itemId]
  return { state, gold, refused: null }
}

/** What the Bag holds that Basil buys. */
export function sellableStock(state: GameState): { item: Item; owned: number }[] {
  return ITEMS.filter((i) => i.sell !== null && (state.inventory[i.id] ?? 0) > 0).map((item) => ({ item, owned: state.inventory[item.id]! }))
}

/** The categories the Shop sells, in counter order (Basil's bakery counter is the Stat Sweets). */
export const SHOP_CATEGORIES: readonly ItemCategory[] = ['sweet', 'recovery', 'mood', 'form', 'toy', 'charm', 'tonic', 'potential', 'catalyst']
