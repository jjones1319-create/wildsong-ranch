import { BREEDS, BREED_BY_ID } from '../data/breeds.ts'
import { BIRTH, RANGES } from '../data/tuning.ts'
import { STAT_KEYS, type BreedId } from '../data/types.ts'
import { phraseSeed, type PhraseSeed } from './hash.ts'
import { createMonster, mixBreeds, rollLikes, zeroStats, type BirthOffsets, type Likes, type Monster } from './monster.ts'
import { createRng } from './rng.ts'

/**
 * GAME_DESIGN §14.1: the Shrine of Echoes turns a phrase into a monster. The order of the rolls is
 * part of the contract (changing it changes every monster ever made), so it is spelled out step by
 * step here and pinned by a snapshot test. Secret phrases, teasers and Sleeping Stones come in M6.
 */

export interface ShrineRoll {
  seed: PhraseSeed
  mainBreed: BreedId
  /** True when the main breed is not unlocked: in the game no monster is made (the stone hums). The Lab ignores this. */
  mainLocked: boolean
  subBreed: BreedId
  offsets: BirthOffsets
  likes: Likes
  suggestedName: string
  variantName: string
}

/** The name the Shrine suggests: the first word of the phrase, or the variant name. */
export function suggestName(normalizedPhrase: string, variantName: string): string {
  const first = normalizedPhrase.split(' ').find((w) => w.length > 0) ?? ''
  const name = first ? first.charAt(0).toUpperCase() + first.slice(1) : variantName
  return name.slice(0, RANGES.nameLength.max)
}

export function rollShrine(phrase: string, artist: string, unlocked: readonly BreedId[]): ShrineRoll {
  const seed = phraseSeed(phrase, artist)
  const rng = createRng(seed.seed)
  // 1. Main breed: weighted by commonness among ALL breeds (locked ones included).
  const mainBreed = rng.weightedPick(BREEDS, (b) => b.commonness).id
  const mainLocked = !unlocked.includes(mainBreed)
  // 2. Sub breed: from h2, weighted by commonness among the unlocked breeds.
  const pool = BREEDS.filter((b) => unlocked.includes(b.id))
  const subBreed = createRng(seed.h2).weightedPick(pool.length > 0 ? pool : BREEDS, (b) => b.commonness).id
  // 3. Stat offsets.
  const stats = zeroStats()
  for (const k of STAT_KEYS) stats[k] = rng.nextInt(BIRTH.statOffset.min, BIRTH.statOffset.max)
  // 4. Lifespan offset. 5. Guts rate.
  const lifespan = rng.nextInt(BIRTH.lifespanOffset.min, BIRTH.lifespanOffset.max)
  const gutsRate = rng.nextInt(BIRTH.gutsOffset.min, BIRTH.gutsOffset.max)
  // 6. Personality. 7. Starting nature.
  const likes = rollLikes(rng)
  const nature = rng.nextInt(BIRTH.nature.min, BIRTH.nature.max)
  // 8. Name suggestion.
  const variantName = mixBreeds(mainBreed, subBreed).variantName
  return {
    seed,
    mainBreed,
    mainLocked,
    subBreed,
    offsets: { stats, lifespan, gutsRate, nature },
    likes,
    suggestedName: suggestName(seed.phrase, variantName),
    variantName,
  }
}

/** The newborn from a roll. The caller decides whether a locked main breed is allowed (the Lab always is). */
export function monsterFromRoll(roll: ShrineRoll, id: string): Monster {
  return createMonster({
    id,
    mainBreed: roll.mainBreed,
    subBreed: roll.subBreed,
    likes: roll.likes,
    offsets: roll.offsets,
    seedPhrase: roll.seed.phrase,
    name: roll.suggestedName,
  })
}

export function breedName(id: BreedId): string {
  return BREED_BY_ID[id].name
}
