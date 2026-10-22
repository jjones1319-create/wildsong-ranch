import { describe, expect, it } from 'vitest'
import { ITEM_BY_ID } from '../data/items.ts'
import { ECONOMY, SHOP } from '../data/tuning.ts'
import { buyItem, canBuy, charge, inDebt, maxAffordable, shopStock } from './economy.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('economy (§9)', () => {
  it('charges with the Guild Loan fee only on the borrowed part', () => {
    expect(charge(1000, 300)).toBe(700)
    expect(charge(1000, 1000)).toBe(0)
    expect(charge(100, 300)).toBe(100 - 300 - Math.ceil((200 * ECONOMY.loanFeePct) / 100))
    expect(charge(0, 300)).toBe(-330)
    expect(charge(-100, 300)).toBe(-430)
    expect(charge(500, 0)).toBe(500)
  })

  it('buys with multi-buy, refuses what money cannot cover, and reports the max', () => {
    const state = createGameState({ monster: makeMonster() })
    const muffin = ITEM_BY_ID['mighty-muffin']!
    expect(canBuy(state, 'mighty-muffin', 5)).toEqual({ ok: true, cost: muffin.price! * 5 })
    expect(maxAffordable(state, 'mighty-muffin')).toBe(Math.floor(ECONOMY.startMoney / muffin.price!))
    const r = buyItem(state, 'mighty-muffin', 7)
    expect(r.refused).toBe(null)
    expect(r.state.money).toBe(ECONOMY.startMoney - 7 * muffin.price!)
    expect(r.state.inventory['mighty-muffin']).toBe(7)
    expect(state.inventory['mighty-muffin']).toBeUndefined() // input untouched
    const broke = buyItem(r.state, 'mighty-muffin', 10)
    expect(broke.refused).toBe('money')
    expect(canBuy(state, 'mighty-muffin', 0)).toEqual({ ok: false, reason: 'quantity' })
    expect(canBuy(state, 'mighty-muffin', SHOP.maxPerPurchase + 1)).toEqual({ ok: false, reason: 'quantity' })
    expect(canBuy(state, 'nothing', 1)).toEqual({ ok: false, reason: 'unknownItem' })
    expect(canBuy(state, 'sunfruit', 1)).toEqual({ ok: false, reason: 'notSold' })
  })

  it('toys stock five uses each', () => {
    const r = buyItem(createGameState({ monster: makeMonster() }), 'rubber-ball', 2)
    expect(r.state.inventory['rubber-ball']).toBe(10)
  })

  it('gates: rank for the Wondercake and Pearl, grade C for Grand sweets', () => {
    const state = createGameState({ monster: makeMonster() })
    expect(canBuy(state, 'wondercake', 1)).toEqual({ ok: false, reason: 'rank' })
    expect(canBuy(state, 'potential-pearl', 1)).toEqual({ ok: false, reason: 'rank' })
    expect(canBuy(state, 'grand-muffin', 1)).toEqual({ ok: false, reason: 'gradeC' })
    const promoted = structuredClone(state)
    promoted.monster!.grade = 'C'
    promoted.money = 10_000
    expect(canBuy(promoted, 'grand-muffin', 1)).toMatchObject({ ok: true })
    const remembered = structuredClone(state)
    remembered.monster!.records.highestGrade = 'B'
    remembered.money = 10_000
    expect(canBuy(remembered, 'grand-muffin', 1)).toMatchObject({ ok: true })
    promoted.breeder.rank = 3
    expect(canBuy(promoted, 'wondercake', 1)).toMatchObject({ ok: true })
    expect(maxAffordable(state, 'wondercake')).toBe(0)
  })

  it('in debt only Recovery items can be bought', () => {
    const state = createGameState({ monster: makeMonster() })
    state.money = -50
    expect(inDebt(state)).toBe(true)
    expect(canBuy(state, 'berry-tart', 1)).toEqual({ ok: false, reason: 'debt' })
    expect(canBuy(state, 'sun-plum', 1)).toEqual({ ok: false, reason: 'money' })
    expect(maxAffordable(state, 'sun-plum')).toBe(0)
    const entries = shopStock(state)
    expect(entries.find((e) => e.item.id === 'berry-tart')?.blocked).toBe('debt')
    expect(entries.find((e) => e.item.id === 'sun-plum')?.blocked).toBeNull()
    expect(entries.every((e) => e.item.price !== null)).toBe(true)
    expect(entries.some((e) => e.item.id === 'sunfruit')).toBe(false)
  })
})
