import { DIFFICULTY, ECONOMY } from '../data/tuning.ts'
import type { Difficulty, DrillId, FoodId, Habit, JourneySiteId, Personality, TournamentGrade, Weather } from '../data/types.ts'
import type { Inventory } from './items.ts'
import type { JourneyProgress } from './journey.ts'
import type { EditHistoryEntry } from './lab.ts'
import type { Monster } from './monster.ts'
import type { MonsterRequest } from './training.ts'

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
export type WeekAction = { kind: 'drill'; drill: DrillId } | { kind: 'rest' } | { kind: 'play' } | { kind: 'journey'; site: JourneySiteId } | { kind: 'none' }

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

export type MailKind = 'sale' | 'crown' | 'legend' | 'promotion' | 'rank' | 'info'

export interface MailItem {
  id: string
  week: number
  kind: MailKind
  /** What it is about: a month number for sales, a grade for promotions, a rank number, an event id. */
  ref: string
  read: boolean
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
  }
}
