import type { GameState } from '../../../core/state.ts'

/**
 * The ranch's card gates, pure so they are unit-tested. The trial card takes over the ranch when a Journey
 * Trial is waiting (a trial in progress, a technique waiting to be learned, or a trial outcome to show).
 * With no journey at all, nothing is pending: `undefined` must not count as "something".
 */
export function trialGateOpen(g: Pick<GameState, 'trial' | 'journey'>, hasOutcome: boolean): boolean {
  return g.trial !== null || (g.journey?.pendingTechnique ?? null) !== null || hasOutcome
}
