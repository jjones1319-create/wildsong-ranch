import { FOOD_BY_ID } from '../data/foods.ts'
import { FOOD, RANGES, TRAIT_EFFECTS } from '../data/tuning.ts'
import type { FoodEffect, FoodId } from '../data/types.ts'
import { clamp, divRound } from './mathx.ts'
import { addCondition, addForm, traitOf, type Monster } from './monster.ts'
import { likesEveryFood } from './variants.ts'

/** GAME_DESIGN §8 monthly food (tables in CONTENT §5). */

export type FoodRelation = 'liked' | 'disliked' | 'neutral'

export function foodRelation(m: Monster, food: FoodId): FoodRelation {
  if (m.likes.food === food || likesEveryFood(m)) return 'liked'
  if (m.likes.dislikedFood === food) return 'disliked'
  return 'neutral'
}

/** True when this would be the 3rd (or later) month in a row of the same food. */
export function isBoredOf(m: Monster, food: FoodId): boolean {
  return m.diet.lastFood === food && m.diet.sameFoodStreak >= FOOD.boredomMonths - 1
}

/** The effect this month's food would have, after boredom and traits. */
export function monthlyFoodEffect(m: Monster, food: FoodId): FoodEffect {
  const base = FOOD_BY_ID[food][foodRelation(m, food)]
  let stress = base.stress ?? 0
  let spoil = base.spoil ?? 0
  let fear = base.fear ?? 0
  let form = base.form ?? 0
  const life = base.life ?? 0
  if (isBoredOf(m, food)) {
    if (stress < 0) stress = divRound(stress, FOOD.boredomDivisor)
    if (spoil > 0) spoil = divRound(spoil, FOOD.boredomDivisor)
  }
  const trait = traitOf(m)
  if (trait === 'big-appetite') {
    const { num, den } = TRAIT_EFFECTS.bigAppetite
    stress = divRound(stress * num, den)
    spoil = divRound(spoil * num, den)
    fear = divRound(fear * num, den)
    form = divRound(form * num, den)
  }
  if (trait === 'hungry-grub') form = divRound(form * TRAIT_EFFECTS.hungryGrubForm.num, TRAIT_EFFECTS.hungryGrubForm.den)
  return { stress, spoil, fear, form, life }
}

/** Feeds the month's food (week 1 of each month). Pure: returns a new monster. */
export function applyMonthlyFood(input: Monster, food: FoodId): { monster: Monster; effect: FoodEffect; bored: boolean; relation: FoodRelation } {
  const m = structuredClone(input)
  const bored = isBoredOf(m, food)
  const effect = monthlyFoodEffect(m, food)
  m.stress = addCondition(m.stress, effect.stress ?? 0)
  m.spoil = addCondition(m.spoil, effect.spoil ?? 0)
  m.fear = addCondition(m.fear, effect.fear ?? 0)
  m.form = addForm(m.form, effect.form ?? 0)
  m.lifespanTotal = clamp(m.lifespanTotal + (effect.life ?? 0), RANGES.lifespan.min, RANGES.lifespan.max)
  m.diet.sameFoodStreak = m.diet.lastFood === food ? m.diet.sameFoodStreak + 1 : 1
  m.diet.lastFood = food
  m.diet.monthsFed += 1
  if (food === 'berry-pudding') m.diet.puddingCount += 1
  return { monster: m, effect, bored, relation: foodRelation(m, food) }
}
