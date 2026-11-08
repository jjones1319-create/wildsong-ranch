import { ULTRA_LOOKS, ultraHeightPct, type UltraId, type UltraLook } from '../../art/ultraLooks.ts'
import { ART } from '../../data/tuning.ts'
import type { BreedId } from '../../data/types.ts'

/**
 * docs/BATTLE_3D.md §8: who stands in the ring. Each side's look (an Ultra registry look: a breed, or a grown form
 * such as `hearthwing-grown`; anything else is Puddlepup), its variant (only one its file holds) and its height in
 * metres: every look at its true size beside Puddlepup, who stands ART.duel.monsterHeightM tall. Pure (no three), so
 * it is tested on its own.
 */

export interface DuelFighter {
  /** The look shown (its files). */
  look: UltraId
  /** Its breed (the fighter's NPC monster). */
  breed: BreedId
  variant: string | null
  /** Its height at the top (head, ears or horns), metres. */
  heightM: number
}

type Looks = Readonly<Record<UltraId, UltraLook>>

export function duelFighter(id: UltraId | undefined, variant: string | null | undefined, looks: Looks = ULTRA_LOOKS): DuelFighter {
  const look = (id && Object.prototype.hasOwnProperty.call(looks, id) ? looks[id] : undefined) ?? looks.puddlepup ?? ULTRA_LOOKS.puddlepup!
  return {
    look: look.id,
    breed: look.breed,
    variant: variant && look.variants.includes(variant) ? variant : null,
    heightM: (ART.duel.monsterHeightM * ultraHeightPct(look)) / 100,
  }
}

export function duelFighters(o: { looks?: readonly [UltraId, UltraId]; variants: readonly [string | null, string | null] }, looks: Looks = ULTRA_LOOKS): [DuelFighter, DuelFighter] {
  return [duelFighter(o.looks?.[0], o.variants[0], looks), duelFighter(o.looks?.[1], o.variants[1], looks)]
}

/** The models a duel loads: one per look, so two fighters of the same look share one download. */
export function duelLoads(f: readonly DuelFighter[]): UltraId[] {
  return [...new Set(f.map((x) => x.look))]
}
