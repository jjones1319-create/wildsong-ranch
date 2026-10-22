import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { buySheet, sheetsForSale } from './guild.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('the Guild Library (§10.5)', () => {
  it('sells every universal sheet and the breed sheets of unlocked breeds, never Signatures', () => {
    const state = createGameState({ monster: makeMonster() })
    const offers = sheetsForSale(state)
    expect(offers.filter((o) => o.tech.breed === 'universal')).toHaveLength(24)
    expect(offers.some((o) => o.tech.family === 'Signature')).toBe(false)
    expect(offers.some((o) => o.tech.family === 'Basic' && o.tech.breed !== 'universal')).toBe(false)
    expect(offers.some((o) => o.tech.breed === 'puddlepup')).toBe(true)
    expect(offers.some((o) => o.tech.breed === 'velvesper')).toBe(false) // locked at the start
    expect(sheetsForSale(state, ['velvesper']).some((o) => o.tech.breed === 'velvesper')).toBe(true)
  })

  it('marks rank gates, ownership, fit and learnability for the active monster', () => {
    const state = createGameState({ monster: makeMonster({ stats: { POW: 300, INT: 50 } }) })
    state.songbook = ['universal.beat-bump']
    const offers = sheetsForSale(state)
    const beat = offers.find((o) => o.tech.id === 'universal.beat-bump')!
    expect(beat).toMatchObject({ owned: true, blocked: null, fit: true, learnable: true, price: 500, rankMin: 1 })
    const wither = offers.find((o) => o.tech.family === 'Wither' && o.tech.breed === 'universal')!
    expect(wither.blocked).toBe('rank')
    const otherBreed = offers.find((o) => o.tech.breed === 'tumblefox' && o.tech.family === 'Hit')!
    expect(otherBreed.learnable).toBe(false)
    const own = offers.find((o) => o.tech.breed === 'puddlepup' && o.tech.family === 'Hit')!
    expect(own.learnable).toBe(true)
  })

  it('buying a sheet costs its price once and keeps it forever', () => {
    const state = createGameState({ monster: makeMonster() })
    const r = buySheet(state, 'universal.hum-pulse')
    expect(r.refused).toBeNull()
    expect(r.cost).toBe(TECHNIQUE_BY_ID['universal.hum-pulse']!.sheet!.price)
    expect(r.state.songbook).toEqual(['universal.hum-pulse'])
    expect(r.state.money).toBe(state.money - r.cost)
    expect(buySheet(r.state, 'universal.hum-pulse').refused).toBe('owned')
    expect(buySheet(state, 'universal.drumroll-stomp').refused).toBe('rank')
    expect(buySheet(state, 'puddlepup.splash-nip').refused).toBe('notSold')
    expect(buySheet(state, 'nope').refused).toBe('unknown')
    const poor = { ...state, money: 100 }
    expect(buySheet(poor, 'universal.hum-pulse').refused).toBe('money')
    expect(buySheet({ ...state, money: -1 }, 'universal.hum-pulse').refused).toBe('debt')
  })
})
