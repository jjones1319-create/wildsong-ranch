import { describe, expect, it } from 'vitest'
import { addItems } from './items.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { endWeek, resolveAction, runWeek, startWeek, useItemInGame, type WeekEvent, type WeekPolicy } from './week.ts'

const trainer: WeekPolicy = {
  food: () => 'honey-bread',
  request: () => true,
  action: () => ({ kind: 'drill', drill: 'log-toss' }),
  reaction: (_s, r) => (r.outcome === 'Cheat' || r.outcome === 'Slacked' ? 'scold' : 'praise'),
}

const phases = (events: WeekEvent[]) => events.filter((e) => e.kind === 'phase').map((e) => (e.kind === 'phase' ? e.phase : ''))

describe('the week (§3)', () => {
  it('runs the four phases in the strict order', () => {
    const state = createGameState({ monster: makeMonster() })
    const r = runWeek(state, createRng(1), trainer)
    expect(phases(r.events)).toEqual(['startOfWeek', 'requestCheck', 'action', 'endOfWeek'])
    expect(r.state.week).toBe(1)
    expect(r.state.monster!.ageWeeks).toBe(1)
    expect(r.events.some((e) => e.kind === 'autosave')).toBe(true)
    expect(r.events.some((e) => e.kind === 'weather')).toBe(true)
    expect(state.week).toBe(0) // input untouched
  })

  it('feeds the monthly food only in week 1 of a month and keeps last month’s choice by default', () => {
    let state = createGameState({ monster: makeMonster(), foodChoice: 'turnips' })
    const first = runWeek(state, createRng(1), trainer)
    expect(first.events.find((e) => e.kind === 'food')).toMatchObject({ food: 'honey-bread', relation: 'liked' })
    expect(first.state.foodChoice).toBe('honey-bread')
    state = first.state
    for (let i = 0; i < 3; i++) {
      const r = runWeek(state, createRng(i), { ...trainer, food: () => 'turnips' })
      expect(r.events.some((e) => e.kind === 'food')).toBe(false)
      state = r.state
    }
    const nextMonth = runWeek(state, createRng(9), { ...trainer, food: () => undefined })
    expect(nextMonth.events.find((e) => e.kind === 'food')).toMatchObject({ food: 'honey-bread' })
  })

  it('items are free actions that never use the week', () => {
    let state = createGameState({ monster: makeMonster({ fatigue: 60 }) })
    state.inventory = addItems(state.inventory, 'sun-plum', 3)
    const used = useItemInGame(state, 'sun-plum', 3)
    expect(used.used).toBe(3)
    expect(used.state.monster!.fatigue).toBe(30)
    expect(used.state.week).toBe(0)
    const r = runWeek(used.state, createRng(1), { ...trainer, beforeAction: (s) => useItemInGame(addItemsTo(s, 'sun-plum', 2), 'sun-plum', 2).state })
    expect(r.state.week).toBe(1)
    expect(r.events.some((e) => e.kind === 'drill')).toBe(true)
  })

  it('a sick monster can only rest; a missing monster cannot act at all', () => {
    const sick = makeMonster()
    sick.status.sickWeeks = 2
    const r = resolveAction(createGameState({ monster: sick }), { kind: 'drill', drill: 'log-toss' }, createRng(1))
    expect(r.events.some((e) => e.kind === 'forcedRest')).toBe(true)
    expect(r.events.some((e) => e.kind === 'rest')).toBe(true)
    expect(r.drill).toBeNull()
    const missing = makeMonster()
    missing.status.missingWeeks = 2
    const r2 = resolveAction(createGameState({ monster: missing }), { kind: 'rest' }, createRng(1))
    expect(r2.events.some((e) => e.kind === 'locked')).toBe(true)
    expect(r2.state.monster!.fatigue).toBe(0)
  })

  it('a Journey takes four weeks, costs 2,000G and then clears', () => {
    const state = createGameState({ monster: makeMonster({ agePct: 50, fear: 30, stats: { POW: 400 } }) })
    const first = runWeek(state, createRng(1), { ...trainer, action: () => ({ kind: 'journey', site: 'iron-quarry' }) })
    expect(first.state.money).toBe(1000)
    expect(first.state.journey?.weekNo).toBe(2)
    let cur = first.state
    for (let i = 0; i < 3; i++) {
      const r = runWeek(cur, createRng(10 + i), trainer) // the policy's drill is ignored while the Journey runs
      expect(r.events.some((e) => e.kind === 'journeyWeek')).toBe(true)
      expect(r.events.some((e) => e.kind === 'drill')).toBe(false)
      cur = r.state
    }
    expect(cur.journey).toBeNull()
    expect(cur.week).toBe(4)
    expect(cur.monster!.fatigue).toBeGreaterThanOrEqual(4 * 18 - 60)
  })

  it('marks the end of life and stops acting afterwards', () => {
    const m = makeMonster()
    m.lifespanTotal = 100
    m.ageWeeks = 99
    const r = endWeek(createGameState({ monster: m }), createRng(1))
    expect(r.state.ended).toBe('passed')
    const after = startWeek(r.state, createRng(2))
    expect(after.request).toBeNull()
    const gentle = endWeek(createGameState({ monster: m, difficulty: 'Gentle' }), createRng(1))
    expect(gentle.state.ended).toBe('retired')
  })

  it('charges breakdown fees and applies the Cozy Barn each week', () => {
    const wrecked = makeMonster({ fatigue: 100, stress: 100 })
    let fees = 0
    for (let seed = 0; seed < 40; seed++) {
      const r = endWeek(createGameState({ monster: wrecked }), createRng(seed))
      const fee = r.events.find((e) => e.kind === 'fees')
      if (fee && fee.kind === 'fees') {
        fees++
        expect(r.state.money).toBe(3000 - fee.amount)
      }
    }
    expect(fees).toBeGreaterThan(3)
    const barn = createGameState({ monster: makeMonster({ stress: 20 }) })
    barn.upgrades.cozyBarn = true
    barn.week = 1
    expect(startWeek(barn, createRng(1)).state.monster!.stress).toBe(18)
  })
})

function addItemsTo(state: ReturnType<typeof createGameState>, id: string, qty: number) {
  return { ...state, inventory: addItems(state.inventory, id, qty) }
}
