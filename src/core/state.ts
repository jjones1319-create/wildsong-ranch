import { DIFFICULTY, ECONOMY } from '../data/tuning.ts'
import type { Difficulty, FoodId, Weather } from '../data/types.ts'
import type { Inventory } from './items.ts'
import type { JourneyProgress } from './journey.ts'
import type { Monster } from './monster.ts'

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
}

export interface NewGameOptions {
  difficulty?: Difficulty
  monster?: Monster | null
  breederName?: string
  ranchName?: string
  weather?: Weather
  foodChoice?: FoodId
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
  }
}
