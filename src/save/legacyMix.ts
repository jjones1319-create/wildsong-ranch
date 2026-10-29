import { BREED_BY_ID } from '../data/breeds.ts'
import type { BreedId } from '../data/types.ts'

/**
 * Art P0 (save v15) retired the main/sub mix: every monster is one whole breed. Older records still carry a
 * `subBreed` (a Heartstone a `donorSub`), which the validator simply drops. A mixed monster that still wears the
 * name the game gave it ("Cinder Tumblefox") takes its breed's name instead; a name the player chose is kept.
 * The sub adjectives are frozen here because the live breed data no longer has them.
 */
const LEGACY_SUB_ADJECTIVES: Record<BreedId, string> = {
  puddlepup: 'Puddle',
  tumblefox: 'Tumble',
  cobblemaw: 'Cobble',
  moatshell: 'Bastion',
  wishlume: 'Lantern',
  quillion: 'Quilled',
  cinderlynx: 'Cinder',
  bloatoad: 'Bog',
  coilfang: 'Jade',
  nimbusheep: 'Nimbus',
  galeheron: 'Gale',
  nibblegrub: 'Grub',
  velvesper: 'Dusk',
  ashwraith: 'Ashen',
  zipwisp: 'Zappy',
  mirrorkin: 'Mirror',
  gearhoot: 'Brass',
  reefclaw: 'Coral',
  lootlid: 'Gilded',
  aurelwyrm: 'Golden',
  hearthwing: 'Hearth',
  grumblestone: 'Geode',
  pluckrex: 'Plucky',
  paladove: 'Haloed',
  starhowl: 'Starry',
  petalphant: 'Blossom',
  scrollopus: 'Inky',
  gloomgrin: 'Gloomy',
  rammerjack: 'Rammy',
  frostlance: 'Frosty',
}

function isBreedId(x: unknown): x is BreedId {
  return typeof x === 'string' && Object.hasOwn(LEGACY_SUB_ADJECTIVES, x)
}

/** The name the old mix system gave a main/sub pair, or null when the pair was pure or isn't two known breeds. */
export function legacyMixName(main: unknown, sub: unknown): string | null {
  if (!isBreedId(main) || !isBreedId(sub) || main === sub) return null
  return `${LEGACY_SUB_ADJECTIVES[sub]} ${BREED_BY_ID[main].name}`
}

/**
 * For a raw record with a breed, an old sub breed and a name: renames an untouched mix name to the breed's name.
 * Anything else (no sub, a custom name, not an object) comes back as it was. Never throws.
 */
export function retireMixName(raw: unknown, breedKey: string, subKey: string, nameKey: string): unknown {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return raw
  const rec = raw as Record<string, unknown>
  const mixName = legacyMixName(rec[breedKey], rec[subKey])
  if (mixName === null || rec[nameKey] !== mixName) return raw
  return { ...rec, [nameKey]: BREED_BY_ID[rec[breedKey] as BreedId].name }
}
