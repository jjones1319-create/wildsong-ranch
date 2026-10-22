import type { BreedId } from '../data/types.ts'
import { createMonster, type Likes, type Monster } from './monster.ts'

/** Shared fixtures for core tests (not a test file itself). */

export const NEUTRAL_LIKES: Likes = { food: 'honey-bread', dislikedFood: 'turnips', toy: 'rubber-ball', battle: 0, drill: 'puzzle-stones', dislikedDrill: 'acorn-shower' }

export interface MonsterOverrides {
  id?: string
  main?: BreedId
  sub?: BreedId
  likes?: Likes
  /** Set lifespanTotal to 100 and ageWeeks to this percentage to pin a life stage. */
  agePct?: number
  fatigue?: number
  stress?: number
  spoil?: number
  fear?: number
  nature?: number
  stats?: Partial<Monster['stats']>
}

export function makeMonster(o: MonsterOverrides = {}): Monster {
  const m = createMonster({ id: o.id ?? 'test', mainBreed: o.main ?? 'puddlepup', subBreed: o.sub ?? o.main ?? 'puddlepup', likes: o.likes ?? NEUTRAL_LIKES })
  if (o.agePct !== undefined) {
    m.lifespanTotal = 100
    m.ageWeeks = o.agePct
  }
  if (o.fatigue !== undefined) m.fatigue = o.fatigue
  if (o.stress !== undefined) m.stress = o.stress
  if (o.spoil !== undefined) m.spoil = o.spoil
  if (o.fear !== undefined) m.fear = o.fear
  if (o.nature !== undefined) m.nature = o.nature
  if (o.stats) Object.assign(m.stats, o.stats)
  return m
}
