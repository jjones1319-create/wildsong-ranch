import { TECHNIQUE_BY_ID, TECHNIQUES } from '../data/techniques.ts'
import { SONGBOOK } from '../data/tuning.ts'
import { STAT_KEYS, type Technique } from '../data/types.ts'
import { isPure, type Monster, type TechniqueSlot } from './monster.ts'

/**
 * GAME_DESIGN §10.4–§10.5: learning, forgetting, mastery and Songsheets.
 * A Songbook is the set of sheet technique ids the player owns, forever.
 */

export type Songbook = readonly string[]

export function ownsSheet(songbook: Songbook, techId: string): boolean {
  return songbook.includes(techId)
}

export function addSheet(songbook: Songbook, techId: string): string[] {
  if (ownsSheet(songbook, techId)) return [...songbook]
  return [...songbook, techId].sort()
}

export type LearnBlock = 'unknownTechnique' | 'known' | 'notInKit' | 'signatureNotPure'

/** Who can learn what (§10.5): universal → anyone; breed kit; sub quirk; Signature → pure breed only. */
export function canLearn(m: Monster, techId: string): { ok: true } | { ok: false; reason: LearnBlock } {
  const tech = TECHNIQUE_BY_ID[techId]
  if (!tech) return { ok: false, reason: 'unknownTechnique' }
  if (m.techniques.some((t) => t.id === techId)) return { ok: false, reason: 'known' }
  if (tech.breed === 'universal') return { ok: true }
  if (tech.family === 'Signature') {
    if (tech.breed !== m.mainBreed) return { ok: false, reason: 'notInKit' }
    return isPure(m) ? { ok: true } : { ok: false, reason: 'signatureNotPure' }
  }
  if (tech.breed === m.mainBreed) return { ok: true }
  if (tech.breed === m.subBreed && tech.subQuirk) return { ok: true }
  return { ok: false, reason: 'notInKit' }
}

export function isFull(m: Monster): boolean {
  return m.techniques.length >= SONGBOOK.maxTechniques
}

export type LearnStatus = 'learned' | 'full' | LearnBlock

/** Learn a technique instantly (Songsheet or scene). At the 12 cap the caller must ask which one to forget. */
export function learnTechnique(input: Monster, techId: string): { monster: Monster; status: LearnStatus } {
  const check = canLearn(input, techId)
  if (!check.ok) return { monster: input, status: check.reason }
  if (isFull(input)) return { monster: input, status: 'full' }
  const m = structuredClone(input)
  m.techniques.push({ id: techId, uses: 0, level: 1 })
  return { monster: m, status: 'learned' }
}

/** Forgetting is free. Mastery restarts if the technique is learned again. */
export function forgetTechnique(input: Monster, techId: string): Monster {
  const m = structuredClone(input)
  m.techniques = m.techniques.filter((t) => t.id !== techId)
  return m
}

export function learnReplacing(input: Monster, techId: string, forgetId: string): { monster: Monster; status: LearnStatus } {
  return learnTechnique(forgetTechnique(input, forgetId), techId)
}

/** ★ good fit: the technique's stat (POW or INT) is one of the monster's top two stats. */
export function goodFit(m: Monster, tech: Technique): boolean {
  const sorted = [...STAT_KEYS].sort((a, b) => m.stats[b] - m.stats[a])
  const topTwo = sorted.slice(0, 2)
  return topTwo.includes(tech.type)
}

/** Owned sheets this monster could learn right now (not yet known, allowed by the kit rules). */
export function learnableFromSongbook(m: Monster, songbook: Songbook): Technique[] {
  return songbook.map((id) => TECHNIQUE_BY_ID[id]).filter((t): t is Technique => t !== undefined && canLearn(m, t.id).ok)
}

/** Every technique a monster could ever learn from a sheet (for the Guild Library and the editor). */
export function sheetCatalogFor(m: Monster): Technique[] {
  return TECHNIQUES.filter((t) => t.sheet !== null && canLearn(m, t.id).ok)
}

export function masteryLevel(uses: number): 1 | 2 | 3 {
  if (uses >= SONGBOOK.lv3Uses) return 3
  if (uses >= SONGBOOK.lv2Uses) return 2
  return 1
}

/** +1 use after a technique is used in battle; levels up at 15 and 40 uses. */
export function recordUse(input: Monster, techId: string): Monster {
  const m = structuredClone(input)
  const slot = m.techniques.find((t) => t.id === techId)
  if (slot) {
    slot.uses += 1
    slot.level = masteryLevel(slot.uses)
  }
  return m
}

export function masteryBonuses(slot: TechniqueSlot): { hit: number; force: number } {
  return { hit: slot.level >= 2 ? SONGBOOK.lv2HitBonus : 0, force: slot.level >= 3 ? SONGBOOK.lv3ForceBonus : 0 }
}
