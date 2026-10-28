import { describe, expect, it } from 'vitest'
import { KEEPSAKE_BY_ID } from '../data/keepsakes.ts'
import { BOND } from '../data/tuning.ts'
import { KEEPSAKE_IDS } from '../data/types.ts'
import { bondEffect, bondMonster, bondScore, canBuyKeepsake, fadeBond, keepsakeStress, shopFind } from './bond.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { resolveDrill } from './training.ts'
import { endWeek, resolveAction } from './week.ts'

describe('Bond weeks (GAME_DESIGN §6.9)', () => {
  it('calms the monster and builds affection by score, costs a little fatigue, and sets the boost to ×1.75', () => {
    expect(bondEffect('fetch', 0, false)).toEqual({ stress: -8, spoil: 2, fatigue: 4 })
    expect(bondEffect('hide', 5, false)).toEqual({ stress: -18, spoil: 7, fatigue: 4 })
    expect(bondEffect('shop', 0, false)).toEqual({ stress: -14, spoil: 5, fatigue: 4 })
    expect(bondEffect('shop', 0, true).spoil).toBe(8)
    expect(bondScore('fetch', 9)).toBe(5)
    expect(bondScore('fetch', -2)).toBe(0)
    expect(bondScore('hide', Number.NaN)).toBe(0)
    const m = makeMonster({ stress: 30, spoil: 40, fatigue: 10 })
    const r = bondMonster(m, 'fetch', 4, false)
    expect(r.monster).toMatchObject({ stress: 14, spoil: 46, fatigue: 14 })
    expect(r.monster.status.bondPct).toBe(BOND.boostPct)
    expect(m.status.bondPct).toBe(100)
  })

  it('fades the boost by 0.25 a week back to ×1, and bonding again sets ×1.75 (no stacking)', () => {
    let m = makeMonster()
    m.status.bondPct = 175
    const seen: number[] = []
    for (let i = 0; i < 5; i++) {
      m = fadeBond(m)
      seen.push(m.status.bondPct)
    }
    expect(seen).toEqual([150, 125, 100, 100, 100])
    m.status.bondPct = 150
    expect(bondMonster(m, 'hide', 2, false).monster.status.bondPct).toBe(175)
  })

  it('a Bond week boosts the next weeks: ×1.75, ×1.5, ×1.25, then ×1', () => {
    let state = createGameState({ monster: makeMonster({ agePct: 50, stress: 20, spoil: 40, fear: 40 }) })
    state.weekPhase = 'action'
    state = resolveAction(state, { kind: 'bondWeek', activity: 'fetch', score: 3, buy: null }, createRng(1)).state
    expect(state.monster!.status.bondPct).toBe(175)
    const boosts: number[] = []
    for (let i = 0; i < 4; i++) {
      boosts.push(state.monster!.status.bondPct)
      state = resolveAction(state, { kind: 'rest' }, createRng(i)).state
    }
    expect(boosts).toEqual([175, 150, 125, 100])
  })

  it('the boost multiplies drill gains (and only gains)', () => {
    const m = makeMonster({ agePct: 50, spoil: 30, fear: 30 })
    const bonded = structuredClone(m)
    bonded.status.bondPct = 150
    const a = resolveDrill(m, 'log-toss', createRng(3))
    const b = resolveDrill(bonded, 'log-toss', createRng(3))
    expect(b.result.outcome).toBe(a.result.outcome)
    if (a.result.outcome !== 'Fail') expect(b.result.gains.POW).toBe(Math.round((a.result.gains.POW! * 150) / 100))
  })

  it('shopping finds a keepsake the ranch does not have yet, from a seed', () => {
    expect(shopFind(5, [])).toBe(shopFind(5, []))
    for (let seed = 0; seed < 50; seed++) {
      const owned = KEEPSAKE_IDS.slice(0, seed % 9)
      const found = shopFind(seed, owned)
      expect(found).not.toBeNull()
      expect(owned).not.toContain(found)
    }
    expect(shopFind(1, [...KEEPSAKE_IDS])).toBeNull()
  })

  it('buys the keepsake only when the ranch can afford it and has none yet; it then stays on the ranch', () => {
    const base = createGameState({ monster: makeMonster({ stress: 20 }) })
    base.weekPhase = 'action'
    base.money = 1000
    const r = resolveAction(base, { kind: 'bondWeek', activity: 'shop', score: 0, buy: 'pinwheel' }, createRng(1))
    expect(r.state.keepsakes).toEqual(['pinwheel'])
    expect(r.state.money).toBe(1000 - KEEPSAKE_BY_ID.pinwheel.price)
    expect(r.events.find((e) => e.kind === 'bondWeek')).toMatchObject({ bought: 'pinwheel', price: 450 })
    // Too expensive, or already owned: the trip still happens, nothing is bought.
    const poor = resolveAction({ ...base, money: 100 }, { kind: 'bondWeek', activity: 'shop', score: 0, buy: 'story-blocks' }, createRng(1))
    expect(poor.state.keepsakes).toEqual([])
    expect(poor.state.money).toBe(100)
    expect(poor.state.monster!.status.bondPct).toBe(175)
    const again = resolveAction(r.state, { kind: 'bondWeek', activity: 'shop', score: 0, buy: 'pinwheel' }, createRng(1))
    expect(again.state.keepsakes).toEqual(['pinwheel'])
    // Only a shopping trip buys.
    expect(resolveAction(base, { kind: 'bondWeek', activity: 'fetch', score: 2, buy: 'pinwheel' }, createRng(1)).state.keepsakes).toEqual([])
    expect(canBuyKeepsake(450, [], 'pinwheel')).toBe(true)
    expect(canBuyKeepsake(449, [], 'pinwheel')).toBe(false)
  })

  it('keepsakes take 1 stress off each week, at most 4', () => {
    expect(keepsakeStress([])).toBe(0)
    expect(keepsakeStress(['pinwheel', 'kick-ball'])).toBe(2)
    expect(keepsakeStress([...KEEPSAKE_IDS])).toBe(BOND.keepsakeStressMax)
    const state = createGameState({ monster: makeMonster({ stress: 30 }) })
    state.keepsakes = ['pinwheel', 'kick-ball', 'star-plush']
    const plain = endWeek({ ...state, keepsakes: [] }, createRng(2))
    const calmed = endWeek(state, createRng(2))
    expect(plain.state.monster!.stress - calmed.state.monster!.stress).toBe(3)
    expect(calmed.events.some((e) => e.kind === 'keepsakes')).toBe(true)
  })
})
