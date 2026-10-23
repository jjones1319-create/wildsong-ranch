import type { TournamentEvent } from './types.ts'

/**
 * CONTENT §9: the 48-week tournament calendar. Week index = (month − 1) · 4 + (week − 1).
 * Some weeks hold two events; some events only exist in even, odd or Summit years (year 4, 8, 12…).
 * Purses are for 1st place. The Officials' purse and the Summit Qualifier's scale by grade (tuning TOURNAMENT).
 */
const w = (month: number, week: number) => (month - 1) * 4 + (week - 1)

export const EVENTS: readonly TournamentEvent[] = [
  // January (winter)
  { id: 'frost-fair', name: 'Frost Fair Cup', week: w(1, 1), grade: 'C', format: 'RR4', purse: 2500, kind: 'cup' },
  { id: 'snowdrift', name: 'Snowdrift Cup', week: w(1, 2), grade: 'E', format: 'Elim4', purse: 800, kind: 'cup' },
  { id: 'hearthfire', name: 'Hearthfire Cup', week: w(1, 3), grade: 'B', format: 'RR4', purse: 4000, kind: 'cup' },
  { id: 'new-year-open', name: 'New Year Open', week: w(1, 4), grade: 'any', format: 'Elim8', purse: 4000, kind: 'open' },
  // February
  { id: 'ice-lantern', name: 'Ice Lantern Cup', week: w(2, 1), grade: 'D', format: 'RR4', purse: 1500, kind: 'cup' },
  { id: 'crown-of-dawn', name: 'Crown of Dawn', week: w(2, 2), grade: 'S', format: 'RR4', purse: 10000, kind: 'crown', crownId: 'dawn' },
  { id: 'cocoa', name: 'Cocoa Cup', week: w(2, 2), grade: 'C', format: 'RR4', purse: 2500, kind: 'cup' },
  { id: 'thaw', name: 'Thaw Cup', week: w(2, 3), grade: 'E', format: 'RR4', purse: 1000, kind: 'cup' },
  { id: 'twin-hearts', name: 'Twin Hearts Cup', week: w(2, 4), grade: 'A', format: 'Elim4', purse: 6000, kind: 'cup' },
  // March (spring)
  { id: 'bud', name: 'Bud Cup', week: w(3, 1), grade: 'D', format: 'Elim4', purse: 1500, kind: 'cup' },
  { id: 'meadow', name: 'Meadow Cup', week: w(3, 2), grade: 'B', format: 'RR4', purse: 4000, kind: 'cup' },
  { id: 'spring-masters', name: 'Spring Masters', week: w(3, 3), grade: 'S', format: 'RR4', purse: 8000, kind: 'cup' },
  { id: 'kite-day', name: 'Kite Day Cup', week: w(3, 3), grade: 'E', format: 'RR4', purse: 900, kind: 'cup' },
  { id: 'spring-ascension', name: 'Spring Ascension', week: w(3, 4), grade: 'own', format: 'RR6', purse: 0, kind: 'official' },
  // April
  { id: 'blossom', name: 'Blossom Cup', week: w(4, 1), grade: 'C', format: 'RR4', purse: 3000, kind: 'cup' },
  { id: 'rain', name: 'Rain Cup', week: w(4, 2), grade: 'E', format: 'RR4', purse: 1000, kind: 'cup' },
  { id: 'pebble', name: 'Pebble Cup', week: w(4, 3), grade: 'A', format: 'RR4', purse: 7000, kind: 'cup' },
  { id: 'wildsong-legend', name: 'The Wildsong Legend', week: w(4, 4), grade: 'S', format: '1v1', purse: 15000, kind: 'legend' },
  { id: 'daffodil', name: 'Daffodil Cup', week: w(4, 4), grade: 'D', format: 'RR4', purse: 2000, kind: 'cup' },
  // May
  { id: 'iron', name: 'Iron Cup', week: w(5, 1), grade: 'B', format: 'RR4', purse: 5000, kind: 'cup', rule: 'powOnly' },
  { id: 'crown-of-tides', name: 'Crown of Tides', week: w(5, 2), grade: 'S', format: 'RR4', purse: 10000, kind: 'crown', crownId: 'tides' },
  { id: 'clover', name: 'Clover Cup', week: w(5, 2), grade: 'D', format: 'RR4', purse: 2000, kind: 'cup' },
  { id: 'songbird', name: 'Songbird Cup', week: w(5, 3), grade: 'E', format: 'RR4', purse: 1000, kind: 'cup' },
  { id: 'may-fair', name: 'May Fair Cup', week: w(5, 4), grade: 'C', format: 'Elim4', purse: 3000, kind: 'cup' },
  // June (summer)
  { id: 'sunny', name: 'Sunny Cup', week: w(6, 1), grade: 'A', format: 'RR4', purse: 7000, kind: 'cup' },
  { id: 'sprout', name: 'Sprout Cup', week: w(6, 2), grade: 'any', format: 'RR4', purse: 3000, kind: 'cup', rule: 'sprout', years: 'even' },
  { id: 'elders', name: "Elders' Cup", week: w(6, 2), grade: 'any', format: 'RR4', purse: 8000, kind: 'cup', rule: 'elders', years: 'odd' },
  { id: 'firefly', name: 'Firefly Cup', week: w(6, 3), grade: 'D', format: 'RR4', purse: 2000, kind: 'cup' },
  { id: 'summer-masters', name: 'Summer Masters', week: w(6, 3), grade: 'S', format: 'RR4', purse: 8000, kind: 'cup' },
  { id: 'summer-ascension', name: 'Summer Ascension', week: w(6, 4), grade: 'own', format: 'RR6', purse: 0, kind: 'official' },
  // July
  { id: 'tidepool', name: 'Tidepool Cup', week: w(7, 1), grade: 'C', format: 'RR4', purse: 3000, kind: 'cup' },
  { id: 'arcane', name: 'Arcane Cup', week: w(7, 2), grade: 'B', format: 'RR4', purse: 5000, kind: 'cup', rule: 'intOnly' },
  { id: 'seashell', name: 'Seashell Cup', week: w(7, 3), grade: 'E', format: 'RR4', purse: 1200, kind: 'cup' },
  { id: 'summit-qualifier', name: 'Summit Qualifier', week: w(7, 4), grade: 'own', format: 'RR4', purse: 0, kind: 'summitQualifier', years: 'summit' },
  { id: 'heatwave', name: 'Heatwave Cup', week: w(7, 4), grade: 'A', format: 'Elim4', purse: 7000, kind: 'cup', years: 'nonSummit' },
  // August
  { id: 'lantern-festival', name: 'Lantern Festival Cup', week: w(8, 1), grade: 'D', format: 'Elim4', purse: 2000, kind: 'cup' },
  { id: 'crown-of-embers', name: 'Crown of Embers', week: w(8, 2), grade: 'S', format: 'RR4', purse: 10000, kind: 'crown', crownId: 'embers' },
  { id: 'sandcastle', name: 'Sandcastle Cup', week: w(8, 2), grade: 'C', format: 'RR4', purse: 3000, kind: 'cup' },
  { id: 'thunder', name: 'Thunder Cup', week: w(8, 3), grade: 'B', format: 'RR4', purse: 5000, kind: 'cup' },
  { id: 'vale-coast-summit', name: 'Vale–Coast Summit', week: w(8, 4), grade: 'own', format: 'Relay', purse: 0, kind: 'summit', years: 'summit', minGrade: 'D' },
  { id: 'stargazer', name: 'Stargazer Cup', week: w(8, 4), grade: 'E', format: 'RR4', purse: 1200, kind: 'cup', years: 'nonSummit' },
  // September (autumn)
  { id: 'harvest', name: 'Harvest Cup', week: w(9, 1), grade: 'A', format: 'RR4', purse: 8000, kind: 'cup' },
  { id: 'apple', name: 'Apple Cup', week: w(9, 2), grade: 'C', format: 'RR4', purse: 3000, kind: 'cup' },
  { id: 'scarecrow', name: 'Scarecrow Cup', week: w(9, 3), grade: 'E', format: 'Elim4', purse: 1000, kind: 'cup' },
  { id: 'autumn-masters', name: 'Autumn Masters', week: w(9, 3), grade: 'S', format: 'RR4', purse: 8000, kind: 'cup' },
  { id: 'autumn-ascension', name: 'Autumn Ascension', week: w(9, 4), grade: 'own', format: 'RR6', purse: 0, kind: 'official' },
  // October
  { id: 'masquerade', name: 'Masquerade Cup', week: w(10, 1), grade: 'any', format: '1v1', purse: 6000, kind: 'masquerade', minGrade: 'B' },
  { id: 'acorn', name: 'Acorn Cup', week: w(10, 2), grade: 'D', format: 'RR4', purse: 2000, kind: 'cup' },
  { id: 'bonfire', name: 'Bonfire Cup', week: w(10, 3), grade: 'B', format: 'Elim4', purse: 5000, kind: 'cup' },
  { id: 'heros-rally', name: "Hero's Rally", week: w(10, 4), grade: 'any', format: 'RR6', purse: 4000, kind: 'cup', rule: 'hero' },
  { id: 'rogues-rally', name: "Rogue's Rally", week: w(10, 4), grade: 'any', format: 'RR6', purse: 4000, kind: 'cup', rule: 'rogue' },
  // November
  { id: 'maple', name: 'Maple Cup', week: w(11, 1), grade: 'C', format: 'RR4', purse: 3000, kind: 'cup' },
  { id: 'crown-of-frost', name: 'Crown of Frost', week: w(11, 2), grade: 'S', format: 'RR4', purse: 10000, kind: 'crown', crownId: 'frost' },
  { id: 'mushroom', name: 'Mushroom Cup', week: w(11, 2), grade: 'E', format: 'RR4', purse: 1000, kind: 'cup' },
  { id: 'copper', name: 'Copper Cup', week: w(11, 3), grade: 'A', format: 'RR4', purse: 8000, kind: 'cup' },
  { id: 'hearth', name: 'Hearth Cup', week: w(11, 4), grade: 'D', format: 'Elim4', purse: 2000, kind: 'cup' },
  // December
  { id: 'starlight', name: 'Starlight Cup', week: w(12, 1), grade: 'S', format: 'RR4', purse: 9000, kind: 'cup' },
  { id: 'snowflake', name: 'Snowflake Cup', week: w(12, 2), grade: 'B', format: 'RR4', purse: 5000, kind: 'cup' },
  { id: 'rival-showdown', name: 'Rival Showdown', week: w(12, 3), grade: 'own', format: '1v1', purse: 3000, kind: 'rival', minGrade: 'C' },
  { id: 'winter-ascension', name: 'Winter Ascension', week: w(12, 4), grade: 'own', format: 'RR6', purse: 0, kind: 'official' },
]

export const EVENT_BY_ID: Readonly<Record<string, TournamentEvent>> = Object.fromEntries(EVENTS.map((e) => [e.id, e]))

/** Summit years are 4, 8, 12… */
export function isSummitYear(year: number): boolean {
  return year % 4 === 0
}

/** The events held in a given week of a given year (year rules applied). */
export function eventsAt(weekInYear: number, year: number): TournamentEvent[] {
  return EVENTS.filter((e) => {
    if (e.week !== weekInYear) return false
    switch (e.years) {
      case 'even':
        return year % 2 === 0
      case 'odd':
        return year % 2 === 1
      case 'summit':
        return isSummitYear(year)
      case 'nonSummit':
        return !isSummitYear(year)
      default:
        return true
    }
  })
}

/** Matches per participant and participant count for a format. */
export function formatSize(format: TournamentEvent['format']): { participants: number; playerMatches: number } {
  switch (format) {
    case 'RR4':
      return { participants: 4, playerMatches: 3 }
    case 'RR6':
      return { participants: 6, playerMatches: 5 }
    case 'Elim4':
      return { participants: 4, playerMatches: 2 }
    case 'Elim8':
      return { participants: 8, playerMatches: 3 }
    case '1v1':
      return { participants: 2, playerMatches: 1 }
    case 'Relay':
      return { participants: 2, playerMatches: 1 }
  }
}
