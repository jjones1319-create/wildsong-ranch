import { divRound } from '../mathx.ts'
import { BATTLE_TRAITS } from '../../data/tuning.ts'
import type { Family, TechRange, TechType, TraitId } from '../../data/types.ts'

/**
 * GAME_DESIGN §12.8, CONTENT §2.1 and NEW_MONSTERS §2: what each breed trait does in a fight, as small pure
 * queries the engine asks at the right moment. Raising traits (Cheerful, Big Appetite, Quick Study, Fluffy,
 * Hungry Grub, Clockwork, Gilded's chore pay) live in the raising code and answer "nothing" here.
 * Multipliers are thousandths (1000 = ×1).
 */

const T = BATTLE_TRAITS

/** Flat hit bonus in whole percent: Glow (Far), En Garde (Near), Underdog (against a bigger total). */
export function traitHitBonus(trait: TraitId, range: TechRange, underdog: boolean): number {
  let bonus = 0
  if (trait === 'glow' && range === 4) bonus += T.glowHit
  if (trait === 'en-garde' && range === 2) bonus += T.enGardeHit
  if (trait === 'underdog' && underdog) bonus += T.underdog.hit
  return bonus
}

export interface DealtContext {
  family: Family
  /** Attacker's HP as tenths of a percent. */
  hpPct: number
  underdog: boolean
  /** Battering Ram: the first technique after a dash. */
  ramArmed: boolean
}

/** Damage-dealt multipliers: Heavy Hitter, Hot-Blooded, Underdog, Battering Ram. */
export function traitDealtMul(trait: TraitId, c: DealtContext): number {
  if (trait === 'heavy-hitter' && c.family === 'Heavy') return T.heavyHitterPct * 10
  if (trait === 'hot-blooded' && c.hpPct <= T.hotBlooded.hpPctMax * 10) return T.hotBlooded.pct * 10
  if (trait === 'underdog' && c.underdog) return T.underdog.pct * 10
  if (trait === 'battering-ram' && c.ramArmed) return T.batteringRamPct * 10
  return 1000
}

export interface TakenContext {
  techType: TechType
  /** Statue Pose: has stood still long enough. */
  still: boolean
}

/** Damage-taken multipliers: Fortified, Hard Shell (POW), Unshakable, Statue Pose. */
export function traitTakenMul(trait: TraitId, c: TakenContext): number {
  if (trait === 'fortified') return T.fortifiedPct * 10
  if (trait === 'hard-shell' && c.techType === 'POW') return T.hardShellPct * 10
  if (trait === 'unshakable') return T.unshakablePct * 10
  if (trait === 'statue-pose' && c.still) return T.statuePosePct * 10
  return 1000
}

/** Moonlit: +6 % crit, in whole percent. */
export function traitCritBonus(trait: TraitId): number {
  return trait === 'moonlit' ? T.moonlitCrit : 0
}

/** Moth Dust: crits against it are halved (thousandths). */
export function traitCritTakenMul(trait: TraitId): number {
  return trait === 'moth-dust' ? T.mothDustCritPct * 10 : 1000
}

/** Regal: +5 to the fame-crit cap. */
export function traitFameCapBonus(trait: TraitId): number {
  return trait === 'regal' ? T.regalCritCapBonus : 0
}

/** Ethereal: wither taken ×0.7. */
export function traitWitherTakenMul(trait: TraitId): number {
  return trait === 'ethereal' ? T.etherealWitherPct * 10 : 1000
}

/** Live Wire: guts regen +25 % while guts < 30. */
export function traitRegenMul(trait: TraitId, guts: number): number {
  return trait === 'live-wire' && guts < T.liveWire.gutsBelow ? T.liveWire.regenPct * 10 : 1000
}

/** Tailwind: walking and dashing +20 %. */
export function traitSpeedMul(trait: TraitId): number {
  return trait === 'tailwind' ? T.tailwindPct * 10 : 1000
}

/** Unshakable: never pushed back or stunned. */
export function traitImmovable(trait: TraitId): boolean {
  return trait === 'unshakable'
}

/** Reflective: a chance to send part of INT damage back. */
export function traitReflect(trait: TraitId): { chancePct: number; pct: number } | null {
  return trait === 'reflective' ? { chancePct: T.reflective.chancePct, pct: T.reflective.pct } : null
}

/** Eight Arms: multi-hit techniques get an extra hit. */
export function traitExtraHits(trait: TraitId): number {
  return trait === 'eight-arms' ? T.eightArmsExtraHits : 0
}

/** Green Thumb: heals and drains restore 50 % more. */
export function traitHealMul(trait: TraitId): number {
  return trait === 'green-thumb' ? T.greenThumbPct * 10 : 1000
}

/** Battering Ram: dashing costs no guts. */
export function traitFreeDash(trait: TraitId): boolean {
  return trait === 'battering-ram'
}

/** Chill: hits slow the target. */
export function traitChills(trait: TraitId): boolean {
  return trait === 'chill'
}

export function traitBlessed(trait: TraitId): boolean {
  return trait === 'blessed'
}

export function traitDragonheart(trait: TraitId): boolean {
  return trait === 'dragonheart'
}

/** Gilded (M10): guts gained on every landed hit. */
export function traitGutsOnHit(trait: TraitId): number {
  return trait === 'gilded' ? T.gildedGutsOnHit : 0
}

/** Nimble: +50 SPD when targeted. */
export function traitNimble(trait: TraitId): boolean {
  return trait === 'nimble'
}

/* ---------- a fighter's traits (v1.11: the breed's own plus an inherited one) ---------- */

type Traits = readonly TraitId[]

/** Bonuses add up (from 0). One trait (the usual case) skips the loop: these run every tick. */
export function traitsSum(traits: Traits, f: (t: TraitId) => number): number {
  if (traits.length === 1) return f(traits[0]!)
  let sum = 0
  for (const t of traits) sum += f(t)
  return sum
}

/** Multipliers in thousandths multiply (from ×1); one trait gives exactly its own value. */
export function traitsMul(traits: Traits, f: (t: TraitId) => number): number {
  if (traits.length === 1) return f(traits[0]!)
  let acc = 1000
  for (const t of traits) acc = divRound(acc * f(t), 1000)
  return acc
}

/** A yes/no effect works if any trait has it. */
export function traitsAny(traits: Traits, f: (t: TraitId) => boolean): boolean {
  if (traits.length === 1) return f(traits[0]!)
  return traits.some(f)
}

/** The first trait's answer that isn't null (Reflective). */
export function traitsFirst<T>(traits: Traits, f: (t: TraitId) => T | null): T | null {
  for (const t of traits) {
    const v = f(t)
    if (v !== null) return v
  }
  return null
}
