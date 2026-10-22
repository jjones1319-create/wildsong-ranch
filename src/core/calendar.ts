import { CALENDAR, WEATHER_WEIGHTS } from '../data/tuning.ts'
import { WEATHERS, type Season, type Weather } from '../data/types.ts'
import type { Rng } from './rng.ts'

/** GAME_DESIGN §3: 1 turn = 1 week, 4 weeks per month, 12 months per year. Week index 0 = Year 1, January, week 1. */

export const WEEKS_PER_YEAR = CALENDAR.weeksPerMonth * CALENDAR.monthsPerYear

export interface CalendarDate {
  year: number
  /** 1–12 */
  month: number
  /** 1–4 */
  week: number
}

export function dateOf(weekIndex: number): CalendarDate {
  const i = Math.max(0, Math.floor(weekIndex))
  return {
    year: 1 + Math.floor(i / WEEKS_PER_YEAR),
    month: 1 + Math.floor((i % WEEKS_PER_YEAR) / CALENDAR.weeksPerMonth),
    week: 1 + (i % CALENDAR.weeksPerMonth),
  }
}

export function weekIndexOf(d: CalendarDate): number {
  return (d.year - 1) * WEEKS_PER_YEAR + (d.month - 1) * CALENDAR.weeksPerMonth + (d.week - 1)
}

export function seasonOf(month: number): Season {
  if (month === 12 || month <= 2) return 'Winter'
  if (month <= 5) return 'Spring'
  if (month <= 8) return 'Summer'
  return 'Autumn'
}

export function isMonthStart(weekIndex: number): boolean {
  return weekIndex % CALENDAR.weeksPerMonth === 0
}

/** Ranch upgrades are offered by mail in May week 4. */
export function isUpgradeOfferWeek(weekIndex: number): boolean {
  const d = dateOf(weekIndex)
  return d.month === CALENDAR.upgradeOfferMonth && d.week === CALENDAR.upgradeOfferWeek
}

/** One seeded weather roll. Storm only happens in summer and Snow only in winter. */
export function rollWeather(rng: Rng, month: number): Weather {
  const weights = WEATHER_WEIGHTS[seasonOf(month)]
  return rng.weightedPick(WEATHERS, (w) => weights[w] ?? 0)
}
