import { BREEDS, BREED_BY_ID } from '../data/breeds.ts'
import type { SecretVariant } from '../data/secrets.ts'
import { BIRTH, RANGES, SHRINE } from '../data/tuning.ts'
import { STAT_KEYS, type BreedId } from '../data/types.ts'
import { phraseSeed, type PhraseSeed } from './hash.ts'
import { createMonster, rollLikes, zeroStats, type BirthOffsets, type Likes, type Monster } from './monster.ts'
import { createRng, scrambleSeed, type Rng } from './rng.ts'
import { applyBirthPerkMut, secretForPhrase, variantNameOf, variantStatBonus } from './variants.ts'

/**
 * GAME_DESIGN §14.1: the Shrine of Echoes turns a phrase into a monster. The order of the rolls is
 * part of the contract (changing it changes every monster ever made), so it is spelled out step by
 * step here and pinned by snapshot tests. A secret phrase (CONTENT §12) skips the breed rolls: its
 * variant names the breed, and the monster gets the variant's colours and bonus.
 */

export interface ShrineRoll {
  seed: PhraseSeed
  mainBreed: BreedId
  /** True when the main breed is not unlocked: in the game no monster is made (the stone hums). The Lab ignores this. */
  mainLocked: boolean
  offsets: BirthOffsets
  likes: Likes
  suggestedName: string
  variantName: string
  /** The secret variant this phrase names, if any. */
  secret: SecretVariant | null
}

/** The name the Shrine suggests: the first word of the phrase, or the variant name. */
export function suggestName(normalizedPhrase: string, variantName: string): string {
  const first = normalizedPhrase.split(' ').find((w) => w.length > 0) ?? ''
  const name = first ? first.charAt(0).toUpperCase() + first.slice(1) : variantName
  return name.slice(0, RANGES.nameLength.max)
}

/** Breeds 1–30, the launch roster: the main breed draw picks among them exactly as it always has. */
const LAUNCH_BREEDS = BREEDS.slice(0, SHRINE.launchBreedCount)
/** Breeds added after launch (31 Stripeneck, 32 Plumdrake…), reached through their own draw. */
const ADDED_BREEDS = BREEDS.slice(SHRINE.launchBreedCount)
const LAUNCH_WEIGHT = LAUNCH_BREEDS.reduce((a, b) => a + b.commonness, 0)

/**
 * The added-breed draw (GAME_DESIGN §14.1): from its own stream, the phrase lands on an added breed with their
 * share of all the commonness, picked among them by commonness; otherwise null. It never touches the main RNG.
 */
export function addedBreedFor(seed: PhraseSeed): BreedId | null {
  if (!ADDED_BREEDS.length) return null
  const own = createRng(scrambleSeed((seed.seed ^ SHRINE.addedBreedSalt) >>> 0))
  const choices: readonly { id: BreedId | null; weight: number }[] = [
    { id: null, weight: LAUNCH_WEIGHT },
    ...ADDED_BREEDS.map((b) => ({ id: b.id, weight: b.commonness })),
  ]
  return own.weightedPick(choices, (c) => c.weight).id
}

/** Step 1: the launch-roster draw always happens (so every later roll stays put), then the added-breed draw may replace it. */
function pickBreed(rng: Rng, seed: PhraseSeed): BreedId {
  const launch = rng.weightedPick(LAUNCH_BREEDS, (b) => b.commonness).id
  return addedBreedFor(seed) ?? launch
}

export function rollShrine(phrase: string, artist: string, unlocked: readonly BreedId[]): ShrineRoll {
  const seed = phraseSeed(phrase, artist)
  const rng = createRng(seed.seed)
  const secret = secretForPhrase(seed.phrase)
  // A secret phrase names the variant's breed: no breed roll, so the seed goes straight to the offsets.
  // 1. Breed: weighted by commonness among the launch roster (locked ones included); an added breed may replace it
  //    through its own draw, so every older phrase keeps its monster (GAME_DESIGN §14.1).
  // 2. (Retired in v1.12: the sub breed. It drew from its own h2 stream, so no other roll moved.)
  const mainBreed: BreedId = secret ? secret.breed : pickBreed(rng, seed)
  const mainLocked = !unlocked.includes(mainBreed)
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
  const variantName = variantNameOf({ mainBreed, variantId: secret?.id ?? null })
  return {
    seed,
    mainBreed,
    mainLocked,
    offsets: { stats, lifespan, gutsRate, nature },
    likes,
    suggestedName: suggestName(seed.phrase, variantName),
    variantName,
    secret,
  }
}

/** The newborn from a roll. The caller decides whether a locked main breed is allowed (the Lab always is). */
export function monsterFromRoll(roll: ShrineRoll, id: string): Monster {
  const offsets: BirthOffsets = { ...roll.offsets, stats: { ...roll.offsets.stats } }
  if (roll.secret) {
    const bonus = variantStatBonus(roll.secret)
    for (const k of STAT_KEYS) offsets.stats[k] += bonus[k]
    offsets.lifespan += roll.secret.lifespan
  }
  const m = createMonster({
    id,
    mainBreed: roll.mainBreed,
    likes: roll.likes,
    offsets,
    seedPhrase: roll.seed.phrase,
    name: roll.suggestedName,
    variantId: roll.secret?.id ?? null,
  })
  return applyBirthPerkMut(m)
}

export function breedName(id: BreedId): string {
  return BREED_BY_ID[id].name
}

/** Randomize: one to three words from the Shrine's word list, joined with spaces. */
export function randomPhrase(rng: Rng, words: readonly string[]): string {
  const n = rng.nextInt(SHRINE.randomWords.min, SHRINE.randomWords.max)
  const out: string[] = []
  for (let i = 0; i < n; i++) out.push(rng.pick(words))
  return out.join(' ')
}
