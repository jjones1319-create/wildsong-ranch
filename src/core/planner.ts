import { PLANNER } from '../data/tuning.ts'
import { availability } from './aging.ts'
import { isMonthStart } from './calendar.ts'
import { beginWeek, chooseAction, finishWeek, react } from './game.ts'
import type { Rng } from './rng.ts'
import type { GameState, PlannerLogEntry, PlannerStep, PlannerStop } from './state.ts'
import type { WeekEvent } from './week.ts'

export type { PlannerLogEntry, PlannerStep, PlannerStop } from './state.ts'

/**
 * GAME_DESIGN §3 the planner (M8): up to eight queued weeks of drills and rests, run one at a time through
 * the same controller the ranch uses (beginWeek → chooseAction → react → finishWeek). It keeps last month's
 * food, says nothing after a drill (so it never changes balance), and stops the moment something needs the
 * player: before a week on a request, a pending event, a trial or new mail (invitations included); after a
 * week on illness, a breakdown, a lifespan warning, a forced rest, the Signature, a grow-up, prime, or
 * fatigue / stress at the PLANNER thresholds. Ordinary cups never stop it: almost every week holds one, and
 * the ranch lists them, so entering a cup is a choice the player makes between runs.
 *
 */

export const PLANNER_MAX = PLANNER.maxWeeks

export function queueStep(input: GameState, step: PlannerStep): GameState {
  if (input.planner.queue.length >= PLANNER_MAX) return input
  const state = structuredClone(input)
  state.planner.queue.push(step)
  return state
}

export function removeStep(input: GameState, index: number): GameState {
  if (index < 0 || index >= input.planner.queue.length) return input
  const state = structuredClone(input)
  state.planner.queue.splice(index, 1)
  return state
}

export function clearQueue(input: GameState): GameState {
  if (input.planner.queue.length === 0 && input.planner.log.length === 0 && input.planner.lastStop === null) return input
  const state = structuredClone(input)
  state.planner = { queue: [], log: [], lastStop: null }
  return state
}

/** A new run forgets the previous run's log and reason. */
export function startRun(input: GameState): GameState {
  const state = structuredClone(input)
  state.planner.log = []
  state.planner.lastStop = null
  return state
}

export interface PlannedWeek {
  state: GameState
  events: WeekEvent[]
  /** Null while the run may go on. */
  stop: PlannerStop | null
  /** True when a week was actually played (the queue moved on). */
  acted: boolean
}

/** Why a run cannot even begin a week from here, or null. */
export function plannerBlocker(state: GameState): PlannerStop | null {
  if (state.ended) return 'ended'
  if (!state.monster) return 'noMonster'
  if (state.planner.queue.length === 0) return 'empty'
  if (state.tournament) return 'tournament'
  if (state.trial) return 'trial'
  if (state.expedition) return 'expedition'
  if (state.journey) return 'journey'
  if (state.weekPhase === 'action') {
    if (state.pendingRequest) return 'request'
    if (state.pendingEvent) return 'event'
  }
  const a = availability(state.monster)
  if (a.locked) return 'locked'
  return null
}

const unread = (s: GameState) => s.mail.filter((m) => !m.read).length

/** What stops a run once the week has begun (a request, an event, new mail). */
function stopAfterBegin(before: GameState, after: GameState): PlannerStop | null {
  if (after.pendingRequest) return 'request'
  if (after.pendingEvent) return 'event'
  if (unread(after) > unread(before)) return 'mail'
  return null
}

/** What stops a run once the week has ended, in order of importance. */
function stopAfterFinish(state: GameState, events: readonly WeekEvent[]): PlannerStop | null {
  if (state.ended) return 'ended'
  for (const e of events) {
    if (e.kind !== 'aging') continue
    switch (e.event.kind) {
      case 'illness':
        return 'illness'
      case 'breakdown':
        return 'breakdown'
      case 'endOfLife':
        return 'ended'
      default:
        break
    }
  }
  if (events.some((e) => e.kind === 'forcedRest')) return 'forcedRest'
  if (events.some((e) => e.kind === 'emerged')) return 'grewUp'
  if (events.some((e) => e.kind === 'signature')) return 'signature'
  if (events.some((e) => e.kind === 'aging' && e.event.kind === 'prime')) return 'prime'
  if (events.some((e) => e.kind === 'aging' && (e.event.kind === 'warning' || e.event.kind === 'pastPrime'))) return 'warning'
  const m = state.monster
  if (m && m.fatigue >= PLANNER.stopFatigue) return 'fatigue'
  if (m && m.stress >= PLANNER.stopStress) return 'stress'
  if (state.planner.queue.length === 0) return 'empty'
  return null
}

/**
 * Plays the next queued week, or stops before it. When it stops before acting, the week may already have
 * begun (the request card or the letter is then waiting on the ranch) and the step stays in the queue.
 */
export function runPlannedWeek(input: GameState, rng: Rng): PlannedWeek {
  const blocked = plannerBlocker(input)
  if (blocked) return { state: withStop(input, blocked), events: [], stop: blocked, acted: false }
  let state = input
  const events: WeekEvent[] = []
  if (state.weekPhase === 'start') {
    const begun = beginWeek(state, rng, isMonthStart(state.week) ? state.foodChoice : undefined)
    events.push(...begun.events)
    const stop = stopAfterBegin(state, begun.state)
    state = begun.state
    if (stop) return { state: withStop(state, stop), events, stop, acted: false }
  } else {
    const stop = stopAfterBegin(state, state)
    if (stop) return { state: withStop(state, stop), events, stop, acted: false }
  }
  const step = state.planner.queue[0]!
  const monsterBefore = state.monster!
  const acted = chooseAction(state, step, rng)
  events.push(...acted.events)
  state = acted.state
  if (acted.events.some((e) => e.kind === 'invalidAction')) {
    // The drill is not available (the Training Yard is missing): drop the step and let the player decide.
    state = structuredClone(state)
    state.planner.queue.shift()
    return { state: withStop(state, 'invalid'), events, stop: 'invalid', acted: false }
  }
  if (acted.drill) {
    state = react(state, acted.drill.outcome, 'skip')
    events.push({ kind: 'reaction', reaction: 'skip' })
  }
  state = structuredClone(state)
  state.planner.queue.shift()
  const entry: PlannerLogEntry = {
    week: input.week,
    step,
    outcome: acted.drill?.outcome ?? null,
    gains: acted.drill?.gains ?? {},
    pay: acted.drill?.pay ?? 0,
  }
  state.planner.log = [...state.planner.log, entry].slice(-PLANNER_MAX)
  const finished = finishWeek(state, rng)
  events.push(...finished.events)
  state = finished.state
  const stop = stopAfterFinish(state, events)
  void monsterBefore
  return { state: stop ? withStop(state, stop) : state, events, stop, acted: true }
}

function withStop(input: GameState, stop: PlannerStop): GameState {
  if (input.planner.lastStop === stop) return input
  const state = structuredClone(input)
  state.planner.lastStop = stop
  return state
}

/** Runs the queue until it stops (for tests and simulations). */
export function runPlanner(input: GameState, rng: Rng, maxSteps = PLANNER_MAX): { state: GameState; stop: PlannerStop; weeks: number } {
  let state = startRun(input)
  let weeks = 0
  for (let i = 0; i <= maxSteps; i++) {
    const r = runPlannedWeek(state, rng)
    state = r.state
    if (r.acted) weeks += 1
    if (r.stop) return { state, stop: r.stop, weeks }
  }
  return { state, stop: 'empty', weeks }
}
