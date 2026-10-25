import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { DIFFICULTY, ECONOMY } from '../data/tuning.ts'
import type { BreedId, Difficulty, DrillId, ExpeditionSiteId, Family, FoodId, Habit, JourneySiteId, MailKind, Personality, Stats, TournamentGrade, UnlockChain, Weather } from '../data/types.ts'
import type { Inventory } from './items.ts'
import type { JourneyProgress } from './journey.ts'
import type { EditHistoryEntry } from './lab.ts'
import type { Monster } from './monster.ts'
import type { DrillOutcome, MonsterRequest } from './training.ts'
import { variantNameOf } from './variants.ts'

/** The whole raising game in one plain object (what a save slot stores, minus the RNG state). */

export interface Upgrades {
  cozyBarn: boolean
  trainingYard: boolean
  tidePool: boolean
  lanternGarden: boolean
}

export interface GameSettings {
  /** The optional "one item per week" rule (on by default only in Classic). */
  onePerWeek: boolean
}

export interface Breeder {
  name: string
  ranchName: string
  /** Breeder rank 1–10. */
  rank: number
}

/** The one action of a week (§3 step 3). Lives here so the save can remember "last week" for Repeat. */
export type WeekAction =
  | { kind: 'drill'; drill: DrillId }
  | { kind: 'rest' }
  | { kind: 'play' }
  | { kind: 'journey'; site: JourneySiteId }
  /** §17: the trip starts; the map is played at once and weeks 2–4 pass as away weeks. */
  | { kind: 'expedition'; site: ExpeditionSiteId }
  /** CONTENT §11: the pending event (the storm chase) is accepted and uses the week. */
  | { kind: 'event' }
  | { kind: 'none' }

/** §3 planner: a queued week is a drill or a rest; nothing that needs a decision. */
export type PlannerStep = { kind: 'drill'; drill: DrillId } | { kind: 'rest' }

/** Why a planner run stopped (Wren explains each in WREN.planner). */
export type PlannerStop =
  | 'empty'
  | 'noMonster'
  | 'ended'
  | 'request'
  | 'event'
  | 'trial'
  | 'tournament'
  | 'expedition'
  | 'journey'
  | 'locked'
  | 'mail'
  | 'illness'
  | 'breakdown'
  | 'warning'
  | 'forcedRest'
  | 'signature'
  | 'grewUp'
  | 'prime'
  | 'fatigue'
  | 'stress'
  | 'invalid'

export interface PlannerLogEntry {
  week: number
  step: PlannerStep
  outcome: DrillOutcome | null
  gains: Partial<Stats>
  pay: number
}

export interface PlannerState {
  /** Up to PLANNER.maxWeeks steps, next first. */
  queue: PlannerStep[]
  /** What the current (or last) run did, oldest first. */
  log: PlannerLogEntry[]
  lastStop: PlannerStop | null
}

/**
 * Where the current week stands (M3). `start`: the week has not begun (food, charms and the request roll
 * are still to come). `action`: the start-of-week phase ran; the player may use items, shop and then act.
 */
export type WeekPhase = 'start' | 'action'

/** Small running counters for the Monster Card, titles (M7) and Wren's remarks. */
export interface GameCounters {
  sweetsEaten: number
  sheetsLearned: number
  drillsDone: number
  restsTaken: number
}

/* ---------- tournaments (§13) ---------- */

export interface Participant {
  name: string
  monster: Monster
  personality: Personality
  habit: Habit
  rivalId: string | null
  player: boolean
}

export interface MatchResult {
  /** 0 = participant `a`, 1 = participant `b`, null = draw. */
  winner: 0 | 1 | null
  how: 'ko' | 'time' | 'forfeit' | 'walkover'
  hpPct: [number, number]
  /** How long the match lasted, in battle ticks (v9; older results and walkovers have none). */
  ticks?: number
}

export interface MatchRecord {
  round: number
  a: number
  b: number
  result: MatchResult | null
}

export interface TournamentState {
  eventId: string
  /** The absolute week index the cup is held in. */
  week: number
  seed: number
  /** The cup's default for the player's matches (§12.11): 'manual' = Fight, 'auto' = Auto. Each match still offers Fight, Auto and Skip. */
  mode: 'auto' | 'manual'
  /** Participant 0 is the player. */
  participants: Participant[]
  matches: MatchRecord[]
  /** Participants who were knocked out (they withdraw from their remaining matches). */
  koOut: number[]
  /** For elimination brackets: who is out. */
  eliminated: number[]
  /** For the Summit relay: the NPC teammates' results (wins for the Vale side). */
  relayWins: number
  done: boolean
  /** Technique uses in the player's matches, for mastery at the end. */
  playerTechUses?: Record<string, number>
}

export interface TrialState {
  site: JourneySiteId
  /** A technique earned in the last Journey week while the monster already knew 12 (the UI asks what to forget). */
  pendingTechnique: string | null
}

export interface GuildState {
  officialsWon: TournamentGrade[]
  crownsWon: string[]
  legendWon: boolean
  crownInvite: boolean
  legendInvite: boolean
  creditsRolled: boolean
}

export interface HallEntry {
  monster: Monster
  week: number
}

export type { MailKind } from '../data/types.ts'

export interface MailItem {
  id: string
  week: number
  kind: MailKind
  /** What it is about: a month number for sales, a grade for promotions, a rank number, an event id. */
  ref: string
  read: boolean
}

/* ---------- legacy (§14.1, §15, §16) ---------- */

export type MemorialCause = 'passed' | 'retired' | 'fused'

export interface MemorialEntry {
  /** The monster as it was at the end; its id stays the monster's id (the family tree points at it). */
  monster: Monster
  cause: MemorialCause
  epitaph: string
  week: number
}

export interface Heartstone {
  id: string
  donorId: string
  donorName: string
  donorBreed: BreedId
  donorSub: BreedId
  donorVariant: string | null
  /** The donor's trained gains per stat (stat − breed base at birth, never below 0). */
  gains: Stats
  /** The donor's most-used technique family: the Heirloom. */
  family: Family
  week: number
}

/** A Shrine creation that can be re-created for a fee. */
export interface EncyclopediaPhrase {
  phrase: string
  artist: string
  name: string
  mainBreed: BreedId
  subBreed: BreedId
  variantId: string | null
}

export interface Encyclopedia {
  /** Breeds owned (as a main) on this ranch. */
  breeds: BreedId[]
  /** Secret variants owned. */
  variants: string[]
  phrases: EncyclopediaPhrase[]
  /** Distinct looks owned ("Cinder Puddlepup", secret variants included): CONTENT §14 Collector. */
  combos: string[]
}

/* ---------- M7: expeditions, unlock chains, the Journal (§17, §18) ---------- */

export interface ExpeditionLoot {
  id: string
  qty: number
}

export type ExpeditionEnd = 'camp' | 'retreat' | 'exhausted'

/** A trip in progress or just finished. The map itself is rebuilt from `site` and `seed`. */
export interface ExpeditionState {
  site: ExpeditionSiteId
  seed: number
  /** The absolute week the trip began. */
  startWeek: number
  /** 1 while the map is played; 2–4 are the weeks away; after week 4 the trip is cleared. */
  weekNo: number
  stamina: number
  staminaMax: number
  /** The node the party stands on. */
  at: number
  visited: number[]
  /** Nodes already searched, opened or triggered. */
  searched: number[]
  /** Obstacles passed or detoured. */
  passed: number[]
  /** An obstacle the party stands before and has not passed yet (Detour or Turn back). */
  blockedAt: number | null
  /** Which visit to this site this is (1-based): the Strange Chest's pity timer. */
  visit: number
  loot: ExpeditionLoot[]
  sheets: string[]
  /** 'lootlid' or 'brass-blueprint' once found. */
  keyFound: string | null
  /** Where the Lootlid went when the trip ended. */
  lootlidPlaced: 'ranch' | 'freezer' | 'none' | null
  ended: ExpeditionEnd | null
  /** Tomas's narration keys with their fill-ins, newest last (bounded). */
  log: string[]
}

export type PendingEvent = { kind: 'stormChase' }

/** Where each CONTENT §11 chain stands. The breed itself is in `unlocked`; this is the rest. */
export interface UnlockProgress {
  rumorsHeard: UnlockChain[]
  /** Basil's September whisper arrived: the Masquerade Cup is open every October from then on. */
  masqueradeInvited: boolean
  /** A farewell happened; Sister Mara's letter comes with the next week 1. */
  vigilPending: boolean
  /** The Vigil can be attended at the Shrine. */
  vigilOpen: boolean
  /** The active monster is in a cocoon and emerges as this breed. */
  cocoonInto: BreedId | null
  expeditionsBySite: Record<ExpeditionSiteId, number>
  reefclawArrived: boolean
  wyrmScaleGiven: boolean
}

/** The Journal's Records page. */
export interface JournalRecords {
  bestTotal: number
  bestTotalName: string
  oldestWeeks: number
  oldestName: string
  cupsWon: number
  expeditionsDone: number
  stonesWoken: number
  highestGeneration: number
}

/** A phrase whose main breed was still asleep (§14.1). It wakes for free once the breed unlocks. */
export interface SleepingStone {
  phrase: string
  artist: string
  breed: BreedId
  week: number
}

export interface GameState {
  /** Week index: 0 = Year 1, January, week 1. */
  week: number
  money: number
  difficulty: Difficulty
  settings: GameSettings
  monster: Monster | null
  inventory: Inventory
  /** Owned Songsheets (technique ids), kept forever. */
  songbook: string[]
  upgrades: Upgrades
  /** This month's food (defaults to last month's choice). */
  foodChoice: FoodId
  weather: Weather
  itemsUsedThisWeek: number
  journey: JourneyProgress | null
  /** Set by the end-of-week tick when the active monster's life ended. */
  ended: 'passed' | 'retired' | null
  breeder: Breeder
  weekPhase: WeekPhase
  /** The request the monster made at the start of this week, until the player answers it. */
  pendingRequest: MonsterRequest | null
  /** What the player did last week, for the "Repeat last week" button. */
  lastAction: WeekAction | null
  /** §19: previous versions of the active monster, oldest first, at most LAB.historyLimit. */
  monsterHistory: EditHistoryEntry[]
  /** Onboarding tips the player has seen (ids from core/onboarding). */
  tipsSeen: string[]
  counters: GameCounters
  /** §19: set once any Sandbox tool was used on this ranch (shown as a badge; never limits anything). */
  sandbox: boolean
  /** The cup being played this week (M5). */
  tournament: TournamentState | null
  /** A Journey's Trial waiting to be fought (M5). */
  trial: TrialState | null
  guild: GuildState
  hallOfFame: HallEntry[]
  mail: MailItem[]
  /** Months (1–12) with half-price Journeys this year. */
  saleMonths: number[]
  journeysBySite: Record<JourneySiteId, number>
  /** CONTENT §14 titles earned on this ranch. */
  titles: string[]
  /** §16 the Freezer (FREEZER.slots). Time stops for frozen monsters. */
  freezer: Monster[]
  /** §7 Gentle retirees. They can fuse like frozen monsters and mentor Journeys. */
  elderGrove: Monster[]
  /** §16 every monster that passed away, retired or was fused. Never deleted. */
  memorial: MemorialEntry[]
  heartstones: Heartstone[]
  encyclopedia: Encyclopedia
  sleepingStones: SleepingStone[]
  /** Breeds the Shrine may wake. Starts as every breed that isn't locked; M7's unlock chains add the rest. */
  unlocked: BreedId[]
  /** The absolute month (week ÷ 4) an Elder last mentored, or null. One mentoring per month. */
  elderMentorMonth: number | null
  /** §17 the expedition in progress (the map in week 1, then the weeks away). */
  expedition: ExpeditionState | null
  /** CONTENT §11 an event waiting for a yes or no (the storm chase). */
  pendingEvent: PendingEvent | null
  unlocks: UnlockProgress
  records: JournalRecords
  /** The week index of the last paid Turnip Sort (one per in-game week). */
  oddJobWeek: number | null
  /** The week index of the last paid Echo Stones game, and the best round reached (practice counts). */
  echoStonesWeek: number | null
  echoStonesBest: number
  /** The absolute month the Lantern Garden was last visited (once a month). */
  memorialVisitMonth: number | null
  /** §3 the planner queue (M8). */
  planner: PlannerState
}

export interface NewGameOptions {
  difficulty?: Difficulty
  monster?: Monster | null
  breederName?: string
  ranchName?: string
  weather?: Weather
  foodChoice?: FoodId
}

export function zeroCounters(): GameCounters {
  return { sweetsEaten: 0, sheetsLearned: 0, drillsDone: 0, restsTaken: 0 }
}

export function emptyGuild(): GuildState {
  return { officialsWon: [], crownsWon: [], legendWon: false, crownInvite: false, legendInvite: false, creditsRolled: false }
}

export function zeroJourneys(): Record<JourneySiteId, number> {
  return { 'iron-quarry': 0, 'windrun-steppe': 0, 'starfall-observatory': 0, 'archers-glade': 0, 'glacier-bastion': 0 }
}

export function createGameState(opts: NewGameOptions = {}): GameState {
  const difficulty = opts.difficulty ?? 'Standard'
  // The first monster counts in the Encyclopedia from day one (§18).
  const first = opts.monster ?? null
  const encyclopedia = emptyEncyclopedia()
  if (first) {
    encyclopedia.breeds.push(first.mainBreed)
    if (first.variantId) encyclopedia.variants.push(first.variantId)
    encyclopedia.combos.push(variantNameOf(first))
  }
  return {
    week: 0,
    money: ECONOMY.startMoney,
    difficulty,
    settings: { onePerWeek: DIFFICULTY[difficulty].onePerWeekDefault },
    monster: opts.monster ?? null,
    inventory: {},
    songbook: [],
    upgrades: { cozyBarn: false, trainingYard: false, tidePool: false, lanternGarden: false },
    foodChoice: opts.foodChoice ?? 'turnips',
    weather: opts.weather ?? 'Sunny',
    itemsUsedThisWeek: 0,
    journey: null,
    ended: null,
    breeder: { name: opts.breederName ?? 'Breeder', ranchName: opts.ranchName ?? 'Wildsong Ranch', rank: 1 },
    weekPhase: 'start',
    pendingRequest: null,
    lastAction: null,
    monsterHistory: [],
    tipsSeen: [],
    counters: zeroCounters(),
    sandbox: false,
    tournament: null,
    trial: null,
    guild: emptyGuild(),
    hallOfFame: [],
    mail: [],
    saleMonths: [],
    journeysBySite: zeroJourneys(),
    titles: [],
    freezer: [],
    elderGrove: [],
    memorial: [],
    heartstones: [],
    encyclopedia,
    sleepingStones: [],
    unlocked: [...STARTING_UNLOCKED],
    elderMentorMonth: null,
    expedition: null,
    pendingEvent: null,
    unlocks: emptyUnlocks(),
    records: zeroRecords(),
    oddJobWeek: null,
    echoStonesWeek: null,
    echoStonesBest: 0,
    memorialVisitMonth: null,
    planner: emptyPlanner(),
  }
}

export function emptyPlanner(): PlannerState {
  return { queue: [], log: [], lastStop: null }
}

export function emptyEncyclopedia(): Encyclopedia {
  return { breeds: [], variants: [], phrases: [], combos: [] }
}

export function zeroExpeditions(): Record<ExpeditionSiteId, number> {
  return { 'thornwood-ruins': 0, 'sunken-library': 0, 'hollowmoon-caverns': 0, 'skyreef-isles': 0 }
}

export function emptyUnlocks(): UnlockProgress {
  return { rumorsHeard: [], masqueradeInvited: false, vigilPending: false, vigilOpen: false, cocoonInto: null, expeditionsBySite: zeroExpeditions(), reefclawArrived: false, wyrmScaleGiven: false }
}

export function zeroRecords(): JournalRecords {
  return { bestTotal: 0, bestTotalName: '', oldestWeeks: 0, oldestName: '', cupsWon: 0, expeditionsDone: 0, stonesWoken: 0, highestGeneration: 1 }
}
