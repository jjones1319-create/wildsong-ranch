import { BREEDS, BREED_BY_ID } from '../data/breeds.ts'
import { startersOf, techniquesOfBreed } from '../data/techniques.ts'
import { PRESETS, SONGBOOK } from '../data/tuning.ts'
import { BREED_IDS, type BreedId } from '../data/types.ts'
import { cyrb53 } from './hash.ts'
import { scaleToTotal } from './lab.ts'
import { createMonster, lifeStage, rollLikes, type Monster } from './monster.ts'
import { createRng } from './rng.ts'
import { masteryLevel } from './songbook.ts'

/**
 * GAME_DESIGN §19 presets: every breed's pure baby, plus trained presets at E / C / A / S power made
 * with scaleToTotal. They are generated, never stored, and always the same (seeded by breed and tier).
 */

export const PRESET_TIERS = ['baby', 'E', 'C', 'A', 'S'] as const
export type PresetTier = (typeof PRESET_TIERS)[number]

export interface Preset {
  id: string
  breed: BreedId
  tier: PresetTier
  monster: Monster
}

export const PRESET_ID_PREFIX = 'preset.'

export function presetId(breed: BreedId, tier: PresetTier): string {
  return `${PRESET_ID_PREFIX}${breed}.${tier}`
}

export function isPresetId(id: string): boolean {
  return id.startsWith(PRESET_ID_PREFIX)
}

/** The first week of a life stage for this monster's growth type and lifespan. */
export function firstWeekOfStage(m: Monster, stage: number): number {
  for (let age = 0; age <= m.lifespanTotal; age++) if (lifeStage(age, m.lifespanTotal, m.growthType) >= stage) return age
  return m.lifespanTotal
}

export function makePreset(breed: BreedId, tier: PresetTier): Monster {
  const rng = createRng(cyrb53(`${PRESET_ID_PREFIX}${breed}.${tier}`))
  const m = createMonster({ id: presetId(breed, tier), mainBreed: breed, subBreed: breed, likes: rollLikes(rng), name: BREED_BY_ID[breed].name })
  if (tier === 'baby') return m
  const t = PRESETS.tiers[tier]
  m.stats = scaleToTotal(m.grades, t.total)
  m.ageWeeks = firstWeekOfStage(m, PRESETS.stage)
  m.grade = tier
  m.fame = t.fame
  m.spoil = PRESETS.spoil
  m.fear = PRESETS.fear
  m.records.wins = t.wins
  m.records.losses = t.losses
  m.records.highestGrade = tier
  // Techniques: the starters, then the kit in CONTENT order; the Signature only at S (it comes last).
  const starters = startersOf(breed).map((x) => x.id)
  const kit = techniquesOfBreed(breed).filter((x) => !starters.includes(x.id))
  const regular = kit.filter((x) => x.family !== 'Signature').map((x) => x.id)
  const signature = kit.filter((x) => x.family === 'Signature').map((x) => x.id)
  const wanted = Math.min(t.techniques, SONGBOOK.maxTechniques)
  const ids = [...starters, ...regular]
  if (tier === 'S') ids.splice(Math.min(ids.length, wanted - 1), 0, ...signature)
  m.techniques = ids.slice(0, wanted).map((id) => ({ id, uses: t.uses, level: masteryLevel(t.uses) }))
  return m
}

/** All 100 presets, breed by breed, baby first. */
export function allPresets(): Preset[] {
  const out: Preset[] = []
  for (const breed of BREED_IDS) for (const tier of PRESET_TIERS) out.push({ id: presetId(breed, tier), breed, tier, monster: makePreset(breed, tier) })
  return out
}

export function presetBreeds(): readonly BreedId[] {
  return BREEDS.map((b) => b.id)
}
