import { describe, expect, it } from 'vitest'
import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { FREEZER, MARKET, SHRINE } from '../data/tuning.ts'
import { awaken, buyFromMarket, isKeptStone, placeNewMonster, recreate, wakeStone } from './creation.ts'
import { rollShrine } from './shrine.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

/** A phrase whose main breed is still asleep at the start of a game. */
function sleepingPhrase(): string {
  for (let i = 0; i < 5000; i++) if (rollShrine(`sleeper ${i}`, '', STARTING_UNLOCKED).mainLocked) return `sleeper ${i}`
  throw new Error('no sleeping phrase found')
}

describe('the Shrine in play (§14.1)', () => {
  it('a newborn takes the empty ranch, the next goes to the Freezer, and a full Freezer refuses', () => {
    const state = createGameState({ monster: null })
    const first = awaken(state, 'River Song', 'the valley choir', 'id1')
    expect(first.kind).toBe('born')
    if (first.kind !== 'born') return
    expect(first.placed).toBe('ranch')
    expect(first.state.monster?.id).toBe('id1')
    expect(first.state.weekPhase).toBe('start')
    expect(first.state.encyclopedia.phrases).toEqual([{ phrase: 'river song', artist: 'the valley choir', name: 'River', mainBreed: first.monster.mainBreed, variantId: null }])
    expect(first.state.encyclopedia.breeds).toEqual([first.monster.mainBreed])
    const second = awaken(first.state, 'river song', 'the valley choir', 'id2')
    expect(second.kind).toBe('born')
    if (second.kind !== 'born') return
    expect(second.placed).toBe('freezer')
    expect(second.state.freezer.map((m) => m.id)).toEqual(['id2'])
    expect(second.state.encyclopedia.phrases).toHaveLength(1) // the same song is listed once
    const full = structuredClone(second.state)
    full.freezer = Array.from({ length: FREEZER.slots }, (_, i) => makeMonster({ id: `f${i}` }))
    const r = awaken(full, 'river song', 'the valley choir', 'id3')
    expect(r.kind).toBe('refused')
    if (r.kind === 'refused') expect(r.reason).toBe('freezerFull')
    expect(placeNewMonster(full, makeMonster({ id: 'z' })).refused).toBe('freezerFull')
  })

  it('a sleeping breed keeps the song among the Sleeping Stones, once, until the breed wakes', () => {
    const phrase = sleepingPhrase()
    const state = createGameState({ monster: null })
    const r = awaken(state, phrase, '', 'id1')
    expect(r.kind).toBe('sleeping')
    if (r.kind !== 'sleeping') return
    expect(r.alreadyKept).toBe(false)
    expect(r.state.sleepingStones).toHaveLength(1)
    expect(r.state.sleepingStones[0]!.breed).toBe(r.roll.mainBreed)
    expect(r.state.monster).toBeNull()
    expect(isKeptStone(r.state, phrase.toUpperCase(), '')).toBe(true)
    const again = awaken(r.state, phrase, '', 'id2')
    expect(again.kind === 'sleeping' && again.alreadyKept).toBe(true)
    expect(wakeStone(r.state, 0, 'id3').refused).toBe('asleep')
    const unlocked = structuredClone(r.state)
    unlocked.unlocked = [...unlocked.unlocked, r.roll.mainBreed]
    const woke = wakeStone(unlocked, 0, 'id3')
    expect(woke.refused).toBeNull()
    expect(woke.placed).toBe('ranch')
    expect(woke.monster?.mainBreed).toBe(r.roll.mainBreed)
    expect(woke.state.sleepingStones).toEqual([])
    expect(woke.state.money).toBe(state.money) // free
    expect(woke.state.encyclopedia.phrases).toHaveLength(1)
    expect(wakeStone(woke.state, 0, 'x').refused).toBe('notFound')
  })

  it('the Encyclopedia re-creates a song for 500G', () => {
    const state = createGameState({ monster: null })
    const born = awaken(state, 'twinkle', '', 'id1')
    if (born.kind !== 'born') throw new Error('expected a birth')
    const r = recreate(born.state, 0, 'id2')
    expect(r.refused).toBeNull()
    expect(r.placed).toBe('freezer')
    expect(r.state.money).toBe(born.state.money - SHRINE.encyclopediaPrice)
    expect({ ...r.monster!, id: '' }).toEqual({ ...born.monster, id: '' })
    expect(recreate({ ...born.state, money: 10 }, 0, 'id3').refused).toBe('money')
    expect(recreate(born.state, 5, 'id3').refused).toBe('notFound')
  })
})

describe('the Market in play (§14.2)', () => {
  it('sells the starters for 1,500G and the season’s breed for 2,500G, to the ranch or the Freezer', () => {
    const state = createGameState({ monster: null })
    const r = buyFromMarket(state, 'puddlepup', 'id1')
    expect(r.refused).toBeNull()
    expect(r.price).toBe(MARKET.price)
    expect(r.placed).toBe('ranch')
    expect(r.state.money).toBe(state.money - MARKET.price)
    expect(r.state.monster?.mainBreed).toBe('puddlepup')
    const seasonal = buyFromMarket({ ...r.state, money: 5000 }, 'nimbusheep', 'id2') // January: Winter
    expect(seasonal.price).toBe(MARKET.seasonalPrice)
    expect(seasonal.placed).toBe('freezer')
    expect(buyFromMarket(state, 'cobblemaw', 'id3').refused).toBe('notStocked')
    expect(buyFromMarket({ ...state, money: 100 }, 'puddlepup', 'id3').refused).toBe('money')
  })
})
