/**
 * SOUND_UPGRADE §7.4: the per-event arrangement table, one row for every event in `data/calendar.ts`.
 * Each row names the theme, the season palette and kit, the lead instrument (and its articulation when it
 * changes), the colour instrument, a named arrangement, a transposition (−3…+3), a tempo nudge (−6…+6
 * quarter-note BPM, +4 more for elimination cups), the reverb send, the crowd and a note. The rows are
 * computed from the calendar and the §7.4 rules, then `OVERRIDES` (plain data the owner can edit) wins.
 *
 * Regular cups share the `cup` theme in their season's palette; every big event plays its own composition
 * (S2) with its own lead and kit, which `THEME_DEFAULTS` records so the rows stay concrete without loading
 * the songs (a test checks it against them). Journey Trials and the Lab have rows of their own.
 */
import { dateOf, seasonOf } from '../../core/calendar.ts'
import { EVENTS } from '../../data/calendar.ts'
import type { JourneySiteId, Season } from '../../data/types.ts'
import type { CrowdSize } from './ambience.ts'
import type { InstrumentId } from './instruments.ts'
import type { KitId } from './kits.ts'

export const THEME_IDS = ['cup', 'open', 'ascension', 'crown-dawn', 'crown-tides', 'crown-embers', 'crown-frost', 'legend', 'masquerade', 'rival', 'summit', 'rally', 'rally-rogue', 'sprout', 'elders', 'trial', 'practice'] as const
export type ThemeId = (typeof THEME_IDS)[number]

/** Every theme is written as of S2. */
export const WRITTEN_THEMES: readonly ThemeId[] = THEME_IDS

export interface ThemeDefaults {
  /** The instrument of the song's `lead` line. */
  lead: InstrumentId
  /** The song's kit for its role-based percussion lines. */
  kit: KitId
  /** Quarter-note BPM (6/8 counts a dotted quarter as 1.5). */
  bpm: number
  /** The instrument of the song's `colour` line. */
  colour: InstrumentId
}

/** Each theme's own lead, kit, tempo and colour, as written in its song file (checked by a test). */
export const THEME_DEFAULTS: Record<ThemeId, ThemeDefaults> = {
  cup: { lead: 'ocarina', kit: 'meadow', bpm: 120, colour: 'harp' },
  open: { lead: 'strumstick', kit: 'festival', bpm: 126, colour: 'glock' },
  ascension: { lead: 'violins', kit: 'ceremony', bpm: 112, colour: 'harp' },
  'crown-dawn': { lead: 'violins', kit: 'ceremony', bpm: 116, colour: 'glock' },
  'crown-tides': { lead: 'flute', kit: 'tide', bpm: 114, colour: 'harp' },
  'crown-embers': { lead: 'flute', kit: 'harvest', bpm: 126, colour: 'strumstick' },
  'crown-frost': { lead: 'vibes', kit: 'frost', bpm: 108, colour: 'wine-glasses' },
  legend: { lead: 'violins', kit: 'ceremony', bpm: 120, colour: 'glock' },
  masquerade: { lead: 'clarinet', kit: 'masque', bpm: 126, colour: 'harpsichord' },
  rival: { lead: 'violins', kit: 'festival', bpm: 124, colour: 'strumstick' },
  summit: { lead: 'ocarina', kit: 'festival', bpm: 116, colour: 'glock' },
  rally: { lead: 'violins', kit: 'wild', bpm: 118, colour: 'harp' },
  'rally-rogue': { lead: 'clarinet', kit: 'knockout', bpm: 118, colour: 'harp' },
  sprout: { lead: 'kalimba', kit: 'meadow', bpm: 108, colour: 'glock' },
  elders: { lead: 'recorder-tenor', kit: 'meadow', bpm: 100, colour: 'harp' },
  trial: { lead: 'recorder-tenor', kit: 'wild', bpm: 116, colour: 'strumstick' },
  practice: { lead: 'marimba', kit: 'meadow', bpm: 112, colour: 'kalimba' },
}

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
  /** The composition the event plays. */
  theme: ThemeId
  /** What plays (the same as `theme` now that every theme is written; kept for the Lab and older notes). */
  plays: ThemeId
  palette: Season
  kit: KitId
  lead: InstrumentId
  /** The lead's articulation when the row asks for one (a violin tremolo); null keeps the line's. */
  leadArt: string | null
  colour: InstrumentId
  /** A named arrangement of the theme (the Summit Qualifier), or null. */
  arrangement: string | null
  transpose: number
  tempoNudge: number
  /** Reverb send 0–1 (elimination cups are drier); null keeps the song's own. */
  musicSend: number | null
  crowd: CrowdSize
  note: string
  status: 'S2'
}

/** Hand edits: any field of a row, by event id. */
export const OVERRIDES: Partial<Record<string, Partial<EventArrangement>>> = {
  iron: { kit: 'wild', lead: 'cellos', note: 'powOnly: a heavier kit and cello drive' },
  arcane: { lead: 'vibes', colour: 'wine-glasses', note: 'intOnly: a glassy colour, vibes doubled with wine glasses' },
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

export function crowdFor(kind: string): CrowdSize {
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

function themeRow(event: string, theme: ThemeId, season: Season, crowd: CrowdSize, note: string): EventArrangement {
  const d = THEME_DEFAULTS[theme]
  return { event, theme, plays: theme, palette: season, kit: d.kit, lead: d.lead, leadArt: null, colour: d.colour, arrangement: null, transpose: 0, tempoNudge: 0, musicSend: null, crowd, note, status: 'S2' }
}

function build(): EventArrangement[] {
  const rows: EventArrangement[] = []
  let previous: EventArrangement | null = null
  for (const e of EVENTS) {
    const season = seasonOf(dateOf(e.week).month)
    const palette = SEASON_PALETTES[season]
    const theme = themeFor(e.kind, e.rule, e.id)
    const crowd = crowdFor(e.kind)
    let row: EventArrangement
    if (theme === 'cup') {
      const elimination = e.format.startsWith('Elim')
      const h = hash(e.id)
      let lead = palette.leads[h % 2]!
      const kit: KitId = elimination ? 'knockout' : palette.kit
      // Neighbouring cups never share both lead and kit.
      if (previous && previous.lead === lead && previous.kit === kit) lead = palette.leads[(h + 1) % 2]!
      row = {
        ...themeRow(e.id, 'cup', season, crowd, elimination ? 'elimination: knockout kit, drier, +4 BPM' : ''),
        kit,
        lead,
        colour: palette.colour,
        transpose: (h % 7) - 3,
        tempoNudge: ((h >>> 8) % 9) - 4 + (elimination ? 4 : 0),
        musicSend: elimination ? 0.14 : 0.22,
      }
    } else if (theme === 'ascension') {
      // The Ascensions are tinted by their season: the colour line takes the season's colour.
      row = { ...themeRow(e.id, theme, season, crowd, `tinted by ${season.toLowerCase()}: ${palette.colour}`), colour: palette.colour }
    } else if (e.kind === 'summitQualifier') {
      row = { ...themeRow(e.id, theme, season, crowd, 'the Summit with fewer layers'), arrangement: 'qualifier', crowd: 'medium' }
    } else {
      row = themeRow(e.id, theme, season, crowd, '')
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

/** §7.4 Journey sites: the Trial theme moves to the site's tonic and takes the site's lead and doubling. */
export const TRIAL_SITES: Record<JourneySiteId, { tonic: string; transpose: number; lead: InstrumentId; leadArt: string | null; colour: InstrumentId; note: string }> = {
  'iron-quarry': { tonic: 'E', transpose: 0, lead: 'recorder-tenor', leadArt: null, colour: 'strumstick', note: 'tenor recorder' },
  'windrun-steppe': { tonic: 'A', transpose: 5, lead: 'flute', leadArt: null, colour: 'harp', note: 'flute' },
  'starfall-observatory': { tonic: 'B', transpose: -5, lead: 'vibes', leadArt: null, colour: 'wine-glasses', note: 'vibes doubled with wine glass' },
  'archers-glade': { tonic: 'G', transpose: 3, lead: 'recorder-alto', leadArt: null, colour: 'balafon', note: 'alto recorder and balafon' },
  'glacier-bastion': { tonic: 'D', transpose: -2, lead: 'violins', leadArt: 'trem', colour: 'vibes', note: 'violin tremolo and vibes' },
}

export const TRIAL_ARRANGEMENTS: Record<JourneySiteId, EventArrangement> = Object.fromEntries(
  (Object.entries(TRIAL_SITES) as [JourneySiteId, (typeof TRIAL_SITES)[JourneySiteId]][]).map(([site, s]) => [
    site,
    { ...themeRow(`trial:${site}`, 'trial', 'Autumn', 'none', `${s.tonic}: ${s.note}`), lead: s.lead, leadArt: s.leadArt, colour: s.colour, transpose: s.transpose },
  ]),
) as Record<JourneySiteId, EventArrangement>

/** A Trial whose site is unknown plays the Iron Quarry's row (the theme's own key). */
export const TRIAL_ARRANGEMENT: EventArrangement = TRIAL_ARRANGEMENTS['iron-quarry']

/** The Monster Lab's Versus and the Battle Lab: the light practice theme. */
export const PRACTICE_ARRANGEMENT: EventArrangement = themeRow('practice', 'practice', 'Summer', 'none', 'the light practice theme')

/**
 * §11.10 a match against Corin Hale plays `rival` with the event's lead and kit (in the Rival Showdown the
 * row is already `rival`). The tempo nudge is clamped so the rival tempo stays inside the battle band.
 */
export function corinRow(row: EventArrangement): EventArrangement {
  if (row.theme === 'rival') return row
  const bpm = THEME_DEFAULTS.rival.bpm
  const nudge = Math.max(100 - bpm, Math.min(132 - bpm, row.tempoNudge))
  return { ...row, theme: 'rival', plays: 'rival', transpose: 0, tempoNudge: nudge, arrangement: null, note: `Corin Hale: the rival theme with ${row.event}'s lead and kit` }
}
