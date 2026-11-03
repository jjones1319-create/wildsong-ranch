import { describe, expect, it } from 'vitest'
import { FARM_PENS, FARM_PERKS } from '../data/farm.ts'
import { FARM, FREEZER } from '../data/tuning.ts'
import { newRanchmate } from './creation.ts'
import { buyPen, canBuyPen, farmLevel, farmView, farmWeek, hasPerk, penCapacity, perkAtLevel, seedFarm, startTally, tallyXp } from './farm.ts'
import { finishWeek } from './game.ts'
import { freezerSlots } from './legacy.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { endWeek } from './week.ts'

function game(): GameState {
  return createGameState({ monster: makeMonster({ id: 'star' }) })
}

describe('farm levels (§9.1)', () => {
  it('levels 1–10 follow FARM.levelXp', () => {
    expect(FARM.levelXp).toHaveLength(10)
    expect(farmLevel(0)).toBe(1)
    for (let i = 1; i < FARM.levelXp.length; i++) {
      expect(farmLevel(FARM.levelXp[i]! - 1)).toBe(i)
      expect(farmLevel(FARM.levelXp[i]!)).toBe(i + 1)
    }
    expect(farmLevel(FARM.maxXp)).toBe(10)
    for (let i = 1; i < FARM.levelXp.length; i++) expect(FARM.levelXp[i]!).toBeGreaterThan(FARM.levelXp[i - 1]!)
  })

  it('a new game starts at 0 XP, its first breed and rank already counted', () => {
    const g = game()
    expect(g.farm).toEqual({ xp: 0, pensBought: 0, tally: { titles: 0, cupsWon: 0, journeys: 0, expeditions: 0, breeds: 1, rank: 1 } })
    expect(createGameState().farm.xp).toBe(0)
  })

  it('XP each week: the star and each ranch-mate, plus each new achievement once', () => {
    const g = game()
    g.ranchmates = [newRanchmate(makeMonster({ id: 'a' })), newRanchmate(makeMonster({ id: 'b' }))]
    const week = farmWeek(g)
    expect(week.state.farm.xp).toBe(FARM.xp.star + 2 * FARM.xp.mate)
    expect(week.leveledTo).toBeNull()
    g.titles = ['Collector']
    g.records.cupsWon = 2
    g.journeysBySite['iron-quarry'] = 1
    g.records.expeditionsDone = 1
    g.encyclopedia.breeds = ['puddlepup', 'tumblefox']
    g.breeder.rank = 3
    const busy = farmWeek(g).state
    const x = FARM.xp
    expect(busy.farm.xp).toBe(x.star + 2 * x.mate + x.title + 2 * x.cup + x.journey + x.expedition + x.breed + 2 * x.rank)
    // Counted once: the next week only pays the weekly XP.
    expect(farmWeek(busy).state.farm.xp - busy.farm.xp).toBe(x.star + 2 * x.mate)
    expect(tallyXp(busy.farm.tally, { ...busy.farm.tally, titles: 0 })).toBe(0)
  })

  it('reports a level-up (silent in v1.20.0)', () => {
    const g = game()
    g.farm.xp = FARM.levelXp[1]! - 1
    expect(farmWeek(g).leveledTo).toBe(2)
  })

  it('finishWeek earns the week’s XP without touching the random stream', () => {
    const g = game()
    g.weekPhase = 'action'
    const a = createRng(4)
    const b = createRng(4)
    const r = finishWeek(g, a)
    expect(r.state.farm.xp).toBe(FARM.xp.star)
    // Exactly the end of the week's own draws (the tick and the weather).
    const plain = endWeek(g, b)
    expect(a.getState()).toBe(b.getState())
    expect(plain.state.monster).toEqual(r.state.monster)
  })

  it('seedFarm gives a long-time save the XP the star would have earned and a tally of its history', () => {
    const g = game()
    g.week = 200
    g.titles = ['Collector', 'Sweet Tooth']
    g.records.cupsWon = 12
    g.journeysBySite['iron-quarry'] = 3
    g.journeysBySite['archers-glade'] = 1
    g.records.expeditionsDone = 2
    g.encyclopedia.breeds = ['puddlepup', 'tumblefox', 'cobblemaw']
    g.breeder.rank = 4
    const seeded = seedFarm(g, 2)
    const x = FARM.xp
    expect(seeded.xp).toBe(200 * x.star + 2 * x.title + 12 * x.cup + 4 * x.journey + 2 * x.expedition + 2 * x.breed + 3 * x.rank)
    expect(seeded.pensBought).toBe(2)
    expect(seeded.tally).toEqual({ titles: 2, cupsWon: 12, journeys: 4, expeditions: 2, breeds: 3, rank: 4 })
    expect(tallyXp(startTally(), startTally())).toBe(0)
  })
})

describe('pens and perks (CONTENT §11)', () => {
  it('capacity is the base pen plus the pens bought (v1.20.0: the star + 1)', () => {
    const g = game()
    expect(penCapacity(g)).toBe(FARM.basePens)
    expect(penCapacity({ farm: { ...g.farm, pensBought: 99 } })).toBe(FARM.basePens + FARM_PENS.length)
  })

  it('a pen needs its farm level and its gold, in order', () => {
    const g = game()
    g.money = 100_000
    expect(canBuyPen(g)).toEqual({ ok: false, reason: 'level' })
    g.farm.xp = FARM.levelXp[FARM_PENS[0]!.level - 1]!
    const first = buyPen(g)
    expect(first.refused).toBeNull()
    expect(first.state.money).toBe(100_000 - FARM_PENS[0]!.price)
    expect(penCapacity(first.state)).toBe(FARM.basePens + 1)
    expect(buyPen(first.state).refused).toBe('level')
    expect(buyPen({ ...g, money: FARM_PENS[0]!.price - 1 }).refused).toBe('money')
    const all = { ...g, farm: { ...g.farm, xp: FARM.maxXp, pensBought: FARM_PENS.length } }
    expect(buyPen(all).refused).toBe('allBuilt')
    expect(farmView(all).pens).toMatchObject({ capacity: FARM.basePens + FARM_PENS.length, next: null, blocked: 'allBuilt' })
  })

  it('the pens and perks mirror CONTENT §11', () => {
    expect(FARM_PENS.map((p) => [p.price, p.level])).toEqual([
      [3000, 2],
      [6000, 4],
      [10000, 6],
      [15000, 8],
      [20000, 10],
    ])
    expect(FARM_PERKS.map((p) => [p.name, p.level])).toEqual([
      ['Feed Shed', 3],
      ['Farmhand', 5],
      ['Deep Freezer', 7],
      ['Campfire Circle', 9],
    ])
  })

  it('perks come with their level, and stay off until v1.21.0 switches them on', () => {
    expect(perkAtLevel('feedShed', 2)).toBe(false)
    expect(perkAtLevel('feedShed', 3)).toBe(true)
    expect(perkAtLevel('campfire', 10)).toBe(true)
    const top = { ...game(), farm: { xp: FARM.maxXp, pensBought: 0, tally: startTally() } }
    expect(FARM.perksLive).toBe(false)
    expect(hasPerk(top, 'deepFreezer')).toBe(false)
    expect(freezerSlots(top)).toBe(FREEZER.slots)
    const view = farmView(top)
    expect(view.level).toBe(10)
    expect(view.levelTo).toBeNull()
    expect(view.perks.every((p) => p.unlocked)).toBe(true)
  })
})
