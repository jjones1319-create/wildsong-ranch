import { TRANSPARENCY } from '../data/tuning.ts'
import type { DrillId } from '../data/types.ts'
import { loyaltyOf, type Monster } from './monster.ts'
import { DEFAULT_TRAINING, levelPercents, levelWeights, outcomePercents, outcomeWeights, truancyChancePct, type OutcomeWeights, type TrainingSetting } from './training.ts'

/**
 * GAME_DESIGN §6.8: what the Train sheet may say about a drill. Classic shows nothing, Guided a word for the
 * chance of a good outcome (Great + Success), Breeder's Lens the exact percentages.
 */

export type OddsWord = 'eager' | 'likely' | 'risky' | 'veryRisky'

export function oddsWord(goodPct: number): OddsWord {
  const b = TRANSPARENCY.oddsBands
  if (goodPct >= b.eager) return 'eager'
  if (goodPct >= b.likely) return 'likely'
  if (goodPct >= b.risky) return 'risky'
  return 'veryRisky'
}

export interface DrillOdds {
  /** Exact percentages, floats. */
  pct: OutcomeWeights
  /** Great + Success, after the truancy chance is taken off the top. */
  good: number
  /** §6.2 the Perfect and Superb shares (0 until loyalty allows them). */
  perfect: number
  superb: number
  truancyPct: number
  word: OddsWord
}

export function drillOdds(m: Monster, drill: DrillId, setting: TrainingSetting = DEFAULT_TRAINING): DrillOdds {
  const w = outcomeWeights(m, drill, setting)
  const pct = outcomePercents(w)
  const levels = levelPercents(levelWeights(w, loyaltyOf(m)))
  const truancyPct = Math.min(100, truancyChancePct(m.fatigue, loyaltyOf(m)))
  const good = ((pct.great + pct.success) * (100 - truancyPct)) / 100
  return { pct, good, perfect: levels.Perfect, superb: levels.Superb, truancyPct, word: oddsWord(good) }
}
