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
  /** True for the breeds an unlock chain added to the stall (CONTENT §11: Gearhoot, the summer Reefclaw). */
  unlocked: boolean
}

/** The stall this month. CONTENT §11: Gearhoot once the Blueprint is handed in; the Reefclaw as the summer pick once it moved in. */
export function marketStock(month: number, unlocked: readonly BreedId[] = []): MarketOffer[] {
  const season = seasonOf(month)
  const always = BREEDS.filter((b) => b.availability === 'market' && b.marketSeason === null).map((b) => ({ breed: b.id, seasonal: false, price: MARKET.price, unlocked: false }))
  const seasonal = BREEDS.filter((b) => b.availability === 'market' && b.marketSeason === season).map((b) => ({ breed: b.id, seasonal: true, price: MARKET.seasonalPrice, unlocked: false }))
  const extra: MarketOffer[] = []
  if (unlocked.includes('gearhoot')) extra.push({ breed: 'gearhoot', seasonal: false, price: MARKET.seasonalPrice, unlocked: true })
  if (unlocked.includes('reefclaw') && season === 'Summer') extra.push({ breed: 'reefclaw', seasonal: true, price: MARKET.seasonalPrice, unlocked: true })
  return [...always, ...seasonal, ...extra]
}

/** The Market's monster of a breed: pure, zero offsets, personality from the breed's fixed seed. */
export function marketMonster(breed: BreedId, id: string): Monster {
  const rng = createRng(MARKET.seedBase + BREED_IDS.indexOf(breed))
  const likes = rollLikes(rng)
  return createMonster({ id, mainBreed: breed, likes, name: BREED_BY_ID[breed].name })
}
