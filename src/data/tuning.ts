/**
 * ALL tuning numbers for Wildsong Ranch live in this file (CLAUDE.md golden rule 4).
 * Game rules in src/core/ import from here and never hard-code a number.
 * Every value starts from docs/GAME_DESIGN.md (section numbers in the comments); balance changes happen here.
 * Fractions are stored as integers over a stated denominator so the core can stay in integer math.
 */
import type { Difficulty, Grade, GrowthType, Season, Weather } from './types.ts'

/** App-shell timings (milliseconds). */
export const UI = {
  /** How long the "Ready to play offline" toast stays up. */
  offlineToastMs: 4000,
  /** How often the installed app asks GitHub Pages for a newer build while open. */
  updateCheckIntervalMs: 60 * 60 * 1000,
} as const

/** §5.2 grade factor gf, in hundredths. */
export const GRADE_FACTOR_100: Record<Grade, number> = { E: 58, D: 79, C: 100, B: 132, A: 155 }

/** §5.3 stage factor sf, in hundredths; index = stage − 1. */
export const STAGE_FACTOR_100: readonly number[] = [45, 60, 75, 88, 100, 96, 85, 72, 55, 35]

/** §5.3 cumulative percentage of life at which each stage ends; index = stage − 1. */
export const STAGE_END_PCT: Record<GrowthType, readonly number[]> = {
  Early: [5, 11, 20, 30, 37, 43, 56, 70, 82, 100],
  Steady: [10, 20, 34, 48, 60, 66, 75, 82, 90, 100],
  Late: [14, 28, 42, 56, 68, 78, 85, 90, 95, 100],
  Evergreen: [5, 11, 20, 30, 45, 55, 66, 77, 87, 100],
}

export const STAGES = {
  count: 10,
  prime: [5, 6] as readonly number[],
  pastPrime: 7,
  visiblyOld: 8,
  /** Drawn size by stage (§5.3). */
  sizePct: { smallUntil: 2, smallPct: 70, mediumUntil: 4, mediumPct: 85, fullPct: 100 },
} as const

export const RANGES = {
  stat: { min: 1, max: 999 },
  condition: { min: 0, max: 100 },
  nature: { min: -100, max: 100 },
  form: { min: -100, max: 100 },
  fame: { min: 0, max: 100 },
  gutsRate: { min: 6, max: 20 },
  nameLength: { min: 1, max: 16 },
  lifespan: { min: 1, max: 2000 },
} as const

/** §4, §7, §14.3: what a monster is born with. */
export const BIRTH = {
  spoil: 30,
  fear: 30,
  statOffset: { min: -10, max: 20 },
  lifespanOffset: { min: -10, max: 30 },
  gutsOffset: { min: -1, max: 1 },
  nature: { min: -30, max: 30 },
  /** Base stats = (3·main + 1·sub) / 4. */
  mainStatWeight: 3,
  subStatWeight: 1,
  /** Lifespan = (6·main + 4·sub) / 10. */
  mainLifeWeight: 6,
  subLifeWeight: 4,
  pureLifespanBonusPct: 10,
  /** Guts rate = main + (sub − main) / 4. */
  gutsBlendDivisor: 4,
} as const

/** §6.1 drill costs and pay. */
export const DRILL = {
  light: { fatigue: 10, stress: 4, form: -1, pay: 30 },
  heavy: { fatigue: 15, stress: 9, form: -2, pay: 50 },
  greatPayBonusPct: 50,
  greatFatigueRelief: 3,
  cheatFatigueRelief: 5,
  /** Main stat under the first value → 1★, under the second → 2★, otherwise 3★. */
  starThresholds: [300, 600] as readonly number[],
  truancy: { minFatigue: 70, pctPerPointOver69: 2, loyaltyDivisor: 150, fatigueRelief: 5, stressRelief: 2 },
  gains: {
    lightBase: 10,
    lightMin: 1,
    lightMax: 15,
    heavyBase: 16,
    heavyMin: 3,
    heavyMax: 20,
    secondBase: 7,
    secondMin: 1,
    secondMax: 10,
    noise: { min: -1, max: 1 },
    greatMainBonus: 3,
    greatSecondBonus: 1,
    cheatMainDivisor: 2,
    cheatSecond: { min: 0, max: 1 },
    loweredOnSuccess: { min: 2, max: 3 },
    loweredOnCheat: { min: 1, max: 4 },
    breedBonusDrill: 1,
    tonicBonus: 3,
  },
} as const

/** §6.2 outcome weights, scaled by 1000 so every term stays an integer. */
export const OUTCOME = {
  scale: 1000,
  great: {
    base: 10_000,
    loyaltyOver: 40,
    loyaltyPer: 150,
    naturePer: 100,
    fatigueOver: 40,
    fatiguePer: 200,
    primeBonus: 3_000,
    likedDrillBonus: 6_000,
  },
  cheat: {
    base: 8_000,
    stressOver: 20,
    stressPer: 450,
    wickedStressPer: 675,
    spoilPer: 50,
    loyaltyOver: 50,
    loyaltyPer: 100,
    naturePer: 100,
    dislikedDrillBonus: 6_000,
  },
  fail: {
    base: 7_000,
    perExtraStar: 6_000,
    fatigueOver: 30,
    fatiguePer: 600,
    fearPer: 60,
    edgeStageBonus: 4_000,
  },
  floors: { great: 1_000, cheat: 1_000, fail: 2_000, success: 20_000 },
  total: 100_000,
} as const

/** §6.4 praise / scold / skip effects. `scoldStressBad` applies when nature < 0. */
export const REACTIONS = {
  Great: {
    praise: { spoil: 4, stress: -5, nature: 0 },
    scold: { fear: 3, stress: 8, stressBad: 8, spoil: -2, nature: 0 },
    skip: { spoil: 0, stress: 5, nature: 0 },
  },
  Success: {
    praise: { spoil: 2, stress: -3, nature: 0 },
    scold: { fear: 3, stress: 6, stressBad: 6, spoil: -1, nature: 0 },
    skip: { spoil: 0, stress: 0, nature: 0 },
  },
  Cheat: {
    praise: { spoil: 5, stress: -3, nature: -2 },
    scold: { fear: 4, stress: 4, stressBad: 10, spoil: 0, nature: 1 },
    skip: { spoil: 2, stress: 0, nature: -1 },
  },
  Fail: {
    praise: { spoil: 3, stress: -2, nature: 0 },
    scold: { fear: 3, stress: 2, stressBad: 5, spoil: 0, nature: 0 },
    skip: { spoil: 0, stress: 0, nature: 0 },
  },
  Slacked: {
    praise: { spoil: 4, stress: 0, nature: -2 },
    scold: { fear: 5, stress: 4, stressBad: 4, spoil: 0, nature: 1 },
    skip: { spoil: 2, stress: 0, nature: -1 },
  },
} as const

/** Trait numbers (CONTENT §2.1) that touch raising. Battle traits live with the battle code in M4. */
export const TRAIT_EFFECTS = {
  cheerfulScoldStressPct: 50,
  clockworkDrillFatiguePct: 80,
  fluffyRestBonus: 8,
  gildedChorePayMul: 2,
  quickStudyJourneyPct: 10,
  bigAppetite: { num: 3, den: 2 },
  hungryGrubForm: { num: 3, den: 2 },
} as const

/** §6.5 rest and play: value = base + perSf · sf (sf in hundredths). */
export const REST = { fatigueBase: 30, fatiguePerSf: 20, stressBase: 6, stressPerSf: 8, form: 1 } as const
export const PLAY = { fatigueBase: 14, fatiguePerSf: 10, stressBase: 10, stressPerSf: 12 } as const

export type StrainMode = 'ladder' | 'debt'

/**
 * §6.6 strain → extra lifespan loss per week.
 * `mode: 'ladder'` is the rule as written (0 below 80 strain; 80–124 → 1, 125–169 → 2, 170+ → 3).
 * `mode: 'debt'` is the proposed smoother rule (M1 finding, awaiting the owner's decision): every week adds
 * max(0, strain − threshold) to a running debt, and each `perWeek` of debt costs one week of life.
 */
export const STRAIN = {
  mode: 'ladder' as StrainMode,
  threshold: 80,
  step: 45,
  cap: 3,
  /** Above `tailFrom`, the debt compounds: each point of strain over it adds 1/tailDiv more. */
  debt: { threshold: 10, perWeek: 160, tailFrom: 150, tailDiv: 100, gentlePct: 50, classicPct: 125 },
}
export const ILLNESS = { fatigueMin: 90, chancePct: 10, weeks: 2, lifespanLoss: 2 } as const
export const BREAKDOWN = {
  strainMin: 200,
  chancePct: 25,
  runAway: { weeks: 2, fee: 300, fatigueAfter: 30, stressAfter: 30, spoil: -5, fear: -5 },
  collapse: { weeks: 2, fee: 200, lifespanLoss: 2, fatigueAfter: 30, stressAfter: 30 },
} as const

/** §6.7 requests. Chance = basePct + (max(F, S) − minLevel) · perPointTenths / 10. */
export const REQUEST = { minLevel: 40, basePct: 8, perPointTenths: 8, treatOneIn: 10, denyStress: 8, denySpoil: -2 } as const

/** §7 warnings and lifespan costs. */
export const LIFESPAN = {
  warnAtRemainingPct: 25,
  warnAtWeeksLeft: [48, 10] as readonly number[],
  tonicCost: 6,
  sunfruit: 40,
  moonfruit: 20,
  tournamentBase: 1,
  tournamentKoExtra: 2,
} as const

/** §7 difficulty table. */
export const DIFFICULTY: Record<
  Difficulty,
  {
    endOfLife: 'retire' | 'pass'
    strainExtraStep: number
    strainCap: number
    breakdownPct: number
    prizeMulPct: number
    onePerWeekDefault: boolean
    koInjury: boolean
    koDeathPct: number
  }
> = {
  Gentle: {
    endOfLife: 'retire',
    strainExtraStep: 0,
    strainCap: 1,
    breakdownPct: 10,
    prizeMulPct: 125,
    onePerWeekDefault: false,
    koInjury: false,
    koDeathPct: 0,
  },
  Standard: {
    endOfLife: 'pass',
    strainExtraStep: 0,
    strainCap: STRAIN.cap,
    breakdownPct: BREAKDOWN.chancePct,
    prizeMulPct: 100,
    onePerWeekDefault: false,
    koInjury: true,
    koDeathPct: 0,
  },
  Classic: {
    endOfLife: 'pass',
    strainExtraStep: 1,
    strainCap: 4,
    breakdownPct: BREAKDOWN.chancePct,
    prizeMulPct: 100,
    onePerWeekDefault: true,
    koInjury: true,
    koDeathPct: 15,
  },
}

/** §8 food. */
export const FOOD = { boredomMonths: 3, boredomDivisor: 2 } as const

/** §8 items. Effect sizes are content (data/items.ts); these are the rules around them. */
export const ITEMS = {
  tonicWeeks: 4,
  toyUses: 5,
  toy: { favoriteStress: -12, favoriteSpoil: 4, otherStress: -4 },
  pearlMaxGrade: 'A' as Grade,
  tempoBellMin: RANGES.gutsRate.min,
} as const

/** §10.4 techniques and mastery. */
export const SONGBOOK = { maxTechniques: 12, lv2Uses: 15, lv3Uses: 40, lv2HitBonus: 2, lv3ForceBonus: 2 } as const

/** §11 Journeys. */
export const JOURNEY = {
  weeks: 4,
  cost: 2000,
  saleCost: 1000,
  fatiguePerWeek: 18,
  stressPerWeek: 7,
  thresholds: [10, 20, 30, 40] as readonly number[],
  score: { sitePerGrade: 3, lifPerGrade: 2, perStage: 4, fearDivisor: 5, fatigueDivisor: 5, roll: { min: 0, max: 29 } },
  gains: { siteBase: 8, siteMin: 1, siteMax: 12, lifBase: 5, lifMin: 1, lifMax: 8 },
  technique: { basePct: 30, perPointsOver: 50, pctPerStep: 10, capPct: 90, elderMentorPct: 10 },
} as const

/** §3 calendar. */
export const CALENDAR = { weeksPerMonth: 4, monthsPerYear: 12, upgradeOfferMonth: 5, upgradeOfferWeek: 4 } as const

/** §3 weather weights per season (Storm only in summer, Snow only in winter; CONTENT §11 wants ~20% summer storms). */
export const WEATHER_WEIGHTS: Record<Season, Partial<Record<Weather, number>>> = {
  Winter: { Sunny: 30, Cloudy: 30, Rain: 10, Snow: 30 },
  Spring: { Sunny: 45, Cloudy: 30, Rain: 25 },
  Summer: { Sunny: 40, Cloudy: 25, Rain: 15, Storm: 20 },
  Autumn: { Sunny: 45, Cloudy: 30, Rain: 25 },
}

/** §9 economy. */
export const ECONOMY = { startMoney: 3000, loanCap: 5000, loanFeePct: 10, loanRepayPct: 50 } as const

/** CONTENT §11 ranch upgrades that touch the weekly loop. */
export const UPGRADES = { cozyBarnStress: 2, tidePoolSummerStress: 1, trainingYardGreatBonus: 5_000 } as const

/** §6.6 assistant labels: upper bounds of each band, lowest first. */
export const LABEL_BANDS = {
  fatigue: [14, 34, 54, 74, 89] as readonly number[],
  stress: [9, 24, 44, 64, 84] as readonly number[],
  loyalty: [19, 39, 59, 79] as readonly number[],
} as const

/** §6.6 expression cues. */
export const EXPRESSION = { droopyFatigue: 55, sweatStress: 45, sparkleLoyalty: 80, grinNature: -60 } as const

/** §6.4 style bands (spoil − fear), lower bound of each band from the top. */
export const STYLE_BANDS = { doting: 80, fond: 50, gentle: 20, even: -19, firm: -49, strict: -79 } as const

/** §12.6 loyalty → distraction chance (used by battle in M4; listed here so every number is in one place). */
export const DISTRACTION_POINTS: readonly (readonly [number, number])[] = [
  [0, 45],
  [20, 30],
  [40, 17],
  [50, 12],
  [60, 8],
  [70, 4],
  [80, 2],
  [85, 1],
]
