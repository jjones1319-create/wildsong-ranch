import type { Food, FoodId } from './types.ts'

/** CONTENT §5 monthly food. Effects are per month; "S" = stress, "Sp" = spoil, "Fe" = fear. */
export const FOODS: readonly Food[] = [
  { id: 'turnips', name: 'Turnips', price: 20, neutral: { stress: 4, fear: 2 }, liked: { spoil: 2 }, disliked: { stress: 12 } },
  { id: 'river-fish', name: 'River Fish', price: 100, neutral: { stress: -3, form: 2 }, liked: { stress: -6, form: 2 }, disliked: { stress: 2 } },
  { id: 'honey-bread', name: 'Honey Bread', price: 120, neutral: { stress: -4, form: 3 }, liked: { stress: -6, form: 4, spoil: 1 }, disliked: { stress: 2 } },
  { id: 'berry-pudding', name: 'Berry Pudding', price: 150, neutral: { stress: -5, form: -2 }, liked: { stress: -8, form: -3 }, disliked: { stress: 1 } },
  { id: 'roast-haunch', name: 'Roast Haunch', price: 300, neutral: { stress: -6, form: 6 }, liked: { stress: -9, form: 7 }, disliked: { fear: 2 } },
  { id: 'hearty-stew', name: 'Hearty Stew', price: 450, neutral: { stress: -8, form: 3, life: 1 }, liked: { stress: -11, form: 3, life: 1 }, disliked: { stress: -2, life: 1 } },
  { id: 'herbal-pellets', name: 'Herbal Pellets', price: 500, neutral: { stress: -12 }, liked: { stress: -15 }, disliked: { stress: -9 } },
]

export const FOOD_BY_ID = Object.fromEntries(FOODS.map((f) => [f.id, f])) as Record<FoodId, Food>
