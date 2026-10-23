import { JOURNEY_SITES } from '../data/journeys.ts'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { CALENDAR, FREEZER, HEARTSTONE, RANGES } from '../data/tuning.ts'
import { FAMILIES, STAT_KEYS, type Family, type JourneySiteId, type StatKey, type Stats } from '../data/types.ts'
import { finishEdit } from './lab.ts'
import { clamp, divRound } from './mathx.ts'
import { mixBreeds, zeroStats, type Monster } from './monster.ts'
import type { GameState, Heartstone, MemorialCause } from './state.ts'

/**
 * GAME_DESIGN §16 (the Freezer, the Memorial, Heartstones) and §7 (the farewell, the Elder Grove).
 * Pure functions over the game state; the UI generates nothing but ids for new monsters.
 */

export type StoredWhere = 'freezer' | 'elders'

export interface Stored {
  where: StoredWhere
  index: number
  monster: Monster
}

export function freezerRoom(state: GameState): number {
  return Math.max(0, FREEZER.slots - state.freezer.length)
}

export function freezerFull(state: GameState): boolean {
  return state.freezer.length >= FREEZER.slots
}

/** A cup, a Journey or a waiting Trial keeps the active monster where it is. */
export function ranchBusy(state: GameState): boolean {
  return state.tournament !== null || state.journey !== null || state.trial !== null
}

/** Finds a monster in the Freezer or the Elder Grove. */
export function findStored(state: GameState, id: string): Stored | null {
  const f = state.freezer.findIndex((m) => m.id === id)
  if (f >= 0) return { where: 'freezer', index: f, monster: state.freezer[f]! }
  const e = state.elderGrove.findIndex((m) => m.id === id)
  if (e >= 0) return { where: 'elders', index: e, monster: state.elderGrove[e]! }
  return null
}

/** Everything that can fuse: the Freezer and the Elder Grove. */
export function fusionCandidates(state: GameState): Stored[] {
  return [...state.freezer.map((monster, index) => ({ where: 'freezer' as const, index, monster })), ...state.elderGrove.map((monster, index) => ({ where: 'elders' as const, index, monster }))]
}

/** The ranch after its monster left: the week waits for the next arrival. */
function clearRanch(state: GameState): void {
  state.monster = null
  state.ended = null
  state.weekPhase = 'start'
  state.pendingRequest = null
  state.lastAction = null
  state.monsterHistory = []
  state.journey = null
  state.trial = null
  state.tournament = null
}

/** Puts a monster on the ranch (the ranch must be empty). Records it in the Encyclopedia. */
export function placeOnRanch(state: GameState, m: Monster): void {
  clearRanch(state)
  state.monster = m
  recordInEncyclopedia(state, m)
}

export function recordInEncyclopedia(state: GameState, m: Monster): void {
  if (!state.encyclopedia.breeds.includes(m.mainBreed)) state.encyclopedia.breeds.push(m.mainBreed)
  if (m.variantId && !state.encyclopedia.variants.includes(m.variantId)) state.encyclopedia.variants.push(m.variantId)
}

export type FreezeRefusal = 'noMonster' | 'busy' | 'full' | 'ended'

/** Freezes the active monster: free and instant; the ranch is then empty. */
export function freezeActive(input: GameState): { state: GameState; refused: FreezeRefusal | null } {
  if (!input.monster) return { state: input, refused: 'noMonster' }
  if (input.ended) return { state: input, refused: 'ended' }
  if (ranchBusy(input)) return { state: input, refused: 'busy' }
  if (freezerFull(input)) return { state: input, refused: 'full' }
  const state = structuredClone(input)
  const m = state.monster!
  state.freezer.push(m)
  clearRanch(state)
  return { state, refused: null }
}

export type SendRefusal = 'full' | 'duplicate'

/** Sends a monster (a Lab creation, a newborn) into the Freezer. Its id must be new to this ranch. */
export function sendToFreezer(input: GameState, m: Monster): { state: GameState; refused: SendRefusal | null } {
  if (freezerFull(input)) return { state: input, refused: 'full' }
  if (findStored(input, m.id) || input.monster?.id === m.id) return { state: input, refused: 'duplicate' }
  const state = structuredClone(input)
  state.freezer.push(structuredClone(m))
  recordInEncyclopedia(state, m)
  return { state, refused: null }
}

export type ThawRefusal = 'notFound' | 'busy' | 'ended' | 'full'

/** Make Active: the stored monster comes to the ranch; the current one (if any) takes its place in the Freezer. */
export function makeActive(input: GameState, id: string): { state: GameState; refused: ThawRefusal | null } {
  const found = findStored(input, id)
  if (!found) return { state: input, refused: 'notFound' }
  if (input.ended) return { state: input, refused: 'ended' }
  if (ranchBusy(input)) return { state: input, refused: 'busy' }
  // Swapping with a frozen one frees a slot first; an Elder leaving the Grove does not.
  if (input.monster && found.where === 'elders' && freezerFull(input)) return { state: input, refused: 'full' }
  const state = structuredClone(input)
  const list = found.where === 'freezer' ? state.freezer : state.elderGrove
  const [thawed] = list.splice(found.index, 1)
  const current = state.monster
  if (current) state.freezer.push(current)
  placeOnRanch(state, thawed!)
  return { state, refused: null }
}

/** Removes a stored monster (after the UI copied it to the Library, or on an explicit release). */
export function releaseStored(input: GameState, id: string): GameState {
  const found = findStored(input, id)
  if (!found) return input
  const state = structuredClone(input)
  ;(found.where === 'freezer' ? state.freezer : state.elderGrove).splice(found.index, 1)
  return state
}

/** The Lab editor saved a frozen monster (§19: Freezer → Edit). The id stays. */
export function replaceStored(input: GameState, edited: Monster): GameState {
  const found = findStored(input, edited.id)
  if (!found) return input
  const state = structuredClone(input)
  const finished = finishEdit(found.monster, edited)
  finished.id = found.monster.id
  ;(found.where === 'freezer' ? state.freezer : state.elderGrove)[found.index] = finished
  return state
}

/* ---------- Heartstones (§16) ---------- */

export function heartstoneCap(state: Pick<GameState, 'upgrades'>): number {
  return state.upgrades.lanternGarden ? HEARTSTONE.maxWithLanternGarden : HEARTSTONE.max
}

/** The family this monster used most (ties: more total uses first, then CONTENT family order). */
export function mostUsedFamily(m: Monster): Family {
  const uses = new Map<Family, number>()
  for (const slot of m.techniques) {
    const tech = TECHNIQUE_BY_ID[slot.id]
    if (!tech) continue
    uses.set(tech.family, (uses.get(tech.family) ?? 0) + slot.uses)
  }
  let best: Family = 'Basic'
  let bestUses = -1
  for (const fam of FAMILIES) {
    const n = uses.get(fam)
    if (n !== undefined && n > bestUses) {
      best = fam
      bestUses = n
    }
  }
  return best
}

/** Trained gains: stat − the breed base at birth, never below 0. */
export function trainedGains(m: Monster): Stats {
  const base = mixBreeds(m.mainBreed, m.subBreed).base
  const out = zeroStats()
  for (const k of STAT_KEYS) out[k] = Math.max(0, m.stats[k] - base[k])
  return out
}

export function heartstoneFrom(m: Monster, week: number): Heartstone {
  return {
    id: `hs-${m.id}`,
    donorId: m.id,
    donorName: m.name,
    donorBreed: m.mainBreed,
    donorSub: m.subBreed,
    donorVariant: m.variantId,
    gains: trainedGains(m),
    family: mostUsedFamily(m),
    week,
  }
}

/** What a Heartstone grants per stat: HEARTSTONE.gainPct of the gains, capped per stat. */
export function heartstoneGrant(stone: Pick<Heartstone, 'gains'>): Stats {
  const out = zeroStats()
  for (const k of STAT_KEYS) out[k] = Math.min(HEARTSTONE.capPerStat, divRound(stone.gains[k] * HEARTSTONE.gainPct, 100))
  return out
}

export type ReceiveRefusal = 'age' | 'has'

export function canReceiveHeartstone(m: Monster): { ok: true } | { ok: false; reason: ReceiveRefusal } {
  if (m.status.heartstoneReceived) return { ok: false, reason: 'has' }
  if (m.ageWeeks >= HEARTSTONE.maxAgeWeeks) return { ok: false, reason: 'age' }
  return { ok: true }
}

export type GiveRefusal = 'noStone' | 'noTarget' | ReceiveRefusal

/** Gives a stored Heartstone to the active monster (or a stored one by id). */
export function giveHeartstone(input: GameState, stoneId: string, targetId?: string): { state: GameState; refused: GiveRefusal | null; grant: Stats | null } {
  const stone = input.heartstones.find((h) => h.id === stoneId)
  if (!stone) return { state: input, refused: 'noStone', grant: null }
  const target = targetId ? (findStored(input, targetId)?.monster ?? (input.monster?.id === targetId ? input.monster : null)) : input.monster
  if (!target) return { state: input, refused: 'noTarget', grant: null }
  const can = canReceiveHeartstone(target)
  if (!can.ok) return { state: input, refused: can.reason, grant: null }
  const state = structuredClone(input)
  const found = targetId ? (findStored(state, targetId)?.monster ?? state.monster!) : state.monster!
  const grant = heartstoneGrant(stone)
  for (const k of STAT_KEYS) found.stats[k] = clamp(found.stats[k] + grant[k], RANGES.stat.min, RANGES.stat.max)
  found.status.heartstoneReceived = true
  found.heirloom = stone.family
  state.heartstones = state.heartstones.filter((h) => h.id !== stoneId)
  return { state, refused: null, grant }
}

/* ---------- the farewell (§7) ---------- */

export interface ConcludeResult {
  state: GameState
  cause: MemorialCause
  heartstone: Heartstone | null
  /** True when the Heartstone shelf was full and the stone could not be kept. */
  heartstoneLost: boolean
}

/**
 * Ends the life the end-of-week tick announced (`state.ended`): the monster moves to the Memorial with its
 * epitaph (and, when it retired, to the Elder Grove too), leaves a Heartstone if there is room, and the ranch
 * empties. Nothing is deleted.
 */
export function concludeLife(input: GameState, epitaph: string): ConcludeResult | null {
  if (!input.monster || !input.ended) return null
  const state = structuredClone(input)
  const m = state.monster!
  const cause: MemorialCause = state.ended === 'retired' ? 'retired' : 'passed'
  state.memorial.unshift({ monster: structuredClone(m), cause, epitaph: epitaph.trim().slice(0, 80), week: state.week })
  if (cause === 'retired') state.elderGrove.push(structuredClone(m))
  let heartstone: Heartstone | null = null
  let heartstoneLost = false
  if (state.heartstones.length < heartstoneCap(state)) {
    heartstone = heartstoneFrom(m, state.week)
    state.heartstones.unshift(heartstone)
  } else heartstoneLost = true
  clearRanch(state)
  return { state, cause, heartstone, heartstoneLost }
}

/** Edits a Memorial entry's name and epitaph in place (§16). */
export function editMemorial(input: GameState, monsterId: string, name: string, epitaph: string): GameState {
  const i = input.memorial.findIndex((e) => e.monster.id === monsterId)
  if (i < 0) return input
  const state = structuredClone(input)
  const entry = state.memorial[i]!
  const trimmed = name.trim().slice(0, RANGES.nameLength.max)
  if (trimmed) entry.monster.name = trimmed
  entry.epitaph = epitaph.trim().slice(0, 80)
  return state
}

/* ---------- the Elder Grove (§7, Gentle) ---------- */

/** An Elder's best stat, LIF aside (LIF has no mentor site); ties go to the earlier stat. */
export function elderBestStat(m: Monster): StatKey {
  let best: StatKey = 'POW'
  for (const k of STAT_KEYS) {
    if (k === 'LIF') continue
    if (m.stats[k] > m.stats[best]) best = k
  }
  return best
}

export function elderSite(m: Monster): JourneySiteId {
  const stat = elderBestStat(m)
  return (JOURNEY_SITES.find((s) => s.stat === stat) ?? JOURNEY_SITES[0]!).id
}

export function monthIndexOf(week: number): number {
  return Math.floor(week / CALENDAR.weeksPerMonth)
}

export function elderMentorUsedThisMonth(state: Pick<GameState, 'week' | 'elderMentorMonth'>): boolean {
  return state.elderMentorMonth !== null && state.elderMentorMonth === monthIndexOf(state.week)
}

/** The Elder who would mentor a Journey at this site this month, or null. */
export function elderMentorFor(state: GameState, site: JourneySiteId): Monster | null {
  if (elderMentorUsedThisMonth(state)) return null
  return state.elderGrove.find((e) => elderSite(e) === site) ?? null
}

export type AdoptRefusal = 'busy' | 'full' | 'duplicate' | 'ended'

/** §19 Make Active from the Lab: the current monster (if any) goes to the Freezer and this one takes the ranch. */
export function adopt(input: GameState, m: Monster): { state: GameState; refused: AdoptRefusal | null } {
  if (input.ended) return { state: input, refused: 'ended' }
  if (ranchBusy(input)) return { state: input, refused: 'busy' }
  if (findStored(input, m.id) || input.monster?.id === m.id) return { state: input, refused: 'duplicate' }
  if (input.monster && freezerFull(input)) return { state: input, refused: 'full' }
  const state = structuredClone(input)
  if (state.monster) state.freezer.push(state.monster)
  placeOnRanch(state, structuredClone(m))
  return { state, refused: null }
}
