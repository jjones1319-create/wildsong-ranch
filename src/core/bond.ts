import { KEEPSAKE_BY_ID } from '../data/keepsakes.ts'
import { BOND } from '../data/tuning.ts'
import { KEEPSAKE_IDS, type BondActivity, type KeepsakeId } from '../data/types.ts'
import { addCondition, type Monster } from './monster.ts'
import { createRng } from './rng.ts'

/**
 * GAME_DESIGN §6.9 the Bond week: a game of fetch, hide-and-seek or a shopping trip with your monster, as the
 * week's one action. It calms the monster and builds its affection, and boosts the next weeks' drill gains (×1.75,
 * then 0.25 less each week). A shopping trip finds a keepsake it loves; bought, it stays on the ranch and takes a
 * little stress off every week. The games run in the UI; their score and the purchase come here.
 */

export interface BondEffect {
  stress: number
  spoil: number
  fatigue: number
}

/** The score a Bond week counts: the game's (0–5), or the shopping trip's fixed one. */
export function bondScore(activity: BondActivity, score: number): number {
  if (activity === 'shop') return BOND.shopScore
  return Number.isFinite(score) ? Math.min(BOND.maxScore, Math.max(0, Math.floor(score))) : 0
}

/** What a Bond week does to the monster: calmer, fonder (more so with a gift), a little tired. */
export function bondEffect(activity: BondActivity, score: number, bought: boolean): BondEffect {
  const s = bondScore(activity, score)
  return {
    stress: -(BOND.stressRelief.base + BOND.stressRelief.perPoint * s),
    spoil: BOND.spoil.base + BOND.spoil.perPoint * s + (bought ? BOND.buySpoil : 0),
    fatigue: BOND.fatigue,
  }
}

/** Applies a Bond week to the monster: the effect, and the training boost set to its top. */
export function bondMonster(input: Monster, activity: BondActivity, score: number, bought: boolean): { monster: Monster; effect: BondEffect } {
  const m = structuredClone(input)
  const effect = bondEffect(activity, score, bought)
  m.stress = addCondition(m.stress, effect.stress)
  m.spoil = addCondition(m.spoil, effect.spoil)
  m.fatigue = addCondition(m.fatigue, effect.fatigue)
  m.status.bondPct = BOND.boostPct
  return { monster: m, effect }
}

/** One week on: the boost fades by 0.25, down to none (after every week that isn't a Bond week). */
export function fadeBond(input: Monster): Monster {
  if (input.status.bondPct <= 100) return input
  const m = structuredClone(input)
  m.status.bondPct = Math.max(100, m.status.bondPct - BOND.decayPct)
  return m
}

/** The keepsake a shopping trip finds, from a seed the game's RNG hands out: one the ranch doesn't have yet (null once it has them all). */
export function shopFind(seed: number, owned: readonly KeepsakeId[]): KeepsakeId | null {
  const left = KEEPSAKE_IDS.filter((id) => !owned.includes(id))
  if (left.length === 0) return null
  return left[createRng(seed).nextInt(0, left.length - 1)]!
}

/** Can the ranch buy this keepsake now? */
export function canBuyKeepsake(money: number, owned: readonly KeepsakeId[], id: KeepsakeId): boolean {
  const k = KEEPSAKE_BY_ID[id]
  return k !== undefined && !owned.includes(id) && money >= k.price
}

/** The stress the ranch's keepsakes take off at the end of each week. */
export function keepsakeStress(owned: readonly KeepsakeId[]): number {
  return Math.min(BOND.keepsakeStressMax, owned.length * BOND.keepsakeStress)
}

/** Hide-and-seek: the haystack the monster hides behind each round, from a seed the game's RNG hands out. */
export function hideSpots(seed: number): number[] {
  const rng = createRng(seed)
  return Array.from({ length: BOND.hide.rounds }, () => rng.nextInt(0, BOND.hide.spots - 1))
}

/** Fetch: a throw lands in reach when the power bar stops in the green zone (percent of the bar). */
export function fetchCaught(powerPct: number): boolean {
  return powerPct >= BOND.fetch.zone.from && powerPct <= BOND.fetch.zone.to
}
