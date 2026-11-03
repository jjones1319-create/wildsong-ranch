import { describe, expect, it } from 'vitest'
import { FREEZER, HOMECOMING, LIFESPAN } from '../data/tuning.ts'
import { newRanchmate } from './creation.ts'
import { dismissHomecoming, returnHome, welcomeHome, welcomeWhere } from './homecoming.ts'
import { heartstoneFrom } from './legacy.ts'
import { weeksLeft, type Monster } from './monster.ts'
import { createGameState, type GameState, type MemorialCause } from './state.ts'
import { makeMonster } from './test-helpers.ts'

/** A save that has never had its homecoming. */
function due(monster: Monster | null = makeMonster({ id: 'star' })): GameState {
  const s = createGameState({ monster })
  s.week = 300
  s.homecoming = { status: 'due', welcome: [] }
  s.away = { armedAt: 1_000, lastGreetAt: 2_000 }
  return s
}

function lost(id: string, cause: MemorialCause = 'neglected', week = 10): GameState['memorial'][number] {
  const m = makeMonster({ id, fatigue: 80, stress: 70 })
  m.status.sickWeeks = 1
  m.status.missingWeeks = 2
  m.status.clinicWeeks = 3
  return { monster: m, cause, epitaph: 'Gone too soon', week }
}

describe('returnHome', () => {
  it('heals the timers, rests and calms, and gives back at least 24 weeks of life with the warnings re-armed', () => {
    const m = lost('x').monster
    m.lifespanTotal = 200
    m.ageWeeks = 199
    m.status.warned48 = true
    m.status.warned10 = true
    m.status.warnedQuarterLife = true
    const back = returnHome(m)
    expect(back.status).toMatchObject({ sickWeeks: 0, missingWeeks: 0, clinicWeeks: 0 })
    expect(back.fatigue).toBe(0)
    expect(back.stress).toBe(HOMECOMING.stress)
    expect(weeksLeft(back)).toBe(HOMECOMING.minWeeksLeft)
    expect(back.status.warned48).toBe(true) // 24 ≤ 48
    expect(back.status.warned10).toBe(false) // the 10-week warning can come again
    // Plenty of life left: nothing added, and the warnings clear.
    const young = makeMonster({ id: 'y', stress: 5 })
    young.status.warned10 = true
    const fine = returnHome(young)
    expect(fine.lifespanTotal).toBe(young.lifespanTotal)
    expect(fine.stress).toBe(5)
    expect(fine.status.warned10).toBe(weeksLeft(fine) <= LIFESPAN.warnAtWeeksLeft[1]!)
  })
})

describe('welcomeHome: the one-time homecoming (§6.10)', () => {
  it('an empty ranch: the newest runaway becomes the star, the next takes the pen, the rest go to the Freezer', () => {
    const s = due(null)
    s.memorial = [lost('c', 'neglected', 30), lost('b', 'wandered', 20), lost('a', 'neglected', 10), lost('old', 'passed', 5)]
    const r = welcomeHome(s)
    expect(r.monster!.id).toBe('c')
    expect(r.ranchmates.map((m) => m.monster.id)).toEqual(['b'])
    expect(r.freezer.map((m) => m.id)).toEqual(['a'])
    expect(r.memorial.map((e) => e.monster.id)).toEqual(['old']) // returnees leave the wall; the passing stays
    expect(r.homecoming).toEqual({ status: 'done', welcome: ['c', 'b', 'a'] })
    expect(welcomeWhere(r, 'c')).toBe('star')
    expect(welcomeWhere(r, 'b')).toBe('pen')
    expect(welcomeWhere(r, 'a')).toBe('freezer')
    expect(r.mail[0]).toMatchObject({ kind: 'homecoming', ref: '3', read: false })
    expect(r.monster!.fatigue).toBe(0)
    expect(r.away.armedAt).toBeNull()
    expect(r.away.lastGreetAt).toBe(2_000)
    expect(s.homecoming.status).toBe('due') // pure
  })

  it('past the Freezer’s hard maximum a runaway stays on the Memorial wall (never lost)', () => {
    const s = due()
    s.ranchmates = [newRanchmate(makeMonster({ id: 'pen' }))]
    s.freezer = Array.from({ length: FREEZER.hardMax - 1 }, (_, i) => makeMonster({ id: `f${i}` }))
    s.memorial = [lost('x'), lost('y')]
    const r = welcomeHome(s)
    expect(r.freezer).toHaveLength(FREEZER.hardMax)
    expect(r.freezer.at(-1)!.id).toBe('x')
    expect(r.memorial.map((e) => e.monster.id)).toEqual(['y'])
    expect(r.homecoming.welcome).toEqual(['x'])
  })

  it('a runaway still waiting for its Farewell stays as the star', () => {
    const s = due()
    s.ended = 'neglected'
    s.monster!.fatigue = 90
    const r = welcomeHome(s)
    expect(r.ended).toBeNull()
    expect(r.monster!.id).toBe('star')
    expect(r.monster!.fatigue).toBe(0)
    expect(r.homecoming.welcome).toEqual(['star'])
    const wild = due()
    wild.ended = 'wandered'
    expect(welcomeHome(wild).ended).toBeNull()
  })

  it('old-age endings are left alone', () => {
    const s = due()
    s.ended = 'passed'
    s.memorial = [lost('p', 'passed'), lost('r', 'retired'), lost('f', 'fused'), lost('free', 'freed')]
    const r = welcomeHome(s)
    expect(r.ended).toBe('passed')
    expect(r.memorial).toHaveLength(4)
    expect(r.homecoming).toEqual({ status: 'done', welcome: [] })
    expect(r.mail).toEqual([]) // no letter when nobody came home
  })

  it('duplicate ids: only the newest entry counts, and an owned id never comes back twice', () => {
    const s = due()
    s.memorial = [lost('twice', 'neglected', 50), lost('twice', 'neglected', 40), lost('later', 'passed', 30), lost('later', 'neglected', 20), lost('star', 'neglected', 10)]
    const r = welcomeHome(s)
    expect(r.ranchmates.map((m) => m.monster.id)).toEqual(['twice'])
    expect(r.freezer).toEqual([])
    expect(r.memorial.map((e) => [e.monster.id, e.week])).toEqual([
      ['twice', 40],
      ['later', 30],
      ['later', 20],
      ['star', 10],
    ])
    expect(r.homecoming.welcome).toEqual(['twice'])
  })

  it('Heartstones and titles stay; a second passing leaves a stone with a new id', () => {
    const s = due()
    const entry = lost('hero')
    entry.monster.records.titles = ['Collector']
    s.memorial = [entry]
    s.titles = ['Collector']
    s.heartstones = [heartstoneFrom(entry.monster, 10)]
    const r = welcomeHome(s)
    expect(r.heartstones.map((h) => h.id)).toEqual(['hs-hero'])
    expect(r.titles).toEqual(['Collector'])
    expect(r.ranchmates[0]!.monster.records.titles).toEqual(['Collector'])
    expect(heartstoneFrom(r.ranchmates[0]!.monster, 400, r.heartstones).id).toBe('hs-hero-2')
  })

  it('runs only once, seeds the farm, and the card can be dismissed', () => {
    const s = due()
    s.memorial = [lost('a')]
    s.titles = ['Collector']
    s.farm = { xp: 0, pensBought: 0, tally: { titles: 0, cupsWon: 0, journeys: 0, expeditions: 0, breeds: 0, rank: 1 } }
    const r = welcomeHome(s)
    expect(r.farm.xp).toBeGreaterThan(0)
    expect(r.farm.tally.titles).toBe(1)
    const again = { ...r, memorial: [lost('b')] }
    expect(welcomeHome(again)).toBe(again)
    const closed = dismissHomecoming(r)
    expect(closed.homecoming).toEqual({ status: 'done', welcome: [] })
    expect(dismissHomecoming(closed)).toBe(closed)
  })
})
