import type { BreedId, Element, TechType } from './types.ts'

/**
 * VISUAL_V1_EFFECTS §5: the element of every technique, for its effects (presentation only; no rule reads it).
 *
 * Assignment order:
 *   1. keyword rules on the name (the categories below, first category wins; a few named exceptions);
 *      every universal technique is Sound unless a keyword said otherwise;
 *   3. a plain melee name is Physical regardless of breed;
 *   2. otherwise the breed's default (INT / POW split for three breeds).
 * (Rule 3 sits before rule 2 because the spec says "regardless of breed".)
 * The owner's corrections go in ELEMENT_OVERRIDES, never into the rows. CONTENT §3 carries the result.
 */

export interface ElementInput {
  name: string
  breed: BreedId | 'universal'
  type: TechType
}

export interface ElementVerdict {
  element: Element
  /** Which rule fired, for the printed table ("kw Fire: ember", "universal → Sound", "melee: jab", "breed default", "override"). */
  rule: string
  /** Other categories whose keyword also matched: worth a second look. */
  alsoMatched: Element[]
}

/** Keyword categories in spec order. A keyword matches a word of the name exactly or as its prefix; a phrase matches the whole name. */
const KEYWORDS: readonly [Element, readonly string[]][] = [
  ['Fire', ['fire', 'flame', 'ember', 'cinder', 'blaze', 'furnace', 'pyre', 'inferno', 'kindled', 'smoulder', 'sun', 'solar', 'hearth', 'torrent', 'bonfire', 'wildfire', 'flare', 'blazing', 'foxfire', 'ghostflame']],
  ['Water', ['water', 'splash', 'wave', 'tide', 'geyser', 'rain', 'drizzle', 'puddle', 'bubble', 'soggy', 'bog', 'swamp', 'pool', 'drench', 'riptide', 'kingtide', 'barnacle', 'moat', 'downpour', 'sea', 'tsunami', 'fog']],
  ['Ice', ['ice', 'icicle', 'frost', 'snow', 'glacier', 'blizzard', 'polar', 'chill', 'hail', 'crystal lance']],
  ['Lightning', ['bolt', 'spark', 'static', 'zap', 'crackle', 'arc', 'volt', 'lightning', 'overcharge', 'feedback']],
  ['Wind', ['wind', 'gale', 'gust', 'squall', 'tempest', 'storm', 'breeze', 'whirl', 'cyclone', 'tornado', 'downdraft', 'slipstream', 'stride', 'northwind']],
  ['Earth', ['stone', 'rock', 'boulder', 'gravel', 'quake', 'landslide', 'crag', 'geode', 'crystal', 'pebble', 'bedrock', 'mountain', 'avalanche', 'cobble', 'knuckle', 'mountainfall', 'rockfall']],
  ['Nature', ['petal', 'bloom', 'blossom', 'seed', 'thorn', 'leaf', 'bramble', 'moss', 'silk', 'vine', 'cocoon', 'sneeze', 'lily']],
  ['Light', ['light', 'glow', 'beam', 'prism', 'glimmer', 'star', 'halo', 'dawn', 'moon', 'lantern', 'gleam', 'flash', 'ray', 'reflection', 'mirror', 'glint', 'shard', 'lens', 'wish', 'festival', 'sunrise', 'constellation', 'supernova', 'comet', 'twinkle']],
  ['Dark', ['shadow', 'dusk', 'gloom', 'ash', 'wraith', 'phantom', 'soul', 'ink', 'venom', 'poison', 'hush', 'wail', 'spooky', 'mournful', 'siphon', 'eclipse', 'night', 'twilight', 'drowsy', 'hypno', 'lullaby', 'sleepy', 'trickster', 'mocking', 'fools gold', 'snicker', 'midnight']],
  ['Sound', ['roar', 'howl', 'yip', 'croak', 'bleat', 'chime', 'hum', 'whistle', 'drum', 'cymbal', 'note', 'song', 'crier']],
]

/** Keywords that only count for some breeds (spec: "bolt (Zipwisp/Nimbusheep only)", "spark (Zipwisp)", "shard (Mirrorkin)", "crystal (Grumblestone)"). */
const BREED_ONLY: Record<string, readonly BreedId[]> = {
  bolt: ['zipwisp', 'nimbusheep'],
  spark: ['zipwisp'],
  shard: ['mirrorkin'],
  crystal: ['grumblestone'],
}

/** Named exceptions from the spec: the whole name decides. */
const EXCEPTIONS: Record<string, Element> = {
  'crest flare': 'Light',
  'sunrise roar': 'Light',
  'lightning stride': 'Wind',
  'harmony mend': 'Light',
  'resonance drain': 'Dark',
}

/** Rule 3: a plain melee name is Physical. The spec's list plus a few equally plain blows (slap, swat, bop, nip, chomp, nibble, pinch, snap, peck, check, rake, bash, hook, thump). */
const MELEE = ['bite', 'jab', 'swipe', 'slam', 'punch', 'kick', 'bump', 'poke', 'thrust', 'claw', 'tackle', 'headbutt', 'bonk', 'stomp', 'shove', 'slap', 'swat', 'bop', 'nip', 'chomp', 'nibble', 'pinch', 'snap', 'peck', 'check', 'rake', 'bash', 'hook', 'thump']

/** Rule 2: the breed default (INT / POW split where the spec says so). */
const BREED_DEFAULT: Record<BreedId, Element | { INT: Element; POW: Element }> = {
  puddlepup: 'Water',
  tumblefox: 'Fire',
  cobblemaw: 'Earth',
  moatshell: 'Earth',
  wishlume: 'Light',
  quillion: 'Physical',
  cinderlynx: 'Fire',
  bloatoad: 'Water',
  coilfang: 'Dark',
  nimbusheep: 'Water',
  galeheron: 'Wind',
  nibblegrub: 'Nature',
  velvesper: 'Dark',
  ashwraith: 'Fire',
  zipwisp: 'Lightning',
  mirrorkin: 'Light',
  gearhoot: { INT: 'Light', POW: 'Physical' },
  reefclaw: 'Water',
  lootlid: { INT: 'Light', POW: 'Physical' },
  aurelwyrm: { INT: 'Fire', POW: 'Physical' },
  hearthwing: 'Fire',
  grumblestone: 'Earth',
  pluckrex: 'Physical',
  paladove: 'Light',
  starhowl: 'Light',
  petalphant: 'Nature',
  scrollopus: 'Dark',
  gloomgrin: 'Dark',
  rammerjack: 'Physical',
  frostlance: 'Ice',
}

/**
 * The owner's corrections, by technique id (`breed.slug` or `universal.slug`). Checked before every rule.
 * Add a row here when a technique should not follow the rules; never edit the rows or the rule lists for one case.
 */
export const ELEMENT_OVERRIDES: Readonly<Record<string, Element>> = {}

function words(name: string): string[] {
  return name
    .toLowerCase()
    .replace(/['’]/g, '')
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
}

function keywordHit(ws: readonly string[], keyword: string, breed: BreedId | 'universal'): boolean {
  const only = BREED_ONLY[keyword]
  if (only && !only.includes(breed as BreedId)) return false
  if (keyword.includes(' ')) return ` ${ws.join(' ')} `.includes(` ${keyword} `)
  return ws.some((w) => w === keyword || w.startsWith(keyword))
}

/** Every keyword category the name matches, in spec order, with the keyword that matched. */
export function keywordMatches(input: ElementInput): { element: Element; keyword: string }[] {
  const ws = words(input.name)
  const out: { element: Element; keyword: string }[] = []
  for (const [element, list] of KEYWORDS) {
    const keyword = list.find((k) => keywordHit(ws, k, input.breed))
    if (keyword) out.push({ element, keyword })
  }
  return out
}

export function isMeleeName(name: string): string | null {
  return words(name).find((w) => MELEE.includes(w)) ?? null
}

export function breedDefaultElement(breed: BreedId, type: TechType): Element {
  const d = BREED_DEFAULT[breed]
  return typeof d === 'string' ? d : d[type]
}

/** The element of a technique and why (see the module comment for the order). */
export function assignElement(input: ElementInput, id?: string): ElementVerdict {
  const override = id ? ELEMENT_OVERRIDES[id] : undefined
  const matches = keywordMatches(input)
  const also = matches.map((m) => m.element)
  if (override) return { element: override, rule: 'override', alsoMatched: also.filter((e) => e !== override) }
  const exception = EXCEPTIONS[words(input.name).join(' ')]
  if (exception) return { element: exception, rule: 'named exception', alsoMatched: also.filter((e) => e !== exception) }
  if (matches.length > 0) {
    const first = matches[0]!
    return { element: first.element, rule: `kw ${first.element}: ${first.keyword}`, alsoMatched: also.slice(1) }
  }
  if (input.breed === 'universal') return { element: 'Sound', rule: 'universal → Sound', alsoMatched: [] }
  const melee = isMeleeName(input.name)
  if (melee) return { element: 'Physical', rule: `melee: ${melee}`, alsoMatched: [] }
  return { element: breedDefaultElement(input.breed, input.type), rule: 'breed default', alsoMatched: [] }
}

export function elementOf(input: ElementInput, id?: string): Element {
  return assignElement(input, id).element
}
