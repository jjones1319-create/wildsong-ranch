import { describe, expect, it } from 'vitest'
import { BREED_BY_ID } from '../data/breeds.ts'
import { MARKET } from '../data/tuning.ts'
import { marketMonster, marketStock } from './market.ts'
import { breedBirth } from './monster.ts'

describe('the Market (§14.2)', () => {
  it('always stocks the four starters plus the season’s breed', () => {
    const jan = marketStock(1)
    expect(jan.filter((o) => !o.seasonal).map((o) => o.breed).sort()).toEqual(['pluckrex', 'puddlepup', 'quillion', 'tumblefox'])
    expect(jan.find((o) => o.seasonal)).toMatchObject({ breed: 'nimbusheep', price: MARKET.seasonalPrice })
    expect(marketStock(4).find((o) => o.seasonal)?.breed).toBe('coilfang')
    expect(marketStock(7).find((o) => o.seasonal)?.breed).toBe('galeheron')
    expect(marketStock(10).find((o) => o.seasonal)?.breed).toBe('cinderlynx')
    expect(marketStock(12).find((o) => o.seasonal)?.breed).toBe('nimbusheep')
    expect(jan.filter((o) => !o.seasonal).every((o) => o.price === MARKET.price)).toBe(true)
  })

  it('gift monsters are the same for everyone: the breed itself, zero offsets, a fixed personality', () => {
    const a = marketMonster('puddlepup', 'x')
    const b = marketMonster('puddlepup', 'y')
    expect({ ...a, id: '' }).toEqual({ ...b, id: '' })
    expect(a.stats).toEqual(breedBirth('puddlepup').base)
    expect(a.lifespanTotal).toBe(breedBirth('puddlepup').lifespan)
    expect(a.nature).toBe(0)
    expect(a.name).toBe(BREED_BY_ID.puddlepup.name)
    expect(a.likes.food).not.toBe(a.likes.dislikedFood)
    expect(marketMonster('tumblefox', 'z').likes).not.toEqual(a.likes)
  })
})
