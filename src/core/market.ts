import { BREEDS, BREED_BY_ID } from '../data/breeds.ts'
import { MARKET } from '../data/tuning.ts'
import { BREED_IDS, type BreedId } from '../data/types.ts'
import { seasonOf } from './calendar.ts'
import { createMonster, rollLikes, type Monster } from './monster.ts'
import { createRng } from './rng.ts'

/**
 * GAME_DESIGN §14.2: the Market. Four starters are always in stock plus one seasonal breed. Market monsters
 * use fixed seeds and zero offsets, so every player's gift is the same monster. The first one is free;
 * buying later ones (to the Freezer) arrives with M6.
 */

export interface MarketOffer {
  breed: BreedId
  seasonal: boolean
  price: number
}

export function marketStock(month: number): MarketOffer[] {
  const season = seasonOf(month)
  const always = BREEDS.filter((b) => b.availability === 'market' && b.marketSeason === null).map((b) => ({ breed: b.id, seasonal: false, price: MARKET.price }))
  const seasonal = BREEDS.filter((b) => b.availability === 'market' && b.marketSeason === season).map((b) => ({ breed: b.id, seasonal: true, price: MARKET.seasonalPrice }))
  return [...always, ...seasonal]
}

/** The Market's monster of a breed: pure, zero offsets, personality from the breed's fixed seed. */
export function marketMonster(breed: BreedId, id: string): Monster {
  const rng = createRng(MARKET.seedBase + BREED_IDS.indexOf(breed))
  const likes = rollLikes(rng)
  return createMonster({ id, mainBreed: breed, subBreed: breed, likes, name: BREED_BY_ID[breed].name })
}
