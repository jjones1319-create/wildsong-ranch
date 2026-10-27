import { describe, expect, it } from 'vitest'
import { EVENTS } from '../data/calendar.ts'
import { RIVALS } from '../data/rivals.ts'
import { loadAllSongs } from './music/songs/index.ts'
import { lineFoldShift, foldedPitches, type Song } from './music/song.ts'
import { EVENT_ARRANGEMENT_BY_ID, EVENT_ARRANGEMENTS, PRACTICE_ARRANGEMENT, SEASON_PALETTES, THEME_DEFAULTS, THEME_IDS, TRIAL_ARRANGEMENTS, corinRow, type EventArrangement } from './recipes/events.ts'
import { articulationOf, INSTRUMENTS, nearestRoot, playableRange } from './recipes/instruments.ts'
import { isKitId } from './recipes/kits.ts'
import { manifestRoots } from './songs.test.ts'

const roots = manifestRoots()
const songs = await loadAllSongs()
const ALL_ROWS: readonly EventArrangement[] = [...EVENT_ARRANGEMENTS, ...Object.values(TRIAL_ARRANGEMENTS), PRACTICE_ARRANGEMENT]

describe('the per-event arrangement table (§7.4)', () => {
  it('has a valid row for every event, and every row plays its own written theme', () => {
    expect(EVENT_ARRANGEMENTS).toHaveLength(EVENTS.length)
    for (const e of EVENTS) {
      const row = EVENT_ARRANGEMENT_BY_ID[e.id]
      expect(row, e.id).toBeTruthy()
      expect(THEME_IDS).toContain(row!.theme)
      expect(row!.plays).toBe(row!.theme)
      expect(row!.status).toBe('S2')
      expect(isKitId(row!.kit)).toBe(true)
      expect(INSTRUMENTS[row!.lead]).toBeTruthy()
      expect(INSTRUMENTS[row!.colour]).toBeTruthy()
      expect(row!.transpose).toBeGreaterThanOrEqual(-3)
      expect(row!.transpose).toBeLessThanOrEqual(3)
      expect(Math.abs(row!.tempoNudge)).toBeLessThanOrEqual(8)
      expect(SEASON_PALETTES[row!.palette]).toBeTruthy()
      if (row!.arrangement) expect(songs[row!.theme].arrangements?.[row!.arrangement], `${e.id} names ${row!.arrangement}`).toBeTruthy()
    }
    // The themes the calendar asks for.
    const themeOf = (id: string) => EVENT_ARRANGEMENT_BY_ID[id]!.theme
    expect(themeOf('new-year-open')).toBe('open')
    expect(themeOf('spring-ascension')).toBe('ascension')
    expect(themeOf('crown-of-embers')).toBe('crown-embers')
    expect(themeOf('wildsong-legend')).toBe('legend')
    expect(themeOf('masquerade')).toBe('masquerade')
    expect(themeOf('rival-showdown')).toBe('rival')
    expect(themeOf('summit-qualifier')).toBe('summit')
    expect(EVENT_ARRANGEMENT_BY_ID['summit-qualifier']!.arrangement).toBe('qualifier')
    expect(themeOf('heros-rally')).toBe('rally')
    expect(themeOf('rogues-rally')).toBe('rally-rogue')
    expect(themeOf('sprout')).toBe('sprout')
    expect(themeOf('elders')).toBe('elders')
    expect(themeOf('meadow')).toBe('cup')
  })

  it('THEME_DEFAULTS matches every song: its lead, kit, tempo and colour lines', () => {
    for (const id of THEME_IDS) {
      const song = songs[id]
      const d = THEME_DEFAULTS[id]
      expect(song.kind, id).toBe('battle')
      expect(song.lines.find((l) => l.id === 'lead')?.inst, `${id} lead`).toBe(d.lead)
      expect(song.lines.find((l) => l.id === 'colour')?.inst, `${id} colour`).toBe(d.colour)
      expect(song.kit, `${id} kit`).toBe(d.kit)
      expect(song.bpm, `${id} tempo`).toBe(d.bpm)
    }
  })

  it('keeps the effective tempo of every row inside 100–132 and the elimination rules', () => {
    for (const row of [...ALL_ROWS, ...EVENT_ARRANGEMENTS.map(corinRow)]) {
      const tempo = songs[row.theme].bpm + row.tempoNudge
      expect(tempo, row.event).toBeGreaterThanOrEqual(100)
      expect(tempo, row.event).toBeLessThanOrEqual(132)
    }
    for (const e of EVENTS) {
      const row = EVENT_ARRANGEMENT_BY_ID[e.id]!
      if (row.theme === 'cup' && e.format.startsWith('Elim')) {
        expect(row.kit).toBe('knockout')
        expect(row.musicSend!).toBeLessThan(0.2)
        expect(row.tempoNudge).toBeGreaterThanOrEqual(0)
      }
    }
  })

  it('neighbouring events never share both lead and kit', () => {
    for (let i = 1; i < EVENT_ARRANGEMENTS.length; i++) {
      const a = EVENT_ARRANGEMENTS[i - 1]!
      const b = EVENT_ARRANGEMENTS[i]!
      expect(a.lead === b.lead && a.kit === b.kit, `${a.event} and ${b.event}`).toBe(false)
    }
  })

  /** Checker rules 2–3 for a row: its lead and colour lines, moved onto the row's instruments and transposed, stay on samples. */
  function rowInRange(row: EventArrangement, song: Song): string[] {
    const bad: string[] = []
    for (const [lineId, inst, wantArt] of [['lead', row.lead, row.leadArt], ['lobbyLead', row.lead, null], ['colour', row.colour, null]] as const) {
      const line = song.lines.find((l) => l.id === lineId)
      if (!line) continue
      // The runtime swaps the lobby lead only when the row's lead is not the song's own.
      if (lineId === 'lobbyLead' && row.lead === song.lines.find((l) => l.id === 'lead')!.inst) continue
      const art = articulationOf(inst, wantArt ?? line.art)
      const range = playableRange(roots, inst, art)
      if (!range) {
        bad.push(`${row.event}: ${inst}/${art} has no samples`)
        continue
      }
      const list = roots[inst]?.[art] ?? []
      const moved = inst !== line.inst
      const shift = moved ? lineFoldShift(song, lineId, inst, row.transpose) : 0
      for (const sec of Object.values(song.sections)) {
        for (const e of sec.events[lineId] ?? []) {
          const pitches = moved ? foldedPitches(e.pitches, inst, row.transpose, shift) : e.pitches.map((p) => p + row.transpose)
          for (const p of pitches) if (INSTRUMENTS[inst].patch ? p < range[0] || p > range[1] : nearestRoot(list, p) === null) bad.push(`${row.event}: ${lineId} on ${inst} plays ${p}`)
        }
      }
    }
    return bad
  }

  it('every row keeps its theme’s lead and colour on samples after the swap, the transposition and octave folding (rules 2–3)', () => {
    const bad = ALL_ROWS.flatMap((row) => rowInRange(row, songs[row.theme]))
    expect(bad.slice(0, 12)).toEqual([])
  })

  it('a Corin match in any event keeps the rival theme on samples with that event’s lead', () => {
    const bad = EVENT_ARRANGEMENTS.map(corinRow).flatMap((row) => rowInRange(row, songs.rival))
    expect(bad.slice(0, 12)).toEqual([])
  })

  it('the hand overrides apply and every named rival exists', () => {
    expect(EVENT_ARRANGEMENT_BY_ID.iron!.kit).toBe('wild')
    expect(EVENT_ARRANGEMENT_BY_ID.iron!.lead).toBe('cellos')
    expect(EVENT_ARRANGEMENT_BY_ID.arcane!.lead).toBe('vibes')
    expect(EVENT_ARRANGEMENT_BY_ID.arcane!.colour).toBe('wine-glasses')
    expect(EVENT_ARRANGEMENT_BY_ID['kite-day']!.lead).toBe('flute')
    expect(RIVALS.some((r) => r.id === 'corin-hale')).toBe(true)
  })

  it('Ascensions take their season’s colour, Trials their site’s tonic and voices', () => {
    for (const e of EVENTS.filter((x) => x.kind === 'official')) {
      const row = EVENT_ARRANGEMENT_BY_ID[e.id]!
      expect(row.colour).toBe(SEASON_PALETTES[row.palette].colour)
    }
    expect(TRIAL_ARRANGEMENTS['windrun-steppe'].transpose).toBe(5)
    expect(TRIAL_ARRANGEMENTS['starfall-observatory'].colour).toBe('wine-glasses')
    expect(TRIAL_ARRANGEMENTS['archers-glade'].colour).toBe('balafon')
    expect(TRIAL_ARRANGEMENTS['glacier-bastion'].leadArt).toBe('trem')
  })
})
