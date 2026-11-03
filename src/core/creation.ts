import { HERD, SHRINE } from '../data/tuning.ts'
import type { BreedId } from '../data/types.ts'
import { penRoom } from './farm.ts'
import { normalizePhrase } from './hash.ts'
import { freezerFull, placeOnRanch, ranchBusy, recordInEncyclopedia } from './legacy.ts'
import { marketMonster, marketStock } from './market.ts'
import type { Monster } from './monster.ts'
import { monsterFromRoll, rollShrine, type ShrineRoll } from './shrine.ts'
import type { GameState, Ranchmate } from './state.ts'
import { dateOf } from './calendar.ts'

/**
 * Where new monsters come from during a game (§14): the Shrine (free; Sleeping Stones when the breed is
 * asleep; the Encyclopedia's paid re-creation) and the Market. A newborn lives on the ranch when it is empty,
 * otherwise in a free pen (v16), otherwise in the Freezer. Pure.
 */

export type Placed = 'ranch' | 'pen' | 'freezer'

export type PlaceRefusal = 'freezerFull' | 'busy'

export type Home = { placed: Placed; refused: null } | { placed: null; refused: PlaceRefusal }

/** A ranch-mate fresh in its pen: the default order, no last week, no edit history. */
export function newRanchmate(m: Monster): Ranchmate {
  return { monster: m, order: { kind: HERD.defaultOrder }, last: null, history: [] }
}

/** Where a new monster would go now: an empty ranch, then a free pen, then the Freezer. */
export function nextHome(state: GameState): Home {
  if (state.monster === null && !state.ended) return ranchBusy(state) ? { placed: null, refused: 'busy' } : { placed: 'ranch', refused: null }
  if (penRoom(state) > 0) return { placed: 'pen', refused: null }
  if (!freezerFull(state)) return { placed: 'freezer', refused: null }
  return { placed: null, refused: 'freezerFull' }
}

/** Places a new monster in `state` itself (the caller owns the copy) and records it in the Encyclopedia. */
export function placeMut(state: GameState, m: Monster): Home {
  const home = nextHome(state)
  if (home.placed === 'ranch') placeOnRanch(state, m)
  else if (home.placed === 'pen') {
    state.ranchmates.push(newRanchmate(m))
    recordInEncyclopedia(state, m)
  } else if (home.placed === 'freezer') {
    state.freezer.push(m)
    recordInEncyclopedia(state, m)
  }
  return home
}

/** Puts a newborn on the ranch, in a pen or in the Freezer. */
export function placeNewMonster(input: GameState, m: Monster): { state: GameState; placed: Placed | null; refused: PlaceRefusal | null } {
  const home = nextHome(input)
  if (!home.placed) return { state: input, placed: null, refused: home.refused }
  const state = structuredClone(input)
  placeMut(state, m)
  return { state, placed: home.placed, refused: null }
}

export type AwakenResult =
  | { kind: 'born'; state: GameState; monster: Monster; placed: Placed; roll: ShrineRoll }
  | { kind: 'sleeping'; state: GameState; roll: ShrineRoll; alreadyKept: boolean }
  | { kind: 'refused'; state: GameState; reason: PlaceRefusal; roll: ShrineRoll }

/** Sings to the stone. Free. A sleeping breed keeps the phrase among the Sleeping Stones instead. */
export function awaken(input: GameState, phrase: string, artist: string, id: string): AwakenResult {
  const roll = rollShrine(phrase, artist, input.unlocked)
  if (roll.mainLocked) {
    const alreadyKept = input.sleepingStones.some((s) => s.phrase === roll.seed.phrase && s.artist === roll.seed.artist)
    if (alreadyKept) return { kind: 'sleeping', state: input, roll, alreadyKept }
    const state = structuredClone(input)
    state.sleepingStones.push({ phrase: roll.seed.phrase, artist: roll.seed.artist, breed: roll.mainBreed, week: state.week })
    return { kind: 'sleeping', state, roll, alreadyKept: false }
  }
  const monster = monsterFromRoll(roll, id)
  const placed = placeNewMonster(input, monster)
  if (!placed.placed) return { kind: 'refused', state: input, reason: placed.refused!, roll }
  const state = placed.state
  if (!state.encyclopedia.phrases.some((p) => p.phrase === roll.seed.phrase && p.artist === roll.seed.artist)) {
    state.encyclopedia.phrases.push({ phrase: roll.seed.phrase, artist: roll.seed.artist, name: monster.name, mainBreed: monster.mainBreed, variantId: monster.variantId })
  }
  return { kind: 'born', state, monster, placed: placed.placed, roll }
}

export type RecreateRefusal = 'notFound' | 'money' | PlaceRefusal

/** The Encyclopedia: any monster born at the Shrine can be sung back for SHRINE.encyclopediaPrice. */
export function recreate(input: GameState, index: number, id: string): { state: GameState; monster: Monster | null; placed: Placed | null; refused: RecreateRefusal | null } {
  const entry = input.encyclopedia.phrases[index]
  if (!entry) return { state: input, monster: null, placed: null, refused: 'notFound' }
  if (input.money < SHRINE.encyclopediaPrice) return { state: input, monster: null, placed: null, refused: 'money' }
  const roll = rollShrine(entry.phrase, entry.artist, input.unlocked)
  const monster = monsterFromRoll(roll, id)
  const placed = placeNewMonster(input, monster)
  if (!placed.placed) return { state: input, monster: null, placed: null, refused: placed.refused }
  placed.state.money -= SHRINE.encyclopediaPrice
  return { state: placed.state, monster, placed: placed.placed, refused: null }
}

export type WakeRefusal = 'notFound' | 'asleep' | PlaceRefusal

/** A Sleeping Stone wakes for free once its breed is unlocked. */
export function wakeStone(input: GameState, index: number, id: string): { state: GameState; monster: Monster | null; placed: Placed | null; refused: WakeRefusal | null } {
  const stone = input.sleepingStones[index]
  if (!stone) return { state: input, monster: null, placed: null, refused: 'notFound' }
  if (!input.unlocked.includes(stone.breed)) return { state: input, monster: null, placed: null, refused: 'asleep' }
  const roll = rollShrine(stone.phrase, stone.artist, input.unlocked)
  const monster = monsterFromRoll(roll, id)
  const placed = placeNewMonster(input, monster)
  if (!placed.placed) return { state: input, monster: null, placed: null, refused: placed.refused }
  const state = placed.state
  state.sleepingStones.splice(index, 1)
  state.records.stonesWoken += 1
  if (!state.encyclopedia.phrases.some((p) => p.phrase === stone.phrase && p.artist === stone.artist)) {
    state.encyclopedia.phrases.push({ phrase: stone.phrase, artist: stone.artist, name: monster.name, mainBreed: monster.mainBreed, variantId: monster.variantId })
  }
  return { state, monster, placed: placed.placed, refused: null }
}

export type BuyRefusal = 'notStocked' | 'money' | PlaceRefusal

/** The Market after the first monster: 1,500G, or 2,500G for the season's breed (§14.2). */
export function buyFromMarket(input: GameState, breed: BreedId, id: string): { state: GameState; monster: Monster | null; placed: Placed | null; price: number; refused: BuyRefusal | null } {
  const offer = marketStock(dateOf(input.week).month, input.unlocked).find((o) => o.breed === breed)
  if (!offer) return { state: input, monster: null, placed: null, price: 0, refused: 'notStocked' }
  if (input.money < offer.price) return { state: input, monster: null, placed: null, price: offer.price, refused: 'money' }
  const monster = marketMonster(breed, id)
  const placed = placeNewMonster(input, monster)
  if (!placed.placed) return { state: input, monster: null, placed: null, price: offer.price, refused: placed.refused }
  placed.state.money -= offer.price
  return { state: placed.state, monster, placed: placed.placed, price: offer.price, refused: null }
}

/** For the UI's "is this phrase already kept" hints. */
export function isKeptStone(state: GameState, phrase: string, artist: string): boolean {
  const p = normalizePhrase(phrase)
  const a = normalizePhrase(artist)
  return state.sleepingStones.some((s) => s.phrase === p && s.artist === a)
}
