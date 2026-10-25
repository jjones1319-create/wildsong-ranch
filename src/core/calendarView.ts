import { EVENT_BY_ID, eventsAt } from '../data/calendar.ts'
import { EXPEDITION_SITES, EXPEDITION_SITE_BY_ID } from '../data/expeditions.ts'
import { CALENDAR } from '../data/tuning.ts'
import { TOURNAMENT_GRADES, type BreedId, type ExpeditionSite, type TournamentEvent, type TournamentGrade } from '../data/types.ts'
import { WEEKS_PER_YEAR, dateOf, isMonthStart, isUpgradeOfferWeek, type CalendarDate } from './calendar.ts'
import { marketStock } from './market.ts'
import type { GameState, PlannerStep } from './state.ts'
import { entryCheck, gradeIndex, itemPrizeKind, opponentGradeOf, purseOf, roundsOf, weekInYear, type EntryCheck, type ItemPrizeKind } from './tournament.ts'
import type { NpcGrade } from './npc.ts'

/**
 * GAME_DESIGN §3 the calendar: what each week holds, built only from the existing data (the cup calendar and its
 * year rules, the expedition months, the Market's seasons, the upgrade letter, the monster's age) and the save.
 * Pure and deterministic. Nothing secret is shown before the save records it, and the weather is never forecast.
 */

export interface CalendarEvent {
  /** `${week}:${eventId}`, the pin key. */
  key: string
  event: TournamentEvent
  /** 1st-place purse at the monster's grade today. */
  purse: number
  opponentGrade: NpcGrade
  rounds: number
  prize: ItemPrizeKind
  /** §13 entry rules, as far as they are knowable today for a later week. */
  entry: EntryCheck
  pinned: boolean
}

export type ExpeditionBlockToday = 'grade' | 'fame' | null

export interface CalendarExpedition {
  /** `${first week of the month}:${siteId}`, the pin key. */
  key: string
  site: ExpeditionSite
  /** True on the month's first week (the invitation week). */
  opens: boolean
  /** What stands in the way today, if anything (the letter's grade and fame). */
  block: ExpeditionBlockToday
  pinned: boolean
}

export type CalendarNote =
  /** A Crown in four weeks: invited (S and the invitation), or close to it (S, not yet invited). */
  | { kind: 'crown'; eventId: string; invited: boolean }
  /** March: the Wildsong Legend in April, once all four Crowns are won. */
  | { kind: 'legend'; eventId: string }
  /** The Market's seasonal stall changes with the season. */
  | { kind: 'market'; breeds: BreedId[] }
  /** Ines's ranch upgrade letter (May week 4). */
  | { kind: 'upgrades' }
  /** The monster turns `years` at the end of this week. */
  | { kind: 'birthday'; years: number }

export type BusyMark =
  | { kind: 'plan'; step: PlannerStep; index: number }
  | { kind: 'journey' }
  | { kind: 'expedition' }
  | { kind: 'injured' }
  | { kind: 'sick' }
  | { kind: 'away' }

export interface CalendarWeek {
  week: number
  date: CalendarDate
  /** Weeks from now (0 = this week, negative = past). */
  offset: number
  events: CalendarEvent[]
  expeditions: CalendarExpedition[]
  notes: CalendarNote[]
  busy: BusyMark | null
  /** Notable events the monster could enter that a planned week runs through. */
  clashes: CalendarEvent[]
}

/** How far ahead the calendar goes: four years, so the next Summit is always in view. */
export const CALENDAR_YEARS_AHEAD = 4
const WEEKS_PER_MONTH = CALENDAR.weeksPerMonth

/** Events worth a warning and the "Next:" line: everything but an ordinary cup (almost every week holds one). */
export function isNotable(e: TournamentEvent): boolean {
  return e.kind !== 'cup'
}

export function pinKey(week: number, id: string): string {
  return `${week}:${id}`
}

function parsePin(key: string): { week: number; id: string } | null {
  const i = key.indexOf(':')
  if (i <= 0) return null
  const week = Number(key.slice(0, i))
  const id = key.slice(i + 1)
  if (!Number.isInteger(week) || week < 0 || id === '') return null
  return { week, id }
}

/** The last week a pinned occurrence covers: its own week for an event, the month's last week for an expedition. */
function pinLastWeek(key: string): number | null {
  const p = parsePin(key)
  if (!p) return null
  return EXPEDITION_SITE_BY_ID[p.id as ExpeditionSite['id']] ? p.week + WEEKS_PER_MONTH - 1 : p.week
}

/** What occupies a week already: the plan, a Journey or Expedition in progress, injury, sickness, being away. */
export function busyAt(state: GameState, week: number): BusyMark | null {
  const offset = week - state.week
  if (offset < 0) return null
  const m = state.monster
  if (state.journey) {
    if (offset < 5 - state.journey.weekNo) return { kind: 'journey' }
  }
  // A trip keeps the monster away for its four weeks (the map, then three weeks out), finished map or not.
  if (state.expedition) {
    if (offset < 5 - state.expedition.weekNo) return { kind: 'expedition' }
  }
  if (m) {
    if (offset < m.status.injuredWeeks) return { kind: 'injured' }
    if (offset < m.status.sickWeeks) return { kind: 'sick' }
    if (offset < Math.max(m.status.missingWeeks, m.status.clinicWeeks, m.status.cocoonWeeks)) return { kind: 'away' }
  }
  // The queue starts this week: the week's action hasn't been taken yet in either phase.
  const step = state.planner.queue[offset]
  if (step && !state.journey && !state.expedition) return { kind: 'plan', step, index: offset }
  return null
}

function eventsOf(state: GameState, week: number, pins: ReadonlySet<string>): CalendarEvent[] {
  const d = dateOf(week)
  const grade = state.monster?.grade ?? 'E'
  return eventsAt(weekInYear(week), d.year).map((event) => {
    const key = pinKey(week, event.id)
    return {
      key,
      event,
      purse: purseOf(event, grade),
      opponentGrade: opponentGradeOf(event, grade),
      rounds: roundsOf(event.format),
      prize: itemPrizeKind(event, grade),
      entry: entryCheck(state, event, week),
      pinned: pins.has(key),
    }
  })
}

function expeditionsOf(state: GameState, week: number, pins: ReadonlySet<string>): CalendarExpedition[] {
  const d = dateOf(week)
  const first = week - (d.week - 1)
  const m = state.monster
  return EXPEDITION_SITES.filter((s) => s.months.includes(d.month)).map((site) => {
    const key = pinKey(first, site.id)
    const block: ExpeditionBlockToday = !m ? 'grade' : TOURNAMENT_GRADES.indexOf(m.grade) < TOURNAMENT_GRADES.indexOf(site.gradeMin) ? 'grade' : m.fame < site.fameMin ? 'fame' : null
    return { key, site, opens: d.week === 1, block, pinned: pins.has(key) }
  })
}

function notesOf(state: GameState, week: number): CalendarNote[] {
  const notes: CalendarNote[] = []
  const d = dateOf(week)
  const m = state.monster
  // A Crown four weeks ahead: shown when invited, or one Official away from it (an S monster not yet invited).
  if (m?.grade === 'S') {
    const ahead = week + WEEKS_PER_MONTH
    for (const e of eventsAt(weekInYear(ahead), dateOf(ahead).year)) {
      if (e.kind === 'crown') notes.push({ kind: 'crown', eventId: e.id, invited: state.guild.crownInvite })
    }
  }
  // The Legend Cup is in April; March's first week says so once all four Crowns are won.
  if (state.guild.legendInvite && !state.guild.legendWon && isMonthStart(week) && d.month === 3) {
    const legend = Object.values(EVENT_BY_ID).find((e) => e.kind === 'legend')
    if (legend) notes.push({ kind: 'legend', eventId: legend.id })
  }
  // The Market's seasonal stall turns over with each season (Dec, Mar, Jun, Sep). Unlocked breeds only appear once the save has them.
  if (isMonthStart(week) && d.month % 3 === 0) {
    const breeds = marketStock(d.month, state.unlocked)
      .filter((o) => o.seasonal)
      .map((o) => o.breed)
    if (breeds.length > 0) notes.push({ kind: 'market', breeds })
  }
  if (isUpgradeOfferWeek(week)) notes.push({ kind: 'upgrades' })
  // Birthdays: the age ticks at the end of the week; a monster turns a year older on every 48th week.
  if (m && week >= state.week) {
    const ageAfter = m.ageWeeks + (week - state.week) + 1
    if (ageAfter % WEEKS_PER_YEAR === 0 && ageAfter > 0 && ageAfter <= m.lifespanTotal) notes.push({ kind: 'birthday', years: ageAfter / WEEKS_PER_YEAR })
  }
  return notes
}

/**
 * `count` weeks from `fromWeek` (absolute). Each holds the cups (year rules applied), the expeditions open that
 * month, dated notes, what already occupies it, and any clash between the plan and a notable event the monster
 * could enter (or a pinned one).
 */
export function calendarWeeks(state: GameState, fromWeek: number, count: number): CalendarWeek[] {
  const pins = new Set(state.calendarPins)
  const out: CalendarWeek[] = []
  for (let i = 0; i < count; i++) {
    const week = fromWeek + i
    if (week < 0) continue
    const events = eventsOf(state, week, pins)
    const busy = busyAt(state, week)
    const clashes = busy?.kind === 'plan' ? events.filter((e) => e.entry.eligible && (isNotable(e.event) || e.pinned)) : []
    out.push({ week, date: dateOf(week), offset: week - state.week, events, expeditions: expeditionsOf(state, week, pins), notes: notesOf(state, week), busy, clashes })
  }
  return out
}

/** The planned weeks that run through a notable event the monster could enter (or a pinned one), in order. */
export function planClashes(state: GameState): CalendarEvent[] {
  return calendarWeeks(state, state.week, state.planner.queue.length).flatMap((w) => w.clashes)
}

/* ---------- pins ---------- */

export function isPinned(state: GameState, key: string): boolean {
  return state.calendarPins.includes(key)
}

/** ★ on or off. Only well-formed keys for this week or later are kept. */
export function togglePin(input: GameState, key: string): GameState {
  const last = pinLastWeek(key)
  if (last === null) return input
  const state = structuredClone(input)
  state.calendarPins = state.calendarPins.includes(key) ? state.calendarPins.filter((k) => k !== key) : last >= state.week ? [...state.calendarPins, key] : state.calendarPins
  return state
}

/** Drops pins whose occurrence is over (an event's week, or an expedition's month, has passed). */
export function prunePins(pins: readonly string[], week: number): string[] {
  return pins.filter((k) => {
    const last = pinLastWeek(k)
    return last !== null && last >= week
  })
}

export interface PinnedItem {
  key: string
  /** The week it starts (an expedition: the month's first week). */
  week: number
  name: string
  kind: 'event' | 'expedition'
  /** The tournament event or expedition site id. */
  id: string
}

/** The pins that still lie ahead (or are on now), soonest first. */
export function pinnedItems(state: GameState): PinnedItem[] {
  const out: PinnedItem[] = []
  for (const key of state.calendarPins) {
    const p = parsePin(key)
    const last = pinLastWeek(key)
    if (!p || last === null || last < state.week) continue
    const event = EVENT_BY_ID[p.id]
    const site = EXPEDITION_SITE_BY_ID[p.id as ExpeditionSite['id']]
    if (event) out.push({ key, week: p.week, name: event.name, kind: 'event', id: p.id })
    else if (site) out.push({ key, week: p.week, name: site.name, kind: 'expedition', id: p.id })
  }
  return out.sort((a, b) => a.week - b.week)
}

/** True when a pinned cup is held this week (the Battle button's dot). */
export function pinnedEventThisWeek(state: GameState): boolean {
  return pinnedItems(state).some((p) => p.kind === 'event' && p.week === state.week)
}

/* ---------- the date bar's "Next:" line ---------- */

export interface NextUp {
  name: string
  week: number
  /** Weeks from now (0 = this week). */
  inWeeks: number
  pinned: boolean
}

/** How far the "Next:" line looks for a notable event the monster can enter. */
const NEXT_HORIZON = WEEKS_PER_YEAR

/** The next notable event the monster can enter, or the next pinned item if that comes sooner (a tie goes to the pin). */
export function nextUp(state: GameState): NextUp | null {
  if (!state.monster) return null
  const pin = pinnedItems(state)[0] ?? null
  let found: NextUp | null = null
  for (let w = state.week; w < state.week + NEXT_HORIZON && !found; w++) {
    for (const e of eventsAt(weekInYear(w), dateOf(w).year)) {
      if (!isNotable(e) || !entryCheck(state, e, w).eligible) continue
      found = { name: e.name, week: w, inWeeks: w - state.week, pinned: false }
      break
    }
  }
  if (pin && (!found || Math.max(pin.week, state.week) <= found.week)) {
    const week = Math.max(pin.week, state.week)
    return { name: pin.name, week, inWeeks: week - state.week, pinned: true }
  }
  return found
}

/** The grade a cup sits at for the monster today: an Official's is the monster's own (and promotion). */
export function gradeLine(event: TournamentEvent, grade: TournamentGrade): { kind: 'own' | 'any' | 'fixed' | 'invite'; grade: TournamentGrade } {
  if (event.kind === 'crown' || event.kind === 'legend') return { kind: 'invite', grade: 'S' }
  if (event.grade === 'own') return { kind: 'own', grade }
  if (event.grade === 'any') return { kind: 'any', grade }
  return { kind: 'fixed', grade: event.grade }
}

/** The lowest grade that may enter a fixed-grade cup (one below its grade, §13). */
export function lowestEntryGrade(event: TournamentEvent): TournamentGrade | null {
  if (event.grade === 'own' || event.grade === 'any') return null
  const i = Math.max(0, gradeIndex(event.grade) - 2)
  return TOURNAMENT_GRADES[i]!
}
