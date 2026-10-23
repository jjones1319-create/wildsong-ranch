import type { RanchUpgrade, UpgradeId } from './types.ts'

/**
 * CONTENT §11 ranch upgrades, offered by mail every May week 4. Prices and gates are content, like item prices;
 * the weekly effects (stress relief, the Great bonus, the garden visit, the Heartstone slots) are rules in tuning.ts.
 */
export const RANCH_UPGRADES: readonly RanchUpgrade[] = [
  { id: 'cozyBarn', name: 'Cozy Barn', price: 8000, requires: { kind: 'rank', rank: 2 } },
  { id: 'trainingYard', name: 'Training Yard', price: 10000, requires: { kind: 'rank', rank: 3 } },
  { id: 'tidePool', name: 'Tide Pool', price: 12000, requires: { kind: 'rank', rank: 4 } },
  { id: 'lanternGarden', name: 'Lantern Garden', price: 6000, requires: { kind: 'memorial' } },
]

export const RANCH_UPGRADE_BY_ID = Object.fromEntries(RANCH_UPGRADES.map((u) => [u.id, u])) as Record<UpgradeId, RanchUpgrade>
