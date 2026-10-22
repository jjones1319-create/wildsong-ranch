import { ITEM_BY_ID } from '../data/items.ts'
import type { FoodId, StatKey } from '../data/types.ts'
import { availability } from './aging.ts'
import { isMonthStart } from './calendar.ts'
import { finishEdit, pushHistory } from './lab.ts'
import type { Monster } from './monster.ts'
import type { Rng } from './rng.ts'
import type { UseItemResult } from './items.ts'
import type { JourneyWeekResult } from './journey.ts'
import { forgetTechnique, learnReplacing, learnTechnique, type LearnStatus } from './songbook.ts'
import type { GameState, WeekAction } from './state.ts'
import type { DrillOutcome, DrillResult, Reaction } from './training.ts'
import { endWeek, reactToDrill, resolveAction, respondToRequest, startWeek, useItemInGame, type WeekEvent } from './week.ts'

/**
 * The turn controller (M3): the thin, pure layer between the UI and the week loop in week.ts. It keeps the
 * week's phase in the save (`weekPhase`, `pendingRequest`), so a game can be closed at any moment and
 * reopened exactly where it was, and it remembers "last week" for the Repeat button.
 *
 *   beginWeek → (answerRequest) → chooseAction → (react) → finishWeek → beginWeek …
 *
 * Free actions (items, sheets, edits) may happen whenever the phase is `action`.
 */

export interface StepResult {
  state: GameState
  events: WeekEvent[]
}

/** Week 1 of a month starts with the food prompt (§3): true while that choice is still to be made. */
export function needsFoodChoice(state: GameState): boolean {
  return state.weekPhase === 'start' && isMonthStart(state.week) && state.monster !== null && state.ended === null
}

/** Runs the start-of-week phase once (food, charms, the request roll) and records the request in the save. */
export function beginWeek(input: GameState, rng: Rng, food?: FoodId): StepResult {
  if (input.weekPhase !== 'start' || !input.monster || input.ended) return { state: input, events: [] }
  const r = startWeek(input, rng, isMonthStart(input.week) ? food : undefined)
  r.state.weekPhase = 'action'
  r.state.pendingRequest = r.request
  return { state: r.state, events: r.events }
}

export interface AnswerResult extends StepResult {
  /** Rest or play when the request was accepted: the week's action, to be passed to chooseAction at once. */
  forcedAction: WeekAction | null
}

/** Answers the pending request. Accepting a treat uses the toy and the week goes on. */
export function answerRequest(input: GameState, accept: boolean): AnswerResult {
  const request = input.pendingRequest
  if (!request) return { state: input, events: [], forcedAction: null }
  const r = respondToRequest(input, request, accept)
  r.state.pendingRequest = null
  return { state: r.state, events: r.events, forcedAction: r.forcedAction }
}

export interface ActionResult extends StepResult {
  drill: DrillResult | null
  journey: JourneyWeekResult | null
}

/** The one action of the week. A still-pending request counts as denied. */
export function chooseAction(input: GameState, action: WeekAction, rng: Rng): ActionResult {
  let state = input
  const events: WeekEvent[] = []
  if (state.weekPhase !== 'action' || !state.monster || state.ended) return { state, events, drill: null, journey: null }
  if (state.pendingRequest) {
    const denied = answerRequest(state, false)
    state = denied.state
    events.push(...denied.events)
  }
  const r = resolveAction(state, action, rng)
  state = r.state
  events.push(...r.events)
  const done = r.events.some((e) => e.kind === 'drill') ? 'drill' : r.events.some((e) => e.kind === 'rest' || e.kind === 'play') ? 'rest' : null
  if (done === 'drill') {
    state.counters.drillsDone += 1
    state.lastAction = action
  } else if (done === 'rest') {
    state.counters.restsTaken += 1
    state.lastAction = { kind: 'rest' }
  }
  return { state, events, drill: r.drill, journey: r.journey }
}

/** The praise / scold / skip prompt after a drill. */
export function react(input: GameState, outcome: DrillOutcome, reaction: Reaction): GameState {
  return reactToDrill(input, outcome, reaction)
}

/** The end of the week: aging, checks, next week's weather. The next week is then waiting to begin. */
export function finishWeek(input: GameState, rng: Rng): StepResult {
  if (input.weekPhase !== 'action') return { state: input, events: [] }
  const r = endWeek(input, rng)
  r.state.weekPhase = 'start'
  r.state.pendingRequest = null
  return { state: r.state, events: r.events }
}

export type MenuReason = 'ended' | 'noMonster' | 'request' | 'journey' | 'missing' | 'clinic' | 'cocoon' | 'sick' | 'injured' | null

export interface ActionMenu {
  train: boolean
  rest: boolean
  /** The week has to pass without an action (away at the clinic, missing, on a Journey). */
  wait: boolean
  reason: MenuReason
  /** "Repeat last week", when last week's action is possible now. */
  repeat: WeekAction | null
}

/** Which buttons the ranch should enable, and why the others are off. */
export function actionMenu(state: GameState): ActionMenu {
  const none: ActionMenu = { train: false, rest: false, wait: false, reason: null, repeat: null }
  if (state.ended) return { ...none, reason: 'ended' }
  if (!state.monster) return { ...none, reason: 'noMonster' }
  if (state.weekPhase !== 'action') return none
  if (state.pendingRequest) return { ...none, reason: 'request' }
  if (state.journey) return { ...none, wait: true, reason: 'journey' }
  const a = availability(state.monster)
  if (a.locked) return { ...none, wait: true, reason: a.reason }
  if (a.restOnly) return { ...none, rest: true, reason: a.reason, repeat: state.lastAction?.kind === 'rest' ? state.lastAction : null }
  return { train: true, rest: true, wait: false, reason: null, repeat: state.lastAction && state.lastAction.kind !== 'none' ? state.lastAction : null }
}

/* ---------- free actions ---------- */

export interface UseResult {
  state: GameState
  used: number
  result: UseItemResult | null
}

/** Uses items from the Bag (any number, any time the week is in play). */
export function useItems(input: GameState, itemId: string, qty: number, stat?: StatKey): UseResult {
  if (input.weekPhase !== 'action' || !input.monster || input.ended) return { state: input, used: 0, result: null }
  const r = useItemInGame(input, itemId, qty, stat)
  if (r.used > 0 && ITEM_BY_ID[itemId]?.category === 'sweet') r.state.counters.sweetsEaten += r.used
  return r
}

/** Learns a technique from the Songbook, forgetting `forgetId` first when the monster already knows 12. */
export function learnFromSongbook(input: GameState, techId: string, forgetId?: string): { state: GameState; status: LearnStatus | 'notOwned' } {
  const m = input.monster
  if (!m || input.ended) return { state: input, status: 'unknownTechnique' }
  if (!input.songbook.includes(techId)) return { state: input, status: 'notOwned' }
  const r = forgetId ? learnReplacing(m, techId, forgetId) : learnTechnique(m, techId)
  if (r.status !== 'learned') return { state: input, status: r.status }
  const state = structuredClone(input)
  state.monster = r.monster
  state.counters.sheetsLearned += 1
  return { state, status: 'learned' }
}

/** Forgetting is free and can be undone through the Songbook (§10.5). */
export function forgetFromCard(input: GameState, techId: string): GameState {
  if (!input.monster) return input
  const state = structuredClone(input)
  state.monster = forgetTechnique(state.monster!, techId)
  return state
}

/**
 * §19: the Lab editor saved the active monster. The version it replaced joins the edit history, and the
 * edited flag follows the usual rule (anything but the name). `savedAt` comes from the UI clock.
 */
export function replaceActiveMonster(input: GameState, edited: Monster, savedAt: number): GameState {
  const before = input.monster
  if (!before) return input
  const state = structuredClone(input)
  const finished = finishEdit(before, edited)
  finished.id = before.id
  state.monsterHistory = pushHistory(state.monsterHistory, before, savedAt)
  state.monster = finished
  return state
}

/** Gentle ↔ Standard can be switched during a game; Classic is locked in (§7). */
export function canSwitchDifficulty(state: GameState, to: GameState['difficulty']): boolean {
  if (state.difficulty === 'Classic' || to === 'Classic') return false
  return to !== state.difficulty
}

export function switchDifficulty(input: GameState, to: GameState['difficulty']): GameState {
  if (!canSwitchDifficulty(input, to)) return input
  const state = structuredClone(input)
  state.difficulty = to
  return state
}
