import { SPECIALS } from '../../data/tuning.ts'
import type { Rng } from '../rng.ts'
import type { ActiveSpecial, BattleEvent, FighterState, SpecialKind } from './types.ts'

/**
 * GAME_DESIGN §12.7 specials. Each activates at most once per battle; only one is active at a time, except
 * Last Stand, which is instant. A trigger is rolled every time its condition occurs until it activates.
 */

export interface SpecialMods {
  dealtPct: number
  takenPct: number
  witherDealtPct: number
  regenPct: number
  costPct: number
  critMul: number
  /** Rage: enemies get +1 advantage against you. */
  givesAdvantage: boolean
  /** Composure: the opponent's hits suffer a disadvantage. */
  givesDisadvantage: boolean
}

const NONE: SpecialMods = { dealtPct: 100, takenPct: 100, witherDealtPct: 100, regenPct: 100, costPct: 100, critMul: 1, givesAdvantage: false, givesDisadvantage: false }

export function specialMods(s: ActiveSpecial | null): SpecialMods {
  if (!s) return NONE
  switch (s.kind) {
    case 'valor':
      return { ...NONE, dealtPct: SPECIALS.valor.dealtPct }
    case 'rage':
      return { ...NONE, witherDealtPct: SPECIALS.rage.witherPct, regenPct: SPECIALS.rage.regenPct, givesAdvantage: true }
    case 'bulwark':
      return { ...NONE, takenPct: SPECIALS.bulwark.takenPct, regenPct: SPECIALS.bulwark.regenPct, dealtPct: SPECIALS.bulwark.dealtPct }
    case 'clutch':
      return { ...NONE, critMul: SPECIALS.clutch.critMul }
    case 'composure':
      return { ...NONE, costPct: SPECIALS.composure.costPct, takenPct: SPECIALS.composure.takenPct, givesDisadvantage: true }
    case 'lastStand':
      return NONE
  }
}

/** Can this special still be rolled? Used ones never return; a timed special blocks every other timed one. */
export function canTrigger(f: FighterState, kind: SpecialKind): boolean {
  if (f.usedSpecials.includes(kind)) return false
  if (kind === 'lastStand') return true
  return f.special === null
}

/** Rolls `chancePct` and, on success, activates the special and logs it. Returns whether it fired. */
export function tryTrigger(f: FighterState, kind: SpecialKind, chancePct: number, rng: Rng, tick: number, log: BattleEvent[]): boolean {
  if (!canTrigger(f, kind) || chancePct <= 0) return false
  if (!rng.chance(Math.min(100, chancePct))) return false
  f.usedSpecials = [...f.usedSpecials, kind]
  if (kind !== 'lastStand') f.special = { kind, ticksLeft: kind === 'clutch' ? -1 : SPECIALS.durationTicks }
  log.push({ t: tick, kind: 'special', side: f.side, special: kind })
  return true
}

/* ---------- the trigger chances (percent, may be fractional) ---------- */

export function lastStandPct(f: FighterState): number {
  const s = SPECIALS.lastStand
  return Math.min(s.cap, f.guts / s.gutsDiv + f.loyalty / s.loyaltyDiv + f.stats.DEF / s.defDiv)
}

/** After taking a hit: nature ≥ +20 and HP ≤ 30 %. */
export function valorPct(f: FighterState): number {
  const s = SPECIALS.valor
  if (f.nature < s.natureMin || f.hp * 100 > f.maxHp * s.hpPctMax) return 0
  return Math.min(s.cap, f.nature / s.natureDiv)
}

/** After being withered: nature ≤ −20. */
export function ragePct(f: FighterState, wither: number): number {
  const s = SPECIALS.rage
  if (f.nature > s.natureMax || wither <= 0) return 0
  return Math.min(s.cap, wither / s.witherDiv + Math.abs(f.nature) / s.natureDiv)
}

/** Three hits taken in a row. */
export function bulwarkPct(f: FighterState): number {
  const s = SPECIALS.bulwark
  if (f.hitsTakenRow < s.hitsInRow) return 0
  return (100 - f.guts) / s.div
}

/** The last ten seconds, behind on HP %: (gap in %) / 2. */
export function clutchPct(f: FighterState, opp: FighterState): number {
  const mine = (f.hp * 1000) / f.maxHp
  const theirs = (opp.hp * 1000) / opp.maxHp
  if (mine >= theirs) return 0
  return (theirs - mine) / 10 / SPECIALS.clutch.div
}

/** Four hits landed or dodges in a row. */
export function composurePct(f: FighterState): number {
  const s = SPECIALS.composure
  if (f.successRow < s.streak) return 0
  return (100 - f.guts) / s.div
}

/** Ticks the active special down; Clutch (−1) lasts until the end. */
export function tickSpecial(f: FighterState): void {
  if (!f.special || f.special.ticksLeft < 0) return
  f.special.ticksLeft -= 1
  if (f.special.ticksLeft <= 0) f.special = null
}
