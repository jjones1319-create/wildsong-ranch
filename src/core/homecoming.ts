import { FREEZER, HOMECOMING, LIFESPAN, RANGES } from '../data/tuning.ts'
import { newRanchmate } from './creation.ts'
import { penRoom, seedFarm } from './farm.ts'
import { ownedIds, placeOnRanch, recordInEncyclopedia } from './legacy.ts'
import { clamp } from './mathx.ts'
import { weeksLeft, type Monster } from './monster.ts'
import type { GameState, MemorialCause, MemorialEntry } from './state.ts'

/**
 * GAME_DESIGN §6.10 the one-time v16 homecoming. Every monster that ran away from the away clock ("Gone": `neglected`,
 * or `wandered` on Gentle) comes back exactly as it was, because the Memorial kept the whole monster. It runs once,
 * from validateSave after tidyGame (the one path every load and import takes), while `homecoming.status` is `due`.
 * Pure and deterministic. Old-age passings and retirements are left alone.
 */

export type WelcomeWhere = 'star' | 'pen' | 'freezer'

const RUNAWAY: readonly MemorialCause[] = ['neglected', 'wandered']

/**
 * A runaway's welcome: no illness, no missing or clinic timers (nor a cocoon that can never open), rested, calm,
 * at least HOMECOMING.minWeeksLeft weeks of life, and its lifespan warnings re-armed to match.
 */
export function returnHome(input: Monster): Monster {
  const m = structuredClone(input)
  m.status.sickWeeks = 0
  m.status.missingWeeks = 0
  m.status.clinicWeeks = 0
  m.status.cocoonWeeks = 0
  m.fatigue = 0
  m.stress = Math.min(m.stress, HOMECOMING.stress)
  if (weeksLeft(m) < HOMECOMING.minWeeksLeft) m.lifespanTotal = clamp(m.ageWeeks + HOMECOMING.minWeeksLeft, RANGES.lifespan.min, RANGES.lifespan.max)
  const left = weeksLeft(m)
  m.status.warnedQuarterLife = left * 100 <= LIFESPAN.warnAtRemainingPct * m.lifespanTotal
  m.status.warned48 = left <= LIFESPAN.warnAtWeeksLeft[0]!
  m.status.warned10 = left <= LIFESPAN.warnAtWeeksLeft[1]!
  return m
}

/** The Memorial entries that come home: per monster id only its newest entry, when that was a runaway and the id isn't owned. */
export function runawaysToWelcome(state: GameState): MemorialEntry[] {
  const owned = ownedIds(state)
  const seen = new Set<string>()
  const out: MemorialEntry[] = []
  for (const e of state.memorial) {
    if (seen.has(e.monster.id)) continue
    seen.add(e.monster.id)
    if (RUNAWAY.includes(e.cause) && !owned.has(e.monster.id)) out.push(e)
  }
  return out
}

/**
 * Brings the runaways home, once. In order: a runaway still waiting for its Farewell is cancelled and stays as the
 * star; then each runaway on the Memorial wall (newest first) takes the empty ranch, else a free pen, else the
 * Freezer up to FREEZER.hardMax, else stays on the wall (never lost). Returnees leave the Memorial; their Heartstones
 * and titles stay. Then the farm is seeded from the save's history, Ines writes when anyone came home, and the away
 * clock is un-armed so nobody can run off again on this first launch.
 */
export function welcomeHome(input: GameState): GameState {
  if (input.homecoming.status !== 'due') return input
  const state = structuredClone(input)
  const welcome: string[] = []
  if (state.monster && state.ended && RUNAWAY.includes(state.ended)) {
    state.ended = null
    state.monster = returnHome(state.monster)
    welcome.push(state.monster.id)
  }
  for (const entry of runawaysToWelcome(state)) {
    const m = returnHome(entry.monster)
    const where = homeFor(state)
    if (!where) continue
    if (where === 'star') placeOnRanch(state, m)
    else if (where === 'pen') state.ranchmates.push(newRanchmate(m))
    else state.freezer.push(m)
    recordInEncyclopedia(state, m)
    state.memorial = state.memorial.filter((e) => e !== entry)
    welcome.push(m.id)
  }
  state.farm = seedFarm(state, state.farm.pensBought)
  if (welcome.length > 0) state.mail.unshift({ id: `${state.week}-homecoming`, week: state.week, kind: 'homecoming', ref: String(welcome.length), read: false })
  state.away = { armedAt: null, lastGreetAt: state.away.lastGreetAt }
  state.homecoming = { status: 'done', welcome }
  return state
}

/** Where the next returnee goes: the empty ranch, a free pen, the Freezer (up to hardMax), or nowhere. */
function homeFor(state: GameState): WelcomeWhere | null {
  if (!state.monster && !state.ended) return 'star'
  if (penRoom(state) > 0) return 'pen'
  if (state.freezer.length < FREEZER.hardMax) return 'freezer'
  return null
}

/** Where a welcomed monster is living now (for the card's line), or null when it is no longer owned. */
export function welcomeWhere(state: GameState, id: string): WelcomeWhere | null {
  if (state.monster?.id === id) return 'star'
  if (state.ranchmates.some((r) => r.monster.id === id)) return 'pen'
  if (state.freezer.some((m) => m.id === id)) return 'freezer'
  return null
}

/** The card was closed: the welcome list empties (the homecoming itself never runs again). */
export function dismissHomecoming(input: GameState): GameState {
  if (input.homecoming.welcome.length === 0) return input
  return { ...input, homecoming: { status: 'done', welcome: [] } }
}
