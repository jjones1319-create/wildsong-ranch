import { BATTLE, BATTLE_TRAITS, DISTRACTION_POINTS } from '../../data/tuning.ts'
import type { StatKey, Stats, TechType } from '../../data/types.ts'
import { clamp, divRound } from '../mathx.ts'

/**
 * GAME_DESIGN §12.5 in integer fixed-point. Percentages are tenths (500 = 50.0 %), multipliers thousandths
 * (1000 = ×1), positions centi-units. The one root in the design (`^0.5`) is an integer square root, so the
 * reference tables come out the same on every engine. Rounding is half to even (divRound), like the tables.
 */

/** Floor of the square root of a non-negative integer (Newton's method; exact for safe integers). */
export function isqrt(n: number): number {
  if (n <= 0) return 0
  let x = Math.floor(Math.sqrt(n))
  // Correct any floating-point slip in the seed.
  while (x * x > n) x -= 1
  while ((x + 1) * (x + 1) <= n) x += 1
  return x
}

/** §12.5 form: round monsters are slower but sturdier. f = form/100 → SPD′ = SPD·(1 − 0.2f), DEF′ = DEF·(1 + 0.2f). */
export function formAdjusted(stats: Stats, form: number): { spd: number; def: number } {
  const span = divRound(100 * 100, BATTLE.form.pct) // 500 when the swing is 20 %
  return { spd: divRound(stats.SPD * (span - form), span), def: divRound(stats.DEF * (span + form), span) }
}

/** §12.3 walking speed per tick in centi-units: (70 + 50·SPD/999) units per second, SPD counted up to 1500 (v1.11). */
export function walkPerTick(spd: number): number {
  const w = BATTLE.walk
  const unitsPerSecondXScale = w.base * w.spdScale + w.perSpd * Math.min(spd, w.spdLimit)
  return divRound(unitsPerSecondXScale * 100, w.spdScale * BATTLE.ticksPerSecond)
}

/** §12.1 bands from the gap in units: 1 Close … 4 Far, 5 out of range. */
export function bandOf(gap: number): number {
  const ends = BATTLE.bandEnds
  for (let i = 0; i < ends.length; i++) if (gap < ends[i]!) return i + 1
  return ends.length + 1
}

export function bandCentre(band: number): number {
  return BATTLE.bandCentres[clamp(band, 1, 4) - 1]!
}

export interface HitInput {
  techHit: number
  skiAtt: number
  /** Defender SPD′, plus Nimble's bonus when it applies. */
  spdDef: number
  gutsAtt: number
  gutsDef: number
  /** Flat bonuses from traits (Glow, En Garde, Underdog), in whole percent. */
  bonus: number
  /** Advantages (defender distracted, Rage) and disadvantage (defender's Composure). */
  advantages: number
  disadvantage: boolean
}

/** Hit chance in tenths of a percent, clamped 5–95 %. */
export function hitTenths(i: HitInput): number {
  const h = BATTLE.hit
  let t = h.base * 10 + i.techHit * 10 + i.bonus * 10 + divRound((i.skiAtt - i.spdDef) * 10, h.skillDivisor) + divRound((i.gutsAtt - 50) * 10, h.gutsDivisor) - divRound((i.gutsDef - 50) * 10, h.gutsDivisor)
  t = clamp(t, h.min * 10, h.max * 10)
  if (i.advantages >= 2) t = 1000 - divRound((1000 - t) * (1000 - t) * (1000 - t), 1_000_000)
  else if (i.advantages === 1) t = 1000 - divRound((1000 - t) * (1000 - t), 1000)
  if (i.disadvantage) t = divRound(t * t, 1000)
  return clamp(t, h.min * 10, h.max * 10)
}

/** k(R) = 0.15 + 0.03·(R − 6), in thousandths. */
export function gutsK(rate: number): number {
  return BATTLE.damage.kBase * 10 + BATTLE.damage.kPerRate * 10 * (rate - BATTLE.damage.kRateFrom)
}

/** gAtt = 1 + (G − 50)/100 · k, in thousandths. */
export function gutsAttackMul(guts: number, rate: number): number {
  return 1000 + divRound((guts - 50) * gutsK(rate), 100)
}

/** gDef = 1 − (G − 50)/100 · k · 0.5, in thousandths. */
export function gutsDefenseMul(guts: number, rate: number): number {
  return 1000 - divRound((guts - 50) * gutsK(rate), 100 * BATTLE.damage.gDefHalf)
}

export interface DamageInput {
  force: number
  /** Attacker's POW or INT. */
  a: number
  /** Defender's DEF′. */
  defDef: number
  /** Defender's same-type stat (POW against a POW technique, INT against INT). */
  defSame: number
  gutsAtt: number
  rateAtt: number
  gutsDef: number
  rateDef: number
}

/** The deterministic part of §12.5 damage, scaled ×10⁸ so the random, crit, trait and special multipliers can follow. */
export function damageBase(i: DamageInput): number {
  const d = BATTLE.damage
  const baseT = i.force * (d.baseFlat * 100 + divRound(10_000 * i.a, d.basePerA)) // force·(0.7 + A/180) ×10⁴
  const e4 = 3 * i.defDef + i.defSame // 4·E
  const inside = Math.floor((4 * (i.a + d.ratioOffset) * 100_000_000) / (e4 + 4 * d.ratioOffset))
  const ratioT = clamp(isqrt(inside), d.ratioMin * 100, d.ratioMax * 100) // ×10⁴
  let v = baseT * ratioT // ×10⁸
  v = divRound(v * gutsAttackMul(i.gutsAtt, i.rateAtt), 1000)
  v = divRound(v * gutsDefenseMul(i.gutsDef, i.rateDef), 1000)
  return v
}

/** Applies thousandth multipliers to a ×10⁸ amount and returns whole damage, at least 1. */
export function finishDamage(baseT8: number, multipliers: readonly number[]): number {
  let v = baseT8
  for (const m of multipliers) v = divRound(v * m, 1000)
  return Math.max(1, divRound(v, 100_000_000))
}

/** §12.5 expected damage with no crit and no random roll (for the AI and for tests). */
export function expectedDamage(i: DamageInput): number {
  return finishDamage(damageBase(i), [])
}

export interface CritInput {
  sharp: number
  fame: number
  oppFame: number
  nature: number
  stress: number
  /** Regal adds to the fame cap. */
  fameCapBonus: number
  /** Moonlit +6, as whole percent. */
  bonus: number
}

/** Crit chance in tenths of a percent (before Moth Dust and Clutch, which the engine applies). */
export function critTenths(i: CritInput): number {
  const c = BATTLE.crit
  let t = i.sharp * 10 + i.bonus * 10
  if (i.nature >= 0) t += Math.min((c.fameCapGood + i.fameCapBonus) * 10, divRound(i.fame * 10, c.fameDivGood))
  else t += Math.min((c.fameCapBad + i.fameCapBonus) * 10, divRound(i.fame * 10, c.fameDivBad)) + Math.min(c.fameCapBad * 10, divRound(i.oppFame * 10, c.fameDivBad)) + Math.min(c.stressCap * 10, divRound(i.stress * 10, c.stressDiv))
  return clamp(t, 0, 1000)
}

/** §12.6: the distraction chance (percent) interpolated between the loyalty points. */
export function distractionPct(loyalty: number): number {
  const pts = DISTRACTION_POINTS
  if (loyalty <= pts[0]![0]) return pts[0]![1]
  for (let i = 1; i < pts.length; i++) {
    const [l1, c1] = pts[i]!
    if (loyalty <= l1) {
      const [l0, c0] = pts[i - 1]!
      return c0 + ((c1 - c0) * (loyalty - l0)) / (l1 - l0)
    }
  }
  return pts[pts.length - 1]![1]
}

export function sameTypeStat(type: TechType): StatKey {
  return type
}

/** Nimble's extra SPD when it is the one being targeted. */
export function nimbleBonus(hasNimble: boolean): number {
  return hasNimble ? BATTLE_TRAITS.nimbleSpd : 0
}

/** HP left as tenths of a percent, truncated (§12.9). */
export function hpPctTenths(hp: number, maxHp: number): number {
  return Math.floor((Math.max(0, hp) * 1000) / Math.max(1, maxHp))
}
