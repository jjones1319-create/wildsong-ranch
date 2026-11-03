import { DRILL_BY_ID } from '../data/drills.ts'
import { fill } from '../data/text/format.ts'
import { HERD_TEXT } from '../data/text/herd.ts'
import { HERD } from '../data/tuning.ts'
import { newRanchmate } from './creation.ts'
import { penRoom } from './farm.ts'
import { finishEdit, pushHistory } from './lab.ts'
import { freezerFull, placeOnRanch, pruneFriendshipsMut, ranchBusy } from './legacy.ts'
import type { Monster } from './monster.ts'
import type { GameState, MateOrder, WeekAction } from './state.ts'

/**
 * GAME_DESIGN §6.11 moving the herd around (v16): picking the star, setting orders, the pens ↔ the Freezer,
 * setting a monster free, and saving a ranch-mate from the Lab editor. Pure: each returns a new state, or the
 * input untouched with the reason it was refused. (Re-exported from herd.ts.)
 */

export type StarRefusal = 'notFound' | 'ended' | 'busy' | 'cocoon'

/** The order a star takes into the pen: last week's drill or rest goes on; anything else is the default. */
function orderFrom(last: WeekAction | null): MateOrder {
  if (last?.kind === 'drill') return { kind: 'drill', drill: last.drill }
  if (last?.kind === 'rest') return { kind: 'rest' }
  return { kind: HERD.defaultOrder }
}

/**
 * ⭐ Make star: the ranch-mate and the star swap places, each with its edit history. The pending request and event
 * and "last week" belong to the old star and are cleared; the week's phase stays. With no star (after a Farewell,
 * or "Later"), the ranch-mate simply steps onto the ranch. Refused while a life has ended, the ranch is busy (a cup,
 * a Journey, a Trial or an expedition) or a cocoon hangs in the barn.
 */
export function makeStar(input: GameState, id: string): { state: GameState; refused: StarRefusal | null } {
  const i = input.ranchmates.findIndex((r) => r.monster.id === id)
  if (i < 0) return { state: input, refused: 'notFound' }
  if (input.ended) return { state: input, refused: 'ended' }
  if (ranchBusy(input)) return { state: input, refused: 'busy' }
  if (input.unlocks.cocoonInto !== null || (input.monster?.status.cocoonWeeks ?? 0) > 0) return { state: input, refused: 'cocoon' }
  const state = structuredClone(input)
  const mate = state.ranchmates[i]!
  const old = state.monster
  if (!old) {
    state.ranchmates.splice(i, 1)
    placeOnRanch(state, mate.monster)
    state.monsterHistory = mate.history
    return { state, refused: null }
  }
  state.ranchmates[i] = { monster: old, order: orderFrom(state.lastAction), last: null, history: state.monsterHistory }
  state.monster = mate.monster
  state.monsterHistory = mate.history
  state.pendingRequest = null
  state.pendingEvent = null
  state.lastAction = null
  return { state, refused: null }
}

export type OrderRefusal = 'notFound' | 'unknownDrill'

/** A ranch-mate's standing order. A Training Yard drill may be set without the Yard; the ranch-mate rests instead. */
export function setOrder(input: GameState, id: string, order: MateOrder): { state: GameState; refused: OrderRefusal | null } {
  const i = input.ranchmates.findIndex((r) => r.monster.id === id)
  if (i < 0) return { state: input, refused: 'notFound' }
  if (order.kind === 'drill' && !DRILL_BY_ID[order.drill]) return { state: input, refused: 'unknownDrill' }
  const state = structuredClone(input)
  state.ranchmates[i]!.order = order.kind === 'drill' ? { kind: 'drill', drill: order.drill } : { kind: order.kind }
  return { state, refused: null }
}

export type MoveRefusal = 'notFound' | 'full'

/** ❄️ To the Freezer: time stops for it (its pen edit history stays behind, as when the star is frozen). */
export function penToFreezer(input: GameState, id: string): { state: GameState; refused: MoveRefusal | null } {
  const i = input.ranchmates.findIndex((r) => r.monster.id === id)
  if (i < 0) return { state: input, refused: 'notFound' }
  if (freezerFull(input)) return { state: input, refused: 'full' }
  const state = structuredClone(input)
  const [mate] = state.ranchmates.splice(i, 1)
  state.freezer.push(mate!.monster)
  return { state, refused: null }
}

/** Move to a pen: a frozen monster (not an Elder) takes a free pen on the default order. */
export function freezerToPen(input: GameState, id: string): { state: GameState; refused: MoveRefusal | null } {
  const i = input.freezer.findIndex((m) => m.id === id)
  if (i < 0) return { state: input, refused: 'notFound' }
  if (penRoom(input) === 0) return { state: input, refused: 'full' }
  const state = structuredClone(input)
  const [m] = state.freezer.splice(i, 1)
  state.ranchmates.push(newRanchmate(m!))
  return { state, refused: null }
}

export type FreeRefusal = 'star' | 'notFound'

/**
 * 🕊️ Set free: a ranch-mate or a frozen monster leaves for good. Its name goes on the Memorial wall ("Set free",
 * with an epitaph that can be edited later); there is no Heartstone, and its friendships end. The star must be
 * swapped first. (Keeping a copy in the Library is the UI's, before it calls this.)
 */
export function freeMonster(input: GameState, id: string): { state: GameState; refused: FreeRefusal | null } {
  if (input.monster?.id === id) return { state: input, refused: 'star' }
  const p = input.ranchmates.findIndex((r) => r.monster.id === id)
  const f = p < 0 ? input.freezer.findIndex((m) => m.id === id) : -1
  if (p < 0 && f < 0) return { state: input, refused: 'notFound' }
  const state = structuredClone(input)
  const m: Monster = p >= 0 ? state.ranchmates.splice(p, 1)[0]!.monster : state.freezer.splice(f, 1)[0]!
  state.memorial.unshift({ monster: m, cause: 'freed', epitaph: fill(HERD_TEXT.free.epitaph, { name: m.name }).slice(0, 80), week: state.week })
  pruneFriendshipsMut(state)
  return { state, refused: null }
}

/**
 * §19: the Lab editor saved a ranch-mate (✏️ Edit from its sheet or Card). The version it replaced joins its edit
 * history and the edited flag follows the usual rule, exactly as for the star (`replaceActiveMonster`).
 */
export function replaceRanchmate(input: GameState, edited: Monster, savedAt: number): GameState {
  const i = input.ranchmates.findIndex((r) => r.monster.id === edited.id)
  if (i < 0) return input
  const state = structuredClone(input)
  const mate = state.ranchmates[i]!
  const before = mate.monster
  const finished = finishEdit(before, edited)
  finished.id = before.id
  mate.history = pushHistory(mate.history, before, savedAt)
  mate.monster = finished
  return state
}
