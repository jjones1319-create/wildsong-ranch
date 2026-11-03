import { BATTLE } from '../../data/tuning.ts'
import type { Family } from '../../data/types.ts'
import { divRound } from '../mathx.ts'

/**
 * docs/BATTLE_3D.md §3: the duel's pace. The owner (Nov 3) asked for attacks about 20% faster, so in the duel a
 * technique's wind-up and its recovery are `BATTLE.duel.paceTicksPct` of their line-mode lengths, rounded to whole
 * ticks (never below one). Line mode never calls these, so line battles replay bit for bit.
 */

/** A duel length in ticks at the duel's pace. */
export function duelPaced(ticks: number): number {
  return Math.max(1, divRound(ticks * BATTLE.duel.paceTicksPct, 100))
}

/** The wind-up of a technique of this family in the duel: fired now, it lands this many ticks later. */
export function duelWindup(family: Family): number {
  return duelPaced(BATTLE.duel.windup[family])
}
