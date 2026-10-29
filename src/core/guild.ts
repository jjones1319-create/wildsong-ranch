import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { TECHNIQUES, TECHNIQUE_BY_ID } from '../data/techniques.ts'
import type { BreedId, Technique } from '../data/types.ts'
import { categoryAllowedInDebt, inDebt } from './economy.ts'
import { addSheet, goodFit, ownsSheet } from './songbook.ts'
import type { GameState } from './state.ts'

/**
 * GAME_DESIGN §10.5: the Guild Library sells the universal Songsheets and the breed sheets of every unlocked
 * breed. Prices and rank gates are content (data/techniques.ts). Signature sheets are never sold.
 * Until the Journal arrives (M7), "unlocked" means every breed that is not locked at the start.
 */

export interface SheetOffer {
  tech: Technique
  price: number
  rankMin: number
  owned: boolean
  /** Why it can't be bought right now. */
  blocked: 'rank' | 'debt' | null
  /** ★ good fit for the active monster (null without a monster). */
  fit: boolean | null
  /** Whether the active monster could learn it at all (kit, quirk, universal, pure Signature). */
  learnable: boolean | null
}

export function sheetsForSale(state: GameState, unlocked: readonly BreedId[] = STARTING_UNLOCKED): SheetOffer[] {
  const m = state.monster
  const out: SheetOffer[] = []
  for (const tech of TECHNIQUES) {
    if (!tech.sheet || !tech.sheet.sold) continue
    if (tech.breed !== 'universal' && !unlocked.includes(tech.breed)) continue
    const owned = ownsSheet(state.songbook, tech.id)
    const blocked: SheetOffer['blocked'] = state.breeder.rank < tech.sheet.rankMin ? 'rank' : inDebt(state) && !categoryAllowedInDebt('key') ? 'debt' : null
    out.push({
      tech,
      price: tech.sheet.price,
      rankMin: tech.sheet.rankMin,
      owned,
      blocked,
      fit: m ? goodFit(m, tech) : null,
      learnable: m ? learnableBy(m, tech) : null,
    })
  }
  return out
}

function learnableBy(m: NonNullable<GameState['monster']>, tech: Technique): boolean {
  return tech.breed === 'universal' || tech.breed === m.mainBreed
}

export type SheetRefusal = 'unknown' | 'notSold' | 'owned' | 'rank' | 'debt' | 'money'

/** Buys a Songsheet into the Songbook (kept forever). Pure. */
export function buySheet(input: GameState, techId: string): { state: GameState; cost: number; refused: SheetRefusal | null } {
  const tech = TECHNIQUE_BY_ID[techId]
  if (!tech) return { state: input, cost: 0, refused: 'unknown' }
  if (!tech.sheet || !tech.sheet.sold) return { state: input, cost: 0, refused: 'notSold' }
  if (ownsSheet(input.songbook, techId)) return { state: input, cost: 0, refused: 'owned' }
  if (input.breeder.rank < tech.sheet.rankMin) return { state: input, cost: 0, refused: 'rank' }
  if (inDebt(input)) return { state: input, cost: 0, refused: 'debt' }
  if (input.money < tech.sheet.price) return { state: input, cost: 0, refused: 'money' }
  const state = structuredClone(input)
  state.money -= tech.sheet.price
  state.songbook = addSheet(state.songbook, techId)
  return { state, cost: tech.sheet.price, refused: null }
}
