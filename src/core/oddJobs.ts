import { ODD_JOBS } from '../data/tuning.ts'
import { clamp } from './mathx.ts'
import { createRng } from './rng.ts'
import type { GameState } from './state.ts'

/**
 * CONTENT §13 Odd Jobs: Turnip Sort. The round itself runs in the UI (it is a real-time game), but what slides
 * down the chute, the ramp, overtime and the pay are rules: the items come from a seed the game's RNG hands out,
 * so a round can be replayed in a test. The first phase is thirty seconds of turnips and rocks at ±5G an item;
 * reaching 150G inside it starts overtime (no clock, weeds join, each item's window shrinks), which ends on a
 * missed item or the second mix-up. Overtime mix-ups are strikes, not pay, so the 150G stays banked. No pay cap;
 * one paid play per in-game week. Practice pays nothing but keeps the best.
 */

export type Produce = 'turnip' | 'rock' | 'weed'
export type Bin = 'basket' | 'rocks' | 'compost'

const BIN_OF: Record<Produce, Bin> = { turnip: 'basket', rock: 'rocks', weed: 'compost' }

export function binFor(item: Produce): Bin {
  return BIN_OF[item]
}

export function canPlayOddJob(state: GameState): { ok: true } | { ok: false; reason: 'noMonster' | 'played' } {
  if (!state.monster || state.ended) return { ok: false, reason: 'noMonster' }
  if (state.oddJobWeek !== null && state.oddJobWeek === state.week) return { ok: false, reason: 'played' }
  return { ok: true }
}

function count(n: number): number {
  return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0
}

/** +5G per correct item, −5G per first-phase mix-up, never below 0, with no cap. */
export function turnipPay(correct: number, wrong: number): number {
  return Math.max(0, count(correct) * ODD_JOBS.payPerCorrect - count(wrong) * ODD_JOBS.payPerWrong)
}

/** True once the first phase's pay reaches the overtime mark. */
export function inOvertime(correct: number, wrong: number): boolean {
  return turnipPay(correct, wrong) >= ODD_JOBS.overtime.atPay
}

export interface TurnipResult {
  state: GameState
  pay: number
  /** True when this game set a new best (most items sorted). */
  newBest: boolean
  refused: 'noMonster' | 'played' | null
}

/**
 * Settles a finished round: `correct` counts every item sorted right (overtime included), `wrong` only the
 * first phase's mix-ups. A paid play pays and stamps the week; practice only records the best.
 */
export function applyOddJob(input: GameState, correct: number, wrong: number, practice = false): TurnipResult {
  if (!input.monster || input.ended) return { state: input, pay: 0, newBest: false, refused: 'noMonster' }
  if (!practice) {
    const can = canPlayOddJob(input)
    if (!can.ok) return { state: input, pay: 0, newBest: false, refused: can.reason }
  }
  const sorted = count(correct)
  const state = structuredClone(input)
  let pay = 0
  if (!practice) {
    pay = turnipPay(sorted, wrong)
    state.money += pay
    state.oddJobWeek = state.week
  }
  const newBest = sorted > state.turnipBest
  if (newBest) state.turnipBest = sorted
  return { state, pay, newBest, refused: null }
}

export interface TurnipDealer {
  /** The next item down the chute; `overtime` switches to the three-kind stream. */
  next(overtime: boolean): Produce
}

/**
 * Deals a round's items from a seed, endlessly. The first phase is turnips and rocks (60 % turnips). Overtime
 * draws from its own stream, so its items don't depend on when overtime began; its first item is always a weed,
 * to teach the Compost heap.
 */
export function turnipDealer(seed: number): TurnipDealer {
  const first = createRng(seed)
  const late = createRng((seed ^ ODD_JOBS.overtime.salt) >>> 0)
  const mix = ODD_JOBS.overtime.mixPct
  let lateDealt = 0
  return {
    next(overtime: boolean): Produce {
      if (!overtime) return first.chance(ODD_JOBS.turnipPct) ? 'turnip' : 'rock'
      lateDealt += 1
      if (lateDealt === 1) return 'weed'
      const roll = late.nextInt(0, 99)
      return roll < mix.turnip ? 'turnip' : roll < mix.turnip + mix.rock ? 'rock' : 'weed'
    },
  }
}

/** The first phase's ramp: how long an item stays in reach, from the start value to the end value over the 30 seconds. */
export function slideMsAt(elapsedMs: number): number {
  const total = ODD_JOBS.seconds * 1000
  const t = clamp(elapsedMs, 0, total)
  return Math.round(ODD_JOBS.slideMs.start + ((ODD_JOBS.slideMs.end - ODD_JOBS.slideMs.start) * t) / total)
}

export function gapMsAt(elapsedMs: number): number {
  const total = ODD_JOBS.seconds * 1000
  const t = clamp(elapsedMs, 0, total)
  return Math.round(ODD_JOBS.gapMs.start + ((ODD_JOBS.gapMs.end - ODD_JOBS.gapMs.start) * t) / total)
}

/** Overtime's window for its `index`-th item (0-based): shorter by a step each item, never under the floor. */
export function overtimeWindowMs(index: number): number {
  const w = ODD_JOBS.overtime.windowMs
  return Math.max(w.floor, w.start - w.step * Math.max(0, Math.floor(index)))
}
