import { BREED_BY_ID } from '../data/breeds.ts'
import { DRILL_BY_ID } from '../data/drills.ts'
import { DRILL, OUTCOME, PLAY, REACTIONS, REQUEST, REST, TRAIT_EFFECTS, UPGRADES } from '../data/tuning.ts'
import type { DrillId, Grade, Stats, ToyId } from '../data/types.ts'
import { clamp, divRound } from './mathx.ts'
import {
  addCondition,
  addForm,
  addNature,
  addStat,
  gradeFactor100,
  isPrimeStage,
  loyaltyOf,
  stageFactor100,
  stageOf,
  starsFor,
  traitOf,
  type Monster,
} from './monster.ts'
import type { Rng } from './rng.ts'

/** GAME_DESIGN §6: drills, outcomes, gains, praise and scold, rest, play and requests. */

export type DrillOutcome = 'Great' | 'Success' | 'Cheat' | 'Fail' | 'Slacked'
export const ROLLED_OUTCOMES = ['Great', 'Success', 'Cheat', 'Fail'] as const

/** Weights in thousandths of a percent point (see tuning OUTCOME). */
export interface OutcomeWeights {
  great: number
  success: number
  cheat: number
  fail: number
}

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

export function rollOutcome(w: OutcomeWeights, rng: Rng): Exclude<DrillOutcome, 'Slacked'> {
  return rng.weightedPick(ROLLED_OUTCOMES, (o) => (o === 'Great' ? w.great : o === 'Success' ? w.success : o === 'Cheat' ? w.cheat : w.fail))
}

/** §6.2 step 1: only possible at fatigue ≥ 70. */
export function truancyChancePct(fatigue: number, loyalty: number): number {
  if (fatigue < DRILL.truancy.minFatigue) return 0
  return ((fatigue - (DRILL.truancy.minFatigue - 1)) * DRILL.truancy.pctPerPointOver69 * (DRILL.truancy.loyaltyDivisor - loyalty)) / DRILL.truancy.loyaltyDivisor
}

function scaledGain(base: number, grade: Grade, stage: number, noise: number, min: number, max: number): number {
  return clamp(divRound(base * gradeFactor100(grade) * stageFactor100(stage), 100 * 100) + noise, min, max)
}

/** §6.3 table values (no noise). */
export function baseLightGain(grade: Grade, stage: number): number {
  return scaledGain(DRILL.gains.lightBase, grade, stage, 0, DRILL.gains.lightMin, DRILL.gains.lightMax)
}
export function baseHeavyGain(grade: Grade, stage: number): number {
  return scaledGain(DRILL.gains.heavyBase, grade, stage, 0, DRILL.gains.heavyMin, DRILL.gains.heavyMax)
}
export function baseSecondaryGain(grade: Grade, stage: number): number {
  return scaledGain(DRILL.gains.secondBase, grade, stage, 0, DRILL.gains.secondMin, DRILL.gains.secondMax)
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
  const trait = traitOf(m)
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

  const outcome = rollOutcome(outcomeWeights(m, drillId, setting), rng)
  const heavy = drill.kind === 'heavy'
  const costs = heavy ? DRILL.heavy : DRILL.light
  const g = DRILL.gains
  const gains: Partial<Stats> = {}

  if (outcome !== 'Fail') {
    const mainMax = heavy ? g.heavyMax : g.lightMax
    let main = scaledGain(heavy ? g.heavyBase : g.lightBase, m.grades[drill.main], stage, rng.nextInt(g.noise.min, g.noise.max), heavy ? g.heavyMin : g.lightMin, mainMax)
    let second = 0
    if (drill.secondary) second = scaledGain(g.secondBase, m.grades[drill.secondary], stage, rng.nextInt(g.noise.min, g.noise.max), g.secondMin, g.secondMax)
    if (outcome === 'Great') {
      main = Math.min(mainMax, main + g.greatMainBonus)
      if (drill.secondary) second = Math.min(g.secondMax, second + g.greatSecondBonus)
    }
    if (outcome === 'Cheat') {
      main = Math.max(1, Math.floor(main / g.cheatMainDivisor))
      if (drill.secondary) second = rng.nextInt(g.cheatSecond.min, g.cheatSecond.max)
    }
    if (outcome === 'Success' || outcome === 'Great') {
      if (BREED_BY_ID[m.mainBreed].bonusDrill === drillId) main += g.breedBonusDrill
      if ((m.status.tonics[drill.main] ?? 0) > 0) main += g.tonicBonus
    }
    const before = m.stats[drill.main]
    m.stats[drill.main] = addStat(before, main)
    gains[drill.main] = m.stats[drill.main] - before
    if (drill.secondary && second > 0) {
      const b = m.stats[drill.secondary]
      m.stats[drill.secondary] = addStat(b, second)
      gains[drill.secondary] = m.stats[drill.secondary] - b
    }
    if (drill.lowers) {
      const drop = outcome === 'Cheat' ? rng.nextInt(g.loweredOnCheat.min, g.loweredOnCheat.max) : rng.nextInt(g.loweredOnSuccess.min, g.loweredOnSuccess.max)
      const b = m.stats[drill.lowers]
      m.stats[drill.lowers] = addStat(b, -drop)
      gains[drill.lowers] = m.stats[drill.lowers] - b
    }
  }

  let fatigue: number = costs.fatigue
  if (outcome === 'Great') fatigue -= DRILL.greatFatigueRelief
  if (outcome === 'Cheat') fatigue -= DRILL.cheatFatigueRelief
  if (trait === 'clockwork') fatigue = divRound(fatigue * TRAIT_EFFECTS.clockworkDrillFatiguePct, 100)
  const stress = costs.stress
  const form = costs.form
  m.fatigue = addCondition(m.fatigue, fatigue)
  m.stress = addCondition(m.stress, stress)
  m.form = addForm(m.form, form)

  let pay = 0
  if (outcome === 'Success' || outcome === 'Great') {
    pay = costs.pay
    if (outcome === 'Great') pay = divRound(pay * (100 + DRILL.greatPayBonusPct), 100)
    if (trait === 'gilded') pay *= TRAIT_EFFECTS.gildedChorePayMul
  }

  return { monster: m, result: { drill: drillId, outcome, stars, gains, fatigue, stress, form, pay } }
}

export type Reaction = 'praise' | 'scold' | 'skip'

/** §6.4 praise / scold / skip after a drill (or truancy). Cheerful halves the stress from scolding. */
export function applyReaction(input: Monster, outcome: DrillOutcome, reaction: Reaction): Monster {
  const m = structuredClone(input)
  const table = REACTIONS[outcome]
  if (reaction === 'scold') {
    const r = table.scold
    let stress: number = m.nature < 0 ? r.stressBad : r.stress
    if (traitOf(m) === 'cheerful') stress = divRound(stress * TRAIT_EFFECTS.cheerfulScoldStressPct, 100)
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
  if (traitOf(m) === 'fluffy') fatigue += TRAIT_EFFECTS.fluffyRestBonus
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
