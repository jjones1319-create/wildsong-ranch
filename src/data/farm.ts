/**
 * CONTENT §11 the farm (v16): extra pens bought with gold once the farm reaches their level, and the perks every
 * level brings by itself. Prices, levels and names are content, like the ranch upgrades; the effects' numbers live
 * in tuning.ts (`FARM`, `FREEZER`, `FRIENDS`) and the rules in core/farm.ts.
 */

export interface FarmPen {
  /** 1-based: the order the pens are built in. */
  n: number
  price: number
  /** The farm level that opens it for purchase. */
  level: number
}

/** The pens beyond the first (FARM.basePens), in the order they are built. */
export const FARM_PENS: readonly FarmPen[] = [
  { n: 1, price: 3000, level: 2 },
  { n: 2, price: 6000, level: 4 },
  { n: 3, price: 10000, level: 6 },
  { n: 4, price: 15000, level: 8 },
  { n: 5, price: 20000, level: 10 },
]

export const FARM_PERK_IDS = ['feedShed', 'farmhand', 'deepFreezer', 'campfire'] as const
export type FarmPerkId = (typeof FARM_PERK_IDS)[number]

export interface FarmPerk {
  id: FarmPerkId
  name: string
  /** The farm level it comes with (no gold needed). */
  level: number
}

export const FARM_PERKS: readonly FarmPerk[] = [
  { id: 'feedShed', name: 'Feed Shed', level: 3 },
  { id: 'farmhand', name: 'Farmhand', level: 5 },
  { id: 'deepFreezer', name: 'Deep Freezer', level: 7 },
  { id: 'campfire', name: 'Campfire Circle', level: 9 },
]

export const FARM_PERK_BY_ID = Object.fromEntries(FARM_PERKS.map((p) => [p.id, p])) as Record<FarmPerkId, FarmPerk>
