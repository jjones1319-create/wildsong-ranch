import { describe, expect, it } from 'vitest'
import { RANCH_UPGRADES } from '../data/upgrades.ts'
import { UPGRADES } from '../data/tuning.ts'
import { weekIndexOf } from './calendar.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { buyUpgrade, canVisitGarden, upgradeOffers, visitGarden } from './upgrades.ts'

function fresh(rank = 1, money = 0): GameState {
  const g = createGameState({ monster: makeMonster() })
  g.breeder.rank = rank
  g.money = money
  return g
}

describe('ranch upgrades (CONTENT §11)', () => {
  it('lists the four upgrades with their prices and gates', () => {
    expect(RANCH_UPGRADES.map((u) => [u.id, u.price])).toEqual([
      ['cozyBarn', 8000],
      ['trainingYard', 10000],
      ['tidePool', 12000],
      ['lanternGarden', 6000],
    ])
    const offers = upgradeOffers(fresh(1, 100_000))
    expect(offers.map((o) => o.blocked)).toEqual(['rank', 'rank', 'rank', 'memorial'])
    const rich = fresh(4, 100_000)
    rich.memorial.push({ monster: makeMonster({ id: 'gone' }), cause: 'passed', epitaph: '', week: 1 })
    expect(upgradeOffers(rich).every((o) => o.blocked === null)).toBe(true)
    const poor = fresh(4, 100)
    expect(upgradeOffers(poor).map((o) => o.blocked)).toEqual(['money', 'money', 'money', 'memorial'])
  })

  it('buys once, charges the price, and refuses the gates', () => {
    const g = fresh(2, 8000)
    expect(buyUpgrade(g, 'trainingYard').refused).toBe('rank')
    expect(buyUpgrade(g, 'lanternGarden').refused).toBe('memorial')
    const bought = buyUpgrade(g, 'cozyBarn')
    expect(bought.refused).toBeNull()
    expect(bought.state.upgrades.cozyBarn).toBe(true)
    expect(bought.state.money).toBe(0)
    expect(buyUpgrade(bought.state, 'cozyBarn').refused).toBe('owned')
    expect(buyUpgrade(fresh(2, 7999), 'cozyBarn').refused).toBe('money')
    expect(upgradeOffers(bought.state)[0]).toMatchObject({ owned: true, blocked: null })
  })

  it('the Lantern Garden visit relieves stress once a month', () => {
    const g = fresh()
    g.monster!.stress = 30
    expect(canVisitGarden(g)).toMatchObject({ ok: false, reason: 'noGarden' })
    g.upgrades.lanternGarden = true
    g.week = weekIndexOf({ year: 1, month: 3, week: 2 })
    const visited = visitGarden(g)
    expect(visited.refused).toBeNull()
    expect(visited.state.monster!.stress).toBe(30 - UPGRADES.lanternGardenVisitStress)
    expect(visitGarden(visited.state).refused).toBe('visited')
    const later = { ...visited.state, week: weekIndexOf({ year: 1, month: 3, week: 4 }) }
    expect(visitGarden(later).refused).toBe('visited')
    const nextMonth = { ...visited.state, week: weekIndexOf({ year: 1, month: 4, week: 1 }) }
    expect(visitGarden(nextMonth).refused).toBeNull()
    expect(visitGarden({ ...g, monster: null }).refused).toBe('noMonster')
  })
})
