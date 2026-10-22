/**
 * Shared content types. Pure type and constant definitions: no logic, no numbers that tune the game.
 * The data files (breeds, techniques, drills, foods, items, journeys) mirror docs/CONTENT.md using these shapes.
 */

export const STAT_KEYS = ['LIF', 'POW', 'INT', 'SKI', 'SPD', 'DEF'] as const
export type StatKey = (typeof STAT_KEYS)[number]
export type Stats = Record<StatKey, number>

export const GRADES = ['E', 'D', 'C', 'B', 'A'] as const
export type Grade = (typeof GRADES)[number]
export type Grades = Record<StatKey, Grade>

export const GROWTH_TYPES = ['Early', 'Steady', 'Late', 'Evergreen'] as const
export type GrowthType = (typeof GROWTH_TYPES)[number]

export const TOURNAMENT_GRADES = ['E', 'D', 'C', 'B', 'A', 'S'] as const
export type TournamentGrade = (typeof TOURNAMENT_GRADES)[number]

export type TechType = 'POW' | 'INT'
export type TechRange = 1 | 2 | 3 | 4

export const FAMILIES = ['Basic', 'Hit', 'Heavy', 'Wither', 'Sharp', 'Special', 'Chain', 'Signature'] as const
export type Family = (typeof FAMILIES)[number]

export const SEASONS = ['Winter', 'Spring', 'Summer', 'Autumn'] as const
export type Season = (typeof SEASONS)[number]

export const WEATHERS = ['Sunny', 'Cloudy', 'Rain', 'Storm', 'Snow'] as const
export type Weather = (typeof WEATHERS)[number]

export const DIFFICULTIES = ['Gentle', 'Standard', 'Classic'] as const
export type Difficulty = (typeof DIFFICULTIES)[number]

export const BODY_PLANS = [
  'blob',
  'quadruped',
  'biped',
  'serpent',
  'avian',
  'floater',
  'shelled',
  'insect',
  'construct',
] as const
export type BodyPlan = (typeof BODY_PLANS)[number]

export const BREED_IDS = [
  'puddlepup',
  'tumblefox',
  'cobblemaw',
  'moatshell',
  'wishlume',
  'quillion',
  'cinderlynx',
  'bloatoad',
  'coilfang',
  'nimbusheep',
  'galeheron',
  'nibblegrub',
  'velvesper',
  'ashwraith',
  'zipwisp',
  'mirrorkin',
  'gearhoot',
  'reefclaw',
  'lootlid',
  'aurelwyrm',
  'hearthwing',
  'grumblestone',
  'pluckrex',
  'paladove',
  'starhowl',
  'petalphant',
  'scrollopus',
  'gloomgrin',
  'rammerjack',
  'frostlance',
] as const
export type BreedId = (typeof BREED_IDS)[number]

export const TRAIT_IDS = [
  'cheerful',
  'nimble',
  'heavy-hitter',
  'fortified',
  'glow',
  'en-garde',
  'hot-blooded',
  'big-appetite',
  'quick-study',
  'fluffy',
  'tailwind',
  'hungry-grub',
  'moth-dust',
  'ethereal',
  'live-wire',
  'reflective',
  'clockwork',
  'hard-shell',
  'gilded',
  'regal',
  'dragonheart',
  'unshakable',
  'underdog',
  'blessed',
  'moonlit',
  'green-thumb',
  'eight-arms',
  'statue-pose',
  'battering-ram',
  'chill',
] as const
export type TraitId = (typeof TRAIT_IDS)[number]

export const DRILL_IDS = [
  'hill-sprints',
  'log-toss',
  'puzzle-stones',
  'target-toss',
  'dodge-the-gourds',
  'acorn-shower',
  'plow-pull',
  'moon-meditation',
  'wind-chase',
  'waterfall-stand',
  'quarry-haul',
] as const
export type DrillId = (typeof DRILL_IDS)[number]

export const FOOD_IDS = [
  'turnips',
  'river-fish',
  'honey-bread',
  'berry-pudding',
  'roast-haunch',
  'hearty-stew',
  'herbal-pellets',
] as const
export type FoodId = (typeof FOOD_IDS)[number]

export const TOY_IDS = ['rubber-ball', 'rope-tug', 'music-box', 'paper-kite', 'squeaky-fish', 'puzzle-cube'] as const
export type ToyId = (typeof TOY_IDS)[number]

export const JOURNEY_SITE_IDS = [
  'iron-quarry',
  'windrun-steppe',
  'starfall-observatory',
  'archers-glade',
  'glacier-bastion',
] as const
export type JourneySiteId = (typeof JOURNEY_SITE_IDS)[number]

export const UNLOCK_CHAINS = [
  'cocoon',
  'vigil',
  'storm-chase',
  'masquerade',
  'blueprint',
  'tide-pool',
  'strange-chest',
  'four-crowns',
] as const
export type UnlockChain = (typeof UNLOCK_CHAINS)[number]

export interface BreedArt {
  plan: BodyPlan
  brief: string
  palette: { body: string; belly: string; accent: string; eye: string }
  /** The part this breed adds to the main body when it is the sub-breed. */
  accentPart: string
  /** Variant-name adjective when this breed is the sub-breed ("Cinder Puddlepup"). */
  adjective: string
  /** GAME_DESIGN §22 growth forms: the look from Prime onward, for breeds that grow up. Anything left out falls back to the base look. */
  grown?: { brief: string }
}

export interface Breed {
  id: BreedId
  name: string
  niche: string
  /** How the breed first becomes available. */
  availability: 'market' | 'shrine' | 'locked'
  /** For market breeds: the season they are stocked in, or null for always. */
  marketSeason: Season | null
  unlockChain: UnlockChain | null
  growth: GrowthType
  /** Nominal lifespan in weeks. */
  lifespan: number
  /** Ticks per +1 guts in battle (lower regenerates faster). */
  gutsRate: number
  lean: 'POW' | 'INT' | 'Mixed' | 'Both'
  base: Stats
  grades: Grades
  bonusDrill: DrillId
  /** Fusion lineage strength 1–10. */
  strength: number
  /** Shrine pick weight. */
  commonness: number
  trait: TraitId
  art: BreedArt
}

export interface Trait {
  id: TraitId
  name: string
  description: string
}

export type TechEffect =
  | { kind: 'multi'; hits: number }
  | { kind: 'heal'; pct: number }
  | { kind: 'stun'; ticks: number }
  | { kind: 'drain'; pct: number }
  | { kind: 'recoil'; pct: number }
  | { kind: 'gutsSteal' }
  | { kind: 'push' }
  | { kind: 'lunge' }
  | { kind: 'jackpot' }

export type TechLearn =
  | { kind: 'starter' }
  | {
      kind: 'journey'
      site: JourneySiteId
      /** Stats summed (with loyalty) against `value`. */
      stats: StatKey[]
      value: number
      /** For Chains: the base technique that must be at Lv3 on a Journey. */
      chainOf: string | null
      /** Site gate (Glacier Bastion needs grade B or higher). */
      gradeMin: TournamentGrade | null
    }
  | { kind: 'signature' }
  | { kind: 'library' }

export interface Songsheet {
  price: number
  rankMin: number
  /** False for Signature sheets, which are Crown prizes only. */
  sold: boolean
}

export interface Technique {
  id: string
  name: string
  breed: BreedId | 'universal'
  family: Family
  type: TechType
  range: TechRange
  cost: number
  force: number
  hit: number
  wither: number
  sharp: number
  anim: number
  effect: TechEffect | null
  learn: TechLearn
  /** The Basic technique a breed passes on when it is the sub-breed. */
  subQuirk: boolean
  /** The Songsheet that teaches it, or null when none exists (breed Basics). */
  sheet: Songsheet | null
}

export interface Drill {
  id: DrillId
  name: string
  kind: 'light' | 'heavy'
  main: StatKey
  secondary: StatKey | null
  lowers: StatKey | null
  needsTrainingYard: boolean
  vignette: string
}

export interface FoodEffect {
  stress?: number
  spoil?: number
  fear?: number
  form?: number
  /** Lifespan weeks added per month. */
  life?: number
}

export interface Food {
  id: FoodId
  name: string
  price: number
  neutral: FoodEffect
  liked: FoodEffect
  disliked: FoodEffect
}

export const ITEM_CATEGORIES = [
  'recovery',
  'mood',
  'form',
  'sweet',
  'potential',
  'tonic',
  'fruit',
  'toy',
  'charm',
  'catalyst',
  'key',
  'sellable',
] as const
export type ItemCategory = (typeof ITEM_CATEGORIES)[number]

export type ItemEffect =
  | { kind: 'fatigue'; amount: number }
  | { kind: 'stress'; amount: number }
  | { kind: 'stressHalve' }
  | { kind: 'spoil'; amount: number }
  | { kind: 'fear'; amount: number }
  | { kind: 'nature'; amount: number }
  | { kind: 'form'; amount: number }
  | { kind: 'sweet'; stat: StatKey | 'all'; amount: number }
  | { kind: 'potentialGrade' }
  | { kind: 'tempoBell' }
  | { kind: 'tonic'; stat: StatKey }
  | { kind: 'fruit'; weeks: number; flag: 'usedSunfruit' | 'usedMoonfruit' }
  | { kind: 'toy' }
  | { kind: 'charm'; slot: 'comfort' | 'bedding'; tier: 1 | 2 | 3; value: number }
  | { kind: 'catalyst'; stat: StatKey | null; lifespan: number; lineageSeal: boolean }
  | { kind: 'key' }
  | { kind: 'sellable' }

export interface Item {
  id: string
  name: string
  category: ItemCategory
  /** Shop price, or null when the item is only found or given. */
  price: number | null
  gate: { rank?: number; needsGradeC?: boolean } | null
  effect: ItemEffect
  /** Sale value for sellables. */
  sell: number | null
}

export interface JourneySite {
  id: JourneySiteId
  name: string
  mentor: string
  stat: StatKey
  family: Family
  /** Months (1–12) the site is open. */
  openMonths: readonly number[]
  gradeMin: TournamentGrade | null
  trialBreeds: readonly [BreedId, BreedId]
}
