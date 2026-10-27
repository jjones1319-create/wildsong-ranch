import { describe, expect, it } from 'vitest'
import { EVENTS } from '../data/calendar.ts'
import cup from './music/songs/cup.ts'
import { EVENT_ARRANGEMENT_BY_ID, EVENT_ARRANGEMENTS, PRACTICE_ARRANGEMENT, SEASON_PALETTES, THEME_IDS, TRIAL_ARRANGEMENT } from './recipes/events.ts'
import { INSTRUMENTS, playableRange } from './recipes/instruments.ts'
import { isKitId } from './recipes/kits.ts'
import { manifestRoots } from './songs.test.ts'

const roots = manifestRoots()

describe('the per-event arrangement table (§7.4)', () => {
  it('has a valid row for every event', () => {
    expect(EVENT_ARRANGEMENTS).toHaveLength(EVENTS.length)
    for (const e of EVENTS) {
      const row = EVENT_ARRANGEMENT_BY_ID[e.id]
      expect(row, e.id).toBeTruthy()
      expect(THEME_IDS).toContain(row!.theme)
      expect(THEME_IDS).toContain(row!.plays)
      expect(isKitId(row!.kit)).toBe(true)
      expect(INSTRUMENTS[row!.lead]).toBeTruthy()
      expect(INSTRUMENTS[row!.colour]).toBeTruthy()
      expect(row!.transpose).toBeGreaterThanOrEqual(-3)
      expect(row!.transpose).toBeLessThanOrEqual(3)
      expect(Math.abs(row!.tempoNudge)).toBeLessThanOrEqual(8)
      expect(SEASON_PALETTES[row!.palette]).toBeTruthy()
      // In S1 only the cup is written; everything else is a stand-in.
      expect(row!.plays).toBe('cup')
      if (row!.theme !== 'cup') expect(row!.status).toBe('TODO_S2')
    }
  })

  it('keeps the effective tempo inside 100–132 and the elimination rules', () => {
    for (const row of [...EVENT_ARRANGEMENTS, TRIAL_ARRANGEMENT, PRACTICE_ARRANGEMENT]) {
      const tempo = cup.bpm + row.tempoNudge
      expect(tempo, row.event).toBeGreaterThanOrEqual(100)
      expect(tempo, row.event).toBeLessThanOrEqual(132)
    }
    for (const e of EVENTS) {
      const row = EVENT_ARRANGEMENT_BY_ID[e.id]!
      if (e.format.startsWith('Elim')) {
        expect(row.kit).toBe('knockout')
        expect(row.musicSend).toBeLessThan(0.2)
        expect(row.tempoNudge).toBeGreaterThanOrEqual(0)
      }
    }
  })

  it('neighbouring cups never share both lead and kit', () => {
    for (let i = 1; i < EVENT_ARRANGEMENTS.length; i++) {
      const a = EVENT_ARRANGEMENTS[i - 1]!
      const b = EVENT_ARRANGEMENTS[i]!
      expect(a.lead === b.lead && a.kit === b.kit, `${a.event} and ${b.event}`).toBe(false)
    }
  })

  it('every row keeps the cup lead inside its lead instrument after transposition and octave folding (rules 2–3)', () => {
    const lead = cup.lines.find((l) => l.id === 'lead')!
    for (const row of EVENT_ARRANGEMENTS) {
      const def = INSTRUMENTS[row.lead]
      const art = def.arts[0]!
      const range = playableRange(roots, row.lead, art)
      expect(range, `${row.lead} has samples`).not.toBeNull()
      const melody = def.melody!
      for (const sec of Object.values(cup.sections)) {
        for (const e of sec.events[lead.id] ?? []) {
          for (const p of e.pitches) {
            let m = p + row.transpose
            while (m < melody[0]) m += 12
            while (m > melody[1]) m -= 12
            expect(m, `${row.event}: ${row.lead} ${m}`).toBeGreaterThanOrEqual(range![0])
            expect(m, `${row.event}: ${row.lead} ${m}`).toBeLessThanOrEqual(range![1])
          }
        }
      }
    }
  })

  it('the hand overrides apply', () => {
    expect(EVENT_ARRANGEMENT_BY_ID.iron!.kit).toBe('wild')
    expect(EVENT_ARRANGEMENT_BY_ID.iron!.lead).toBe('cellos')
    expect(EVENT_ARRANGEMENT_BY_ID.arcane!.lead).toBe('vibes')
    expect(EVENT_ARRANGEMENT_BY_ID['kite-day']!.lead).toBe('flute')
  })
})
