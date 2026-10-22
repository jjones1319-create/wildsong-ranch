import { BREED_BY_ID } from '../data/breeds.ts'
import { TECHNIQUES, TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { LAB, RANGES } from '../data/tuning.ts'
import { STAT_KEYS, type BreedId, type Grades, type Stats, type Technique } from '../data/types.ts'
import { clamp } from './mathx.ts'
import { createMonster, gradeFactor100, mixBreeds, zeroStats, type Likes, type Monster } from './monster.ts'
import type { Rng } from './rng.ts'
import { canLearn } from './songbook.ts'

/**
 * GAME_DESIGN §19: the rules behind the Monster Lab editor. Pure functions; the UI holds the draft.
 * The editor is "creative mode": nothing here charges money or checks ownership, and the only
 * limits are the field ranges in tuning (RANGES) and the 12-technique cap.
 */

export const DEFAULT_LIKES: Likes = { food: 'honey-bread', dislikedFood: 'turnips', toy: 'rubber-ball', battle: 0, drill: 'target-toss', dislikedDrill: 'acorn-shower' }

/**
 * "Scale to total…": spreads `total` stat points across the six stats in proportion to the growth
 * grades (an A stat gets more than an E stat), with integer math, an exact total and every stat
 * inside 1–999. Any leftover point goes to the stats in LIF, POW, INT, SKI, SPD, DEF order.
 */
export function scaleToTotal(grades: Grades, total: number): Stats {
  const lo = RANGES.stat.min * STAT_KEYS.length
  const hi = RANGES.stat.max * STAT_KEYS.length
  const target = clamp(Math.round(total), lo, hi)
  const weights = STAT_KEYS.map((k) => gradeFactor100(grades[k]))
  const weightSum = weights.reduce((a, b) => a + b, 0)
  const out = zeroStats()
  let assigned = 0
  STAT_KEYS.forEach((k, i) => {
    out[k] = Math.floor((target * weights[i]!) / weightSum)
    assigned += out[k]
  })
  for (let i = 0, rem = target - assigned; rem > 0; i = (i + 1) % STAT_KEYS.length, rem--) out[STAT_KEYS[i]!] += 1
  // Clamping to 1–999 can disturb the total; hand the difference to the stats that still have room.
  for (let pass = 0; pass < 8; pass++) {
    let sum = 0
    for (const k of STAT_KEYS) {
      out[k] = clamp(out[k], RANGES.stat.min, RANGES.stat.max)
      sum += out[k]
    }
    const diff = target - sum
    if (diff === 0) break
    const step = diff > 0 ? 1 : -1
    const movable = STAT_KEYS.filter((k) => (step > 0 ? out[k] < RANGES.stat.max : out[k] > RANGES.stat.min))
    if (movable.length === 0) break
    const each = Math.floor(Math.abs(diff) / movable.length)
    let rest = Math.abs(diff) - each * movable.length
    for (const k of movable) {
      out[k] += step * (each + (rest > 0 ? 1 : 0))
      if (rest > 0) rest--
    }
  }
  return out
}

/** "Breed base": what the Shrine would give this main/sub pair with zero offsets. */
export function breedBaseStats(m: Monster): Stats {
  return { ...mixBreeds(m.mainBreed, m.subBreed).base }
}

/** "Max all". */
export function maxAllStats(): Stats {
  return { LIF: RANGES.stat.max, POW: RANGES.stat.max, INT: RANGES.stat.max, SKI: RANGES.stat.max, SPD: RANGES.stat.max, DEF: RANGES.stat.max }
}

/** "Randomize": every stat lands within ± LAB.randomizeSpreadPct of where it is now (seeded, so it is reproducible). */
export function randomizeStats(current: Stats, rng: Rng): Stats {
  const out = zeroStats()
  for (const k of STAT_KEYS) {
    const spread = Math.floor((current[k] * LAB.randomizeSpreadPct) / 100)
    const lo = clamp(current[k] - spread, RANGES.stat.min, RANGES.stat.max)
    const hi = clamp(current[k] + spread, RANGES.stat.min, RANGES.stat.max)
    out[k] = rng.nextInt(lo, hi)
  }
  return out
}

/** "Reset to breed default" for the Growth section: grades, growth type, guts rate and lifespan from the breeds. */
export function resetGrowthToBreed(input: Monster): Monster {
  const m = structuredClone(input)
  const mix = mixBreeds(m.mainBreed, m.subBreed)
  m.grades = mix.grades
  m.growthType = BREED_BY_ID[m.mainBreed].growth
  m.gutsRate = mix.gutsRate
  m.lifespanTotal = mix.lifespan
  return m
}

/** The blank template: a plain monster with flat C grades and round numbers, ready to be shaped. */
export function blankMonster(id: string, name: string, breed: BreedId = 'puddlepup'): Monster {
  const m = createMonster({ id, mainBreed: breed, subBreed: breed, likes: DEFAULT_LIKES, name })
  for (const k of STAT_KEYS) {
    m.stats[k] = LAB.blank.stat
    m.grades[k] = LAB.blank.grade
  }
  m.growthType = LAB.blank.growth
  m.gutsRate = LAB.blank.gutsRate
  m.lifespanTotal = LAB.blank.lifespan
  m.spoil = LAB.blank.spoil
  m.fear = LAB.blank.fear
  return m
}

/** A copy with a new id. The copy has no lineage of its own; the name is for the caller to adjust. */
export function duplicateMonster(input: Monster, newId: string): Monster {
  const m = structuredClone(input)
  m.id = newId
  m.parents = []
  return m
}

/**
 * Techniques the editor may add. Normally the main kit, the sub's quirk and every universal technique
 * (the Songbook rules); with "Allow any technique" everything, even another breed's Signature.
 * Techniques already learned are left out either way.
 */
export function addableTechniques(m: Monster, allowAny: boolean): Technique[] {
  const known = new Set(m.techniques.map((t) => t.id))
  return TECHNIQUES.filter((t) => !known.has(t.id) && (allowAny || canLearn(m, t.id).ok))
}

/** Learned techniques that the monster's current breeds would not normally allow. */
export function techniquesOutsideKit(m: Monster): string[] {
  const probe = structuredClone(m)
  probe.techniques = []
  return m.techniques.map((t) => t.id).filter((id) => TECHNIQUE_BY_ID[id] === undefined || !canLearn(probe, id).ok)
}

export interface BreedChangeResult {
  monster: Monster
  /** Technique ids that were removed because they are outside the new breeds' kits. */
  removed: string[]
}

/**
 * Changing the main or sub breed: body, trait, kit and growth type follow the new main; palette and
 * accent follow the new sub; techniques outside the new kits are removed unless `keepAll` is ticked.
 * Stats, grades and everything else the player typed stay as they are.
 */
export function applyBreedChange(input: Monster, mainBreed: BreedId, subBreed: BreedId, keepAll: boolean): BreedChangeResult {
  const m = structuredClone(input)
  const changed = m.mainBreed !== mainBreed || m.subBreed !== subBreed
  m.mainBreed = mainBreed
  m.subBreed = subBreed
  const pure = mainBreed === subBreed
  m.flags.pure = pure
  m.appearance = { paletteBreed: subBreed, accentPart: pure ? null : BREED_BY_ID[subBreed].art.accentPart }
  if (changed) m.growthType = BREED_BY_ID[mainBreed].growth
  const outside = keepAll ? [] : techniquesOutsideKit(m)
  m.techniques = m.techniques.filter((t) => !outside.includes(t.id))
  return { monster: m, removed: outside }
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value !== null && typeof value === 'object') {
    const obj = value as Record<string, unknown>
    return `{${Object.keys(obj)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`)
      .join(',')}}`
  }
  return JSON.stringify(value) ?? 'null'
}

/** §19: saving any change other than the name sets the edited flag. The flag itself is ignored in the comparison. */
export function isEditedChange(before: Monster, after: Monster): boolean {
  const strip = (m: Monster) => {
    const c = structuredClone(m)
    c.name = ''
    c.flags.edited = false
    return stableStringify(c)
  }
  return strip(before) !== strip(after)
}

/** The monster as it will be stored after a save: the edited flag set if anything but the name changed. Never clears it. */
export function finishEdit(before: Monster, after: Monster): Monster {
  const m = structuredClone(after)
  if (before.flags.edited || isEditedChange(before, after)) m.flags.edited = true
  return m
}

export interface EditHistoryEntry {
  monster: Monster
  savedAt: number
}

/** Every save keeps the previous version, oldest first, at most LAB.historyLimit (§19 Undo). */
export function pushHistory(history: readonly EditHistoryEntry[], previous: Monster, savedAt: number): EditHistoryEntry[] {
  return [...history, { monster: structuredClone(previous), savedAt }].slice(-LAB.historyLimit)
}

/**
 * "Restore": the chosen old version becomes current, and what was current joins the history, so a
 * restore can itself be undone. Returns null for an index that doesn't exist.
 */
export function restoreFromHistory(
  current: Monster,
  history: readonly EditHistoryEntry[],
  index: number,
  savedAt: number,
): { monster: Monster; history: EditHistoryEntry[] } | null {
  const entry = history[index]
  if (!entry) return null
  const monster = structuredClone(entry.monster)
  monster.id = current.id
  return { monster, history: pushHistory(history, current, savedAt) }
}
