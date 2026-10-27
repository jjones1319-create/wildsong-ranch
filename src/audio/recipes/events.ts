/**
 * SOUND_UPGRADE §7.4: the per-event arrangement table, one row for every event in `data/calendar.ts`.
 * Each row names the theme, the season palette and kit, the lead instrument, a transposition (−3…+3), a
 * tempo nudge (−6…+6 quarter-note BPM), the crowd and a note. The rows are computed from the calendar and
 * the §7.4 rules, then `OVERRIDES` (plain data the owner can edit) wins. In S1 every theme is `cup` in its
 * season palette; the S2 compositions are marked TODO_S2 and take over when they exist.
 */
import { dateOf, seasonOf } from '../../core/calendar.ts'
import { EVENTS } from '../../data/calendar.ts'
import type { Season } from '../../data/types.ts'
import type { CrowdSize } from './ambience.ts'
import type { InstrumentId } from './instruments.ts'
import type { KitId } from './kits.ts'

export const THEME_IDS = ['cup', 'open', 'ascension', 'crown-dawn', 'crown-tides', 'crown-embers', 'crown-frost', 'legend', 'masquerade', 'rival', 'summit', 'rally', 'rally-rogue', 'sprout', 'elders', 'trial', 'practice'] as const
export type ThemeId = (typeof THEME_IDS)[number]

/** Themes that exist as songs in this stage. The rest map to `cup` until S2. */
export const WRITTEN_THEMES: readonly ThemeId[] = ['cup']

export interface SeasonPalette {
  leads: readonly [InstrumentId, InstrumentId]
  kit: KitId
  colour: InstrumentId
}

export const SEASON_PALETTES: Record<Season, SeasonPalette> = {
  Spring: { leads: ['flute', 'recorder-alto'], kit: 'meadow', colour: 'harp' },
  Summer: { leads: ['marimba', 'kalimba'], kit: 'festival', colour: 'glock' },
  Autumn: { leads: ['ocarina', 'cellos'], kit: 'harvest', colour: 'strumstick' },
  Winter: { leads: ['vibes', 'violins'], kit: 'frost', colour: 'glock' },
}

export interface EventArrangement {
  event: string
  /** The composition the event wants. */
  theme: ThemeId
  /** What plays in this stage (a written theme). */
  plays: ThemeId
  palette: Season
  kit: KitId
  lead: InstrumentId
  colour: InstrumentId
  transpose: number
  tempoNudge: number
  /** Elimination cups: a drier reverb send. */
  musicSend: number
  crowd: CrowdSize
  note: string
  status: 'S1' | 'TODO_S2'
}

/** Hand edits: any field of a row, by event id. */
export const OVERRIDES: Partial<Record<string, Partial<EventArrangement>>> = {
  iron: { kit: 'wild', lead: 'cellos', note: 'powOnly: a heavier kit and cello drive' },
  arcane: { lead: 'vibes', note: 'intOnly: a glassy colour (vibes; wine glasses join in S3)' },
  'lantern-festival': { lead: 'kalimba', colour: 'hand-chimes', note: 'glock and hand chimes' },
  'kite-day': { lead: 'flute', colour: 'harp', note: 'flute and light tambourine' },
  firefly: { lead: 'kalimba', colour: 'glock', note: 'fireflies: kalimba and glock sparks' },
  snowflake: { lead: 'violins', colour: 'glock', note: 'crystalline violins and glock' },
  starlight: { lead: 'vibes', colour: 'hand-chimes', note: 'starlight: vibes and hand chimes' },
}

function hash(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619)
  return h >>> 0
}

function themeFor(kind: string, rule: string | undefined, id: string): ThemeId {
  if (kind === 'open') return 'open'
  if (kind === 'official') return 'ascension'
  if (kind === 'crown') return id.replace('crown-of-', 'crown-') as ThemeId
  if (kind === 'legend') return 'legend'
  if (kind === 'masquerade') return 'masquerade'
  if (kind === 'rival') return 'rival'
  if (kind === 'summit' || kind === 'summitQualifier') return 'summit'
  if (rule === 'hero') return 'rally'
  if (rule === 'rogue') return 'rally-rogue'
  if (rule === 'sprout') return 'sprout'
  if (rule === 'elders') return 'elders'
  return 'cup'
}

function crowdFor(kind: string): CrowdSize {
  switch (kind) {
    case 'open':
    case 'rival':
      return 'medium'
    case 'official':
      return 'large'
    case 'crown':
      return 'large+'
    case 'legend':
      return 'huge'
    case 'masquerade':
      return 'hushed'
    case 'summit':
      return 'chanting'
    default:
      return 'small'
  }
}

function build(): EventArrangement[] {
  const rows: EventArrangement[] = []
  let previous: EventArrangement | null = null
  for (const e of EVENTS) {
    const season = seasonOf(dateOf(e.week).month)
    const palette = SEASON_PALETTES[season]
    const theme = themeFor(e.kind, e.rule, e.id)
    const elimination = e.format.startsWith('Elim')
    const h = hash(e.id)
    let lead = palette.leads[h % 2]!
    let kit: KitId = elimination ? 'knockout' : palette.kit
    // Neighbouring cups never share both lead and kit.
    if (previous && previous.lead === lead && previous.kit === kit) lead = palette.leads[(h + 1) % 2]!
    const row: EventArrangement = {
      event: e.id,
      theme,
      plays: WRITTEN_THEMES.includes(theme) ? theme : 'cup',
      palette: season,
      kit,
      lead,
      colour: palette.colour,
      transpose: (h % 7) - 3,
      tempoNudge: ((h >>> 8) % 9) - 4 + (elimination ? 4 : 0),
      musicSend: elimination ? 0.14 : 0.22,
      crowd: crowdFor(e.kind),
      note: elimination ? 'elimination: knockout kit, drier, +4 BPM' : '',
      status: WRITTEN_THEMES.includes(theme) ? 'S1' : 'TODO_S2',
    }
    const o = OVERRIDES[e.id]
    const merged = o ? { ...row, ...o } : row
    rows.push(merged)
    previous = merged
  }
  return rows
}

export const EVENT_ARRANGEMENTS: readonly EventArrangement[] = build()

export const EVENT_ARRANGEMENT_BY_ID: Record<string, EventArrangement> = Object.fromEntries(EVENT_ARRANGEMENTS.map((r) => [r.event, r]))

/** The row for a Journey Trial or the Lab, which are not calendar events. */
export const TRIAL_ARRANGEMENT: EventArrangement = { event: 'trial', theme: 'trial', plays: 'cup', palette: 'Autumn', kit: 'wild', lead: 'ocarina', colour: 'strumstick', transpose: 0, tempoNudge: -4, musicSend: 0.2, crowd: 'none', note: 'TODO_S2: the trial theme at the site tonic', status: 'TODO_S2' }
export const PRACTICE_ARRANGEMENT: EventArrangement = { event: 'practice', theme: 'practice', plays: 'cup', palette: 'Summer', kit: 'festival', lead: 'marimba', colour: 'glock', transpose: 0, tempoNudge: -8, musicSend: 0.18, crowd: 'none', note: 'TODO_S2: the light practice theme', status: 'TODO_S2' }
