import { describe, expect, it } from 'vitest'
import { UNIVERSAL_TECHNIQUES } from '../data/techniques.ts'
import { TITLES } from '../data/tuning.ts'
import { mixBreeds } from './monster.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { awardTitles, livedNominalPct, missingTitles, TITLE_IDS } from './titles.ts'

function fresh(): GameState {
  return createGameState({ monster: makeMonster() })
}

describe('titles (CONTENT §14)', () => {
  it('lists the twenty titles of the table', () => {
    expect(TITLE_IDS).toHaveLength(20)
    expect(missingTitles(fresh())).toEqual([])
  })

  it('Sweet Tooth at 100 sweets, Sleeper Awakened at 10 stones, Songbook Scholar with all 24 universal sheets', () => {
    const g = fresh()
    g.counters.sweetsEaten = 99
    g.records.stonesWoken = 9
    g.songbook = UNIVERSAL_TECHNIQUES.slice(1).map((t) => t.id)
    expect(missingTitles(g)).toEqual([])
    g.counters.sweetsEaten = TITLES.sweetTooth
    g.records.stonesWoken = TITLES.sleeperStones
    g.songbook = UNIVERSAL_TECHNIQUES.map((t) => t.id)
    expect(missingTitles(g)).toEqual(['Sleeper Awakened', 'Songbook Scholar', 'Sweet Tooth'])
  })

  it('Encyclopedist, Collector and Lineage Keeper read the Encyclopedia and the family', () => {
    const g = fresh()
    g.encyclopedia.breeds = Array.from({ length: TITLES.encyclopedistBreeds }, (_, i) => `b${i}`) as GameState['encyclopedia']['breeds']
    g.encyclopedia.combos = Array.from({ length: TITLES.collectorVariants }, (_, i) => `look ${i}`)
    const elder = makeMonster({ id: 'gen5' })
    elder.generation = TITLES.lineageGeneration
    g.freezer.push(elder)
    expect(missingTitles(g)).toEqual(['Lineage Keeper', 'Encyclopedist', 'Collector'])
  })

  it('Gentle Heart: a monster that lived 95 % of its nominal lifespan, passed or retired, never fused', () => {
    const g = fresh()
    const long = makeMonster({ id: 'long' })
    long.ageWeeks = Math.ceil((mixBreeds('puddlepup', 'puddlepup').lifespan * TITLES.gentleHeartPct) / 100)
    expect(livedNominalPct(long)).toBeGreaterThanOrEqual(TITLES.gentleHeartPct)
    g.memorial.push({ monster: long, cause: 'fused', epitaph: '', week: 1 })
    expect(missingTitles(g)).toEqual([])
    g.memorial[0]!.cause = 'passed'
    expect(missingTitles(g)).toEqual(['Gentle Heart'])
    const short = makeMonster({ id: 'short' })
    short.ageWeeks = 10
    expect(livedNominalPct(short)).toBeLessThan(TITLES.gentleHeartPct)
  })

  it('the unlock titles follow the breeds that woke, and awarding writes the ranch and the monster', () => {
    const g = fresh()
    g.unlocked.push('zipwisp', 'velvesper', 'mirrorkin', 'gearhoot', 'lootlid')
    expect(missingTitles(g)).toEqual(['Storm Chaser', 'Silk & Moonlight', 'Unmasked', 'Tinkerer', 'Treasure Hunter'])
    const r = awardTitles(g)
    expect(r.titles).toHaveLength(5)
    expect(r.state.titles).toEqual(r.titles)
    expect(r.state.monster!.records.titles).toEqual(r.titles)
    expect(g.titles).toEqual([])
    const again = awardTitles(r.state)
    expect(again.titles).toEqual([])
    expect(again.state).toBe(r.state)
  })
})
