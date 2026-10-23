import { EXPRESSION, REPORT } from '../data/tuning.ts'
import { loyaltyOf } from './monster.ts'
import type { GameState } from './state.ts'
import type { Reaction } from './training.ts'

/**
 * GAME_DESIGN §22 emotes (♥, ?!, 💢, 💤): a small bubble over the monster that says what it feels right now.
 * Pure selection from the state; the UI only draws it. One at a time, most urgent first.
 */
export type Emote = 'heart' | 'surprise' | 'anger' | 'sleep'

export function emoteFor(state: GameState): Emote | null {
  const m = state.monster
  if (!m || state.ended) return null
  if (state.pendingRequest || state.pendingEvent) return 'surprise'
  if (m.status.sickWeeks > 0 || m.status.clinicWeeks > 0) return 'sleep'
  if (m.fatigue >= REPORT.tiredFatigue) return 'sleep'
  if (m.stress >= EXPRESSION.sweatStress) return 'anger'
  if (loyaltyOf(m) >= EXPRESSION.sparkleLoyalty && m.fatigue <= REPORT.fresh.fatigueMax && m.stress <= REPORT.fresh.stressMax) return 'heart'
  return null
}

/** The bubble after praise or scold on the drill result. */
export function emoteForReaction(reaction: Reaction): Emote | null {
  return reaction === 'praise' ? 'heart' : reaction === 'scold' ? 'anger' : null
}
