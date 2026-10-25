import { weekIndexOf } from '../src/core/calendar.ts'
import { TIP_IDS } from '../src/core/onboarding.ts'
import { makePreset } from '../src/core/presets.ts'
import { createGameState, type GameState } from '../src/core/state.ts'
import type { BreedId, TournamentGrade } from '../src/data/types.ts'
import { makeSave } from '../src/save/schema.ts'

/**
 * Prepared saves for the e2e specs: a ranch parked on a given calendar week in the action phase, every tip
 * already seen, with a preset monster of the given grade. The app reads the localStorage mirror when its
 * IndexedDB is empty, which it always is in a fresh Playwright context.
 */
export interface SaveAt {
  year: number
  month: number
  week: number
  grade?: TournamentGrade
  breed?: BreedId
  /** Tweak the state before it is saved (a Journey Trial, a cup in progress…). */
  edit?: (g: GameState) => void
}

export function saveJsonAt(o: SaveAt): string {
  const grade = o.grade ?? 'E'
  const m = makePreset(o.breed ?? 'tumblefox', grade)
  m.name = 'Pip'
  m.fatigue = 0
  m.stress = 0
  const g = createGameState({ monster: m, breederName: 'Jo', ranchName: 'Hillside' })
  g.week = weekIndexOf({ year: o.year, month: o.month, week: o.week })
  g.weekPhase = 'action'
  g.tipsSeen = [...TIP_IDS]
  g.money = 5000
  o.edit?.(g)
  return JSON.stringify(makeSave(g, 12345, { savedAt: 1, appVersion: 'e2e' }))
}

export const MIRROR_KEY = 'wildsong/mirror/latest'
