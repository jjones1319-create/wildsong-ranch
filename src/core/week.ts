import { DRILL_BY_ID } from '../data/drills.ts'
import { JOURNEY, UPGRADES } from '../data/tuning.ts'
import type { DrillId, FoodId, FoodEffect, JourneySiteId, StatKey, Weather } from '../data/types.ts'
import { availability, endOfWeekTick, type AgingEvent } from './aging.ts'
import { dateOf, isMonthStart, isUpgradeOfferWeek, rollWeather, seasonOf } from './calendar.ts'
import { applyMonthlyFood, type FoodRelation } from './food.ts'
import { charmValue, countOf, useItem, type UseItemResult } from './items.ts'
import { canEnterSite, isJourneyDone, isSiteOpen, journeyWeek, startJourney, type JourneyProgress, type JourneyWeekResult } from './journey.ts'
import { addCondition } from './monster.ts'
import type { Rng } from './rng.ts'
import type { GameState } from './state.ts'
import { applyReaction, denyRequest, playMonster, resolveDrill, restMonster, rollRequest, type DrillOutcome, type DrillResult, type MonsterRequest, type Reaction } from './training.ts'

/**
 * GAME_DESIGN §3: the week, in its strict order.
 *   1. start of week (monthly food, charms, upgrade offer)   2. request check
 *   3. the player's ONE action                               4. end of week (aging, checks, weather, autosave)
 * Items are free actions between the phases and never use the turn.
 * Every exported function is pure: it returns a new state and leaves its input untouched.
 */

export type WeekAction = { kind: 'drill'; drill: DrillId } | { kind: 'rest' } | { kind: 'play' } | { kind: 'journey'; site: JourneySiteId } | { kind: 'none' }

export type WeekPhase = 'startOfWeek' | 'requestCheck' | 'action' | 'endOfWeek'

export type WeekEvent =
  | { kind: 'phase'; phase: WeekPhase }
  | { kind: 'food'; food: FoodId; relation: FoodRelation; bored: boolean; effect: FoodEffect }
  | { kind: 'charm'; stress: number }
  | { kind: 'upgradeOffer' }
  | { kind: 'request'; request: MonsterRequest }
  | { kind: 'requestDenied' }
  | { kind: 'item'; itemId: string; used: number }
  | { kind: 'drill'; result: DrillResult }
  | { kind: 'reaction'; reaction: Reaction }
  | { kind: 'rest'; fatigue: number; stress: number }
  | { kind: 'play'; fatigue: number; stress: number }
  | { kind: 'journeyStart'; site: JourneySiteId; cost: number }
  | { kind: 'journeyWeek'; result: JourneyWeekResult }
  | { kind: 'journeyDone'; progress: JourneyProgress }
  | { kind: 'forcedRest'; reason: string }
  | { kind: 'locked'; reason: string }
  | { kind: 'invalidAction'; reason: string }
  | { kind: 'aging'; event: AgingEvent }
  | { kind: 'fees'; amount: number }
  | { kind: 'weather'; weather: Weather }
  | { kind: 'autosave' }

export interface StartWeekResult {
  state: GameState
  request: MonsterRequest | null
  events: WeekEvent[]
}

/** Phases 1 and 2. `food` is the month's choice when this is week 1 of a month (defaults to last month's). */
export function startWeek(input: GameState, rng: Rng, food?: FoodId): StartWeekResult {
  const state = structuredClone(input)
  const events: WeekEvent[] = [{ kind: 'phase', phase: 'startOfWeek' }]
  state.itemsUsedThisWeek = 0
  let m = state.monster
  if (!m || state.ended) return { state, request: null, events }

  if (isMonthStart(state.week)) {
    if (food) state.foodChoice = food
    const fed = applyMonthlyFood(m, state.foodChoice)
    m = fed.monster
    events.push({ kind: 'food', food: state.foodChoice, relation: fed.relation, bored: fed.bored, effect: fed.effect })
    const comfort = charmValue(state.inventory, 'comfort')
    if (comfort > 0) {
      m.stress = addCondition(m.stress, -comfort)
      events.push({ kind: 'charm', stress: -comfort })
    }
  }
  if (state.upgrades.cozyBarn) m.stress = addCondition(m.stress, -UPGRADES.cozyBarnStress)
  if (state.upgrades.tidePool && seasonOf(dateOf(state.week).month) === 'Summer') m.stress = addCondition(m.stress, -UPGRADES.tidePoolSummerStress)
  if (isUpgradeOfferWeek(state.week)) events.push({ kind: 'upgradeOffer' })
  state.monster = m

  events.push({ kind: 'phase', phase: 'requestCheck' })
  let request: MonsterRequest | null = null
  if (!availability(m).locked && !state.journey) {
    request = rollRequest(m, rng, countOf(state.inventory, m.likes.toy) > 0)
    if (request) events.push({ kind: 'request', request })
  }
  return { state, request, events }
}

/** Answer a request. Accepting rest or play makes that the week's action; a treat uses the toy and the week goes on. */
export function respondToRequest(input: GameState, request: MonsterRequest, accept: boolean): { state: GameState; forcedAction: WeekAction | null; events: WeekEvent[] } {
  const state = structuredClone(input)
  const events: WeekEvent[] = []
  if (!state.monster) return { state, forcedAction: null, events }
  if (!accept) {
    state.monster = denyRequest(state.monster)
    events.push({ kind: 'requestDenied' })
    return { state, forcedAction: null, events }
  }
  if (request.kind === 'rest') return { state, forcedAction: { kind: 'rest' }, events }
  if (request.kind === 'play') return { state, forcedAction: { kind: 'play' }, events }
  if (request.toy) {
    const r = useItemInGame(state, request.toy, 1)
    return { state: r.state, forcedAction: null, events: r.used > 0 ? [{ kind: 'item', itemId: request.toy, used: r.used }] : [] }
  }
  return { state, forcedAction: null, events }
}

/** A free action: use items from the Bag at any time. Honors the optional one-per-week rule. */
export function useItemInGame(input: GameState, itemId: string, qty: number, stat?: StatKey): { state: GameState; used: number; result: UseItemResult | null } {
  if (!input.monster) return { state: input, used: 0, result: null }
  const r = useItem(input.monster, input.inventory, itemId, qty, { stat, onePerWeek: input.settings.onePerWeek, usedThisWeek: input.itemsUsedThisWeek })
  if (r.used === 0) return { state: input, used: 0, result: r }
  const state = structuredClone(input)
  state.monster = r.monster
  state.inventory = r.inventory
  state.itemsUsedThisWeek += r.used
  return { state, used: r.used, result: r }
}

/** What the monster can do this week. */
export function allowedActions(state: GameState): { locked: boolean; restOnly: boolean; journeyRunning: boolean; reason: string | null } {
  if (!state.monster) return { locked: true, restOnly: false, journeyRunning: false, reason: 'noMonster' }
  const a = availability(state.monster)
  return { locked: a.locked, restOnly: a.restOnly, journeyRunning: state.journey !== null, reason: a.reason }
}

export interface ResolveResult {
  state: GameState
  events: WeekEvent[]
  drill: DrillResult | null
  journey: JourneyWeekResult | null
}

/** Phase 3: the one action of the week. */
export function resolveAction(input: GameState, action: WeekAction, rng: Rng): ResolveResult {
  const state = structuredClone(input)
  const events: WeekEvent[] = [{ kind: 'phase', phase: 'action' }]
  const none: ResolveResult = { state, events, drill: null, journey: null }
  const m = state.monster
  if (!m || state.ended) return none

  const avail = availability(m)
  if (avail.locked) {
    events.push({ kind: 'locked', reason: avail.reason ?? 'locked' })
    return none
  }

  if (state.journey) {
    const r = journeyWeek(m, state.journey, rng)
    state.monster = r.monster
    state.journey = r.progress
    events.push({ kind: 'journeyWeek', result: r.result })
    if (isJourneyDone(r.progress)) {
      events.push({ kind: 'journeyDone', progress: r.progress })
      state.journey = null
    }
    return { state, events, drill: null, journey: r.result }
  }

  let chosen = action
  if (avail.restOnly && chosen.kind !== 'rest') {
    events.push({ kind: 'forcedRest', reason: avail.reason ?? 'restOnly' })
    chosen = { kind: 'rest' }
  }

  switch (chosen.kind) {
    case 'drill': {
      const drill = DRILL_BY_ID[chosen.drill]
      if (!drill || (drill.needsTrainingYard && !state.upgrades.trainingYard)) {
        events.push({ kind: 'invalidAction', reason: 'drillUnavailable' })
        return none
      }
      const r = resolveDrill(m, chosen.drill, rng, { trainingYard: state.upgrades.trainingYard })
      state.monster = r.monster
      state.money += r.result.pay
      events.push({ kind: 'drill', result: r.result })
      return { state, events, drill: r.result, journey: null }
    }
    case 'rest': {
      const r = restMonster(m, { beddingBonus: charmValue(state.inventory, 'bedding') })
      state.monster = r.monster
      events.push({ kind: 'rest', fatigue: r.fatigue, stress: r.stress })
      return { state, events, drill: null, journey: null }
    }
    case 'play': {
      const r = playMonster(m)
      state.monster = r.monster
      events.push({ kind: 'play', fatigue: r.fatigue, stress: r.stress })
      return { state, events, drill: null, journey: null }
    }
    case 'journey': {
      const month = dateOf(state.week).month
      if (!isSiteOpen(chosen.site, month) || !canEnterSite(m, chosen.site).ok) {
        events.push({ kind: 'invalidAction', reason: 'siteClosed' })
        return none
      }
      state.money -= JOURNEY.cost
      events.push({ kind: 'journeyStart', site: chosen.site, cost: JOURNEY.cost })
      const r = journeyWeek(m, startJourney(chosen.site), rng)
      state.monster = r.monster
      state.journey = isJourneyDone(r.progress) ? null : r.progress
      events.push({ kind: 'journeyWeek', result: r.result })
      return { state, events, drill: null, journey: r.result }
    }
    case 'none':
      return none
  }
}

/** The praise / scold / skip prompt after a drill or truancy. */
export function reactToDrill(input: GameState, outcome: DrillOutcome, reaction: Reaction): GameState {
  const state = structuredClone(input)
  const m = state.monster
  if (!m) return input
  state.monster = applyReaction(m, outcome, reaction)
  return state
}

/** Phase 4: aging, checks, next week's weather, autosave; then the calendar moves on. */
export function endWeek(input: GameState, rng: Rng): { state: GameState; events: WeekEvent[] } {
  const state = structuredClone(input)
  const events: WeekEvent[] = [{ kind: 'phase', phase: 'endOfWeek' }]
  if (state.monster && !state.ended) {
    const tick = endOfWeekTick(state.monster, state.difficulty, rng)
    state.monster = tick.monster
    if (tick.fees > 0) {
      state.money -= tick.fees
      events.push({ kind: 'fees', amount: tick.fees })
    }
    for (const e of tick.events) {
      events.push({ kind: 'aging', event: e })
      if (e.kind === 'endOfLife') state.ended = e.how
    }
  }
  state.week += 1
  state.weather = rollWeather(rng, dateOf(state.week).month)
  events.push({ kind: 'weather', weather: state.weather })
  events.push({ kind: 'autosave' })
  return { state, events }
}

/** How a player (or a scripted policy) answers the week's prompts. */
export interface WeekPolicy {
  /** The monthly food choice (only consulted in week 1 of a month). */
  food?(state: GameState): FoodId | undefined
  request(state: GameState, request: MonsterRequest): boolean
  /** Free actions before the main action (using items, for example). Returns the new state. */
  beforeAction?(state: GameState): GameState
  action(state: GameState): WeekAction
  reaction(state: GameState, result: DrillResult): Reaction
}

/** A whole week, in order. */
export function runWeek(input: GameState, rng: Rng, policy: WeekPolicy): { state: GameState; events: WeekEvent[] } {
  const events: WeekEvent[] = []
  const started = startWeek(input, rng, isMonthStart(input.week) ? policy.food?.(input) : undefined)
  let state = started.state
  events.push(...started.events)

  let forced: WeekAction | null = null
  if (started.request) {
    const answered = respondToRequest(state, started.request, policy.request(state, started.request))
    state = answered.state
    forced = answered.forcedAction
    events.push(...answered.events)
  }

  if (policy.beforeAction) state = policy.beforeAction(state)

  const resolved = resolveAction(state, forced ?? policy.action(state), rng)
  state = resolved.state
  events.push(...resolved.events)
  if (resolved.drill) {
    const reaction = policy.reaction(state, resolved.drill)
    state = reactToDrill(state, resolved.drill.outcome, reaction)
    events.push({ kind: 'reaction', reaction })
  }

  const ended = endWeek(state, rng)
  events.push(...ended.events)
  return { state: ended.state, events }
}
