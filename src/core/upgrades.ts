import { RANCH_UPGRADES, RANCH_UPGRADE_BY_ID } from '../data/upgrades.ts'
import { UPGRADES } from '../data/tuning.ts'
import type { RanchUpgrade, UpgradeId } from '../data/types.ts'
import { monthIndexOf } from './legacy.ts'
import { addCondition } from './monster.ts'
import type { GameState } from './state.ts'

/**
 * CONTENT §11 ranch upgrades. Ines's letter arrives every May week 4; the upgrades themselves can be bought
 * any time the gate is met (nothing is missable). Their weekly effects run in week.ts and training.ts; the
 * Lantern Garden's monthly visit and the extra Heartstone slots are here and in legacy.ts.
 */

export interface UpgradeOffer {
  upgrade: RanchUpgrade
  owned: boolean
  blocked: 'rank' | 'memorial' | 'money' | null
}

function gate(state: GameState, u: RanchUpgrade): 'rank' | 'memorial' | null {
  if (u.requires.kind === 'rank') return state.breeder.rank >= u.requires.rank ? null : 'rank'
  return state.memorial.length > 0 ? null : 'memorial'
}

export function upgradeOffers(state: GameState): UpgradeOffer[] {
  return RANCH_UPGRADES.map((upgrade) => {
    const owned = state.upgrades[upgrade.id]
    const g = gate(state, upgrade)
    return { upgrade, owned, blocked: owned ? null : (g ?? (state.money < upgrade.price ? 'money' : null)) }
  })
}

export type UpgradeRefusal = 'unknown' | 'owned' | 'rank' | 'memorial' | 'money'

export function buyUpgrade(input: GameState, id: UpgradeId): { state: GameState; refused: UpgradeRefusal | null } {
  const u = RANCH_UPGRADE_BY_ID[id]
  if (!u) return { state: input, refused: 'unknown' }
  if (input.upgrades[id]) return { state: input, refused: 'owned' }
  const g = gate(input, u)
  if (g) return { state: input, refused: g }
  if (input.money < u.price) return { state: input, refused: 'money' }
  const state = structuredClone(input)
  state.money -= u.price
  state.upgrades[id] = true
  return { state, refused: null }
}

export type GardenRefusal = 'noGarden' | 'noMonster' | 'visited'

export function canVisitGarden(state: GameState): { ok: true } | { ok: false; reason: GardenRefusal } {
  if (!state.upgrades.lanternGarden) return { ok: false, reason: 'noGarden' }
  if (!state.monster || state.ended) return { ok: false, reason: 'noMonster' }
  if (state.memorialVisitMonth !== null && state.memorialVisitMonth === monthIndexOf(state.week)) return { ok: false, reason: 'visited' }
  return { ok: true }
}

/** A free visit to the Memorial's Lantern Garden, once a month: stress −5. */
export function visitGarden(input: GameState): { state: GameState; refused: GardenRefusal | null } {
  const can = canVisitGarden(input)
  if (!can.ok) return { state: input, refused: can.reason }
  const state = structuredClone(input)
  state.monster!.stress = addCondition(state.monster!.stress, -UPGRADES.lanternGardenVisitStress)
  state.memorialVisitMonth = monthIndexOf(state.week)
  return { state, refused: null }
}
