import { ODD_JOBS } from '../data/tuning.ts'
import { clamp } from './mathx.ts'
import { createRng } from './rng.ts'
import type { GameState } from './state.ts'

/**
 * CONTENT §13 Odd Jobs: Turnip Sort. The round itself runs in the UI (it is a 30-second real-time game),
 * but what slides down the chute, the ramp and the pay are rules: the item sequence comes from a seed the
 * game's RNG hands out, so a round can be replayed in a test, and the pay is ±5G per item, capped at 150G,
 * once per in-game week.
 */

export type Produce = 'turnip' | 'rock'

export function canPlayOddJob(state: GameState): { ok: true } | { ok: false; reason: 'noMonster' | 'played' } {
  if (!state.monster || state.ended) return { ok: false, reason: 'noMonster' }
  if (state.oddJobWeek !== null && state.oddJobWeek === state.week) return { ok: false, reason: 'played' }
  return { ok: true }
}

/** +5G per correct item, −5G per mix-up, never below 0, capped at 150G. */
export function turnipPay(correct: number, wrong: number): number {
  return clamp(correct * ODD_JOBS.payPerCorrect - wrong * ODD_JOBS.payPerWrong, 0, ODD_JOBS.cap)
}

export function applyOddJob(input: GameState, correct: number, wrong: number): { state: GameState; pay: number; refused: 'noMonster' | 'played' | null } {
  const can = canPlayOddJob(input)
  if (!can.ok) return { state: input, pay: 0, refused: can.reason }
  const pay = turnipPay(Math.max(0, Math.floor(correct)), Math.max(0, Math.floor(wrong)))
  const state = structuredClone(input)
  state.money += pay
  state.oddJobWeek = state.week
  return { state, pay, refused: null }
}

/** The items of a round, from a seed. */
export function turnipSequence(seed: number, count = ODD_JOBS.items): Produce[] {
  const rng = createRng(seed)
  const out: Produce[] = []
  for (let i = 0; i < count; i++) out.push(rng.chance(ODD_JOBS.turnipPct) ? 'turnip' : 'rock')
  return out
}

/** The ramp: how long an item stays in reach, from the start value to the end value over the round. */
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
