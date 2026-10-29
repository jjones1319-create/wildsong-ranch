import { BREED_BY_ID } from '../data/breeds.ts'
import { startersOf } from '../data/techniques.ts'
import { BIRTH, GRADE_FACTOR_100, RANGES, STAGES, STAGE_END_PCT, STAGE_FACTOR_100, STAT_CAP_BY_GRADE, STYLE_BANDS, DRILL } from '../data/tuning.ts'
import {
  DRILL_IDS,
  FOOD_IDS,
  GRADES,
  STAT_KEYS,
  TOY_IDS,
  type BreedId,
  type DrillId,
  type Family,
  type FoodId,
  type Grade,
  type Grades,
  type GrowthType,
  type StatKey,
  type Stats,
  type ToyId,
  type TournamentGrade,
  type TraitId,
} from '../data/types.ts'
import { clamp, divRound } from './mathx.ts'
import type { Rng } from './rng.ts'

/** GAME_DESIGN §4: the monster data model. Derived values are functions, never stored. */

export interface TechniqueSlot {
  id: string
  uses: number
  level: 1 | 2 | 3
}

export interface Likes {
  food: FoodId
  dislikedFood: FoodId
  toy: ToyId
  battle: -1 | 0 | 1
  drill: DrillId
  dislikedDrill: DrillId
}

export interface MonsterStatus {
  injuredWeeks: number
  sickWeeks: number
  /** Weeks still missing after running away. */
  missingWeeks: number
  /** Weeks still at the clinic after collapsing. */
  clinicWeeks: number
  cocoonWeeks: number
  /** Running strain debt (only used by the 'debt' strain rule, see tuning STRAIN). */
  strainDebt: number
  /** Weeks left on each active tonic, by stat. */
  tonics: Partial<Record<StatKey, number>>
  usedSunfruit: boolean
  usedMoonfruit: boolean
  heartstoneReceived: boolean
  announcedPrime: boolean
  announcedPastPrime: boolean
  warnedQuarterLife: boolean
  warned48: boolean
  warned10: boolean
  /** §6.9 the bond boost on drill gains, percent: 175 after a Bond week, 25 less each week after, 100 = none. */
  bondPct: number
}

export interface MonsterDiet {
  lastFood: FoodId | null
  /** Months in a row with the same food (1 = first month). */
  sameFoodStreak: number
  puddingCount: number
  monthsFed: number
}

export interface MonsterRecords {
  wins: number
  losses: number
  draws: number
  kos: number
  cupsWon: number
  titles: string[]
  earnings: number
  highestGrade: TournamentGrade
  crownsWon: number
  /** Stat points that came from Stat Sweets, per stat (shown separately on the Monster Card). */
  fromSweets: Stats
}

export interface Monster {
  id: string
  name: string
  mainBreed: BreedId
  variantId: string | null
  generation: number
  parents: [string, string] | []
  seedPhrase: string
  /** §16 the Heirloom: +hit for this family's techniques, from a Heartstone's donor. */
  heirloom: Family | null
  /** §15 (v1.11) a second trait inherited at Fusion; it works alongside the breed's own. Null for most monsters. */
  inheritedTrait: TraitId | null
  stats: Stats
  grades: Grades
  growthType: GrowthType
  gutsRate: number
  lifespanTotal: number
  ageWeeks: number
  fatigue: number
  stress: number
  spoil: number
  fear: number
  nature: number
  form: number
  fame: number
  grade: TournamentGrade
  techniques: TechniqueSlot[]
  likes: Likes
  status: MonsterStatus
  diet: MonsterDiet
  records: MonsterRecords
  flags: { edited: boolean; sandbox: boolean }
}

export type StyleBand = 'doting' | 'fond' | 'gentle' | 'even' | 'firm' | 'strict' | 'spartan'

export function zeroStats(): Stats {
  return { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }
}

export function gradeIndex(g: Grade): number {
  return GRADES.indexOf(g) + 1
}

export function gradeFactor100(g: Grade): number {
  return GRADE_FACTOR_100[g]
}

export function stepGrade(g: Grade, delta: number): Grade {
  const i = clamp(GRADES.indexOf(g) + delta, 0, GRADES.length - 1)
  return GRADES[i]!
}

export function stageFactor100(stage: number): number {
  return STAGE_FACTOR_100[clamp(stage, 1, STAGES.count) - 1]!
}

/** §5.3: the stage ends when age reaches the listed percentage of the current lifespan total. */
export function lifeStage(ageWeeks: number, lifespanTotal: number, growth: GrowthType): number {
  const bounds = STAGE_END_PCT[growth]
  const total = Math.max(1, lifespanTotal)
  let stage = 1
  for (let i = 0; i < STAGES.count - 1; i++) {
    if (ageWeeks * 100 >= bounds[i]! * total) stage = i + 2
  }
  return clamp(stage, 1, STAGES.count)
}

export function stageOf(m: Monster): number {
  return lifeStage(m.ageWeeks, m.lifespanTotal, m.growthType)
}

export function isPrimeStage(stage: number): boolean {
  return STAGES.prime.includes(stage)
}

/** Drawn size for a stage, in percent. */
export function sizePct(stage: number): number {
  if (stage <= STAGES.sizePct.smallUntil) return STAGES.sizePct.smallPct
  if (stage <= STAGES.sizePct.mediumUntil) return STAGES.sizePct.mediumPct
  return STAGES.sizePct.fullPct
}

export function loyaltyOf(m: Monster): number {
  return divRound(m.spoil + m.fear, 2)
}

export function styleOf(m: Monster): number {
  return m.spoil - m.fear
}

export function styleBandOf(style: number): StyleBand {
  if (style >= STYLE_BANDS.doting) return 'doting'
  if (style >= STYLE_BANDS.fond) return 'fond'
  if (style >= STYLE_BANDS.gentle) return 'gentle'
  if (style >= STYLE_BANDS.even) return 'even'
  if (style >= STYLE_BANDS.firm) return 'firm'
  if (style >= STYLE_BANDS.strict) return 'strict'
  return 'spartan'
}

export function strainOf(m: Monster): number {
  return m.fatigue + 2 * m.stress
}

export function totalStats(stats: Stats): number {
  let t = 0
  for (const k of STAT_KEYS) t += stats[k]
  return t
}

/** §6.1 stars: 1★ under 300, 2★ 300–599, 3★ 600 and up. */
export function starsFor(statValue: number): 1 | 2 | 3 {
  if (statValue < DRILL.starThresholds[0]!) return 1
  if (statValue < DRILL.starThresholds[1]!) return 2
  return 3
}

/** The breed's own trait (§12.8). */
export function traitOf(m: Pick<Monster, 'mainBreed'>): TraitId {
  return BREED_BY_ID[m.mainBreed].trait
}

/** Every trait that works for this monster: the breed's own, then an inherited one (§15, v1.11). */
export function traitsOf(m: Pick<Monster, 'mainBreed' | 'inheritedTrait'>): TraitId[] {
  const own = traitOf(m)
  return m.inheritedTrait && m.inheritedTrait !== own ? [own, m.inheritedTrait] : [own]
}

export function hasTrait(m: Pick<Monster, 'mainBreed' | 'inheritedTrait'>, id: TraitId): boolean {
  return traitsOf(m).includes(id)
}

/* ---------- §5.2 stat caps (v1.11) ---------- */

/** The most trained points a stat can hold, set by its growth grade. Stat Sweets go past it. */
export function statCap(m: Pick<Monster, 'grades'>, k: StatKey): number {
  return STAT_CAP_BY_GRADE[m.grades[k]]
}

/** A stat's Stat Sweets points, never more than the stat itself. */
export function sweetsOf(m: Pick<Monster, 'stats' | 'records'>, k: StatKey): number {
  return clamp(m.records.fromSweets[k], 0, m.stats[k])
}

/** A stat's trained points: everything except Stat Sweets. */
export function trainedOf(m: Pick<Monster, 'stats' | 'records'>, k: StatKey): number {
  return m.stats[k] - sweetsOf(m, k)
}

/**
 * Adds trained points (drills, Journeys, cup growth, Heartstones) up to the stat's cap. It never lowers a stat
 * that is already above its cap (after an edit or a grade drop). Mutates m and returns the points added.
 */
export function addTrained(m: Monster, k: StatKey, delta: number): number {
  if (delta <= 0) return 0
  const ceiling = Math.min(RANGES.stat.max, statCap(m, k) + sweetsOf(m, k))
  const next = Math.max(m.stats[k], Math.min(m.stats[k] + delta, ceiling))
  const added = next - m.stats[k]
  m.stats[k] = next
  return added
}

/** Lowers a stat (a drill's drop); the sweets record never ends up larger than the stat. Mutates m; returns the change. */
export function lowerStat(m: Monster, k: StatKey, delta: number): number {
  const before = m.stats[k]
  m.stats[k] = addStat(before, -delta)
  if (m.records.fromSweets[k] > m.stats[k]) m.records.fromSweets[k] = m.stats[k]
  return m.stats[k] - before
}

export function weeksLeft(m: Monster): number {
  return Math.max(0, m.lifespanTotal - m.ageWeeks)
}

export interface BirthOffsets {
  stats: Stats
  lifespan: number
  gutsRate: number
  nature: number
}

export function zeroOffsets(): BirthOffsets {
  return { stats: zeroStats(), lifespan: 0, gutsRate: 0, nature: 0 }
}

export interface BreedBirth {
  base: Stats
  grades: Grades
  gutsRate: number
  lifespan: number
  name: string
  techniques: string[]
}

/** §14.3 a newborn of one whole breed, before Shrine offsets: the breed's stats, grades and guts, its lifespan plus the bonus. */
export function breedBirth(breedId: BreedId): BreedBirth {
  const breed = BREED_BY_ID[breedId]
  return {
    base: { ...breed.base },
    grades: { ...breed.grades },
    gutsRate: clamp(breed.gutsRate, RANGES.gutsRate.min, RANGES.gutsRate.max),
    lifespan: divRound(breed.lifespan * (100 + BIRTH.lifespanBonusPct), 100),
    name: breed.name,
    techniques: startersOf(breedId).map((t) => t.id),
  }
}

export interface CreateMonsterInput {
  id: string
  mainBreed: BreedId
  likes: Likes
  name?: string
  offsets?: Partial<BirthOffsets>
  seedPhrase?: string
  variantId?: string | null
  generation?: number
  parents?: [string, string] | []
}

/** A newborn monster (§4, §7, §14.3). Offsets come from the Shrine; the Market uses zero offsets. */
export function createMonster(input: CreateMonsterInput): Monster {
  const birth = breedBirth(input.mainBreed)
  const offsets: BirthOffsets = { ...zeroOffsets(), ...input.offsets, stats: { ...zeroStats(), ...input.offsets?.stats } }
  const stats = zeroStats()
  for (const k of STAT_KEYS) stats[k] = clamp(birth.base[k] + offsets.stats[k], RANGES.stat.min, STAT_CAP_BY_GRADE[birth.grades[k]])
  const main = BREED_BY_ID[input.mainBreed]
  return {
    id: input.id,
    name: (input.name ?? birth.name).slice(0, RANGES.nameLength.max),
    mainBreed: input.mainBreed,
    variantId: input.variantId ?? null,
    generation: input.generation ?? 1,
    parents: input.parents ?? [],
    seedPhrase: input.seedPhrase ?? '',
    heirloom: null,
    inheritedTrait: null,
    stats,
    grades: birth.grades,
    growthType: main.growth,
    gutsRate: clamp(birth.gutsRate + offsets.gutsRate, RANGES.gutsRate.min, RANGES.gutsRate.max),
    lifespanTotal: clamp(birth.lifespan + offsets.lifespan, RANGES.lifespan.min, RANGES.lifespan.max),
    ageWeeks: 0,
    fatigue: 0,
    stress: 0,
    spoil: BIRTH.spoil,
    fear: BIRTH.fear,
    nature: clamp(offsets.nature, RANGES.nature.min, RANGES.nature.max),
    form: 0,
    fame: 0,
    grade: 'E',
    techniques: birth.techniques.map((id) => ({ id, uses: 0, level: 1 })),
    likes: { ...input.likes },
    status: {
      injuredWeeks: 0,
      sickWeeks: 0,
      missingWeeks: 0,
      clinicWeeks: 0,
      cocoonWeeks: 0,
      strainDebt: 0,
      tonics: {},
      usedSunfruit: false,
      usedMoonfruit: false,
      heartstoneReceived: false,
      announcedPrime: false,
      announcedPastPrime: false,
      warnedQuarterLife: false,
      warned48: false,
      warned10: false,
      bondPct: 100,
    },
    diet: { lastFood: null, sameFoodStreak: 0, puddingCount: 0, monthsFed: 0 },
    records: { wins: 0, losses: 0, draws: 0, kos: 0, cupsWon: 0, titles: [], earnings: 0, highestGrade: 'E', crownsWon: 0, fromSweets: zeroStats() },
    flags: { edited: false, sandbox: false },
  }
}

/** Rolls the personality a monster is born with (§14.1 step 6). Fixed RNG call order. */
export function rollLikes(rng: Rng): Likes {
  const food = rng.pick(FOOD_IDS)
  const dislikedFood = rng.pick(FOOD_IDS.filter((f) => f !== food))
  const toy = rng.pick(TOY_IDS)
  const battle = rng.nextInt(-1, 1) as -1 | 0 | 1
  const drill = rng.pick(DRILL_IDS)
  const dislikedDrill = rng.pick(DRILL_IDS.filter((d) => d !== drill))
  return { food, dislikedFood, toy, battle, drill, dislikedDrill }
}

/** Shrine-style random offsets (§14.1 steps 3–5 and 7). Fixed RNG call order. */
export function rollOffsets(rng: Rng): BirthOffsets {
  const stats = zeroStats()
  for (const k of STAT_KEYS) stats[k] = rng.nextInt(BIRTH.statOffset.min, BIRTH.statOffset.max)
  const lifespan = rng.nextInt(BIRTH.lifespanOffset.min, BIRTH.lifespanOffset.max)
  const gutsRate = rng.nextInt(BIRTH.gutsOffset.min, BIRTH.gutsOffset.max)
  const nature = rng.nextInt(BIRTH.nature.min, BIRTH.nature.max)
  return { stats, lifespan, gutsRate, nature }
}

/** Clamps every numeric field into its legal range (used after loading, importing or editing). Mutates and returns m. */
export function clampMonsterMut(m: Monster): Monster {
  for (const k of STAT_KEYS) {
    m.stats[k] = clamp(Math.round(m.stats[k]), RANGES.stat.min, RANGES.stat.max)
    // The sweets record can never be larger than the stat it is part of (v1.11 caps count trained points).
    m.records.fromSweets[k] = clamp(Math.round(m.records.fromSweets[k]), 0, m.stats[k])
  }
  m.gutsRate = clamp(Math.round(m.gutsRate), RANGES.gutsRate.min, RANGES.gutsRate.max)
  m.lifespanTotal = clamp(Math.round(m.lifespanTotal), RANGES.lifespan.min, RANGES.lifespan.max)
  m.ageWeeks = clamp(Math.round(m.ageWeeks), 0, RANGES.lifespan.max)
  m.fatigue = clamp(Math.round(m.fatigue), RANGES.condition.min, RANGES.condition.max)
  m.stress = clamp(Math.round(m.stress), RANGES.condition.min, RANGES.condition.max)
  m.spoil = clamp(Math.round(m.spoil), RANGES.condition.min, RANGES.condition.max)
  m.fear = clamp(Math.round(m.fear), RANGES.condition.min, RANGES.condition.max)
  m.nature = clamp(Math.round(m.nature), RANGES.nature.min, RANGES.nature.max)
  m.form = clamp(Math.round(m.form), RANGES.form.min, RANGES.form.max)
  m.fame = clamp(Math.round(m.fame), RANGES.fame.min, RANGES.fame.max)
  m.generation = Math.max(1, Math.round(m.generation))
  m.name = m.name.slice(0, RANGES.nameLength.max) || BREED_BY_ID[m.mainBreed].name
  return m
}

/** Small helpers for mutating condition values inside their ranges. */
export function addCondition(value: number, delta: number): number {
  return clamp(value + delta, RANGES.condition.min, RANGES.condition.max)
}
export function addStat(value: number, delta: number): number {
  return clamp(value + delta, RANGES.stat.min, RANGES.stat.max)
}
export function addNature(value: number, delta: number): number {
  return clamp(value + delta, RANGES.nature.min, RANGES.nature.max)
}
export function addForm(value: number, delta: number): number {
  return clamp(value + delta, RANGES.form.min, RANGES.form.max)
}
