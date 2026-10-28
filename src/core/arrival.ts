import { ARRIVAL, RANGES } from '../data/tuning.ts'
import { clamp } from './mathx.ts'
import { addCondition, loyaltyOf } from './monster.ts'
import type { GameState } from './state.ts'

/**
 * GAME_DESIGN §6.10 arriving at the ranch. Real time is measured in the UI (core never reads the clock) and passed
 * in as `lastSeenAt` (the last time the game was on screen) and `now`, both in ms.
 * - A day away, your monster is sad; two days, the ranch looks abandoned; four days, it has gone (passed away; on
 *   Gentle it leaves for the wild). Each brings real consequences. Vacation mode turns this off.
 * - Otherwise, back after a couple of hours (at most twice a day), your monster comes to say hello, and you can pet
 *   it or give it a treat.
 * The away clock only runs once it is armed: on a save's first launch of this version (after Wren explains the
 * rule), for a new game, after an import, and after Vacation mode is turned off.
 */

export type Arrival = 'none' | 'greet' | 'sad' | 'abandoned' | 'gone'
export type AwayStage = 'sad' | 'abandoned' | 'gone'
export type GreetMood = 'happy' | 'curious' | 'aloof'

/** Is there an active monster on the ranch for the clock to matter to? */
function hasMonster(state: GameState): boolean {
  return state.monster !== null && state.ended === null
}

/** How long the player has been away, or null when the clock isn't running (or ran backwards). */
export function awayMs(state: GameState, lastSeenAt: number | null, now: number): number | null {
  const armed = state.away.armedAt
  if (armed === null) return null
  const since = Math.max(armed, lastSeenAt ?? armed)
  const ms = now - since
  return Number.isFinite(ms) && ms >= 0 ? ms : null
}

/** The away stage for this much time away (vacation is checked by the caller). */
export function awayStage(ms: number): AwayStage | null {
  if (ms >= ARRIVAL.goneMs) return 'gone'
  if (ms >= ARRIVAL.abandonedMs) return 'abandoned'
  if (ms >= ARRIVAL.sadMs) return 'sad'
  return null
}

/** What greets the player on opening the game, or coming back to it. */
export function arrivalFor(state: GameState, lastSeenAt: number | null, now: number): Arrival {
  if (!hasMonster(state)) return 'none'
  const ms = awayMs(state, lastSeenAt, now)
  if (ms === null) return 'none'
  const stage = state.settings.vacation ? null : awayStage(ms)
  if (stage) return stage
  const last = state.away.lastGreetAt
  const greetedRecently = last !== null && now - last >= 0 && now - last < ARRIVAL.greetEveryMs
  return ms >= ARRIVAL.greetAfterMs && !greetedRecently ? 'greet' : 'none'
}

/** Starts the away clock from `now` (a first launch of this version, a new game, an import, vacation ending). */
export function armAway(input: GameState, now: number): GameState {
  return { ...input, away: { ...input.away, armedAt: now } }
}

/** How a monster greets you, by loyalty: runs up happy, trots over curious, or stays put. */
export function greetMood(loyalty: number): GreetMood {
  if (loyalty >= ARRIVAL.greetLoyalty.happy) return 'happy'
  if (loyalty >= ARRIVAL.greetLoyalty.curious) return 'curious'
  return 'aloof'
}

export function greetMoodOf(state: GameState): GreetMood {
  return greetMood(state.monster ? loyaltyOf(state.monster) : 0)
}

/** Records that the monster said hello (so the next greeting waits). */
export function noteGreeting(input: GameState, now: number): GameState {
  return { ...input, away: { ...input.away, lastGreetAt: now } }
}

/** A pat on the head: a little fonder, a little calmer. Free. */
export function petMonster(input: GameState): GameState {
  if (!input.monster) return input
  const state = structuredClone(input)
  const m = state.monster!
  m.spoil = addCondition(m.spoil, ARRIVAL.pet.spoil)
  m.stress = addCondition(m.stress, ARRIVAL.pet.stress)
  return state
}

/** A treat from Basil's biscuit tin (20G): fonder and calmer still. */
export function giveTreat(input: GameState): { state: GameState; refused: 'noMonster' | 'money' | null } {
  if (!input.monster) return { state: input, refused: 'noMonster' }
  if (input.money < ARRIVAL.treat.price) return { state: input, refused: 'money' }
  const state = structuredClone(input)
  const m = state.monster!
  state.money -= ARRIVAL.treat.price
  m.spoil = addCondition(m.spoil, ARRIVAL.treat.spoil)
  m.stress = addCondition(m.stress, ARRIVAL.treat.stress)
  return { state, refused: null }
}

export interface AwayResult {
  state: GameState
  stage: AwayStage
  /** The changes to show on the results card (signed). */
  changes: { stress: number; spoil: number; fear: number; lifespanWeeks: number; sickWeeks: number }
}

/**
 * The consequences of staying away. Sad: stress up, affection and respect down, the bond boost gone. Abandoned:
 * worse, two weeks of lifespan lost, and a week sick (rest only). Gone: the life ends (`ended` = 'neglected', or
 * 'wandered' on Gentle, where monsters never die) and the Farewell follows. The clock restarts from `now`.
 */
export function applyAway(input: GameState, stage: AwayStage, now: number): AwayResult {
  const state = structuredClone(input)
  state.away = { armedAt: now, lastGreetAt: now }
  const none = { stress: 0, spoil: 0, fear: 0, lifespanWeeks: 0, sickWeeks: 0 }
  const m = state.monster
  if (!m || state.ended) return { state, stage, changes: none }
  if (stage === 'gone') {
    state.ended = state.difficulty === 'Gentle' ? 'wandered' : 'neglected'
    state.expedition = null
    return { state, stage, changes: none }
  }
  const p = stage === 'sad' ? { ...ARRIVAL.sad, lifespanWeeks: 0, sickWeeks: 0 } : ARRIVAL.abandoned
  const before = { stress: m.stress, spoil: m.spoil, fear: m.fear, life: m.lifespanTotal, sick: m.status.sickWeeks }
  m.stress = addCondition(m.stress, p.stress)
  m.spoil = addCondition(m.spoil, p.spoil)
  m.fear = addCondition(m.fear, p.fear)
  m.status.bondPct = 100
  if (p.lifespanWeeks > 0) m.lifespanTotal = clamp(m.lifespanTotal - p.lifespanWeeks, RANGES.lifespan.min, RANGES.lifespan.max)
  if (p.sickWeeks > 0) m.status.sickWeeks = Math.max(m.status.sickWeeks, p.sickWeeks)
  const changes = {
    stress: m.stress - before.stress,
    spoil: m.spoil - before.spoil,
    fear: m.fear - before.fear,
    lifespanWeeks: m.lifespanTotal - before.life,
    sickWeeks: m.status.sickWeeks - before.sick,
  }
  return { state, stage, changes }
}

/** Turns Vacation mode on or off. Turning it off restarts the away clock, so the time away doesn't count. */
export function setVacation(input: GameState, on: boolean, now: number): GameState {
  const state = { ...input, settings: { ...input.settings, vacation: on } }
  return on ? state : armAway(state, now)
}
