import { UNIVERSAL_TECHNIQUES } from '../data/techniques.ts'
import { TITLES } from '../data/tuning.ts'
import type { BreedId } from '../data/types.ts'
import { mixBreeds, type Monster } from './monster.ts'
import type { GameState } from './state.ts'

/**
 * CONTENT §14 titles. Cup placings award theirs in tournament.ts as they happen; everything else is a plain
 * check over the save, run at the end of every week and after the farewell, so a title can never be missed
 * because the moment passed. `awardTitles` is pure and returns the same state when nothing is new.
 */

export const TITLE_IDS = [
  'First Ribbon',
  'Ascended',
  'S-Class Breeder',
  'Crowned',
  'Four Crowns',
  'Legend of the Vale',
  'Grand Breeder',
  'Lineage Keeper',
  'Encyclopedist',
  'Collector',
  'Gentle Heart',
  'Iron Bond',
  'Sleeper Awakened',
  'Songbook Scholar',
  'Sweet Tooth',
  'Storm Chaser',
  'Silk & Moonlight',
  'Unmasked',
  'Tinkerer',
  'Treasure Hunter',
  'Perfect Pitch',
] as const
export type TitleId = (typeof TITLE_IDS)[number]

/** The unlock chains' titles: earned when the breed wakes, however it woke. */
const UNLOCK_TITLES: readonly (readonly [TitleId, BreedId])[] = [
  ['Storm Chaser', 'zipwisp'],
  ['Silk & Moonlight', 'velvesper'],
  ['Unmasked', 'mirrorkin'],
  ['Tinkerer', 'gearhoot'],
  ['Treasure Hunter', 'lootlid'],
]

/** Every monster this ranch remembers. */
export function knownMonsters(state: GameState): Monster[] {
  return [...(state.monster ? [state.monster] : []), ...state.freezer, ...state.elderGrove, ...state.memorial.map((e) => e.monster), ...state.hallOfFame.map((h) => h.monster)]
}

/** How much of the breed mix's nominal lifespan a monster has lived, in percent. */
export function livedNominalPct(m: Monster): number {
  const nominal = Math.max(1, mixBreeds(m.mainBreed, m.subBreed).lifespan)
  return Math.floor((m.ageWeeks * 100) / nominal)
}

/** The titles the save has earned but not been given yet. */
export function missingTitles(state: GameState): TitleId[] {
  const has = (t: TitleId) => state.titles.includes(t)
  const out: TitleId[] = []
  const all = knownMonsters(state)
  if (!has('Lineage Keeper') && all.some((m) => m.generation >= TITLES.lineageGeneration)) out.push('Lineage Keeper')
  if (!has('Encyclopedist') && state.encyclopedia.breeds.length >= TITLES.encyclopedistBreeds) out.push('Encyclopedist')
  if (!has('Collector') && state.encyclopedia.combos.length >= TITLES.collectorVariants) out.push('Collector')
  if (!has('Gentle Heart') && state.memorial.some((e) => e.cause !== 'fused' && livedNominalPct(e.monster) >= TITLES.gentleHeartPct)) out.push('Gentle Heart')
  if (!has('Sleeper Awakened') && state.records.stonesWoken >= TITLES.sleeperStones) out.push('Sleeper Awakened')
  if (!has('Songbook Scholar') && UNIVERSAL_TECHNIQUES.every((t) => state.songbook.includes(t.id))) out.push('Songbook Scholar')
  if (!has('Sweet Tooth') && state.counters.sweetsEaten >= TITLES.sweetTooth) out.push('Sweet Tooth')
  for (const [title, breed] of UNLOCK_TITLES) if (!has(title) && state.unlocked.includes(breed)) out.push(title)
  if (!has('Perfect Pitch') && state.echoStonesBest >= TITLES.perfectPitchRound) out.push('Perfect Pitch')
  return out
}

/** Gives every missing title to the ranch and the active monster. */
export function awardTitles(input: GameState): { state: GameState; titles: TitleId[] } {
  const titles = missingTitles(input)
  if (titles.length === 0) return { state: input, titles }
  const state = structuredClone(input)
  for (const t of titles) {
    state.titles.push(t)
    if (state.monster && !state.monster.records.titles.includes(t)) state.monster.records.titles.push(t)
  }
  return { state, titles }
}
