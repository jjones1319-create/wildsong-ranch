import { describe, expect, it } from 'vitest'
import { STAT_KEYS } from '../data/types.ts'
import { makeSave, validateSave } from '../save/schema.ts'
import { awaken, buyFromMarket } from './creation.ts'
import { fuse, findRelative } from './fusion.ts'
import { concludeLife, giveHeartstone, heartstoneGrant } from './legacy.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { runWeek, type WeekPolicy } from './week.ts'

const resting: WeekPolicy = {
  food: () => 'honey-bread',
  request: () => false,
  action: () => ({ kind: 'rest' }),
  reaction: () => 'skip',
}

/** Rests week after week until the life ends. */
function liveOut(state: GameState, seed: number): GameState {
  const rng = createRng(seed)
  let s = state
  for (let i = 0; i < 200 && !s.ended; i++) s = runWeek(s, rng, resting).state
  expect(s.ended).not.toBeNull()
  return s
}

describe('a whole legacy: life → farewell → Heartstone → the Shrine → Fusion (M6)', () => {
  it('runs on Standard and the final save validates round-trip', () => {
    const old = makeMonster({ id: 'old', stats: { POW: 600 } })
    old.lifespanTotal = 6
    old.techniques.push({ id: 'universal.beat-bump', uses: 30, level: 2 })
    let state = createGameState({ monster: old, difficulty: 'Standard' })
    state.money = 20_000
    state = liveOut(state, 11)
    expect(state.ended).toBe('passed')

    const farewell = concludeLife(state, 'Strong as a river.')!
    state = farewell.state
    expect(state.monster).toBeNull()
    expect(state.memorial[0]!.monster.id).toBe('old')
    expect(state.memorial[0]!.monster.ageWeeks).toBeGreaterThanOrEqual(6)
    expect(farewell.heartstone!.gains.POW).toBeGreaterThan(0)
    expect(state.elderGrove).toEqual([])

    // A new monster from the Market takes the Heartstone.
    const bought = buyFromMarket(state, 'quillion', 'q1')
    expect(bought.placed).toBe('ranch')
    state = bought.state
    const grant = heartstoneGrant(farewell.heartstone!)
    const before = { ...state.monster!.stats }
    const given = giveHeartstone(state, farewell.heartstone!.id)
    expect(given.refused).toBeNull()
    state = given.state
    for (const k of STAT_KEYS) expect(state.monster!.stats[k]).toBe(Math.min(999, before[k] + grant[k]))
    expect(state.monster!.heirloom).toBe('Basic')
    expect(state.heartstones).toEqual([])

    // Two songs at the Shrine go to the Freezer (the ranch is taken) and fuse.
    const a = awaken(state, 'river song', '', 'a')
    const b = awaken(a.state, 'twinkle twinkle', 'little star', 'b')
    if (a.kind !== 'born' || b.kind !== 'born') throw new Error('expected two births')
    state = b.state
    expect(state.freezer.map((m) => m.id)).toEqual(['a', 'b'])
    const fused = fuse(state, 'a', 'b', null, 'baby', createRng(3))
    expect(fused.refused).toBeNull()
    state = fused.state
    expect(state.freezer.map((m) => m.id)).toEqual(['baby'])
    expect(state.memorial).toHaveLength(3)
    expect(state.memorial.filter((e) => e.cause === 'fused')).toHaveLength(2)
    const baby = state.freezer[0]!
    expect(baby.parents).toEqual(['a', 'b'])
    expect(findRelative(state, 'a')?.name).toBe(a.monster.name)
    expect(findRelative(state, 'b')?.name).toBe(b.monster.name)
    expect(baby.generation).toBe(2)
    // Fusion 2: the baby is one whole breed, whatever mixes the Shrine made.
    expect(baby.subBreed).toBe(baby.mainBreed)

    // Everything new survives a save round trip.
    const raw = JSON.parse(JSON.stringify(makeSave(state, 99)))
    const v = validateSave(raw)
    expect(v.ok).toBe(true)
    if (v.ok) expect(v.save.game).toEqual(state)
  })

  it('on Gentle the old monster retires to the Elder Grove and can still fuse', () => {
    const old = makeMonster({ id: 'old' })
    old.lifespanTotal = 5
    let state = createGameState({ monster: old, difficulty: 'Gentle' })
    state = liveOut(state, 5)
    expect(state.ended).toBe('retired')
    state = concludeLife(state, '')!.state
    expect(state.elderGrove.map((m) => m.id)).toEqual(['old'])
    expect(state.memorial[0]!.cause).toBe('retired')
    const born = awaken(state, 'a second song', '', 'two')
    if (born.kind !== 'born') throw new Error('expected a birth')
    state = born.state
    expect(state.monster?.id).toBe('two')
    const frozen = awaken(state, 'a third song', '', 'three')
    if (frozen.kind !== 'born') throw new Error('expected a birth')
    state = frozen.state
    const fused = fuse(state, 'old', 'three', null, 'baby', createRng(1))
    expect(fused.refused).toBeNull()
    expect(fused.state.elderGrove).toEqual([])
    expect(fused.state.freezer.map((m) => m.id)).toEqual(['baby'])
  })
})
