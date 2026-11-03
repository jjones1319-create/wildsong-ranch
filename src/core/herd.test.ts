import { describe, expect, it } from 'vitest'
import { FOOD_BY_ID } from '../data/foods.ts'
import { techniquesOfBreed } from '../data/techniques.ts'
import { HERD } from '../data/tuning.ts'
import { endOfWeekTick } from './aging.ts'
import { dateOf, rollWeather } from './calendar.ts'
import { newRanchmate } from './creation.ts'
import { mateFoodPrice, mateNews, monthlyFoodCost, tickHerdMut } from './herd.ts'
import { lifeStage, isPrimeStage } from './monster.ts'
import { runPlanner } from './planner.ts'
import { herdLines } from './report.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState, type MateOrder } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { resolveDrill } from './training.ts'
import { endWeek, runWeek, startWeek, type WeekEvent, type WeekPolicy } from './week.ts'

/** A star and ranch-mates (each `[id, order]`), in the action phase of Year 1, January week 2. */
function herd(mates: [string, MateOrder][] = [], star = makeMonster({ id: 'star' })): GameState {
  const s = createGameState({ monster: star })
  s.week = 1
  s.weekPhase = 'action'
  s.farm.pensBought = 5
  s.ranchmates = mates.map(([id, order]) => ({ ...newRanchmate(makeMonster({ id })), order }))
  return s
}

const mate = (s: GameState, id: string) => s.ranchmates.find((r) => r.monster.id === id)!

describe('the herd’s week (§6.11)', () => {
  it('each order: a drill trains for half pay, rest rests, play plays', () => {
    const s = herd([
      ['d', { kind: 'drill', drill: 'log-toss' }],
      ['r', { kind: 'rest' }],
      ['p', { kind: 'play' }],
    ])
    for (const id of ['r', 'p']) mate(s, id).monster.fatigue = 40
    const before = structuredClone(s)
    const reports = tickHerdMut(s, createRng(5))
    // The drill is resolved first, from the same stream: replaying it gives the same full pay, and the mate keeps half.
    const solo = resolveDrill(mate(before, 'd').monster, 'log-toss', createRng(5), { trainingYard: false })
    const d = reports.find((r) => r.id === 'd')!
    expect(d.last).toMatchObject({ kind: 'drill', drill: 'log-toss', outcome: solo.result.outcome, gains: solo.result.gains })
    expect(d.pay).toBe(Math.floor((solo.result.pay * HERD.payPct) / 100))
    expect(s.money).toBe(before.money + d.pay)
    expect(mate(s, 'd').monster.stats.POW).toBe(solo.monster.stats.POW)
    expect(reports.find((r) => r.id === 'r')!.last).toEqual({ kind: 'rest' })
    expect(mate(s, 'r').monster.fatigue).toBeLessThan(40)
    expect(reports.find((r) => r.id === 'p')!.last).toEqual({ kind: 'play' })
    expect(mate(s, 'p').monster.fatigue).toBeLessThan(40)
    for (const r of s.ranchmates) expect(r.monster.ageWeeks).toBe(1)
    expect(s.ranchmates.map((r) => r.last)).toEqual(reports.map((r) => r.last))
  })

  it('rests by itself when tired, tense, sick, injured or sent to a Yard drill without the Yard', () => {
    const order: MateOrder = { kind: 'drill', drill: 'log-toss' }
    const s = herd([
      ['tired', order],
      ['tense', order],
      ['sick', order],
      ['hurt', order],
      ['yard', { kind: 'drill', drill: 'quarry-haul' }],
      ['resting', { kind: 'rest' }],
    ])
    mate(s, 'tired').monster.fatigue = HERD.autoRest.fatigue
    mate(s, 'tense').monster.stress = HERD.autoRest.stress
    mate(s, 'sick').monster.status.sickWeeks = 2
    mate(s, 'hurt').monster.status.injuredWeeks = 2
    mate(s, 'resting').monster.fatigue = 90
    const money = s.money
    const reports = tickHerdMut(s, createRng(1))
    expect(reports.map((r) => r.last)).toEqual([
      { kind: 'autoRest', reason: 'tired' },
      { kind: 'autoRest', reason: 'stressed' },
      { kind: 'autoRest', reason: 'sick' },
      { kind: 'autoRest', reason: 'injured' },
      { kind: 'autoRest', reason: 'noYard' },
      { kind: 'rest' },
    ])
    expect(s.money).toBe(money)
    expect(mate(s, 'tired').monster.fatigue).toBeLessThan(HERD.autoRest.fatigue)
    // With the Yard, the Yard drill trains.
    const yard = herd([['yard', { kind: 'drill', drill: 'quarry-haul' }]])
    yard.upgrades.trainingYard = true
    expect(tickHerdMut(yard, createRng(1))[0]!.last.kind).toBe('drill')
  })

  it('is away while missing or at the clinic, and comes back with news', () => {
    const s = herd([
      ['gone', { kind: 'play' }],
      ['clinic', { kind: 'play' }],
    ])
    mate(s, 'gone').monster.status.missingWeeks = 1
    mate(s, 'clinic').monster.status.clinicWeeks = 2
    const reports = tickHerdMut(s, createRng(1))
    expect(reports.map((r) => r.last)).toEqual([
      { kind: 'away', reason: 'missing' },
      { kind: 'away', reason: 'clinic' },
    ])
    expect(mateNews(reports[0]!)).toEqual(['cameBack'])
    expect(mateNews(reports[1]!)).toEqual([])
  })

  it('reaches Prime and learns its Signature (a pure breed, loyalty 60+)', () => {
    const m = makeMonster({ id: 'p', spoil: 70, fear: 70 })
    m.lifespanTotal = 200
    m.ageWeeks = [...Array(200).keys()].find((a) => !isPrimeStage(lifeStage(a, 200, m.growthType)) && isPrimeStage(lifeStage(a + 1, 200, m.growthType)))!
    const s = herd()
    s.ranchmates = [{ ...newRanchmate(m), order: { kind: 'rest' } }]
    const r = tickHerdMut(s, createRng(1))[0]!
    const sig = techniquesOfBreed('puddlepup').find((t) => t.family === 'Signature')!
    expect(r.signature).toBe(sig.id)
    expect(mateNews(r)).toEqual(['prime', 'signature'])
    expect(s.ranchmates[0]!.monster.techniques.some((t) => t.id === sig.id)).toBe(true)
  })

  it('at the end of its life it moves quietly to the Memorial, with a Heartstone and the Vigil', () => {
    const s = herd([['old', { kind: 'rest' }]])
    mate(s, 'old').monster.lifespanTotal = 50
    mate(s, 'old').monster.ageWeeks = 49
    s.friendships = [{ a: 'old', b: 'star', points: 20 }]
    const r = tickHerdMut(s, createRng(1))[0]!
    expect(r.ended).toBe('passed')
    expect(s.ranchmates).toEqual([])
    expect(s.memorial[0]).toMatchObject({ cause: 'passed', monster: { id: 'old' } })
    expect(s.memorial[0]!.epitaph).toContain(FOOD_BY_ID[s.memorial[0]!.monster.likes.food].name)
    expect(r.heartstone?.donorId).toBe('old')
    expect(s.heartstones[0]!.id).toBe('hs-old')
    expect(s.unlocks.vigilPending).toBe(true)
    expect(s.friendships).toEqual([])
    expect(mateNews(r)).toEqual(['passed'])
    const lines = herdLines([{ kind: 'herd', reports: [r] }])
    expect(lines.map((l) => l.key)).toEqual(['mate-old-passed', 'mate-old-heartstone'])
    expect(lines[0]!.text).toContain(r.name)
    // On Gentle it retires to the Elder Grove.
    const g = herd([['old', { kind: 'rest' }]])
    g.difficulty = 'Gentle'
    mate(g, 'old').monster.lifespanTotal = 50
    mate(g, 'old').monster.ageWeeks = 49
    expect(tickHerdMut(g, createRng(1))[0]!.ended).toBe('retired')
    expect(g.elderGrove.map((m) => m.id)).toEqual(['old'])
  })

  it('routine weeks are badges, not summary lines', () => {
    const s = herd([['a', { kind: 'play' }]])
    const reports = tickHerdMut(s, createRng(1))
    expect(mateNews(reports[0]!)).toEqual([])
    expect(herdLines([{ kind: 'herd', reports }])).toEqual([])
  })
})

describe('the herd at the start of the week', () => {
  it('one food for everyone: price × mouths, each with its own likes', () => {
    const s = herd([
      ['a', { kind: 'play' }],
      ['b', { kind: 'play' }],
    ])
    s.week = 4 // February week 1
    s.weekPhase = 'start'
    const price = FOOD_BY_ID['honey-bread'].price
    expect(monthlyFoodCost(s, 'honey-bread')).toEqual({ mouths: 3, total: price * 3 })
    expect(mateFoodPrice(s, 'honey-bread')).toBe(price) // the Feed Shed is a v1.21.0 perk
    const r = startWeek(s, createRng(1), 'honey-bread')
    const food = r.events.find((e) => e.kind === 'food')
    expect(food).toMatchObject({ price: price * 3, mouths: 3 })
    expect(r.state.money).toBe(s.money - price * 3)
    for (const m of r.state.ranchmates) expect(m.monster.diet.monthsFed).toBe(1)
  })

  it('the Cozy Barn calms the ranch-mates every week', () => {
    const s = herd([['a', { kind: 'play' }]])
    s.weekPhase = 'start'
    s.upgrades.cozyBarn = true
    mate(s, 'a').monster.stress = 20
    expect(startWeek(s, createRng(1)).state.ranchmates[0]!.monster.stress).toBeLessThan(20)
  })
})

describe('the random-order contract (golden record, sims)', () => {
  it('with no ranch-mates the end of the week draws exactly what it always did', () => {
    const s = herd()
    const a = createRng(42)
    const b = createRng(42)
    endWeek(s, a)
    endOfWeekTick(s.monster!, s.difficulty, b)
    rollWeather(b, dateOf(s.week + 1).month)
    expect(a.getState()).toBe(b.getState())
  })

  it('with ranch-mates exactly one number more is drawn, and the star’s week is the same', () => {
    const alone = herd()
    const busy = herd([
      ['d', { kind: 'drill', drill: 'plow-pull' }],
      ['p', { kind: 'play' }],
    ])
    for (const seed of [1, 2, 3, 99]) {
      const a = createRng(seed)
      const b = createRng(seed)
      const one = endWeek(alone, a)
      const two = endWeek(busy, b)
      expect(two.state.monster).toEqual(one.state.monster)
      expect(two.state.weather).toBe(one.state.weather)
      expect(two.events.some((e) => e.kind === 'herd')).toBe(true)
      a.nextU32()
      expect(b.getState()).toBe(a.getState())
    }
    // A whole week through runWeek: the star's results match too (money differs only by the herd's food and pay).
    const policy: WeekPolicy = { food: () => 'honey-bread', request: () => true, action: () => ({ kind: 'drill', drill: 'log-toss' }), reaction: () => 'praise' }
    const start = (g: GameState): GameState => ({ ...structuredClone(g), weekPhase: 'start', week: 4 })
    const one = runWeek(start(alone), createRng(8), policy)
    const two = runWeek(start(busy), createRng(8), policy)
    expect(two.state.monster).toEqual(one.state.monster)
    const strip = (es: WeekEvent[]) => es.filter((e) => e.kind !== 'herd' && e.kind !== 'food')
    expect(strip(two.events)).toEqual(strip(one.events))
  })

  it('the planner stops for news from the pens, and not for a routine week', () => {
    const s = herd([['old', { kind: 'rest' }]])
    s.weekPhase = 'start'
    s.planner.queue = [{ kind: 'rest' }, { kind: 'rest' }]
    const calm = runPlanner(s, createRng(3))
    expect(calm.stop).toBe('empty')
    expect(calm.weeks).toBe(2)
    mate(s, 'old').monster.lifespanTotal = 50
    mate(s, 'old').monster.ageWeeks = 49
    const sad = runPlanner(s, createRng(3))
    expect(sad.stop).toBe('ranchmate')
    expect(sad.weeks).toBe(1)
    expect(sad.state.planner.lastStop).toBe('ranchmate')
  })
})
