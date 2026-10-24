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

/** GAME_DESIGN §6.8 transparency modes. */
export const TRANSPARENCY_MODES = ['classic', 'guided', 'lens'] as const
export type TransparencyMode = (typeof TRANSPARENCY_MODES)[number]

/** GAME_DESIGN §21 global animation speed. */
export const SPEEDS = ['normal', 'fast', 'instant'] as const
export type Speed = (typeof SPEEDS)[number]

/** GAME_DESIGN §12.10 CPU personalities. */
export const PERSONALITIES = ['Steady', 'Aggressive', 'Cautious', 'Trickster', 'Sniper', 'Brawler'] as const
export type Personality = (typeof PERSONALITIES)[number]

/** CONTENT §10 readable habits of the rival breeders (§12.10). */
export const HABITS = ['none', 'opensFar', 'banksForHeavy', 'walksClose', 'backsAway', 'spamsWither', 'waits99', 'pushesWhenTouching', 'dashesBelowHalf', 'stealsGuts'] as const
export type Habit = (typeof HABITS)[number]

/** GAME_DESIGN §12.10 AI 2.0 skill tiers (M10). */
export const AI_TIERS = ['rookie', 'skilled', 'expert'] as const
export type AiTier = (typeof AI_TIERS)[number]

/** §12.11 the player's Auto styles. */
export const AUTO_STYLES = ['balanced', 'aggressive', 'defensive'] as const
export type AutoStyle = (typeof AUTO_STYLES)[number]

/** §12.11 "Show battle thinking": what a monster's plan icon can say. */
export const PLAN_MODES = ['distance', 'saving', 'pressing', 'pushing', 'punish', 'safe', 'cornered'] as const
export type PlanMode = (typeof PLAN_MODES)[number]

/** GAME_DESIGN §13 tournament formats (CONTENT §9). */
export const FORMATS = ['RR4', 'RR6', 'Elim4', 'Elim8', '1v1', 'Relay'] as const
export type Format = (typeof FORMATS)[number]

export type EventGrade = TournamentGrade | 'own' | 'any'

export const EVENT_KINDS = ['cup', 'official', 'crown', 'legend', 'open', 'summitQualifier', 'summit', 'rival', 'masquerade'] as const
export type EventKind = (typeof EVENT_KINDS)[number]

export type EventRule = 'powOnly' | 'intOnly' | 'sprout' | 'elders' | 'hero' | 'rogue'
export type EventYears = 'even' | 'odd' | 'summit' | 'nonSummit'

export interface TournamentEvent {
  id: string
  name: string
  /** Week index inside the year, 0–47. */
  week: number
  grade: EventGrade
  format: Format
  /** For 1st place. Officials and the Summit Qualifier scale by grade in the rules. */
  purse: number
  kind: EventKind
  years?: EventYears
  rule?: EventRule
  /** Lowest grade that may enter (the Rival Showdown needs C, the Masquerade B). */
  minGrade?: TournamentGrade
  crownId?: string
}

export const CROWN_IDS = ['dawn', 'tides', 'embers', 'frost'] as const
export type CrownId = (typeof CROWN_IDS)[number]

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

/* ---------- M7: expeditions, upgrades, mail (GAME_DESIGN §17, §18; CONTENT §8, §11) ---------- */

export const EXPEDITION_SITE_IDS = ['thornwood-ruins', 'sunken-library', 'hollowmoon-caverns', 'skyreef-isles'] as const
export type ExpeditionSiteId = (typeof EXPEDITION_SITE_IDS)[number]

/** What a node on the expedition map is (§17 table). `hidden` is a search spot that only INT reveals. */
export const NODE_KINDS = ['start', 'path', 'obstacle', 'search', 'hidden', 'fog', 'treasure', 'event', 'camp'] as const
export type NodeKind = (typeof NODE_KINDS)[number]

/** Each site's one special node (CONTENT §8 highlights). */
export const EVENT_NODE_KINDS = ['strange-chest', 'archive', 'crystal-heart', 'sky-puzzle'] as const
export type EventNodeKind = (typeof EVENT_NODE_KINDS)[number]

export interface ExpeditionObstacle {
  id: string
  name: string
  stat: StatKey
  threshold: number
}

/** One row of a loot table: an item, or a universal Songsheet of one of the listed families. */
export type LootEntry = { kind: 'item'; id: string; qty: number; weight: number } | { kind: 'sheet'; families: readonly Family[]; weight: number }

export interface ExpeditionSite {
  id: ExpeditionSiteId
  name: string
  /** Months (1–12) whose week 1 brings the invitation. */
  months: readonly number[]
  gradeMin: TournamentGrade
  fameMin: number
  obstacles: readonly ExpeditionObstacle[]
  /** INT needed to see hidden search spots. */
  hiddenInt: number
  event: EventNodeKind
  /** The stat check some events need (the hidden archive, the sky puzzle), or null. */
  eventCheck: { stat: StatKey; value: number } | null
  search: readonly LootEntry[]
  treasure: readonly LootEntry[]
  /** What the event node gives when it holds no key item. */
  eventLoot: readonly LootEntry[]
  /** A one-line brief for the invitation and the Journal. */
  blurb: string
}

export const UPGRADE_IDS = ['cozyBarn', 'trainingYard', 'tidePool', 'lanternGarden'] as const
export type UpgradeId = (typeof UPGRADE_IDS)[number]

export interface RanchUpgrade {
  id: UpgradeId
  name: string
  price: number
  requires: { kind: 'rank'; rank: number } | { kind: 'memorial' }
}

/** Every kind of letter the Mailbox can hold. */
export const MAIL_KINDS = ['sale', 'crown', 'legend', 'promotion', 'rank', 'info', 'expedition', 'rumor', 'vigil', 'upgrades', 'masquerade', 'reefclaw', 'wyrm'] as const
export type MailKind = (typeof MAIL_KINDS)[number]

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
