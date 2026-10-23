import { BREEDS } from '../data/breeds.ts'
import { SECRETS, type SecretVariant } from '../data/secrets.ts'
import type { Breed } from '../data/types.ts'
import { recordInEncyclopedia } from './legacy.ts'
import { totalStats } from './monster.ts'
import type { GameState } from './state.ts'
import { knownMonsters, TITLE_IDS, type TitleId } from './titles.ts'

/**
 * GAME_DESIGN §18 the Journal: the Records page's numbers and the Encyclopedia's rows. The counters that
 * events bump (cups won, expeditions, stones woken) live on `state.records`; the rest is read from the save.
 */

/** Refreshes the best-total, generation and oldest records from what the ranch knows. Mutates a fresh copy only. */
export function updateRecordsMut(state: GameState): void {
  const r = state.records
  const m = state.monster
  if (m) {
    // Older saves never wrote their first monster into the Encyclopedia; the weekly pass catches that up.
    recordInEncyclopedia(state, m)
    const total = totalStats(m.stats)
    if (total > r.bestTotal) {
      r.bestTotal = total
      r.bestTotalName = m.name
    }
  }
  for (const k of knownMonsters(state)) {
    if (k.generation > r.highestGeneration) r.highestGeneration = k.generation
    if (k.ageWeeks > r.oldestWeeks) {
      r.oldestWeeks = k.ageWeeks
      r.oldestName = k.name
    }
  }
}

export function journeysDone(state: GameState): number {
  return Object.values(state.journeysBySite).reduce((a, b) => a + b, 0)
}

export type BreedStatus = 'owned' | 'awake' | 'asleep'

export function encyclopediaRows(state: GameState): { breed: Breed; status: BreedStatus }[] {
  return BREEDS.map((breed) => ({
    breed,
    status: state.encyclopedia.breeds.includes(breed.id) ? 'owned' : state.unlocked.includes(breed.id) ? 'awake' : 'asleep',
  }))
}

export function variantRows(state: GameState): { secret: SecretVariant; owned: boolean }[] {
  return SECRETS.map((secret) => ({ secret, owned: state.encyclopedia.variants.includes(secret.id) }))
}

export function titleRows(state: GameState): { id: TitleId; earned: boolean }[] {
  return TITLE_IDS.map((id) => ({ id, earned: state.titles.includes(id) }))
}
