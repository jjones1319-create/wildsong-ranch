import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { canEnterSite, chanceTier, isJourneyDone, isSiteOpen, journeyForecast, journeyWeek, startJourney, techniqueCandidates, techniqueChancePct, weekSuccessPct } from './journey.ts'
import { createRng } from './rng.ts'
import { makeMonster } from './test-helpers.ts'

/** Puddlepup is POW C / LIF C: the §11 reference setup at Iron Quarry (POW). */
const reference = (agePct: number) => makeMonster({ agePct, fear: 30, fatigue: 10, spoil: 30 })
const rounded = (pcts: number[]) => pcts.map((p) => Math.round(p))

describe('weekly success check (§11 reference table)', () => {
  it('site C, LIF C, fear 30, fatigue 10 → the reference rows for stages 1, 3, 5 and 8', () => {
    expect(rounded(journeyForecast(reference(0), 'iron-quarry'))).toEqual([100, 87, 40, 0])
    expect(rounded(journeyForecast(reference(25), 'iron-quarry'))).toEqual([100, 100, 67, 23])
    expect(rounded(journeyForecast(reference(50), 'iron-quarry'))).toEqual([100, 100, 93, 50])
    expect(rounded(journeyForecast(reference(78), 'iron-quarry'))).toEqual([100, 100, 100, 90])
  })

  it('site A, LIF B at stage 5 → 100/100/100/77; site E, LIF E → 100/100/60/17', () => {
    const strong = reference(50)
    strong.grades.POW = 'A'
    strong.grades.LIF = 'B'
    expect(rounded(journeyForecast(strong, 'iron-quarry'))).toEqual([100, 100, 100, 77])
    const weak = reference(50)
    weak.grades.POW = 'E'
    weak.grades.LIF = 'E'
    expect(rounded(journeyForecast(weak, 'iron-quarry'))).toEqual([100, 100, 60, 17])
    expect(weekSuccessPct(weak, 'iron-quarry', 4, 64)).toBeCloseTo(16.67, 1)
  })
})

describe('sites', () => {
  it('opens Windrun Steppe March–November and Glacier Bastion September–May, gated to grade B', () => {
    expect([2, 3, 11, 12].map((mo) => isSiteOpen('windrun-steppe', mo))).toEqual([false, true, true, false])
    expect([5, 6, 8, 9].map((mo) => isSiteOpen('glacier-bastion', mo))).toEqual([true, false, false, true])
    expect(isSiteOpen('iron-quarry', 1)).toBe(true)
    const rookie = makeMonster()
    expect(canEnterSite(rookie, 'glacier-bastion')).toEqual({ ok: false, reason: 'grade' })
    rookie.grade = 'B'
    expect(canEnterSite(rookie, 'glacier-bastion')).toEqual({ ok: true })
    expect(canEnterSite(makeMonster(), 'iron-quarry')).toEqual({ ok: true })
  })
})

describe('technique roll', () => {
  it('lists site-family candidates in table order and Chains only with the base at Lv3', () => {
    const m = makeMonster()
    expect(techniqueCandidates(m, 'iron-quarry').map((t) => t.id)).toEqual(['puddlepup.belly-flop'])
    const heavy = { ...m, techniques: [...m.techniques, { id: 'puddlepup.belly-flop', uses: 40, level: 3 as const }] }
    expect(techniqueCandidates(heavy, 'iron-quarry').map((t) => t.id)).toEqual(['puddlepup.cannonball-flop'])
    const lv2 = { ...m, techniques: [...m.techniques, { id: 'puddlepup.belly-flop', uses: 20, level: 2 as const }] }
    expect(techniqueCandidates(lv2, 'iron-quarry')).toEqual([])
    expect(techniqueCandidates(m, 'archers-glade').map((t) => t.id)).toEqual(['puddlepup.frill-flick'])
  })

  it('chance: 0 below the requirement, 30 at it, +10 per 50 over, capped at 90, +10 Quick Study', () => {
    const bellyFlop = TECHNIQUE_BY_ID['puddlepup.belly-flop']! // POW ≥ 360 (+ loyalty)
    const at = (pow: number, spoil = 30, fear = 30) => techniqueChancePct(makeMonster({ stats: { POW: pow }, spoil, fear }), bellyFlop)
    expect(at(329)).toBe(0) // 329 + 30 loyalty = 359
    expect(at(330)).toBe(30)
    expect(at(379)).toBe(30)
    expect(at(380)).toBe(40)
    expect(at(900)).toBe(90)
    const snake = makeMonster({ main: 'coilfang', stats: { POW: 330 }, spoil: 30, fear: 30 })
    expect(techniqueChancePct(snake, TECHNIQUE_BY_ID['coilfang.constrictor-crush']!)).toBe(40)
    expect(techniqueChancePct(snake, TECHNIQUE_BY_ID['coilfang.constrictor-crush']!, true)).toBe(50)
    expect([0, 30, 50, 80, 90].map(chanceTier)).toEqual(['notReady', 'possible', 'likely', 'veryLikely', 'veryLikely'])
  })
})

describe('journeyWeek', () => {
  it('runs four weeks, applies +18 fatigue / +7 stress after each check, grows stats and learns at most one technique', () => {
    const m = makeMonster({ agePct: 50, fear: 30, fatigue: 10, spoil: 30, stats: { POW: 400 } })
    let p = startJourney('iron-quarry')
    let cur = m
    const learned: string[] = []
    for (let i = 0; i < 4; i++) {
      const r = journeyWeek(cur, p, createRng(100 + i))
      expect(r.result.week).toBe(i + 1)
      expect(r.monster.fatigue).toBe(cur.fatigue + 18)
      expect(r.monster.stress).toBe(cur.stress + 7)
      if (r.result.success) {
        expect(r.result.gains.POW).toBeGreaterThanOrEqual(1)
        expect(r.result.gains.LIF).toBeGreaterThanOrEqual(1)
      } else {
        expect(r.result.gains).toEqual({})
      }
      if (r.result.technique) learned.push(r.result.technique)
      cur = r.monster
      p = r.progress
    }
    expect(isJourneyDone(p)).toBe(true)
    expect(learned.length).toBeLessThanOrEqual(1)
    expect(p.learned).toBe(learned[0] ?? null)
    if (learned.length === 1) expect(cur.techniques.some((t) => t.id === learned[0])).toBe(true)
    expect(m.fatigue).toBe(10) // input untouched
  })

  it('is deterministic for a seed and eventually teaches the first ready candidate', () => {
    const m = makeMonster({ agePct: 50, fear: 30, fatigue: 10, spoil: 90, stats: { POW: 900 } })
    const a = journeyWeek(m, startJourney('iron-quarry'), createRng(7))
    const b = journeyWeek(m, startJourney('iron-quarry'), createRng(7))
    expect(a).toEqual(b)
    let taught = 0
    for (let seed = 0; seed < 100; seed++) if (journeyWeek(m, startJourney('iron-quarry'), createRng(seed)).result.technique === 'puddlepup.belly-flop') taught++
    expect(taught).toBeGreaterThan(70) // 90% chance when the check succeeds (always, at this stage)
  })
})
