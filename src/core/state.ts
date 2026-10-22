import { DIFFICULTY, ECONOMY } from '../data/tuning.ts'
import type { Difficulty, DrillId, FoodId, JourneySiteId, Weather } from '../data/types.ts'
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
  }
}
