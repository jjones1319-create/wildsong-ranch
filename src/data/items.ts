import type { Item, StatKey, ToyId } from './types.ts'

/**
 * CONTENT §6 items. There is NO limit on how many you buy or use (GAME_DESIGN §8); the only exceptions are
 * the two life fruits (once per monster each) and the optional "one item per week" setting.
 * Songsheets are not listed here: every non-Basic technique has one (see data/techniques.ts and core/songbook.ts).
 */

const SWEET_NAMES: Record<StatKey, { regular: string; grand: string }> = {
  POW: { regular: 'Mighty Muffin', grand: 'Grand Muffin' },
  INT: { regular: 'Clever Cookie', grand: 'Grand Cookie' },
  SKI: { regular: 'Steady Scone', grand: 'Grand Scone' },
  SPD: { regular: 'Zippy Waffle', grand: 'Grand Waffle' },
  DEF: { regular: 'Sturdy Bun', grand: 'Grand Bun' },
  LIF: { regular: 'Lively Pie', grand: 'Grand Pie' },
}

function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}

const sweets: Item[] = (['POW', 'INT', 'SKI', 'SPD', 'DEF', 'LIF'] as const).flatMap((stat) => [
  { id: slug(SWEET_NAMES[stat].regular), name: SWEET_NAMES[stat].regular, category: 'sweet', price: 400, gate: null, effect: { kind: 'sweet', stat, amount: 5 }, sell: null } satisfies Item,
  { id: slug(SWEET_NAMES[stat].grand), name: SWEET_NAMES[stat].grand, category: 'sweet', price: 1500, gate: { needsGradeC: true }, effect: { kind: 'sweet', stat, amount: 15 }, sell: null } satisfies Item,
])

const TOY_NAMES: Record<ToyId, string> = {
  'rubber-ball': 'Rubber Ball',
  'rope-tug': 'Rope Tug',
  'music-box': 'Music Box',
  'paper-kite': 'Paper Kite',
  'squeaky-fish': 'Squeaky Fish',
  'puzzle-cube': 'Puzzle Cube',
}

const toys: Item[] = (Object.keys(TOY_NAMES) as ToyId[]).map((id) => ({
  id,
  name: TOY_NAMES[id],
  category: 'toy',
  price: 300,
  gate: null,
  effect: { kind: 'toy' },
  sell: null,
}))

const tonic = (id: string, name: string, stat: StatKey): Item => ({
  id,
  name,
  category: 'tonic',
  price: 1500,
  gate: null,
  effect: { kind: 'tonic', stat },
  sell: null,
})

const shard = (id: string, name: string, stat: StatKey): Item => ({
  id,
  name,
  category: 'catalyst',
  price: 3000,
  gate: null,
  effect: { kind: 'catalyst', stat, lifespan: 0, lineageSeal: false },
  sell: null,
})

const keyItem = (id: string, name: string): Item => ({ id, name, category: 'key', price: null, gate: null, effect: { kind: 'key' }, sell: null })
const sellable = (id: string, name: string, sell: number): Item => ({ id, name, category: 'sellable', price: null, gate: null, effect: { kind: 'sellable' }, sell })

export const ITEMS: readonly Item[] = [
  { id: 'sun-plum', name: 'Sun Plum', category: 'recovery', price: 60, gate: null, effect: { kind: 'fatigue', amount: -10 }, sell: null },
  { id: 'warm-compress', name: 'Warm Compress', category: 'recovery', price: 200, gate: null, effect: { kind: 'fatigue', amount: -25 }, sell: null },
  { id: 'lavender-sachet', name: 'Lavender Sachet', category: 'recovery', price: 100, gate: null, effect: { kind: 'stress', amount: -10 }, sell: null },
  { id: 'calmleaf-tea', name: 'Calmleaf Tea', category: 'recovery', price: 200, gate: null, effect: { kind: 'stressHalve' }, sell: null },
  { id: 'berry-tart', name: 'Berry Tart', category: 'mood', price: 150, gate: null, effect: { kind: 'spoil', amount: 8 }, sell: null },
  { id: 'thunder-rattle', name: 'Thunder Rattle', category: 'mood', price: 150, gate: null, effect: { kind: 'fear', amount: 8 }, sell: null },
  { id: 'kindness-charm', name: 'Kindness Charm', category: 'mood', price: 120, gate: null, effect: { kind: 'nature', amount: 5 }, sell: null },
  { id: 'mischief-charm', name: 'Mischief Charm', category: 'mood', price: 120, gate: null, effect: { kind: 'nature', amount: -5 }, sell: null },
  { id: 'honey-taffy', name: 'Honey Taffy', category: 'form', price: 120, gate: null, effect: { kind: 'form', amount: 10 }, sell: null },
  { id: 'leanroot-tea', name: 'Leanroot Tea', category: 'form', price: 120, gate: null, effect: { kind: 'form', amount: -10 }, sell: null },
  ...sweets,
  { id: 'wondercake', name: 'Wondercake', category: 'sweet', price: 2500, gate: { rank: 3 }, effect: { kind: 'sweet', stat: 'all', amount: 5 }, sell: null },
  { id: 'potential-pearl', name: 'Potential Pearl', category: 'potential', price: 8000, gate: { rank: 5 }, effect: { kind: 'potentialGrade' }, sell: null },
  { id: 'tempo-bell', name: 'Tempo Bell', category: 'potential', price: 6000, gate: { rank: 4 }, effect: { kind: 'tempoBell' }, sell: null },
  tonic('ironroot-tonic', 'Ironroot Tonic', 'POW'),
  tonic('sagebrew', 'Sagebrew', 'INT'),
  tonic('hawkeye-drops', 'Hawkeye Drops', 'SKI'),
  tonic('swiftmint', 'Swiftmint', 'SPD'),
  tonic('stoneskin-salve', 'Stoneskin Salve', 'DEF'),
  tonic('heartroot-elixir', 'Heartroot Elixir', 'LIF'),
  { id: 'sunfruit', name: 'Sunfruit', category: 'fruit', price: null, gate: null, effect: { kind: 'fruit', weeks: 40, flag: 'usedSunfruit' }, sell: null },
  { id: 'moonfruit', name: 'Moonfruit', category: 'fruit', price: null, gate: null, effect: { kind: 'fruit', weeks: 20, flag: 'usedMoonfruit' }, sell: null },
  ...toys,
  { id: 'wind-chime', name: 'Wind Chime', category: 'charm', price: 2000, gate: null, effect: { kind: 'charm', slot: 'comfort', tier: 1, value: 2 }, sell: null },
  { id: 'silver-chime', name: 'Silver Chime', category: 'charm', price: 6000, gate: null, effect: { kind: 'charm', slot: 'comfort', tier: 2, value: 4 }, sell: null },
  { id: 'gold-chime', name: 'Gold Chime', category: 'charm', price: 15000, gate: null, effect: { kind: 'charm', slot: 'comfort', tier: 3, value: 6 }, sell: null },
  { id: 'straw-bed', name: 'Straw Bed', category: 'charm', price: 2000, gate: null, effect: { kind: 'charm', slot: 'bedding', tier: 1, value: 3 }, sell: null },
  { id: 'feather-bed', name: 'Feather Bed', category: 'charm', price: 6000, gate: null, effect: { kind: 'charm', slot: 'bedding', tier: 2, value: 6 }, sell: null },
  { id: 'cloud-bed', name: 'Cloud Bed', category: 'charm', price: 15000, gate: null, effect: { kind: 'charm', slot: 'bedding', tier: 3, value: 10 }, sell: null },
  shard('power-shard', 'Power Shard', 'POW'),
  shard('mind-shard', 'Mind Shard', 'INT'),
  shard('skill-shard', 'Skill Shard', 'SKI'),
  shard('swift-shard', 'Swift Shard', 'SPD'),
  shard('guard-shard', 'Guard Shard', 'DEF'),
  shard('life-shard', 'Life Shard', 'LIF'),
  { id: 'amber-charm', name: 'Amber Charm', category: 'catalyst', price: null, gate: null, effect: { kind: 'catalyst', stat: null, lifespan: 20, lineageSeal: false }, sell: null },
  { id: 'lineage-seal', name: 'Lineage Seal', category: 'catalyst', price: 5000, gate: { rank: 5 }, effect: { kind: 'catalyst', stat: null, lifespan: 0, lineageSeal: true }, sell: null },
  keyItem('mentor-charm-iron-quarry', "Oduya's Charm"),
  keyItem('mentor-charm-windrun-steppe', "Lark's Charm"),
  keyItem('mentor-charm-starfall-observatory', "Ilsabet's Charm"),
  keyItem('mentor-charm-archers-glade', "Teo's Charm"),
  keyItem('mentor-charm-glacier-bastion', "Brask's Charm"),
  keyItem('vigil-lantern', 'Vigil Lantern'),
  keyItem('stormglass', 'Stormglass'),
  keyItem('shard-mask', 'Shard Mask'),
  keyItem('brass-blueprint', 'Brass Blueprint'),
  keyItem('wyrm-scale', 'Wyrm Scale'),
  sellable('old-coin', 'Old Coin', 300),
  sellable('silver-locket', 'Silver Locket', 800),
  sellable('ruby-chip', 'Ruby Chip', 2000),
  sellable('starstone', 'Starstone', 6000),
]

export const ITEM_BY_ID: Readonly<Record<string, Item>> = Object.fromEntries(ITEMS.map((i) => [i.id, i]))

export function itemById(id: string): Item | undefined {
  return ITEM_BY_ID[id]
}

/** The regular (+5) Stat Sweet for a stat. */
export function sweetFor(stat: StatKey): Item {
  return ITEM_BY_ID[slug(SWEET_NAMES[stat].regular)]!
}

/** The Grand (+15) Stat Sweet for a stat. */
export function grandSweetFor(stat: StatKey): Item {
  return ITEM_BY_ID[slug(SWEET_NAMES[stat].grand)]!
}
