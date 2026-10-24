/**
 * ALL tuning numbers for Wildsong Ranch live in this file (CLAUDE.md golden rule 4).
 * Game rules in src/core/ import from here and never hard-code a number.
 * Every value starts from docs/GAME_DESIGN.md (section numbers in the comments); balance changes happen here.
 * Fractions are stored as integers over a stated denominator so the core can stay in integer math.
 */
import type { Difficulty, Grade, GrowthType, Season, TournamentGrade, Weather } from './types.ts'

/** App-shell timings (milliseconds). */
export const UI = {
  /** How long the "Ready to play offline" toast stays up. */
  offlineToastMs: 4000,
  /** How often the installed app asks GitHub Pages for a newer build while open. */
  updateCheckIntervalMs: 60 * 60 * 1000,
  /** How long an in-app message ("Saved", "Copied") stays up. */
  toastMs: 2600,
  /** Pause after typing in the Import box before the preview updates. */
  importDebounceMs: 200,
  /** §22 polish: when to fall back to lite portraits (no particles, no secondary motion). */
  perf: {
    /** Phones reporting this much memory (GB) or less, or this many cores or fewer, start in lite mode. */
    liteMemoryGb: 2,
    liteCores: 4,
    /** Otherwise the frame rate is sampled once, after this pause, over this many frames. */
    sampleDelayMs: 1500,
    sampleFrames: 60,
    minFps: 45,
  },
  /** §22 polish: how far the pupils move toward a tap, and how long they hold. */
  glance: { maxPx: 3, holdMs: 1600 },
  /** §21 drill vignette length at normal speed; the speed setting multiplies it (instant = 0). */
  vignetteMs: 2200,
  /** The global speed setting (§21): a multiplier on every skippable animation. */
  speed: { normal: 100, fast: 50, instant: 0 },
  /** §6.4 petting: a finger has to travel this far across the monster to count as a swipe. */
  petSwipePx: 60,
  /** How long the grow-up glow and the stat-delta pop stay on screen (normal speed). */
  glowMs: 1400,
} as const

/** §24 text sizes, as percentages of the base size. */
export const TEXT_SIZES = [100, 115, 130] as const

/** §6.8 Guided-mode odds words: the chance of a good outcome (Great + Success) at or above each bound. */
export const TRANSPARENCY = {
  oddsBands: { eager: 80, likely: 65, risky: 45 },
} as const

/** §14.2 Market: fixed seeds so everyone gets the same gift monsters, the first one free. */
export const MARKET = {
  seedBase: 7_421_000,
  price: 1500,
  seasonalPrice: 2500,
} as const

/** §8 Shop: the multi-buy quantities offered before "Max", and the most of one item in a single purchase. */
export const SHOP = { quantities: [1, 5, 10] as readonly number[], maxPerPurchase: 99 } as const

/** §21 onboarding: Wren guides the first month (in weeks), then one-time contextual tips. */
export const ONBOARDING = { guidedWeeks: 4 } as const

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
 * `mode: 'debt'` (the rule, chosen by the owner after the M1 sims): every week adds max(0, strain − threshold)
 * to a running debt (compounding above `tailFrom`), and each `perWeek` of debt costs one week of life.
 * `mode: 'ladder'` is the original step rule (0 below 80 strain; 80–124 → 1, 125–169 → 2, 170+ → 3), kept for comparison.
 */
export const STRAIN = {
  mode: 'debt' as StrainMode,
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

/** §19 Monster Lab editor rules. */
export const LAB = {
  /** Previous versions kept per monster ("Edit history", Restore). */
  historyLimit: 10,
  /** The blank template a player can start from. */
  blank: { stat: 100, grade: 'C' as Grade, growth: 'Steady' as GrowthType, gutsRate: 12, lifespan: 360, spoil: BIRTH.spoil, fear: BIRTH.fear },
  /** Randomize keeps every stat within ± this percentage of its current value. */
  randomizeSpreadPct: 50,
} as const

/** §19 presets: trained presets at E / C / A / S power, shown at the start of Prime. */
export const PRESETS = {
  tiers: {
    E: { total: 600, techniques: 2, uses: 0, fame: 0, wins: 0, losses: 0 },
    C: { total: 1200, techniques: 4, uses: SONGBOOK.lv2Uses, fame: 20, wins: 6, losses: 3 },
    A: { total: 2000, techniques: 7, uses: SONGBOOK.lv3Uses, fame: 55, wins: 24, losses: 6 },
    /** 9 = the whole kit (2 Basics, one of each other family, the Signature). */
    S: { total: 2800, techniques: 9, uses: SONGBOOK.lv3Uses + 20, fame: 85, wins: 48, losses: 8 },
  },
  /** Trained presets are aged to the first week of this stage. */
  stage: 5,
  /** Trained presets are devoted (spoil/fear) rather than newborn-neutral. */
  spoil: 70,
  fear: 50,
} as const

/** §20 saves on the phone. */
export const SAVES = {
  slots: 3,
  /** Autosave keeps the latest plus this many older copies. */
  autosaveBackups: 3,
  backupReminderDays: 7,
  backupReminderWeeks: 8,
} as const

/** §13 tournaments and ranks. */
export const TOURNAMENT = {
  points: { koWin: 4, win: 3, draw: 2, loss: 0 },
  /** 1st, 2nd and 3rd place shares of the purse (percent). */
  purseSplitPct: [100, 40, 20] as readonly number[],
  perWinGoldPerGrade: 50,
  /** Officials pay little: this × gradeIndex (E = 1). */
  officialPursePerGrade: 500,
  summit: { qualifierPerGrade: 1000, teamWin: 3000, perOwnWin: 1000, slots: ['D', 'C', 'B', 'A', 'S'] as readonly string[] },
  gildedPrizePct: 115,
  /** Entering a cup below your grade ("too easy"). */
  tooEasy: { fame: -2, spoil: -2, fear: -2 },
  /** After the whole event, by placing (§13). */
  after: {
    first: { fatigue: 25, stress: -35 },
    podium: { fatigue: 30, stress: -28 },
    rest: { fatigue: 38, stress: -18 },
    lifespan: 1,
    koFatigue: 10,
    koLifespan: 2,
  },
  injury: { basePct: 5, fatigueDiv: 2, weeks: { min: 2, max: 4 }, lifespan: 2 },
  /** Classic: a KO at this fatigue or more risks DIFFICULTY.koDeathPct. */
  koDeathFatigueMin: 80,
  fame: {
    cupWin: { E: 2, D: 3, C: 4, B: 5, A: 5, S: 6 } as Record<string, number>,
    officialWin: { E: 5, D: 6, C: 7, B: 8, A: 9, S: 10 } as Record<string, number>,
    crownWin: 10,
    legendWin: 15,
    noPodium: -1,
    regalBonus: 5,
  },
  /** Top-3 finishers: `stats` random stats, each by a random amount in the grade's range; ±1 by battle like. */
  growth: { stats: 3, range: { E: [1, 5], D: [2, 6], C: [2, 8], B: [3, 9], A: [4, 11], S: [5, 13] } as Record<string, readonly [number, number]>, battleLike: 1 },
  itemPrizes: { lowSweets: 3, highGrandSweets: 2, highSheetPct: 30 },
  /** Rank 1 → 6 from the first Official win at each of these grades; the Crowns raise 7 → 10. */
  rank: { officialGrades: ['E', 'D', 'C', 'B', 'A'] as readonly string[], crownBase: 6, max: 10 },
  /** Rivals: each eligible one joins a cup with this chance, at most this many per cup. */
  rivals: { chancePct: 50, maxPerCup: 2 },
  /** New Year Open and the open-grade cups generate opponents at your grade ±1. */
  openSpread: 1,
  /** The special cups scale their opponents to the player's stat total (percent), never below the grade's band (M9). */
  specialScalePct: { masquerade: 100, crown: 100, legend: 100 },
} as const

/** CONTENT §10 Corin Hale scales with you. */
export const RIVALS = { corinScalePct: 105, corinAggressiveFrom: 'A' as const } as const

/** §10.4 the Signature technique. */
export const SIGNATURE = { loyaltyMin: 60, glacierRequirement: 700 } as const

/** §11 Journeys. */
export const JOURNEY = {
  weeks: 4,
  cost: 2000,
  saleCost: 1000,
  saleMonthsPerYear: 2,
  /** The Trial at the end: a wild monster of your grade (+1 half the time); win = rewardPerGrade × gradeIndex. */
  trial: { rewardPerGrade: 600, gradeUpPct: 50, rareDropPct: 10, rareDrop: 'moonfruit' },
  /** Mentor bond: every `every` Journeys at a site, a Mentor's Charm lowers that site's requirements by `requirementDrop`. */
  bond: { every: 8, requirementDrop: 50 },
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
export const UPGRADES = { cozyBarnStress: 2, tidePoolSummerStress: 1, trainingYardGreatBonus: 5_000, lanternGardenVisitStress: 5 } as const

/** §6.6 assistant labels: upper bounds of each band, lowest first. */
export const LABEL_BANDS = {
  fatigue: [14, 34, 54, 74, 89] as readonly number[],
  stress: [9, 24, 44, 64, 84] as readonly number[],
  loyalty: [19, 39, 59, 79] as readonly number[],
} as const

/** §6.6 expression cues. */
export const EXPRESSION = { droopyFatigue: 55, sweatStress: 45, sparkleLoyalty: 80, grinNature: -60 } as const

/** Wren's weekly report (CONTENT §15): which line she picks from the condition. */
export const REPORT = { tiredFatigue: 55, exhaustedFatigue: 75, stressed: 45, fresh: { fatigueMax: 34, stressMax: 24 } } as const

/** §6.4 style bands (spoil − fear), lower bound of each band from the top. */
export const STYLE_BANDS = { doting: 80, fond: 50, gentle: 20, even: -19, firm: -49, strict: -79 } as const

/** §12.1–§12.6 battle numbers. Positions are in units (the engine keeps centi-units); percentages here are plain. */
export const BATTLE = {
  ticksPerSecond: 30,
  /** Match lengths offered in Versus (seconds); 60 is the tournament length. */
  timersSec: [60, 90, 180] as readonly number[],
  /** M10: the body radius and the sprite box (BATTLE_CAMERA.spriteHalf) are tuned together; the start gap stays 300. */
  arena: { halfWidth: 600, bodyRadius: 80, startX: 230 },
  /** Gap at which each band ends: Close 0–159, Near 160–309, Mid 310–479, Far 480–679, out of range from 680. */
  bandEnds: [160, 310, 480, 680] as readonly number[],
  bandCentres: [90, 235, 395, 580] as readonly number[],
  walk: { base: 70, perSpd: 50, backPct: 85 },
  dash: { cost: 8, speedMul: 3, maxTicks: 18, cooldown: 60, minGap: 160 },
  push: { maxGap: 40, ticks: 15, distance: 250, cooldown: 90 },
  guts: { start: 50, cap: 99 },
  hit: { base: 50, min: 5, max: 95, skillDivisor: 15, gutsDivisor: 5 },
  damage: { baseFlat: 70, basePerA: 180, ratioOffset: 150, ratioMin: 45, ratioMax: 190, kBase: 15, kPerRate: 3, kRateFrom: 6, gDefHalf: 2, rnd: { min: 95, max: 105 }, critMul: 150 },
  crit: { fameCapGood: 10, fameDivGood: 10, fameCapBad: 5, fameDivBad: 20, stressCap: 10, stressDiv: 10 },
  form: { pct: 20 },
  distraction: { rollCooldown: 90, dawdleTicks: 60 },
  /** The last ten seconds, for Clutch. */
  clutchWindowTicks: 300,
  /** Blessed: 1 % of max HP every 5 s. */
  blessedEveryTicks: 150,
  /** Statue Pose: still for 2 s. */
  statueTicks: 60,
  /** Chill: 3 s of slower walking. */
  chillTicks: 90,
} as const

/** §12.7 specials: trigger numbers and effects. Durations are in ticks (8 s). */
export const SPECIALS = {
  durationTicks: 240,
  lastStand: { cap: 35, gutsDiv: 10, loyaltyDiv: 5, defDiv: 100 },
  valor: { natureMin: 20, hpPctMax: 30, cap: 50, natureDiv: 2, dealtPct: 150 },
  rage: { natureMax: -20, cap: 50, witherDiv: 4, natureDiv: 3, witherPct: 150, regenPct: 140 },
  bulwark: { hitsInRow: 3, div: 3, takenPct: 70, regenPct: 140, dealtPct: 60 },
  clutch: { div: 2, critMul: 2 },
  composure: { streak: 4, div: 3, costPct: 70, takenPct: 150 },
} as const

/** The v1.0 CPU AI's numbers (M4–M9), kept for `aiV1.ts` and its one comparison test. Rates are per tick as thousandths of `rate/30`. */
export const AI_V1 = {
  /** The doc says 30–75; the top end was raised a little so the fastest-regen breeds stay under 12 attacks a match (§26). */
  cooldown: { min: 30, max: 84 },
  thinkEveryTicks: 15,
  stayPct: 75,
  secondBestPct: 20,
  pushFromBand: 3,
  dash: { bandsCloser: 2, gutsMin: 30, pctPerTick: 2 },
  affordSlack: 15,
  bigCost: 35,
  bigGuts: 70,
  gutsSplit: 50,
  rookieReserve: 45,
  /** EV = hit · (damage % of max HP + witherWeight · wither) + sharpWeight · sharp (weights ×100). */
  ev: { witherWeight: 35, sharpWeight: 5 },
  /** A band preference is a multiplier (×100) on that band's score. */
  personalities: {
    Steady: { useLow: 60, useHigh: 140, bigBias: 160, witherBias: 100, farBias: 100, closeBias: 100 },
    Aggressive: { useLow: 90, useHigh: 170, bigBias: 120, witherBias: 100, farBias: 100, closeBias: 100 },
    Cautious: { useLow: 20, useHigh: 100, bigBias: 220, witherBias: 100, farBias: 100, closeBias: 100 },
    Trickster: { useLow: 60, useHigh: 140, bigBias: 160, witherBias: 150, farBias: 100, closeBias: 100 },
    Sniper: { useLow: 50, useHigh: 130, bigBias: 160, witherBias: 100, farBias: 150, closeBias: 100 },
    Brawler: { useLow: 80, useHigh: 160, bigBias: 180, witherBias: 100, farBias: 100, closeBias: 150 },
  },
} as const

/**
 * §12.10 AI 2.0 (M10): skill tiers, the range plan, movement and guts rules. Multipliers are ×100 (100 = ×1)
 * unless noted; times are ticks (30 a second); distances are arena units. Offense and threat scores are
 * EV per second in thousandths of a percent of max HP, so a basic that lands 10 % of HP every 4 s is ~2,500.
 */
export const AI = {
  /** EV = hit · (damage % of max HP + witherWeight · wither) + sharpWeight · sharp (weights ×100). */
  ev: { witherWeight: 35, sharpWeight: 5 },
  /** Reaction delay, mistake chance per plan (and how long a mistaken band is kept), pause after a technique. */
  tiers: {
    rookie: { react: { min: 18, max: 30 }, mistakePct: 20, mistakeTicks: { min: 60, max: 120 }, cooldown: { min: 45, max: 90 } },
    skilled: { react: { min: 10, max: 20 }, mistakePct: 8, mistakeTicks: { min: 60, max: 120 }, cooldown: { min: 36, max: 84 } },
    expert: { react: { min: 6, max: 12 }, mistakePct: 2, mistakeTicks: { min: 60, max: 120 }, cooldown: { min: 33, max: 78 } },
  },
  /** Re-plan every 8–12 ticks, or at once on an event (§12.10). */
  replan: { min: 8, max: 12 },
  /** The player's Auto styles (§12.11): aggression / caution, band biases, pacing, free dashes and the poke horizon. */
  styles: {
    balanced: { aggression: 100, caution: 100, closeBias: 100, farBias: 100, cooldownPct: 100, saveBias: 100, dashFreely: false },
    aggressive: { aggression: 140, caution: 60, closeBias: 140, farBias: 70, cooldownPct: 80, saveBias: 70, dashFreely: true },
    defensive: { aggression: 70, caution: 150, closeBias: 70, farBias: 140, cooldownPct: 115, saveBias: 130, dashFreely: false },
  },
  /**
   * NPC personalities on top of the tier. saveBias shortens (>100) or lengthens the horizon for cheap pokes;
   * cooldownPct scales the pause between techniques (the pacing lever: Aggressive fires more often).
   */
  personalities: {
    Steady: { aggression: 100, caution: 100, witherBias: 100, farBias: 100, closeBias: 100, saveBias: 100, cooldownPct: 100 },
    Aggressive: { aggression: 130, caution: 70, witherBias: 100, farBias: 100, closeBias: 100, saveBias: 70, cooldownPct: 70 },
    Cautious: { aggression: 80, caution: 140, witherBias: 100, farBias: 100, closeBias: 100, saveBias: 140, cooldownPct: 140 },
    Trickster: { aggression: 100, caution: 100, witherBias: 150, farBias: 100, closeBias: 100, saveBias: 100, cooldownPct: 100 },
    Sniper: { aggression: 100, caution: 110, witherBias: 100, farBias: 150, closeBias: 80, saveBias: 110, cooldownPct: 110 },
    Brawler: { aggression: 120, caution: 80, witherBias: 100, farBias: 80, closeBias: 150, saveBias: 90, cooldownPct: 90 },
  },
  /** Band scoring (§12.10): offense × aggression − threat × caution + variety − travel × travelWeight. */
  score: {
    /** The threat term's base weight (×100): my own offense counts fully, the opponent's half, so a mirror still picks its best band. */
    threatWeight: 50,
    /** A technique's offense is its EV × min(1, guts regenerated over this many seconds ÷ its cost). */
    budgetSec: 10,
    /** Bonus (×100) on a technique's rate when it is affordable right now. */
    affordNowPct: 120,
    /** Variety: up to this much for a band unused for `windowTicks` (same units as offense), and at most this share of the band's offense. */
    varietyMax: 4000,
    varietyPct: 30,
    windowTicks: 300,
    /** Score lost per tick of travel; travel is capped at `travelCapTicks`. */
    travelWeight: 6,
    travelCapTicks: 150,
    /** Extra travel ticks for a band I cannot hold against a faster chaser (kiting rule). */
    unholdableTicks: 90,
    /** A player counts as a chaser for this long after walking in. */
    approachTicks: 30,
    /** Switch target bands only when the new best beats the current one by this much (percent of its size, at least `hysteresisMin`). */
    hysteresisPct: 15,
    hysteresisMin: 100,
    /** Chill: bonus for farther bands while kiting after a hit. */
    chillKiteBonus: 800,
  },
  /** The sweet spot sits this far inside the band's edge that is farthest from the opponent's best band. */
  sweetSpotInset: 25,
  /** No walking while the gap is within this of the desired gap. */
  deadZone: 12,
  /** Footsies: wobble ±15–30 units every 1–3 s. */
  footsie: { amp: { min: 15, max: 30 }, every: { min: 30, max: 90 } },
  /** Anti-stall: touching for over 1 s with neither attacking → act; over 2 s → push or back off. */
  stall: { touchGap: 40, softTicks: 30, hardTicks: 60 },
  /** Back within this of the wall counts as cornered. */
  cornerUnits: 120,
  /** Never walk backwards into the wall for longer than this. */
  backIntoWallTicks: 15,
  /** Technique value tweaks (×100). */
  value: {
    punishPct: 130,
    starve: { rateMin: 13, expensiveCost: 40, witherPct: 140 },
    heal: { hpPctMax: 40, threatPct: 50, traitPct: 150 },
    hitPref: { heavyHitBelowPct: 40, gutsOverride: 80, heavyPct: 60 },
    varietyPct: 115,
    /** Rival habits: spamsWither / stealsGuts weight, banksForHeavy threshold, waits99 threshold. */
    habitBias: 300,
    habitBankGuts: 70,
    habitWaitGuts: 99,
  },
  /** Save or spend. */
  guts: {
    /** Never sit at this many guts or more. */
    spendAt: 90,
    /** An attack in range fires when its value is at least this share (×100) of the goal technique's value… */
    slotRatioPct: 60,
    /** …or when the goal cannot be afforded within this horizon of regen anyway (personality saveBias scales it). */
    horizonTicks: 180,
    /** "Affordable soon" for the goal technique: guts plus this horizon of regen. */
    goalHorizonTicks: 240,
    /** The opponent at or below this many guts is a target: fire the best technique in range (0 = only when broke). */
    oppLowGuts: 0,
    /** Below this many guts, no pokes (the goal, a broke or punishing opponent, 90+ guts and stalls still fire); 0 = off. */
    pokeFloor: 0,
    /** Rookies hold this much before attacking. */
    rookieReserve: 45,
    /** "Being punished": hit within this many ticks. */
    punishedTicks: 30,
  },
  dash: { behindSecondsLeft: 15, goalBandsCloser: 2, ramPct: 100 },
  /** §12.10 situation modifiers. */
  situations: {
    aheadLate: { secondsLeft: 20, cautionPct: 200 },
    behindLate: { secondsLeft: 15, aggressionPct: 150, cautionPct: 50 },
    lowHp: { hpPctMax: 30, cautionPct: 150 },
    heavyReady: { cautionPct: 130 },
    punish: { cautionPct: 30 },
    oppDamageUp: { cautionPct: 150 },
    ownDamageUp: { aggressionPct: 130 },
    chillKiteTicks: 90,
  },
  /** Events that force a re-plan: the clock marks (seconds left). */
  clockMarks: [20, 10] as readonly number[],
  /** The plan icon keeps a mode at least this long, so it reads as a thought and not a flicker. */
  modeHoldTicks: 15,
} as const

/** CONTENT §2.1 and NEW_MONSTERS §2: the battle traits' numbers (percentages unless noted). */
export const BATTLE_TRAITS = {
  nimbleSpd: 50,
  heavyHitterPct: 115,
  fortifiedPct: 70,
  glowHit: 6,
  enGardeHit: 8,
  hotBlooded: { hpPctMax: 50, pct: 115 },
  tailwindPct: 120,
  mothDustCritPct: 70,
  etherealWitherPct: 70,
  liveWire: { gutsBelow: 30, regenPct: 110 },
  reflective: { chancePct: 15, pct: 30 },
  hardShellPct: 75,
  regalCritCapBonus: 5,
  dragonheart: { hpPctBelow: 50, guts: 20 },
  unshakablePct: 80,
  underdog: { hit: 8, pct: 110 },
  blessedPct: 1,
  moonlitCrit: 6,
  greenThumbPct: 200,
  eightArmsExtraHits: 1,
  statuePosePct: 50,
  batteringRamPct: 115,
  chillPct: 75,
  /** M10 Gilded: guts gained each time it lands a hit. */
  gildedGutsOnHit: 7,
} as const

/** §13 generated opponents, by tournament grade (Crown and Legend arrive with M5 but the bands are listed). */
export const NPC = {
  totals: { E: [520, 800], D: [800, 1150], C: [1150, 1550], B: [1550, 2000], A: [2000, 2450], S: [2450, 2900], Crown: [2900, 3300], Legend: [3500, 3800] } as Record<string, readonly [number, number]>,
  loyalty: { E: [50, 65], D: [55, 70], C: [60, 75], B: [65, 80], A: [70, 85], S: [80, 95], Crown: [85, 95], Legend: [95, 95] } as Record<string, readonly [number, number]>,
  fame: { E: [5, 15], D: [10, 25], C: [20, 35], B: [30, 50], A: [45, 65], S: [60, 80], Crown: [75, 90], Legend: [100, 100] } as Record<string, readonly [number, number]>,
  /** Stat weight = weightBase/100 + gf. */
  weightBase: 90,
  noisePct: 8,
  chainChancePct: 50,
  universalFrom: 'B' as const,
  universal: { min: 1, max: 2 },
} as const

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

/* ---------- M6: legacy (GAME_DESIGN §14.1, §15, §16, §7) ---------- */

/** §16 the Freezer. */
export const FREEZER = { slots: 20 } as const

/** §15 Fusion at Dr. Pell's Lab. */
export const FUSION = {
  fee: 1000,
  /** Candidate mains come from P1.main, P2.main, P1.sub, P2.sub (duplicates add up). */
  mainWeights: { p1Main: 4, p2Main: 3, p1Sub: 2, p2Sub: 1 },
  /** Candidate subs. */
  subWeights: { p2Main: 3, p1Sub: 2, p2Sub: 2, p1Main: 1 },
  /** weight = mainW · subW · lineageStrength / strengthDivisor. */
  strengthDivisor: 5,
  /** Outcomes under this percentage are dropped; at most `maxOutcomes` are shown. */
  minPct: 1,
  maxOutcomes: 6,
  /** The Lineage Seal multiplies P1.main's main weight. */
  sealMultiplier: 2,
  /** offset = (2·P1gain + P2gain) / 3. */
  offset: { p1: 2, p2: 1, div: 3 },
  /** P = 20 % + 9 % per matching stat rank (M). */
  pBasePct: 20,
  pPerMatchPct: 9,
  /** K by the rarity of the chosen outcome: [up to this %, K %]. The last row catches everything else. */
  rarityK: [
    [2, 100],
    [7, 85],
    [15, 70],
    [30, 60],
    [50, 50],
    [100, 40],
  ] as readonly (readonly [number, number])[],
  /** Same main as P1: inherit this fraction of P1's learned non-Basic techniques (rounded down). */
  inherit: { num: 2, den: 3 },
  /** Nature and form: (2·P1 + P2) / 3. */
  blend: { p1: 2, p2: 1, div: 3 },
  /** Dr. Pell's comment thresholds on M (0–6). */
  comment: { decent: 2, wonderful: 4, perfect: 6 },
  /** A stat shard catalyst adds this much to one stat (CONTENT §6). */
  shardStat: 40,
} as const

/** §16 Heartstones and the Heirloom. */
export const HEARTSTONE = {
  max: 10,
  maxWithLanternGarden: 15,
  /** Percent of the donor's trained gains (stat − breed base) granted per stat. */
  gainPct: 15,
  capPerStat: 60,
  /** Only a monster younger than this (weeks) that has not received one can take a Heartstone. */
  maxAgeWeeks: 48,
  /** +hit for techniques of the donor's most-used family. */
  heirloomHit: 3,
} as const

/** §14.1 the Shrine of Echoes. */
export const SHRINE = {
  /** Re-creating a monster from the Encyclopedia. */
  encyclopediaPrice: 500,
  /** Randomize draws this many words. */
  randomWords: { min: 1, max: 3 },
  /** A salt for the secret-phrase hashes, so they differ from the Shrine's own seeds. */
  secretSalt: 53,
} as const

/** CONTENT §12 variant perks that are rules rather than birth stats. */
export const VARIANTS = {
  /** Party Bloatoad: stress relief on every birthday. */
  birthdayStressRelief: 10,
  /** Beacon Wishlume: +hit on Far techniques. */
  farHit: 5,
  /** Lantern-bearer Ashwraith: +wither on Wither techniques. */
  witherPlus: 5,
  /** Gilded Lootlid: prize money bonus in percent (stacks with the Gilded trait). */
  prizeBonusPct: 25,
} as const

/** §7 Gentle mode: an Elder mentors once a month (the bonus itself is JOURNEY.technique.elderMentorPct). */
export const ELDER = { mentorPerMonth: 1 } as const

/* ---------- M7: exploration and unlocks (GAME_DESIGN §17, §18; CONTENT §8, §11, §13, §14) ---------- */

/** §17 expeditions. */
export const EXPEDITION = {
  weeks: 4,
  /** Stamina = base + LIF / lifDivisor. */
  stamina: { base: 50, lifDivisor: 8 },
  stepCost: { min: 5, max: 12 },
  detourCost: 10,
  /** Lost chance = max(floorPct, basePct − INT / intDivisor) percent; being lost costs `lostCost` stamina. */
  fog: { basePct: 30, intDivisor: 30, floorPct: 5, lostCost: 10 },
  after: { fatigue: 40, stress: -10 },
  map: {
    layers: { min: 4, max: 5 },
    perLayer: { min: 2, max: 3 },
    /** Nodes on the whole map, the start and the camp included. */
    nodes: { min: 12, max: 16 },
    /** The guaranteed route to the event node costs at most this much stamina (the base stamina). */
    spineBudget: 50,
    /** A node links to a second node of the next layer this often (percent). */
    extraEdgePct: 50,
  },
  /** Node-kind weights for ordinary nodes, and for the guaranteed route (no fog, no hidden spots). */
  nodeWeights: { path: 18, obstacle: 26, search: 22, hidden: 10, fog: 14, treasure: 10 },
  spineWeights: { path: 30, obstacle: 40, search: 20, treasure: 10 },
  /** The Strange Chest holds a Lootlid this often, and always on this visit to Thornwood. */
  chest: { lootlidPct: 35, pityVisit: 3 },
  /** Tomas's log keeps this many lines. */
  logLimit: 30,
} as const

/** CONTENT §11 unlock chains. */
export const UNLOCKS = {
  cocoon: { month: 6, week: 4, ageMin: 144, ageMax: 240, loyaltyMin: 70, fatigueMax: 20, stressMax: 15, puddings: 12, weeks: 4, keepGainsPct: 80, lifespanBonus: 60 },
  storm: { spdMin: 300, stressMax: 25, fatigueMax: 30, fatigueCost: 10 },
  /** Basil's cocoon rumor: a Nibblegrub this old (weeks) on the ranch. */
  grubRumorAge: 48,
  /** Basil whispers about the masked breeder in this month once a monster reached this grade. */
  masquerade: { rumorMonth: 9, grade: 'B' as TournamentGrade },
  /** The Reefclaw moves in on this week after the Tide Pool; its likes come from a fixed seed, like the Market's. */
  reefclaw: { month: 6, week: 1, seed: 7_421_100 },
  /** The Lootlid that comes home from the chest rolls its likes from this seed. */
  lootlidSeed: 7_421_200,
} as const

/** CONTENT §13 Odd Jobs: Turnip Sort. */
export const ODD_JOBS = {
  seconds: 30,
  payPerCorrect: 5,
  payPerWrong: 5,
  cap: 150,
  /** How long an item stays in reach at the start and at the end of the round (milliseconds): the ramp. */
  slideMs: { start: 1900, end: 850 },
  /** The pause between items, start → end. */
  gapMs: { start: 450, end: 180 },
  /** Chance an item is a turnip (percent); rocks are the rest. */
  turnipPct: 60,
  /** Items prepared per round (more than a round can show). */
  items: 80,
} as const

/** CONTENT §13 Odd Jobs: Echo Stones (the memory game). Times are milliseconds. */
export const ECHO_STONES = {
  stones: 4,
  payPerRound: 15,
  cap: 150,
  /** Reaching this round takes this much stress off the monster (paid plays only). */
  stressRound: 8,
  stressRelief: 5,
  /** One free retry of the current round per game. */
  retries: 1,
  /** The melody prepared per game; reaching the end wins the game. */
  maxRounds: 40,
  /**
   * How long a stone glows and the pause after it in round 1; every `speedUpEvery` rounds both shrink by
   * `speedUpPct`, never under the minimums. Relaxed stretches both by `relaxedPct`.
   */
  tempo: { noteMs: 520, gapMs: 200, speedUpEvery: 4, speedUpPct: 12, minNoteMs: 240, minGapMs: 90, relaxedPct: 150 },
  /** The pause before the melody plays, and before the next round starts. */
  leadMs: 650,
  /** How long a tapped stone glows. */
  tapMs: 220,
  /** The four stones' notes (Hz): C4 E4 G4 C5. */
  noteHz: [262, 330, 392, 523] as readonly number[],
} as const

/** CONTENT §14 title thresholds that are not tournament placings. */
export const TITLES = { collectorVariants: 50, sweetTooth: 100, sleeperStones: 10, gentleHeartPct: 95, lineageGeneration: 5, encyclopedistBreeds: 30, perfectPitchRound: 15 } as const

/** §23 audio. Volumes are percentages. */
export const AUDIO = {
  defaultVolume: { master: 80, music: 55, sfx: 100 },
  /** Music fades in and out over this long (milliseconds). */
  fadeMs: 700,
  /** Under a burst of effects the music ducks to this percent of its volume and recovers after duckMs. */
  duckPct: 60,
  duckMs: 320,
  /** The sequencer renders at this sample rate: plenty for chiptune, and the buffers stay small. */
  sampleRate: 22050,
  /** How long the victory stinger holds the stage before the previous track returns. */
  stingerMs: 3200,
} as const

/** §3 the planner queue. */
export const PLANNER = {
  maxWeeks: 8,
  /** The run stops after a week that leaves fatigue or stress at or above these. */
  stopFatigue: 60,
  stopStress: 50,
  /** Pause between queued weeks on screen at normal speed (the speed setting multiplies it). */
  stepDelayMs: 700,
} as const

/**
 * §12.11 arena camera (M10): frames both monsters, zooms to fit and never shows past the walls. Units are arena
 * units except the pixel fields. The sprite box is 2 × spriteHalf wide; the drawn body fills about 80 % of it.
 */
export const BATTLE_CAMERA = {
  spriteHalf: 100,
  /** Space beyond each monster's back edge. */
  margin: 40,
  /** One sprite may fill at most this share of the arena width… */
  maxSpritePct: 45,
  /** …and must leave this many pixels for the ruler and floor. */
  reservePx: 56,
  /** Pixel size the portrait is rendered at before the camera scales it. */
  basePx: 160,
  /** Critically damped spring: natural frequency (Hz) and the reduced-motion ease time constant (ms). */
  springHz: 2.2,
  easeMs: 180,
} as const

/** §22 battle effect timings (milliseconds). */
export const BATTLE_FX = { lungeMs: 260, projectileMs: 300, hitFlashMs: 160, knockbackMs: 240, sparkleMs: 650, koMs: 800, hopMs: 900 } as const

/** §22 backgrounds and weather overlays. */
export const BACKGROUND = {
  /** Lightning: one flash per cycle (seconds), far under §24's 3 Hz limit. */
  lightningCycleS: 7,
  drops: { full: 26, lite: 9 },
  flakes: { full: 20, lite: 7 },
  clouds: 4,
} as const

/** The install-help card hides for this many real days after "Later". */
export const INSTALL = { dismissDays: 14 } as const

/** §22 emotes: how long a bubble stays up (milliseconds). */
export const EMOTE = { holdMs: 2400 } as const

/**
 * V1 effects engine (VISUAL_V1_EFFECTS §4, §6): every number the fx layer uses. World units are arena units
 * (x −600…600; y = 0 on the floor, negative is up, so a monster's chest sits near y = −100); times are ms.
 */
export const FX = {
  quality: {
    tiers: ['ultra', 'high', 'lite'] as const,
    budgets: {
      ultra: { maxParticles: 2500, filters: 'all', resolutionCap: 2, lightningPasses: 3 },
      high: { maxParticles: 1200, filters: 'some', resolutionCap: 1.5, lightningPasses: 2 },
      lite: { maxParticles: 400, filters: 'none', resolutionCap: 1, lightningPasses: 1 },
    },
    /** Auto: sample this many frames of the first battle; drop one tier above dropOneMs, two above dropTwoMs. */
    sampleFrames: 90,
    dropOneMs: 18,
    dropTwoMs: 28,
    /** Auto starts at High on phones below these hints. */
    highBelowMemoryGb: 4,
    highBelowCores: 6,
  },
  intensity: {
    cozy: { shakePx: 0, hitstopMs: 0, impactFrames: 'off', flashAlpha: 0, bloom: 'off', particles: 0.6 },
    standard: { shakePx: 4, hitstopMs: 60, impactFrames: 'crits', flashAlpha: 0.2, bloom: 'low', particles: 1 },
    flashy: { shakePx: 8, hitstopMs: 120, impactFrames: 'heavy', flashAlpha: 0.3, bloom: 'high', particles: 1.4 },
  },
  /** §24 photosensitivity: at most this many flashes a second, never brighter than this alpha. */
  flash: { maxPerSecond: 3, maxAlpha: 0.3, defaultMs: 120 },
  /** The fx clock never advances more than this per frame (a background tab coming back). */
  maxFrameMs: 100,
  /** The manual clock (review screenshots) advances in slices this long, like real frames. */
  manualSliceMs: 16.7,
  /** A hit worth at least this share of the target's max HP counts as heavy (impact frames at Flashy, bigger shake). */
  heavyHitPct: 12,
  /** The pool is sized to the Ultra cap; it never grows after warm-up. */
  poolCapacity: 2500,
  /** Defaults per primitive (element styles scale them). */
  burst: { count: 26, speed: 340, spread: Math.PI * 2, gravity: 500, lifeMs: 680, size: 15 },
  cone: { ratePerSec: 220, durationMs: 520, speed: 520, halfAngle: 0.4, lifeMs: 560, size: 24, drag: 0.92 },
  trail: { ratePerSec: 160, lifeMs: 320, size: 15 },
  projectile: { speedUnitsPerSec: 1500, arcHeight: 110, size: 42, minMs: 180 },
  beam: { width: 16, durationMs: 240, jitter: 7, passes: 3 },
  ring: { radius: 150, thickness: 12, durationMs: 460, groundSquash: 0.32 },
  impact: { durationMs: 340, spikes: 8, spikeLength: 95, coreRadius: 18 },
  splash: { drops: 34, speed: 440, gravity: 900, lifeMs: 760, rings: 2, size: 12 },
  sheet: { width: 180, height: 300, durationMs: 950, scroll: 1.1, foam: 0.18 },
  lightning: { levels: 5, jitter: 0.24, branchChance: 0.4, branchScale: 0.55, flickerFrames: 3, durationMs: 280, coreWidth: 3, glowWidth: 14 },
  haze: { strength: 14, durationMs: 650, scroll: 0.35 },
  glow: { radius: 130, pulseHz: 2.2, durationMs: 750, alpha: 0.55 },
  debris: { count: 16, speed: 400, gravity: 1500, bounce: 0.45, lifeMs: 1000, size: 17 },
  mist: { count: 9, lifeMs: 1500, drift: 45, size: 70, alpha: 0.28 },
  shake: { durationMs: 280, hz: 26 },
  impactFrame: { frames: 2 },
  /** Idle: no render while nothing is live; this many ms of grace keep the loop warm between effects. */
  idleGraceMs: 400,
  /** The fps counter's smoothing (exponential moving average weight). */
  fpsSmoothing: 0.08,
  /** Stress test: how many effects fire at once. */
  stressCount: 20,
} as const
