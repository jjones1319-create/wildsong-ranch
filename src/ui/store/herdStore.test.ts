import { beforeEach, describe, expect, it } from 'vitest'
import { newRanchmate } from '../../core/creation.ts'
import { createGameState, type GameState } from '../../core/state.ts'
import { makeMonster } from '../../core/test-helpers.ts'
import { memoryStore, memoryTextStore } from '../../save/db.ts'
import { fill } from '../../data/text/format.ts'
import { HERD_TEXT } from '../../data/text/herd.ts'
import { FARM } from '../../data/tuning.ts'
import { useStores } from './appStore.ts'
import { endWeekNow, flow, game, resetGameStoreForTests } from './gameStore.ts'
import { buyPen } from './herdStore.ts'

/** v1.21.0 the farm through the stores: building a pen, and the week summary's level-up celebration. */

function ranchAt(level: number, money: number): GameState {
  const g = createGameState({ monster: makeMonster({ id: 'star' }) })
  g.weekPhase = 'action'
  g.farm.xp = FARM.levelXp[level - 1]!
  g.money = money
  return g
}

beforeEach(() => {
  useStores(memoryStore(), memoryTextStore())
  resetGameStoreForTests()
})

describe('the farm in the stores (§9.1)', () => {
  it('builds a pen with gold and the level, and says why not otherwise', () => {
    game.value = ranchAt(2, 5000)
    expect(buyPen()).toBeNull()
    expect(game.value.farm.pensBought).toBe(1)
    expect(game.value.money).toBe(2000)
    expect(buyPen()).toBe('level')
    game.value = ranchAt(4, 100)
    game.value.farm.pensBought = 1
    expect(buyPen()).toBe('money')
    expect(game.value.farm.pensBought).toBe(1)
  })

  it('a new level opens the summary with the celebration and Wren’s line', () => {
    const g = ranchAt(1, 5000)
    g.farm.xp = FARM.levelXp[1]! - 1
    g.ranchmates = [newRanchmate(makeMonster({ id: 'fern' }))]
    game.value = g
    endWeekNow()
    const f = flow.value
    expect(f.kind).toBe('summary')
    if (f.kind !== 'summary') return
    expect(f.farmLevel).toBe(2)
    expect(f.herd.map((l) => l.text)).toContain(fill(HERD_TEXT.farm.levelUpLine, { n: 2 }))
    expect(game.value!.mail[0]).toMatchObject({ kind: 'farm', ref: '2' })
  })
})
