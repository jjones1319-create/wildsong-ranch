import type { BreedId, Kind } from './types.ts'

/**
 * CONTENT §2.3: Fusion kinds and recipes (GAME_DESIGN §15). Each breed's kinds, the kind rules ("a reptile and a
 * bird can make a dragon") and the signature recipes that win outright. The surprise table is part of the save
 * contract: changing anything here reshuffles every pair's surprises, and a test pins the whole table.
 */

export const BREED_KINDS: Readonly<Record<BreedId, readonly Kind[]>> = {
  puddlepup: ['beast', 'water'],
  tumblefox: ['beast', 'spirit'],
  cobblemaw: ['beast', 'stone'],
  moatshell: ['stone', 'water'],
  wishlume: ['spirit', 'fire'],
  quillion: ['beast', 'knight'],
  cinderlynx: ['beast', 'fire'],
  bloatoad: ['water', 'plant'],
  coilfang: ['reptile', 'night'],
  nimbusheep: ['sky', 'water'],
  galeheron: ['bird', 'sky'],
  nibblegrub: ['bug', 'plant'],
  velvesper: ['bug', 'sky'],
  ashwraith: ['spirit', 'fire'],
  zipwisp: ['spirit', 'sky'],
  mirrorkin: ['spirit', 'construct'],
  gearhoot: ['construct', 'bird'],
  reefclaw: ['water', 'knight'],
  lootlid: ['construct'],
  aurelwyrm: ['dragon'],
  hearthwing: ['dragon', 'fire'],
  grumblestone: ['stone'],
  pluckrex: ['reptile', 'knight'],
  paladove: ['bird', 'knight'],
  starhowl: ['beast', 'night'],
  petalphant: ['beast', 'plant'],
  scrollopus: ['water', 'night'],
  gloomgrin: ['stone', 'night'],
  rammerjack: ['beast', 'knight'],
  frostlance: ['water', 'ice'],
}

/** One parent has kind `a`, the other has `b` (either way round): breeds of kind `makes` are favored. */
export interface FusionRule {
  a: Kind
  b: Kind
  makes: Kind
}

export const FUSION_RULES: readonly FusionRule[] = [
  { a: 'reptile', b: 'bird', makes: 'dragon' },
  { a: 'reptile', b: 'fire', makes: 'dragon' },
  { a: 'fire', b: 'bird', makes: 'dragon' },
  { a: 'dragon', b: 'reptile', makes: 'dragon' },
  { a: 'bug', b: 'sky', makes: 'bug' },
  { a: 'bug', b: 'bird', makes: 'bug' },
  { a: 'spirit', b: 'fire', makes: 'spirit' },
  { a: 'spirit', b: 'construct', makes: 'construct' },
  { a: 'stone', b: 'spirit', makes: 'night' },
  { a: 'beast', b: 'plant', makes: 'plant' },
  { a: 'water', b: 'sky', makes: 'ice' },
  { a: 'sky', b: 'spirit', makes: 'sky' },
  { a: 'construct', b: 'bird', makes: 'construct' },
  { a: 'bird', b: 'water', makes: 'bird' },
  { a: 'reptile', b: 'plant', makes: 'reptile' },
  { a: 'dragon', b: 'water', makes: 'reptile' },
  { a: 'plant', b: 'sky', makes: 'bug' },
  { a: 'stone', b: 'ice', makes: 'stone' },
  { a: 'stone', b: 'fire', makes: 'stone' },
]

/** A hand-picked pair and its signature surprise. `a` < `b`; a locked result only counts once it is unlocked. */
export interface FusionRecipe {
  a: BreedId
  b: BreedId
  makes: BreedId
}

export const FUSION_RECIPES: readonly FusionRecipe[] = [
  { a: 'coilfang', b: 'galeheron', makes: 'hearthwing' },
  { a: 'coilfang', b: 'pluckrex', makes: 'hearthwing' },
  { a: 'cobblemaw', b: 'gloomgrin', makes: 'grumblestone' },
  { a: 'cobblemaw', b: 'moatshell', makes: 'grumblestone' },
  { a: 'nibblegrub', b: 'puddlepup', makes: 'bloatoad' },
  { a: 'coilfang', b: 'hearthwing', makes: 'aurelwyrm' },
  { a: 'coilfang', b: 'hearthwing', makes: 'pluckrex' },
  { a: 'nibblegrub', b: 'wishlume', makes: 'velvesper' },
  { a: 'galeheron', b: 'nibblegrub', makes: 'velvesper' },
  { a: 'cinderlynx', b: 'wishlume', makes: 'ashwraith' },
  { a: 'nimbusheep', b: 'wishlume', makes: 'zipwisp' },
  { a: 'puddlepup', b: 'quillion', makes: 'reefclaw' },
  { a: 'mirrorkin', b: 'moatshell', makes: 'lootlid' },
]
