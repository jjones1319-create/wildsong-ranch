import { describe, expect, it } from 'vitest'
import { applyMonthlyFood, foodRelation, isBoredOf, monthlyFoodEffect } from './food.ts'
import { makeMonster } from './test-helpers.ts'

describe('monthly food (§8, CONTENT §5)', () => {
  it('applies neutral, liked and disliked effects', () => {
    const m = makeMonster({ stress: 30, spoil: 30, fear: 30 }) // likes honey-bread, dislikes turnips
    expect(foodRelation(m, 'honey-bread')).toBe('liked')
    expect(foodRelation(m, 'turnips')).toBe('disliked')
    expect(foodRelation(m, 'river-fish')).toBe('neutral')
    expect(applyMonthlyFood(m, 'honey-bread').monster).toMatchObject({ stress: 24, form: 4, spoil: 31 })
    expect(applyMonthlyFood(m, 'turnips').monster).toMatchObject({ stress: 42 })
    expect(applyMonthlyFood(m, 'river-fish').monster).toMatchObject({ stress: 27, form: 2 })
    expect(applyMonthlyFood(m, 'roast-haunch').monster).toMatchObject({ stress: 24, form: 6 })
  })

  it('Hearty Stew adds a week of life every month, even when disliked', () => {
    const m = makeMonster()
    expect(applyMonthlyFood(m, 'hearty-stew').monster.lifespanTotal).toBe(419)
    const hater = makeMonster({ likes: { ...m.likes, dislikedFood: 'hearty-stew' } })
    expect(applyMonthlyFood(hater, 'hearty-stew').monster.lifespanTotal).toBe(419)
  })

  it('tracks the diet and halves the positive effects from the 3rd month in a row', () => {
    let m = makeMonster({ stress: 50 })
    expect(isBoredOf(m, 'herbal-pellets')).toBe(false)
    m = applyMonthlyFood(m, 'herbal-pellets').monster // −12 → 38
    expect(m.diet).toMatchObject({ lastFood: 'herbal-pellets', sameFoodStreak: 1, monthsFed: 1 })
    m = applyMonthlyFood(m, 'herbal-pellets').monster // −12 → 26
    expect(isBoredOf(m, 'herbal-pellets')).toBe(true)
    const third = applyMonthlyFood(m, 'herbal-pellets')
    expect(third.bored).toBe(true)
    expect(third.effect.stress).toBe(-6)
    expect(third.monster.stress).toBe(20)
    expect(third.monster.diet.sameFoodStreak).toBe(3)
    const switched = applyMonthlyFood(third.monster, 'berry-pudding')
    expect(switched.monster.diet).toMatchObject({ lastFood: 'berry-pudding', sameFoodStreak: 1, puddingCount: 1 })
  })

  it('Big Appetite scales good and bad effects ×1.5 and Hungry Grub scales form ×1.5', () => {
    const toad = makeMonster({ main: 'bloatoad', stress: 30 })
    expect(monthlyFoodEffect(toad, 'river-fish')).toMatchObject({ stress: -4, form: 3 }) // −3·1.5 = −4.5 → −4 (half even), 2·1.5 = 3
    expect(monthlyFoodEffect(toad, 'turnips')).toMatchObject({ stress: 18 })
    const grub = makeMonster({ main: 'nibblegrub' })
    expect(monthlyFoodEffect(grub, 'roast-haunch')).toMatchObject({ stress: -6, form: 9 })
  })
})
