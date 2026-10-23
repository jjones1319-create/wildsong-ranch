import type { ExpeditionSite, ExpeditionSiteId, LootEntry, StatKey } from './types.ts'

/**
 * CONTENT §8 expedition sites. Each site has its invitation months, the grade and fame the letter asks for,
 * three obstacles with their stat thresholds, the Intellect that reveals hidden spots, one special event node
 * and three loot tables (search spots, treasure, and what the event gives when it holds no key item).
 * Loot is items (sellables, sweets, catalysts, toys, fruit) and universal Songsheets of the listed families.
 */

const item = (id: string, weight: number, qty = 1): LootEntry => ({ kind: 'item', id, qty, weight })
const sheet = (families: readonly ('Basic' | 'Hit' | 'Heavy' | 'Wither' | 'Sharp' | 'Special')[], weight: number): LootEntry => ({ kind: 'sheet', families, weight })
const obstacle = (id: string, name: string, stat: StatKey, threshold: number) => ({ id, name, stat, threshold })

const REGULAR_SWEETS = ['mighty-muffin', 'clever-cookie', 'steady-scone', 'zippy-waffle', 'sturdy-bun', 'lively-pie'] as const
const GRAND_SWEETS = ['grand-muffin', 'grand-cookie', 'grand-scone', 'grand-waffle', 'grand-bun', 'grand-pie'] as const
const TOYS = ['rubber-ball', 'rope-tug', 'music-box', 'paper-kite', 'squeaky-fish', 'puzzle-cube'] as const

export const EXPEDITION_SITES: readonly ExpeditionSite[] = [
  {
    id: 'thornwood-ruins',
    name: 'Thornwood Ruins',
    months: [3, 9],
    gradeMin: 'E',
    fameMin: 20,
    obstacles: [obstacle('brambles', 'Brambles', 'POW', 200), obstacle('riddle-door', 'Riddle door', 'INT', 200), obstacle('snare', 'Snare', 'SKI', 200)],
    hiddenInt: 200,
    event: 'strange-chest',
    eventCheck: null,
    search: [item('old-coin', 30), ...REGULAR_SWEETS.map((id) => item(id, 5)), ...TOYS.map((id) => item(id, 2)), sheet(['Basic', 'Hit'], 15), item('sun-plum', 10, 2)],
    treasure: [item('old-coin', 25, 3), sheet(['Basic', 'Hit'], 25), ...REGULAR_SWEETS.map((id) => item(id, 4, 2)), item('silver-locket', 12), item('moonfruit', 6)],
    eventLoot: [item('old-coin', 50, 5), item('silver-locket', 30, 2), item('moonfruit', 20)],
    blurb: 'Brambles, riddle doors and snares, and a chest that hums.',
  },
  {
    id: 'sunken-library',
    name: 'Sunken Library',
    months: [6],
    gradeMin: 'C',
    fameMin: 40,
    obstacles: [obstacle('sealed-shelves', 'Sealed shelves', 'INT', 300), obstacle('flooded-hall', 'Flooded hall', 'LIF', 200), obstacle('collapsing-floor', 'Collapsing floor', 'SPD', 300)],
    hiddenInt: 350,
    event: 'archive',
    eventCheck: { stat: 'INT', value: 350 },
    search: [item('silver-locket', 30), sheet(['Wither', 'Sharp'], 20), item('clever-cookie', 15, 2), item('old-coin', 15, 2), item('lavender-sachet', 10, 2), item('mind-shard', 5), item('calmleaf-tea', 5)],
    treasure: [item('silver-locket', 30, 3), item('mind-shard', 25), sheet(['Wither', 'Sharp'], 25), item('grand-cookie', 12), item('sunfruit', 8)],
    eventLoot: [item('silver-locket', 50, 3), item('mind-shard', 30), item('sunfruit', 20)],
    blurb: 'Sealed shelves, flooded halls and floors that give way. A hidden archive for the very clever.',
  },
  {
    id: 'hollowmoon-caverns',
    name: 'Hollowmoon Caverns',
    months: [11],
    gradeMin: 'C',
    fameMin: 45,
    obstacles: [obstacle('boulder', 'Boulder', 'POW', 350), obstacle('crystal-trap', 'Crystal trap', 'SKI', 350), obstacle('chill-draft', 'Chill draft', 'DEF', 300)],
    hiddenInt: 300,
    event: 'crystal-heart',
    eventCheck: null,
    search: [item('ruby-chip', 25), item('old-coin', 15, 3), sheet(['Heavy'], 15), ...GRAND_SWEETS.map((id) => item(id, 4)), item('power-shard', 8), item('guard-shard', 8), item('warm-compress', 5)],
    treasure: [item('ruby-chip', 30, 2), sheet(['Heavy'], 25), ...GRAND_SWEETS.map((id) => item(id, 5)), item('power-shard', 7), item('guard-shard', 8)],
    eventLoot: [item('amber-charm', 100)],
    blurb: 'Boulders, crystal traps and dark tunnels that only a bright mind can read.',
  },
  {
    id: 'skyreef-isles',
    name: 'Skyreef Isles',
    months: [8],
    gradeMin: 'B',
    fameMin: 60,
    obstacles: [obstacle('gap', 'Gap', 'SPD', 450), obstacle('gale', 'Gale', 'DEF', 400), obstacle('sky-lock', 'Sky lock', 'INT', 400)],
    hiddenInt: 400,
    event: 'sky-puzzle',
    eventCheck: { stat: 'INT', value: 400 },
    search: [item('starstone', 15), item('ruby-chip', 20), item('swift-shard', 10), item('skill-shard', 10), sheet(['Special'], 10), ...TOYS.map((id) => item(id, 2)), ...GRAND_SWEETS.map((id) => item(id, 3)), item('sunfruit', 5)],
    treasure: [item('starstone', 30, 2), sheet(['Special'], 20), item('swift-shard', 12), item('skill-shard', 12), item('sunfruit', 12), item('potential-pearl', 6), item('wondercake', 8)],
    eventLoot: [item('starstone', 70), item('ruby-chip', 30, 2)],
    blurb: 'Gaps, gales and sky puzzles. Starstones for the brave.',
  },
]

export const EXPEDITION_SITE_BY_ID = Object.fromEntries(EXPEDITION_SITES.map((s) => [s.id, s])) as Record<ExpeditionSiteId, ExpeditionSite>
