import { BREED_BY_ID } from '../data/breeds.ts'
import { TECHNIQUE_BY_ID, techniquesOfBreed } from '../data/techniques.ts'
import { RANGES, SONGBOOK, UNLOCKS } from '../data/tuning.ts'
import { STAT_KEYS, TOURNAMENT_GRADES, type BreedId, type TournamentGrade, type UnlockChain } from '../data/types.ts'
import { availability } from './aging.ts'
import { dateOf } from './calendar.ts'
import { placeNewMonster, type Placed } from './creation.ts'
import { addItems, countOf } from './items.ts'
import { trainedGains } from './legacy.ts'
import { clamp, divRound } from './mathx.ts'
import { addCondition, createMonster, loyaltyOf, mixBreeds, rollLikes, type Monster, type TechniqueSlot } from './monster.ts'
import { createRng } from './rng.ts'
import type { GameState } from './state.ts'

/**
 * CONTENT §11: the eight unlock chains, as pure state changes. The weekly triggers live in core/events.ts;
 * the offerings (a key item laid on the Shrine's stone), the Blueprint for Dr. Pell, the Vigil, the cocoon and
 * its metamorphosis, the storm chase and the Reefclaw's arrival live here. Nothing is ever permanently missed:
 * every chain can be tried again, and the Journal's stage per chain comes from `chainStage`.
 */

/** Key item → the breed its offering wakes. */
export const OFFERINGS: Readonly<Record<string, BreedId>> = { 'vigil-lantern': 'ashwraith', stormglass: 'zipwisp', 'shard-mask': 'mirrorkin', 'wyrm-scale': 'aurelwyrm' }

export const CHAIN_BREED: Readonly<Record<UnlockChain, BreedId>> = {
  cocoon: 'velvesper',
  vigil: 'ashwraith',
  'storm-chase': 'zipwisp',
  masquerade: 'mirrorkin',
  blueprint: 'gearhoot',
  'tide-pool': 'reefclaw',
  'strange-chest': 'lootlid',
  'four-crowns': 'aurelwyrm',
}

export function isUnlocked(state: Pick<GameState, 'unlocked'>, breed: BreedId): boolean {
  return state.unlocked.includes(breed)
}

/** Adds the breed to the Shrine's list. Sleeping Stones for it wake on their own (creation.ts checks `unlocked`). */
export function unlockBreed(input: GameState, breed: BreedId): GameState {
  if (isUnlocked(input, breed)) return input
  const state = structuredClone(input)
  state.unlocked.push(breed)
  return state
}

export type OfferRefusal = 'notOffering' | 'notOwned' | 'awake'

/** Lays a key item on the stone: the item is spent and its breed wakes for good. */
export function offerAtShrine(input: GameState, itemId: string): { state: GameState; refused: OfferRefusal | null; breed: BreedId | null } {
  const breed = OFFERINGS[itemId]
  if (!breed) return { state: input, refused: 'notOffering', breed: null }
  if (countOf(input.inventory, itemId) <= 0) return { state: input, refused: 'notOwned', breed }
  if (isUnlocked(input, breed)) return { state: input, refused: 'awake', breed }
  const state = structuredClone(input)
  state.inventory = addItems(state.inventory, itemId, -1)
  if (state.inventory[itemId]! <= 0) delete state.inventory[itemId]
  state.unlocked.push(breed)
  return { state, refused: null, breed }
}

/** What the Bag holds that the stone would take, with whether the breed is still asleep. */
export function offeringsInBag(state: GameState): { itemId: string; breed: BreedId; awake: boolean }[] {
  return Object.keys(OFFERINGS)
    .filter((id) => countOf(state.inventory, id) > 0)
    .map((itemId) => ({ itemId, breed: OFFERINGS[itemId]!, awake: isUnlocked(state, OFFERINGS[itemId]!) }))
}

export type BlueprintRefusal = 'notOwned' | 'awake'

/** The Brass Blueprint goes to Dr. Pell: Gearhoot wakes at the Shrine and the Market stocks one. */
export function giveBlueprint(input: GameState): { state: GameState; refused: BlueprintRefusal | null } {
  if (countOf(input.inventory, 'brass-blueprint') <= 0) return { state: input, refused: 'notOwned' }
  if (isUnlocked(input, 'gearhoot')) return { state: input, refused: 'awake' }
  const state = structuredClone(input)
  state.inventory = addItems(state.inventory, 'brass-blueprint', -1)
  if (state.inventory['brass-blueprint']! <= 0) delete state.inventory['brass-blueprint']
  state.unlocked.push('gearhoot')
  return { state, refused: null }
}

/** The Lantern Vigil at the Shrine: free, and it leaves a Vigil Lantern in the Bag. */
export function attendVigil(input: GameState): { state: GameState; refused: 'closed' | null } {
  if (!input.unlocks.vigilOpen) return { state: input, refused: 'closed' }
  const state = structuredClone(input)
  state.unlocks.vigilOpen = false
  state.inventory = addItems(state.inventory, 'vigil-lantern', 1)
  return { state, refused: null }
}

/* ---------- the cocoon (Velvesper) ---------- */

function freeThisWeek(state: GameState): boolean {
  return state.tournament === null && state.journey === null && state.trial === null && state.expedition === null
}

/** June week 4: a happy, rested, well-fed Nibblegrub of the right age spins a cocoon. */
export function cocoonReady(state: GameState): boolean {
  const m = state.monster
  const c = UNLOCKS.cocoon
  if (!m || state.ended || !freeThisWeek(state) || state.unlocks.cocoonInto) return false
  if (m.mainBreed !== 'nibblegrub' || m.status.cocoonWeeks > 0) return false
  const d = dateOf(state.week)
  if (d.month !== c.month || d.week !== c.week) return false
  if (m.ageWeeks < c.ageMin || m.ageWeeks > c.ageMax) return false
  if (loyaltyOf(m) < c.loyaltyMin || m.fatigue > c.fatigueMax || m.stress > c.stressMax) return false
  if (m.diet.puddingCount < c.puddings) return false
  return !availability(m).locked
}

export function startCocoon(input: GameState): GameState {
  const state = structuredClone(input)
  state.monster!.status.cocoonWeeks = UNLOCKS.cocoon.weeks
  state.unlocks.cocoonInto = 'velvesper'
  state.pendingRequest = null
  return state
}

/**
 * The metamorphosis: a new main breed with the same sub-breed, 80 % of the trained gains kept on top of the
 * new base, the new breed's grades, growth, guts rate and trait, +60 weeks of life, techniques carried over
 * where the new kit has the same family (same range when it can), otherwise the new starters.
 */
export function metamorphose(input: Monster, into: BreedId): Monster {
  const m = structuredClone(input)
  const gains = trainedGains(m)
  const mix = mixBreeds(into, m.subBreed)
  for (const k of STAT_KEYS) m.stats[k] = clamp(mix.base[k] + divRound(gains[k] * UNLOCKS.cocoon.keepGainsPct, 100), RANGES.stat.min, RANGES.stat.max)
  m.mainBreed = into
  m.grades = mix.grades
  m.growthType = BREED_BY_ID[into].growth
  m.gutsRate = mix.gutsRate
  m.lifespanTotal = clamp(m.lifespanTotal + UNLOCKS.cocoon.lifespanBonus, RANGES.lifespan.min, RANGES.lifespan.max)
  m.flags.pure = mix.pure
  m.appearance = { paletteBreed: m.subBreed, accentPart: mix.pure ? null : BREED_BY_ID[m.subBreed].art.accentPart }

  const kit = techniquesOfBreed(into)
  const taken = new Set<string>()
  const carried: TechniqueSlot[] = []
  for (const slot of m.techniques) {
    const tech = TECHNIQUE_BY_ID[slot.id]
    if (!tech) continue
    if (tech.breed === 'universal') {
      carried.push(slot)
      continue
    }
    if (tech.family === 'Basic') continue
    const sameFamily = kit.filter((t) => t.family === tech.family && !taken.has(t.id))
    const match = sameFamily.find((t) => t.range === tech.range) ?? sameFamily[0]
    if (!match) continue
    taken.add(match.id)
    carried.push({ ...slot, id: match.id })
  }
  const starters: TechniqueSlot[] = mix.techniques.filter((id) => !carried.some((s) => s.id === id)).map((id) => ({ id, uses: 0, level: 1 }))
  m.techniques = [...starters, ...carried].slice(0, SONGBOOK.maxTechniques)
  return m
}

/** The cocoon opened (the aging tick said so): the monster emerges and the breed wakes at the Shrine. */
export function emerge(input: GameState): { state: GameState; breed: BreedId } | null {
  const into = input.unlocks.cocoonInto
  if (!into || !input.monster) return null
  const state = structuredClone(input)
  state.monster = metamorphose(state.monster!, into)
  state.unlocks.cocoonInto = null
  if (!state.unlocked.includes(into)) state.unlocked.push(into)
  return { state, breed: into }
}

/* ---------- the storm chase (Zipwisp) ---------- */

/** A storm week, a fast, calm, rested monster, and Zipwisp still asleep: the spark is out there. */
export function stormChaseReady(state: GameState): boolean {
  const m = state.monster
  const s = UNLOCKS.storm
  if (!m || state.ended || state.weather !== 'Storm' || !freeThisWeek(state)) return false
  if (isUnlocked(state, 'zipwisp') || countOf(state.inventory, 'stormglass') > 0) return false
  if (m.stats.SPD < s.spdMin || m.stress > s.stressMax || m.fatigue > s.fatigueMax) return false
  const a = availability(m)
  return !a.locked && !a.restOnly
}

/** Yes to the spark: the week is spent, and the monster brings back Stormglass. */
export function acceptStormChase(input: GameState): GameState {
  const state = structuredClone(input)
  state.inventory = addItems(state.inventory, 'stormglass', 1)
  state.monster!.fatigue = addCondition(state.monster!.fatigue, UNLOCKS.storm.fatigueCost)
  state.pendingEvent = null
  return state
}

export function declineEvent(input: GameState): GameState {
  if (!input.pendingEvent) return input
  const state = structuredClone(input)
  state.pendingEvent = null
  return state
}

/* ---------- the Tide Pool (Reefclaw) ---------- */

export function reefclawDue(state: GameState): boolean {
  if (!state.upgrades.tidePool || state.unlocks.reefclawArrived || !state.monster || state.ended) return false
  const d = dateOf(state.week)
  return d.month === UNLOCKS.reefclaw.month && d.week === UNLOCKS.reefclaw.week
}

/** A Reefclaw moves into the Tide Pool: the ranch if it is empty, else the Freezer. No room: it tries again next June. */
export function reefclawArrival(input: GameState): { state: GameState; placed: Placed | null } {
  const reefclaw = createMonster({ id: `reefclaw-${input.week}`, mainBreed: 'reefclaw', subBreed: 'reefclaw', likes: rollLikes(createRng(UNLOCKS.reefclaw.seed)), name: 'Reefclaw' })
  const placed = placeNewMonster(input, reefclaw)
  if (!placed.placed) return { state: input, placed: null }
  const state = placed.state
  state.unlocks.reefclawArrived = true
  if (!state.unlocked.includes('reefclaw')) state.unlocked.push('reefclaw')
  return { state, placed: placed.placed }
}

/* ---------- the masquerade (Mirrorkin) and the Crowns (Aurelwyrm) ---------- */

/** Has any monster of this ranch reached the grade (the active one, or anyone remembered)? */
export function reachedGrade(state: GameState, grade: TournamentGrade): boolean {
  const gi = TOURNAMENT_GRADES.indexOf(grade)
  const monsters: Monster[] = [...(state.monster ? [state.monster] : []), ...state.freezer, ...state.elderGrove, ...state.memorial.map((e) => e.monster), ...state.hallOfFame.map((h) => h.monster)]
  return monsters.some((m) => TOURNAMENT_GRADES.indexOf(m.grade) >= gi || TOURNAMENT_GRADES.indexOf(m.records.highestGrade) >= gi)
}

/* ---------- the Journal's Rumors page ---------- */

/** 0 nothing heard · 1 rumor heard · 2 in progress · 3 the breed is awake. */
export type ChainStage = 0 | 1 | 2 | 3

export function chainStage(state: GameState, chain: UnlockChain): ChainStage {
  if (isUnlocked(state, CHAIN_BREED[chain])) return 3
  const heard = state.unlocks.rumorsHeard.includes(chain)
  const inv = state.inventory
  let progress = false
  switch (chain) {
    case 'cocoon':
      progress = state.unlocks.cocoonInto !== null || (state.monster?.mainBreed === 'nibblegrub' && state.monster.diet.puddingCount > 0)
      break
    case 'vigil':
      progress = countOf(inv, 'vigil-lantern') > 0 || state.unlocks.vigilOpen
      break
    case 'storm-chase':
      progress = countOf(inv, 'stormglass') > 0
      break
    case 'masquerade':
      progress = countOf(inv, 'shard-mask') > 0
      break
    case 'blueprint':
      progress = countOf(inv, 'brass-blueprint') > 0
      break
    case 'tide-pool':
      progress = state.upgrades.tidePool
      break
    case 'strange-chest':
      progress = state.unlocks.expeditionsBySite['thornwood-ruins'] > 0
      break
    case 'four-crowns':
      progress = state.guild.crownsWon.length > 0 || state.unlocks.wyrmScaleGiven
      break
  }
  if (progress) return 2
  return heard ? 1 : 0
}

/** The number a chain's progress line mentions, if it mentions one. */
export function chainCount(state: GameState, chain: UnlockChain): number | null {
  switch (chain) {
    case 'cocoon':
      return state.monster?.mainBreed === 'nibblegrub' ? state.monster.diet.puddingCount : 0
    case 'strange-chest':
      return state.unlocks.expeditionsBySite['thornwood-ruins']
    case 'four-crowns':
      return state.guild.crownsWon.length
    default:
      return null
  }
}
