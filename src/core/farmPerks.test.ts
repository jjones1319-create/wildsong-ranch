import { describe, expect, it, vi } from 'vitest'

// The perks are on since v1.21.0 (FARM.perksLive); the mock keeps these tests about the perks themselves either way.
vi.mock('../data/tuning.ts', async (importOriginal) => {
  const real = await importOriginal<typeof import('../data/tuning.ts')>()
  return { ...real, FARM: { ...real.FARM, perksLive: true } }
})

const { FOOD_BY_ID } = await import('../data/foods.ts')
const { FARM, FREEZER, HERD } = await import('../data/tuning.ts')
const { newRanchmate } = await import('./creation.ts')
const { hasPerk } = await import('./farm.ts')
const { mateFoodPrice, monthlyFoodCost, tickHerdMut } = await import('./herd.ts')
const { freezerFull, freezerSlots } = await import('./legacy.ts')
const { createRng } = await import('./rng.ts')
const { createGameState } = await import('./state.ts')
const { makeMonster } = await import('./test-helpers.ts')
const { isGoodOutcome } = await import('./outcomes.ts')
const { applyReaction, resolveDrill } = await import('./training.ts')

function atLevel(level: number) {
  const s = createGameState({ monster: makeMonster({ id: 'star' }) })
  s.farm.xp = FARM.levelXp[level - 1]!
  return s
}

describe('the farm perks, switched on (CONTENT §11)', () => {
  it('Feed Shed (Lv3): ranch-mates eat at 60% of the price', () => {
    const price = FOOD_BY_ID['roast-haunch'].price
    expect(mateFoodPrice(atLevel(2), 'roast-haunch')).toBe(price)
    const s = atLevel(3)
    expect(hasPerk(s, 'feedShed')).toBe(true)
    expect(mateFoodPrice(s, 'roast-haunch')).toBe(Math.round((price * FARM.feedShedPct) / 100))
    s.ranchmates = [newRanchmate(makeMonster({ id: 'a' }))]
    expect(monthlyFoodCost(s, 'roast-haunch')).toEqual({ mouths: 2, total: price + mateFoodPrice(s, 'roast-haunch') })
  })

  it('Farmhand (Lv5): a ranch-mate’s good drill is praised', () => {
    const s = atLevel(5)
    s.ranchmates = [{ ...newRanchmate(makeMonster({ id: 'a' })), order: { kind: 'drill', drill: 'log-toss' } }]
    const before = s.ranchmates[0]!.monster
    const r = tickHerdMut(s, createRng(2))[0]!
    const solo = resolveDrill(before, 'log-toss', createRng(2), { trainingYard: false })
    expect(r.last).toMatchObject({ kind: 'drill', outcome: solo.result.outcome })
    expect(isGoodOutcome(solo.result.outcome)).toBe(true)
    const praised = applyReaction(solo.monster, solo.result.outcome, 'praise')
    expect(s.ranchmates[0]!.monster.spoil).toBe(praised.spoil)
    expect(HERD.payPct).toBe(50)
  })

  it('Deep Freezer (Lv7): the Freezer holds 30', () => {
    expect(freezerSlots(atLevel(6))).toBe(FREEZER.slots)
    const s = atLevel(7)
    expect(freezerSlots(s)).toBe(FREEZER.deepSlots)
    s.freezer = Array.from({ length: FREEZER.slots }, (_, i) => makeMonster({ id: `f${i}` }))
    expect(freezerFull(s)).toBe(false)
  })
})
