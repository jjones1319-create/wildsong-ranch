import type { BreedId, Stats } from './types.ts'

/**
 * CONTENT §12 secret phrases. Only the cyrb53 hash (seed SHRINE.secretSalt) of each normalized phrase is
 * stored here, never the words, so the source doesn't spoil them. The Shrine checks the "Song or phrase"
 * field alone; the artist field still shapes the roll. Each hit is a special variant: a pure monster of its
 * breed with a unique palette (art/monster/variants.ts), a small bonus and an Encyclopedia entry of its own.
 */

export type VariantPerk =
  /** Likes every monthly food. */
  | 'likesEveryFood'
  /** Born loving Honey Bread. */
  | 'lovesHoneyBread'
  /** Stress relief on every birthday (VARIANTS.birthdayStressRelief). */
  | 'birthdayCalm'
  /** Far techniques +hit (VARIANTS.farHit). */
  | 'farHit'
  /** Wither techniques +wither (VARIANTS.witherPlus). */
  | 'witherPlus'
  /** Prize money +VARIANTS.prizeBonusPct (stacks with the Gilded trait). */
  | 'prizeBonus'

export interface SecretVariant {
  id: string
  /** cyrb53(normalizedPhrase, SHRINE.secretSalt). */
  hash: number
  breed: BreedId
  /** "Songheart" in "Songheart Puddlepup". */
  adjective: string
  /** The look, in plain words (the palette lives in art/monster/variants.ts). */
  look: string
  stats: Partial<Stats>
  lifespan: number
  perk: VariantPerk | null
}

const all = (n: number): Stats => ({ LIF: n, POW: n, INT: n, SKI: n, SPD: n, DEF: n })

export const SECRETS: readonly SecretVariant[] = [
  { id: 'songheart-puddlepup', hash: 2462341432342021, breed: 'puddlepup', adjective: 'Songheart', look: 'rainbow fins', stats: all(15), lifespan: 0, perk: 'likesEveryFood' },
  { id: 'town-crier-tumblefox', hash: 5013240312583771, breed: 'tumblefox', adjective: 'Town Crier', look: 'a little bell', stats: { INT: 20 }, lifespan: 0, perk: null },
  { id: 'glitch-tumblefox', hash: 5709847022354368, breed: 'tumblefox', adjective: 'Glitch', look: 'pixel-glitch colours', stats: { SPD: 60, DEF: -20 }, lifespan: 0, perk: null },
  { id: 'party-bloatoad', hash: 2848504179665864, breed: 'bloatoad', adjective: 'Party', look: 'confetti spots', stats: {}, lifespan: 0, perk: 'birthdayCalm' },
  { id: 'stormcrown-nimbusheep', hash: 65416236956455, breed: 'nimbusheep', adjective: 'Stormcrown', look: 'dark cloud wool', stats: { INT: 30 }, lifespan: 0, perk: null },
  { id: 'porcelain-moatshell', hash: 5463167194985905, breed: 'moatshell', adjective: 'Porcelain', look: 'blue-and-white china shell', stats: { DEF: 30 }, lifespan: 0, perk: null },
  { id: 'bonfire-cinderlynx', hash: 578459760967049, breed: 'cinderlynx', adjective: 'Bonfire', look: 'bright flames', stats: { POW: 25 }, lifespan: 0, perk: null },
  { id: 'imperial-coilfang', hash: 1328602912528736, breed: 'coilfang', adjective: 'Imperial', look: 'gold scales', stats: {}, lifespan: 20, perk: null },
  { id: 'syrup-nibblegrub', hash: 5077203295737958, breed: 'nibblegrub', adjective: 'Syrup', look: 'amber', stats: {}, lifespan: 0, perk: 'lovesHoneyBread' },
  { id: 'beacon-wishlume', hash: 5324941139222669, breed: 'wishlume', adjective: 'Beacon', look: 'red-and-white stripes', stats: {}, lifespan: 0, perk: 'farHit' },
  { id: 'champion-quillion', hash: 8841137359569516, breed: 'quillion', adjective: 'Champion', look: 'a gold cape', stats: { SKI: 30 }, lifespan: 0, perk: null },
  { id: 'dawnwing-galeheron', hash: 6502507587277429, breed: 'galeheron', adjective: 'Dawnwing', look: 'peach and rose plumage', stats: { SPD: 25 }, lifespan: 0, perk: null },
  { id: 'granite-cobblemaw', hash: 3668797296081556, breed: 'cobblemaw', adjective: 'Granite', look: 'polished granite', stats: { DEF: 30 }, lifespan: 0, perk: null },
  { id: 'moonlit-velvesper', hash: 3395119998477998, breed: 'velvesper', adjective: 'Moonlit', look: 'silver wings', stats: { INT: 25 }, lifespan: 0, perk: null },
  { id: 'lantern-bearer-ashwraith', hash: 5883716253242414, breed: 'ashwraith', adjective: 'Lantern-bearer', look: 'blue flame', stats: {}, lifespan: 0, perk: 'witherPlus' },
  { id: 'prism-zipwisp', hash: 7915710081152210, breed: 'zipwisp', adjective: 'Prism', look: 'rainbow sparks', stats: { SKI: 25 }, lifespan: 0, perk: null },
  { id: 'obsidian-mirrorkin', hash: 4514155527882556, breed: 'mirrorkin', adjective: 'Obsidian', look: 'black glass', stats: { INT: 25 }, lifespan: 0, perk: null },
  { id: 'silver-gearhoot', hash: 8088189738947126, breed: 'gearhoot', adjective: 'Silver', look: 'silver plates', stats: { DEF: 20, INT: 10 }, lifespan: 0, perk: null },
  { id: 'abyss-reefclaw', hash: 8279694354892750, breed: 'reefclaw', adjective: 'Abyss', look: 'deep-sea blue coral', stats: { DEF: 25 }, lifespan: 0, perk: null },
  { id: 'gilded-lootlid', hash: 1915205757674311, breed: 'lootlid', adjective: 'Gilded', look: 'solid gold', stats: {}, lifespan: 0, perk: 'prizeBonus' },
  { id: 'sunsoul-aurelwyrm', hash: 3366503938878653, breed: 'aurelwyrm', adjective: 'Sunsoul', look: 'white-gold', stats: all(10), lifespan: 0, perk: null },
]

export const SECRET_BY_ID: Readonly<Record<string, SecretVariant>> = Object.fromEntries(SECRETS.map((s) => [s.id, s]))
export const SECRET_BY_HASH: ReadonlyMap<number, SecretVariant> = new Map(SECRETS.map((s) => [s.hash, s]))
