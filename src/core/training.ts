import { BREED_BY_ID } from '../data/breeds.ts'
import { DRILL_BY_ID } from '../data/drills.ts'
import { DRILL, OUTCOME, PLAY, REACTIONS, REQUEST, REST, TRAIT_EFFECTS, UPGRADES } from '../data/tuning.ts'
import type { DrillId, Grade, Stats, ToyId } from '../data/types.ts'
import { clamp, divRound } from './mathx.ts'
import {
  addCondition,
  addForm,
  addNature,
  addTrained,
  gradeFactor100,
  hasTrait,
  isPrimeStage,
  loyaltyOf,
  stageFactor100,
  stageOf,
  lowerStat,
  starsFor,
  type Monster,
} from './monster.ts'
import { isGoodOutcome, ROLLED_OUTCOMES, baseOutcome, type DrillOutcome, type RolledOutcome } from './outcomes.ts'
import type { Rng } from './rng.ts'

/** GAME_DESIGN §6: drills, outcomes, gains, praise and scold, rest, play and requests. */

export { baseOutcome, isGoodOutcome, ROLLED_OUTCOMES, type BaseOutcome, type DrillOutcome, type RolledOutcome } from './outcomes.ts'

/** Weights in thousandths of a percent point (see tuning OUTCOME). */
export interface OutcomeWeights {
  great: number
  success: number
  cheat: number
  fail: number
}

/** Every level's weight, after loyalty splits the great and success buckets (§6.2 step 3). */
export type LevelWeights = Record<RolledOutcome, number>

export interface TrainingSetting {
  trainingYard: boolean
}

export const DEFAULT_TRAINING: TrainingSetting = { trainingYard: false }

/** §6.2 step 2. */
export function outcomeWeights(m: Monster, drillId: DrillId, setting: TrainingSetting = DEFAULT_TRAINING): OutcomeWeights {
  const drill = DRILL_BY_ID[drillId]
  const F = m.fatigue
  const S = m.stress
  const L = loyaltyOf(m)
  const N = m.nature
  const stage = stageOf(m)
  const stars = starsFor(m.stats[drill.main])
  const G = OUTCOME.great
  const C = OUTCOME.cheat
  const X = OUTCOME.fail

  let great =
    G.base +
    Math.max(0, L - G.loyaltyOver) * G.loyaltyPer +
    Math.max(0, N) * G.naturePer -
    Math.max(0, F - G.fatigueOver) * G.fatiguePer +
    (isPrimeStage(stage) ? G.primeBonus : 0) +
    (m.likes.drill === drillId ? G.likedDrillBonus : 0) +
    (setting.trainingYard ? UPGRADES.trainingYardGreatBonus : 0)
  let cheat =
    C.base +
    Math.max(0, S - C.stressOver) * (N < 0 ? C.wickedStressPer : C.stressPer) +
    m.spoil * C.spoilPer -
    Math.max(0, L - C.loyaltyOver) * C.loyaltyPer +
    Math.max(0, -N) * C.naturePer +
    (m.likes.dislikedDrill === drillId ? C.dislikedDrillBonus : 0)
  let fail =
    X.base +
    (stars - 1) * X.perExtraStar +
    Math.max(0, F - X.fatigueOver) * X.fatiguePer -
    m.fear * X.fearPer +
    (stage === 1 || stage === 10 ? X.edgeStageBonus : 0)

  great = Math.max(OUTCOME.floors.great, great)
  cheat = Math.max(OUTCOME.floors.cheat, cheat)
  fail = Math.max(OUTCOME.floors.fail, fail)
  const success = Math.max(OUTCOME.floors.success, OUTCOME.total - great - cheat - fail)
  return { great, success, cheat, fail }
}

/** Normalized percentages (floats, for display and tests). */
export function outcomePercents(w: OutcomeWeights): OutcomeWeights {
  const total = w.great + w.success + w.cheat + w.fail
  return { great: (w.great * 100) / total, success: (w.success * 100) / total, cheat: (w.cheat * 100) / total, fail: (w.fail * 100) / total }
}

/** §6.2 step 3: the share (thousandths) of its bucket that goes to Perfect, Superb and Good at this loyalty. */
export function levelShares(loyalty: number): { perfect: number; superb: number; good: number } {
  const v = OUTCOME.levels
  const from = (min: number, per: number, max: number): number => (loyalty >= min ? Math.min(max, (loyalty - min + 1) * per) : 0)
  return {
    perfect: from(v.perfect.minLoyalty, v.perfect.per, v.perfect.max),
    superb: from(v.superb.minLoyalty, v.superb.per, v.superb.max),
    good: Math.min(v.good.max, Math.max(0, (loyalty - v.good.loyaltyOver) * v.good.per)),
  }
}

/** Splits the four buckets into the seven levels. Integer weights that add up to the buckets' total. */
export function levelWeights(w: OutcomeWeights, loyalty: number): LevelWeights {
  const s = levelShares(loyalty)
  const perfect = divRound(w.great * s.perfect, 1000)
  const superb = divRound(w.great * s.superb, 1000)
  const good = divRound(w.success * s.good, 1000)
  return { Perfect: perfect, Superb: superb, Great: w.great - perfect - superb, Good: good, Success: w.success - good, Cheat: w.cheat, Fail: w.fail }
}

/** Normalized level percentages (floats, for display and tests). */
export function levelPercents(w: LevelWeights): LevelWeights {
  const total = ROLLED_OUTCOMES.reduce((sum, o) => sum + w[o], 0)
  const out = {} as LevelWeights
  for (const o of ROLLED_OUTCOMES) out[o] = (w[o] * 100) / total
  return out
}

export function rollOutcome(w: LevelWeights, rng: Rng): RolledOutcome {
  return rng.weightedPick(ROLLED_OUTCOMES, (o) => w[o])
}

/** §6.2 step 1: only possible at fatigue ≥ 70. */
export function truancyChancePct(fatigue: number, loyalty: number): number {
  if (fatigue < DRILL.truancy.minFatigue) return 0
  return ((fatigue - (DRILL.truancy.minFatigue - 1)) * DRILL.truancy.pctPerPointOver69 * (DRILL.truancy.loyaltyDivisor - loyalty)) / DRILL.truancy.loyaltyDivisor
}

/** §6.3: an S stat has its own, higher ceiling (`maxS`); every other grade uses `max`. */
function scaledGain(base: number, grade: Grade, stage: number, noise: number, min: number, max: number, maxS: number): number {
  return clamp(divRound(base * gradeFactor100(grade) * stageFactor100(stage), 100 * 100) + noise, min, grade === 'S' ? maxS : max)
}

/** §6.3 table values (no noise). */
export function baseLightGain(grade: Grade, stage: number): number {
  return scaledGain(DRILL.gains.lightBase, grade, stage, 0, DRILL.gains.lightMin, DRILL.gains.lightMax, DRILL.gains.lightMaxS)
}
export function baseHeavyGain(grade: Grade, stage: number): number {
  return scaledGain(DRILL.gains.heavyBase, grade, stage, 0, DRILL.gains.heavyMin, DRILL.gains.heavyMax, DRILL.gains.heavyMaxS)
}
export function baseSecondaryGain(grade: Grade, stage: number): number {
  return scaledGain(DRILL.gains.secondBase, grade, stage, 0, DRILL.gains.secondMin, DRILL.gains.secondMax, DRILL.gains.secondMaxS)
}

export interface DrillResult {
  drill: DrillId
  outcome: DrillOutcome
  stars: 1 | 2 | 3
  /** Signed stat changes actually applied. */
  gains: Partial<Stats>
  fatigue: number
  stress: number
  form: number
  pay: number
}

/**
 * §6.1–§6.3: resolve one drill. Pure: returns a new monster. RNG order: truancy (only at fatigue ≥ 70),
 * outcome, main noise, secondary noise, cheat secondary, lowered stat.
 */
export function resolveDrill(input: Monster, drillId: DrillId, rng: Rng, setting: TrainingSetting = DEFAULT_TRAINING): { monster: Monster; result: DrillResult } {
  const m = structuredClone(input)
  const drill = DRILL_BY_ID[drillId]
  const stage = stageOf(m)
  const stars = starsFor(m.stats[drill.main])

  if (m.fatigue >= DRILL.truancy.minFatigue && rng.chance(truancyChancePct(m.fatigue, loyaltyOf(m)))) {
    m.fatigue = addCondition(m.fatigue, -DRILL.truancy.fatigueRelief)
    m.stress = addCondition(m.stress, -DRILL.truancy.stressRelief)
    return {
      monster: m,
      result: { drill: drillId, outcome: 'Slacked', stars, gains: {}, fatigue: -DRILL.truancy.fatigueRelief, stress: -DRILL.truancy.stressRelief, form: 0, pay: 0 },
    }
  }

  const outcome = rollOutcome(levelWeights(outcomeWeights(m, drillId, setting), loyaltyOf(m)), rng)
  const level = outcome === 'Good' || outcome === 'Great' || outcome === 'Superb' || outcome === 'Perfect' ? DRILL.levels[outcome] : null
  const heavy = drill.kind === 'heavy'
  const costs = heavy ? DRILL.heavy : DRILL.light
  const g = DRILL.gains
  const gains: Partial<Stats> = {}

  if (outcome !== 'Fail') {
    let main = scaledGain(heavy ? g.heavyBase : g.lightBase, m.grades[drill.main], stage, rng.nextInt(g.noise.min, g.noise.max), heavy ? g.heavyMin : g.lightMin, heavy ? g.heavyMax : g.lightMax, heavy ? g.heavyMaxS : g.lightMaxS)
    let second = 0
    if (drill.secondary) second = scaledGain(g.secondBase, m.grades[drill.secondary], stage, rng.nextInt(g.noise.min, g.noise.max), g.secondMin, g.secondMax, g.secondMaxS)
    // The level's bonus comes after the caps, so a capped gain still gets all of it.
    if (level) {
      main += level.main
      if (drill.secondary) second += level.second
    }
    if (outcome === 'Cheat') {
      main = Math.max(1, Math.floor(main / g.cheatMainDivisor))
      if (drill.secondary) second = rng.nextInt(g.cheatSecond.min, g.cheatSecond.max)
    }
    if (isGoodOutcome(outcome)) {
      if (BREED_BY_ID[m.mainBreed].bonusDrill === drillId) main += g.breedBonusDrill
      if ((m.status.tonics[drill.main] ?? 0) > 0) main += g.tonicBonus
    }
    // The bond boost (a Bond week: ×1.75, then 0.25 less each week) multiplies the whole gain, last.
    const boost = m.status.bondPct
    if (boost > 100) {
      main = divRound(main * boost, 100)
      second = divRound(second * boost, 100)
    }
    // §5.2 (v1.11): trained points stop at the stat's grade cap.
    gains[drill.main] = addTrained(m, drill.main, main)
    if (drill.secondary && second > 0) gains[drill.secondary] = addTrained(m, drill.secondary, second)
    if (drill.lowers) {
      const drop = outcome === 'Cheat' ? rng.nextInt(g.loweredOnCheat.min, g.loweredOnCheat.max) : rng.nextInt(g.loweredOnSuccess.min, g.loweredOnSuccess.max)
      gains[drill.lowers] = lowerStat(m, drill.lowers, drop)
    }
  }

  let fatigue: number = costs.fatigue
  if (level) fatigue -= level.fatigueRelief
  if (outcome === 'Cheat') fatigue -= DRILL.cheatFatigueRelief
  if (hasTrait(m, 'clockwork')) fatigue = divRound(fatigue * TRAIT_EFFECTS.clockworkDrillFatiguePct, 100)
  const stress = costs.stress
  const form = costs.form
  m.fatigue = addCondition(m.fatigue, fatigue)
  m.stress = addCondition(m.stress, stress)
  m.form = addForm(m.form, form)

  let pay = 0
  if (isGoodOutcome(outcome)) {
    pay = costs.pay
    if (level) pay = divRound(pay * (100 + level.payPct), 100)
    if (hasTrait(m, 'gilded')) pay *= TRAIT_EFFECTS.gildedChorePayMul
  }

  return { monster: m, result: { drill: drillId, outcome, stars, gains, fatigue, stress, form, pay } }
}

export type Reaction = 'praise' | 'scold' | 'skip'

/** §6.4 praise / scold / skip after a drill (or truancy). Cheerful halves the stress from scolding. */
export function applyReaction(input: Monster, outcome: DrillOutcome, reaction: Reaction): Monster {
  const m = structuredClone(input)
  const table = REACTIONS[baseOutcome(outcome)]
  if (reaction === 'scold') {
    const r = table.scold
    let stress: number = m.nature < 0 ? r.stressBad : r.stress
    if (hasTrait(m, 'cheerful')) stress = divRound(stress * TRAIT_EFFECTS.cheerfulScoldStressPct, 100)
    m.fear = addCondition(m.fear, r.fear)
    m.stress = addCondition(m.stress, stress)
    m.spoil = addCondition(m.spoil, r.spoil)
    m.nature = addNature(m.nature, r.nature)
  } else {
    const r = reaction === 'praise' ? table.praise : table.skip
    m.spoil = addCondition(m.spoil, r.spoil)
    m.stress = addCondition(m.stress, r.stress)
    m.nature = addNature(m.nature, r.nature)
  }
  return m
}

export interface RestOptions {
  /** Extra fatigue removed by the best Bedding charm (CONTENT §6). */
  beddingBonus: number
}

export function restAmounts(stage: number): { fatigue: number; stress: number } {
  const sf = stageFactor100(stage)
  return { fatigue: divRound(REST.fatigueBase * 100 + REST.fatiguePerSf * sf, 100), stress: divRound(REST.stressBase * 100 + REST.stressPerSf * sf, 100) }
}

export function playAmounts(stage: number): { fatigue: number; stress: number } {
  const sf = stageFactor100(stage)
  return { fatigue: divRound(PLAY.fatigueBase * 100 + PLAY.fatiguePerSf * sf, 100), stress: divRound(PLAY.stressBase * 100 + PLAY.stressPerSf * sf, 100) }
}

/** §6.5 Rest: a whole week off. */
export function restMonster(input: Monster, opts: RestOptions = { beddingBonus: 0 }): { monster: Monster; fatigue: number; stress: number } {
  const m = structuredClone(input)
  const a = restAmounts(stageOf(m))
  let fatigue = a.fatigue + opts.beddingBonus
  if (hasTrait(m, 'fluffy')) fatigue += TRAIT_EFFECTS.fluffyRestBonus
  m.fatigue = addCondition(m.fatigue, -fatigue)
  m.stress = addCondition(m.stress, -a.stress)
  m.form = addForm(m.form, REST.form)
  return { monster: m, fatigue: -fatigue, stress: -a.stress }
}

/** §6.5 Play: only when the monster asks for it. */
export function playMonster(input: Monster): { monster: Monster; fatigue: number; stress: number } {
  const m = structuredClone(input)
  const a = playAmounts(stageOf(m))
  m.fatigue = addCondition(m.fatigue, -a.fatigue)
  m.stress = addCondition(m.stress, -a.stress)
  return { monster: m, fatigue: -a.fatigue, stress: -a.stress }
}

export interface MonsterRequest {
  kind: 'rest' | 'play' | 'treat'
  toy: ToyId | null
}

/** §6.7: 40 → 8%, 60 → 24%, 100 → 56%. */
export function requestChancePct(fatigue: number, stress: number): number {
  const level = Math.max(fatigue, stress)
  if (level < REQUEST.minLevel) return 0
  return REQUEST.basePct + ((level - REQUEST.minLevel) * REQUEST.perPointTenths) / 10
}

/** Start-of-week request check. RNG order: trigger, treat (always consumed when triggered). */
export function rollRequest(m: Monster, rng: Rng, ownsFavoriteToy: boolean): MonsterRequest | null {
  const pct = requestChancePct(m.fatigue, m.stress)
  if (pct <= 0) return null
  if (!rng.chance(pct)) return null
  const treat = rng.chance(100 / REQUEST.treatOneIn)
  if (treat && ownsFavoriteToy) return { kind: 'treat', toy: m.likes.toy }
  return { kind: m.fatigue >= m.stress ? 'rest' : 'play', toy: null }
}

export function denyRequest(input: Monster): Monster {
  const m = structuredClone(input)
  m.stress = addCondition(m.stress, REQUEST.denyStress)
  m.spoil = addCondition(m.spoil, REQUEST.denySpoil)
  return m
}
