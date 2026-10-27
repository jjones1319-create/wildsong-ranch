import { describe, expect, it } from 'vitest'
import { EVENTS } from '../data/calendar.ts'
import { SEASONS, WEATHERS } from '../data/types.ts'
import { SCREENS } from '../ui/router.ts'
import { arrangementFor, decide, STAND_INS, TENSION_HP, TENSION_SECONDS, type Scene } from './director.ts'

const base: Scene = { screen: 'ranch', season: 'Spring', weather: 'Sunny', eventId: null, opponentRivalId: null, battle: null, drill: null, journeySite: null, expeditionSite: null, oddJob: null }

describe('the director (§11)', () => {
  it('has an explicit decision for every screen', () => {
    for (const screen of SCREENS) {
      const r = decide({ ...base, screen })
      expect(r).toBeTruthy()
      expect(r.song === null || r.song === 'keep' || typeof r.song.id === 'string').toBe(true)
    }
  })

  it('the ranch plays the season song with its bed, and weather is handed through', () => {
    for (const season of SEASONS) {
      const r = decide({ ...base, season })
      expect(r.song).not.toBe('keep')
      expect((r.song as { id: string }).id).toBe(`ranch-${season.toLowerCase()}`)
      expect(r.bed).toBeTruthy()
      expect((r.song as { crossfadeSec: number }).crossfadeSec).toBe(2.5)
    }
    for (const weather of WEATHERS) expect(decide({ ...base, weather }).song).not.toBeNull()
  })

  it('every event has a row and every battle origin resolves; Corin takes the rival rule (a stand-in in S1)', () => {
    for (const e of EVENTS) {
      const r = decide({ ...base, screen: 'tournamentPlay', eventId: e.id })
      expect(r.song).not.toBe('keep')
      expect((r.song as { id: string }).id).toBe('cup')
      expect((r.song as { layers: readonly string[] }).layers).toEqual(['lobby'])
      expect(r.bed).toBe('arena')
    }
    const corin = arrangementFor({ ...base, eventId: 'rival-showdown', opponentRivalId: 'corin-hale' })
    expect(corin.standIn).toBe('TODO_S2')
    const trial = arrangementFor({ ...base, battle: { phase: 'match', origin: 'trial', hp: [1, 1], secondsLeft: 60, matchSeconds: 60, paused: false, speed: 1 } })
    expect(trial.row.event).toBe('trial')
    const lab = arrangementFor({ ...base, battle: { phase: 'match', origin: 'lab', hp: [1, 1], secondsLeft: 60, matchSeconds: 60, paused: false, speed: 1 } })
    expect(lab.row.event).toBe('practice')
  })

  it('battle layers build: base, then drive, then tension at low HP or in the last 10 s; pause is passed on', () => {
    const match = (hp: [number, number], secondsLeft: number, paused = false): Scene => ({ ...base, screen: 'battle', eventId: 'meadow', battle: { phase: 'match', origin: 'cup', hp, secondsLeft, matchSeconds: 60, paused, speed: 1 } })
    const start = decide(match([1, 1], 60))
    expect((start.song as { layers: readonly string[] }).layers).toEqual(['base'])
    const later = decide(match([1, 1], 50))
    expect((later.song as { layers: readonly string[] }).layers).toEqual(['base', 'drive'])
    const low = decide(match([TENSION_HP, 1], 50))
    expect((low.song as { layers: readonly string[] }).layers).toContain('tension')
    const last = decide(match([1, 1], TENSION_SECONDS))
    expect((last.song as { layers: readonly string[] }).layers).toContain('tension')
    expect(decide(match([1, 1], 50, true)).paused).toBe(true)
    expect(decide(match([1, 1], 50)).reverb).toBe('room')
    expect(decide(match([1, 1], 50)).crowd).toBe('small')
    const versus = decide({ ...base, screen: 'battle', battle: { phase: 'match', origin: 'versus', hp: [1, 1], secondsLeft: 50, matchSeconds: 60, paused: false, speed: 1 } })
    expect(versus.crowd).toBe('none')
    expect(versus.bed).toBeNull()
  })

  it('town screens share the town song with their stems and beds', () => {
    expect((decide({ ...base, screen: 'shop' }).song as { stem: string }).stem).toBe('shop')
    expect(decide({ ...base, screen: 'shop' }).bed).toBe('shop')
    expect((decide({ ...base, screen: 'guild' }).song as { stem: string }).stem).toBe('guild')
    expect((decide({ ...base, screen: 'journal' }).song as { stem: string }).stem).toBe('journal')
    expect(decide({ ...base, screen: 'library' }).bed).toBe('library')
    expect((decide({ ...base, screen: 'mail' }).song as { id: string }).id).toBe('town')
  })

  it('overlays keep the music, drills own it, and the stand-ins are listed', () => {
    expect(decide({ ...base, screen: 'settings' }).song).toBe('keep')
    expect(decide({ ...base, screen: 'calendar' }).bed).toBe('keep')
    const d = decide({ ...base, drill: 'waterfall-stand' })
    expect(d.drillOwned).toBe(true)
    expect(d.song).toBe('keep')
    expect(decide({ ...base, screen: 'shrine' }).standIn).toBe('TODO_S3')
    expect(decide({ ...base, screen: 'journey' }).standIn).toBe('TODO_S3')
    expect(decide({ ...base, screen: 'labSound' }).song).toBeNull()
    expect(STAND_INS.length).toBeGreaterThan(5)
    expect(decide({ ...base, screen: 'title' }).song).toMatchObject({ id: 'wildsong', arrangement: null })
    expect(decide({ ...base, screen: 'newGame' }).song).toMatchObject({ id: 'wildsong', arrangement: 'lobby' })
    expect(decide({ ...base, screen: 'creditsRoll' }).song).toMatchObject({ id: 'wildsong', arrangement: 'credits' })
  })
})
