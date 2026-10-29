import { BREED_BY_ID } from '../data/breeds.ts'
import { SECRET_BY_HASH, SECRET_BY_ID, type SecretVariant, type VariantPerk } from '../data/secrets.ts'
import { SHRINE, VARIANTS } from '../data/tuning.ts'
import { STAT_KEYS, type Family, type Stats } from '../data/types.ts'
import { cyrb53 } from './hash.ts'
import type { Monster } from './monster.ts'

/**
 * CONTENT §12 special variants: the lookup from a normalized phrase, what a variant adds at birth, and the
 * small rule hooks the rest of the core asks about (food, birthdays, battle, prizes). Pure.
 */

/** The secret variant a normalized phrase names, or null. */
export function secretForPhrase(normalizedPhrase: string): SecretVariant | null {
  return SECRET_BY_HASH.get(cyrb53(normalizedPhrase, SHRINE.secretSalt)) ?? null
}

export function secretOf(m: Pick<Monster, 'variantId'>): SecretVariant | null {
  return m.variantId ? (SECRET_BY_ID[m.variantId] ?? null) : null
}

export function perkOf(m: Pick<Monster, 'variantId'>): VariantPerk | null {
  return secretOf(m)?.perk ?? null
}

/** "Songheart Puddlepup" for a secret variant, otherwise the breed's name. */
export function variantNameOf(m: Pick<Monster, 'mainBreed' | 'variantId'>): string {
  const secret = secretOf(m)
  if (secret) return `${secret.adjective} ${BREED_BY_ID[secret.breed].name}`
  return BREED_BY_ID[m.mainBreed].name
}

/** The variant's birth stat bonus as full Stats (zeros where it gives nothing). */
export function variantStatBonus(secret: SecretVariant): Stats {
  const out: Stats = { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }
  for (const k of STAT_KEYS) out[k] = secret.stats[k] ?? 0
  return out
}

/** Birth-time perks that change the monster itself (the rest are rule hooks). Mutates and returns m. */
export function applyBirthPerkMut(m: Monster): Monster {
  const perk = perkOf(m)
  if (perk === 'lovesHoneyBread') {
    m.likes.food = 'honey-bread'
    if (m.likes.dislikedFood === 'honey-bread') m.likes.dislikedFood = 'turnips'
  }
  return m
}

/** Beacon Wishlume: +hit on Far techniques. */
export function variantFarHit(m: Pick<Monster, 'variantId'>): number {
  return perkOf(m) === 'farHit' ? VARIANTS.farHit : 0
}

/** Lantern-bearer Ashwraith: +wither on Wither techniques. */
export function variantWitherPlus(m: Pick<Monster, 'variantId'>, family: Family): number {
  return perkOf(m) === 'witherPlus' && family === 'Wither' ? VARIANTS.witherPlus : 0
}

/** Gilded Lootlid: prize money multiplier in percent (100 = none). */
export function variantPrizePct(m: Pick<Monster, 'variantId'>): number {
  return perkOf(m) === 'prizeBonus' ? 100 + VARIANTS.prizeBonusPct : 100
}

/** Party Bloatoad: stress relief on a birthday (0 for everyone else). */
export function variantBirthdayRelief(m: Pick<Monster, 'variantId'>): number {
  return perkOf(m) === 'birthdayCalm' ? VARIANTS.birthdayStressRelief : 0
}

export function likesEveryFood(m: Pick<Monster, 'variantId'>): boolean {
  return perkOf(m) === 'likesEveryFood'
}
