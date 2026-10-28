import { describe, expect, it } from 'vitest'
import { EVENTS } from '../data/calendar.ts'
import { SEASONS, WEATHERS } from '../data/types.ts'
import { SCREENS } from '../ui/router.ts'
import { JOURNEY_SITE_IDS } from '../data/types.ts'
import { arrangementFor, decide, resultStingers, STAND_INS, TENSION_HP, TENSION_SECONDS, type Scene, type SongRequest } from './director.ts'
import { EVENT_ARRANGEMENT_BY_ID, THEME_DEFAULTS, TRIAL_SITES } from './recipes/events.ts'

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

  it('every event plays its own theme in the lobby with its row, the events pack wanted and no stand-in (S2)', () => {
    for (const e of EVENTS) {
      const r = decide({ ...base, screen: 'tournamentPlay', eventId: e.id })
      const song = r.song as SongRequest
      const row = EVENT_ARRANGEMENT_BY_ID[e.id]!
      expect(song.id, e.id).toBe(row.theme)
      expect(song.layers).toEqual(['lobby'])
      expect(song.lead).toBe(row.lead)
      expect(song.kit).toBe(row.kit)
      expect(song.colour).toBe(row.colour)
      expect(song.transpose).toBe(row.transpose)
      expect(song.arrangement).toBe(row.arrangement)
      expect(r.bed).toBe('arena')
      expect(r.packs).toContain('events')
      expect(r.standIn).toBeNull()
    }
    expect((decide({ ...base, screen: 'tournamentPlay', eventId: 'summit-qualifier' }).song as SongRequest).arrangement).toBe('qualifier')
  })

  const fight = (eventId: string | null, origin: 'cup' | 'trial' | 'lab' | 'versus', extra: Partial<Scene> = {}): Scene => ({ ...base, screen: 'battle', eventId, battle: { phase: 'match', origin, hp: [1, 1], secondsLeft: 50, matchSeconds: 60, paused: false, speed: 1 }, ...extra })

  it('a match against Corin plays rival with the event’s lead and kit; the cup screens around it keep the event theme', () => {
    const inCup = decide(fight('meadow', 'cup', { opponentRivalId: 'corin-hale' })).song as SongRequest
    const meadow = EVENT_ARRANGEMENT_BY_ID.meadow!
    expect(inCup.id).toBe('rival')
    expect(inCup.lead).toBe(meadow.lead)
    expect(inCup.kit).toBe(meadow.kit)
    expect(THEME_DEFAULTS.rival.bpm + inCup.tempoNudge).toBeGreaterThanOrEqual(100)
    expect(THEME_DEFAULTS.rival.bpm + inCup.tempoNudge).toBeLessThanOrEqual(132)
    const inCrown = decide(fight('crown-of-frost', 'cup', { opponentRivalId: 'corin-hale' })).song as SongRequest
    expect(inCrown.id).toBe('rival')
    expect(inCrown.lead).toBe(THEME_DEFAULTS['crown-frost'].lead)
    expect(inCrown.kit).toBe('frost')
    expect((decide(fight('rival-showdown', 'cup', { opponentRivalId: 'corin-hale' })).song as SongRequest).id).toBe('rival')
    // Not on the lobby screens: his calling card plays there.
    expect((decide({ ...base, screen: 'tournamentPlay', eventId: 'meadow', opponentRivalId: 'corin-hale' }).song as SongRequest).id).toBe('cup')
  })

  it('Trials play the trial theme at the site’s tonic with its lead; the Lab plays practice', () => {
    for (const site of JOURNEY_SITE_IDS) {
      const song = decide(fight(null, 'trial', { journeySite: site })).song as SongRequest
      expect(song.id).toBe('trial')
      expect(song.transpose).toBe(TRIAL_SITES[site].transpose)
      expect(song.lead).toBe(TRIAL_SITES[site].lead)
      expect(song.colour).toBe(TRIAL_SITES[site].colour)
    }
    expect((decide(fight(null, 'trial', { journeySite: 'glacier-bastion' })).song as SongRequest).leadArt).toBe('trem')
    expect(arrangementFor({ ...base, battle: { phase: 'match', origin: 'trial', hp: [1, 1], secondsLeft: 60, matchSeconds: 60, paused: false, speed: 1 } }).theme).toBe('trial')
    for (const origin of ['lab', 'versus'] as const) {
      const r = decide(fight(null, origin))
      expect((r.song as SongRequest).id).toBe('practice')
      expect(r.crowd).toBe('none')
    }
  })

  it('the crowd claps along in the last 10 s, except a hushed hall or no crowd', () => {
    const last = (eventId: string, secondsLeft: number): Scene => ({ ...base, screen: 'battle', eventId, battle: { phase: 'match', origin: 'cup', hp: [1, 1], secondsLeft, matchSeconds: 60, paused: false, speed: 1 } })
    expect(decide(last('meadow', 30)).clapAlong).toBe(false)
    expect(decide(last('meadow', TENSION_SECONDS)).clapAlong).toBe(true)
    expect(decide(last('vale-coast-summit', 5)).crowd).toBe('chanting')
    expect(decide(last('vale-coast-summit', 5)).clapAlong).toBe(true)
    expect(decide(last('masquerade', 5)).crowd).toBe('hushed')
    expect(decide(last('masquerade', 5)).clapAlong).toBe(false)
    expect(decide({ ...last('meadow', 5), battle: { ...last('meadow', 5).battle!, phase: 'result' } }).clapAlong).toBe(false)
  })

  it('the results screen chains the right stingers', () => {
    const r = (o: Partial<Parameters<typeof resultStingers>[0]>) => resultStingers({ eventId: 'meadow', placing: 1, participants: 4, koed: false, promoted: null, rankBefore: 1, rankAfter: 1, titles: [], relayTeamWin: null, ...o })
    expect(r({})).toEqual(['cupWin'])
    expect(r({ placing: 2 })).toEqual(['cupPlaced'])
    expect(r({ placing: 4 })).toEqual(['cupOut'])
    expect(r({ placing: 2, koed: true })).toEqual(['cupOut'])
    expect(r({ eventId: 'masquerade', placing: 2, participants: 2 })).toEqual(['cupOut'])
    expect(r({ eventId: 'crown-of-tides' })).toEqual(['crownWonTides'])
    expect(r({ eventId: 'wildsong-legend' })).toEqual(['legendWon'])
    expect(r({ eventId: 'spring-ascension', promoted: 'B' })).toEqual(['promotion'])
    expect(r({ rankAfter: 2, titles: ['x'] })).toEqual(['cupWin', 'rankUp', 'titleEarned'])
    expect(r({ eventId: 'vale-coast-summit', placing: 3, relayTeamWin: true })).toEqual(['cupWin'])
    expect(r({ eventId: 'vale-coast-summit', placing: 1, relayTeamWin: false })).toEqual(['cupOut'])
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
    expect(decide({ ...base, screen: 'labSound' }).packs).toContain('events')
    expect(decide({ ...base, screen: 'oddJobs', oddJob: 'dash' })).toMatchObject({ bed: 'meadow', reverb: 'outdoor', standIn: 'TODO_S3' })
    expect(decide({ ...base, screen: 'oddJobs', oddJob: 'dash' }).song).toMatchObject({ id: 'town', stem: 'oddJobs' })
    expect(STAND_INS.some((x) => x.what === 'Meadow Dash')).toBe(true)
    expect(STAND_INS.every((x) => x.stage === 'TODO_S3')).toBe(true)
    expect(STAND_INS.length).toBeGreaterThan(5)
    expect(decide({ ...base, screen: 'title' }).song).toMatchObject({ id: 'wildsong', arrangement: null })
    expect(decide({ ...base, screen: 'newGame' }).song).toMatchObject({ id: 'wildsong', arrangement: 'lobby' })
    expect(decide({ ...base, screen: 'creditsRoll' }).song).toMatchObject({ id: 'wildsong', arrangement: 'credits' })
  })
})
