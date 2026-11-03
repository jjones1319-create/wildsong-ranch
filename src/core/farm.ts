import { FARM_PENS, FARM_PERKS, FARM_PERK_BY_ID, type FarmPen, type FarmPerk, type FarmPerkId } from '../data/farm.ts'
import { FARM } from '../data/tuning.ts'
import type { FarmState, FarmTally, GameState } from './state.ts'

/**
 * GAME_DESIGN §9.1 the farm level (v16). XP comes every week (the star and each ranch-mate) and once for each new
 * achievement, counted against a tally of what was already rewarded. Levels 1–10 open pens to buy (gold plus a
 * level, CONTENT §11) and bring perks by themselves. Pure; never touches the RNG.
 */

/** What the save has achieved so far, in the tally's terms. */
export function farmTallyOf(state: Pick<GameState, 'titles' | 'records' | 'journeysBySite' | 'encyclopedia' | 'breeder'>): FarmTally {
  let journeys = 0
  for (const n of Object.values(state.journeysBySite)) journeys += n
  return {
    titles: state.titles.length,
    cupsWon: state.records.cupsWon,
    journeys,
    expeditions: state.records.expeditionsDone,
    breeds: state.encyclopedia.breeds.length,
    rank: state.breeder.rank,
  }
}

/** XP for the growth from one tally to the next (counts that went down give nothing). */
export function tallyXp(from: FarmTally, to: FarmTally): number {
  const x = FARM.xp
  const up = (a: number, b: number) => Math.max(0, b - a)
  return (
    up(from.titles, to.titles) * x.title +
    up(from.cupsWon, to.cupsWon) * x.cup +
    up(from.journeys, to.journeys) * x.journey +
    up(from.expeditions, to.expeditions) * x.expedition +
    up(from.breeds, to.breeds) * x.breed +
    up(from.rank, to.rank) * x.rank
  )
}

/** The tally a brand-new ranch starts from: its first breed and rank 1 are not achievements. */
export function startTally(): FarmTally {
  return { titles: 0, cupsWon: 0, journeys: 0, expeditions: 0, breeds: 1, rank: 1 }
}

/**
 * A fair start for a save that already has a history (v16 migration, or a farm that failed validation): the XP it
 * would have earned with the star alone, and a tally of everything it has done so far. A new game seeds to 0.
 */
export function seedFarm(state: GameState, pensBought = 0): FarmState {
  const tally = farmTallyOf(state)
  const xp = Math.min(FARM.maxXp, state.week * FARM.xp.star + tallyXp(startTally(), tally))
  return { xp, pensBought, tally }
}

/** The farm level (1–10) for this much XP. */
export function farmLevel(xp: number): number {
  let level = 1
  for (let i = 1; i < FARM.levelXp.length; i++) if (xp >= FARM.levelXp[i]!) level = i + 1
  return level
}

export function farmLevelOf(state: Pick<GameState, 'farm'>): number {
  return farmLevel(state.farm.xp)
}

/**
 * The end of a week (from the controller's finishWeek, never the sims' runWeek): XP for the star, each ranch-mate,
 * and the tally's growth. Returns the new level when it went up, so v1.21.0 can announce it (v1.20.0 is silent).
 */
export function farmWeek(input: GameState): { state: GameState; leveledTo: number | null } {
  const tally = farmTallyOf(input)
  const weekly = (input.monster ? FARM.xp.star : 0) + input.ranchmates.length * FARM.xp.mate
  const gained = weekly + tallyXp(input.farm.tally, tally)
  const before = farmLevelOf(input)
  const state = { ...input, farm: { ...input.farm, xp: Math.min(FARM.maxXp, input.farm.xp + gained), tally } }
  const after = farmLevelOf(state)
  return { state, leveledTo: after > before ? after : null }
}

/* ---------- pens ---------- */

/** How many ranch-mates the farm holds (the star is extra): FARM.basePens plus the pens bought. */
export function penCapacity(state: Pick<GameState, 'farm'>): number {
  return FARM.basePens + Math.max(0, Math.min(FARM_PENS.length, state.farm.pensBought))
}

export function penRoom(state: Pick<GameState, 'farm' | 'ranchmates'>): number {
  return Math.max(0, penCapacity(state) - state.ranchmates.length)
}

/** The next pen for sale, or null when every pen is built. */
export function nextPen(state: Pick<GameState, 'farm'>): FarmPen | null {
  return FARM_PENS[state.farm.pensBought] ?? null
}

export type PenRefusal = 'allBuilt' | 'level' | 'money'

export function canBuyPen(state: GameState): { ok: true; pen: FarmPen } | { ok: false; reason: PenRefusal } {
  const pen = nextPen(state)
  if (!pen) return { ok: false, reason: 'allBuilt' }
  if (farmLevelOf(state) < pen.level) return { ok: false, reason: 'level' }
  if (state.money < pen.price) return { ok: false, reason: 'money' }
  return { ok: true, pen }
}

/** Builds the next pen (gold plus the farm level; CONTENT §11). */
export function buyPen(input: GameState): { state: GameState; refused: PenRefusal | null } {
  const can = canBuyPen(input)
  if (!can.ok) return { state: input, refused: can.reason }
  const state = structuredClone(input)
  state.money -= can.pen.price
  state.farm.pensBought += 1
  return { state, refused: null }
}

/* ---------- perks ---------- */

/** Does this level bring the perk (whether or not perks are switched on yet)? */
export function perkAtLevel(id: FarmPerkId, level: number): boolean {
  return level >= FARM_PERK_BY_ID[id].level
}

/** Is the perk working on this ranch? Perks switch on with v1.21.0's farm card (FARM.perksLive). */
export function hasPerk(state: Pick<GameState, 'farm'>, id: FarmPerkId): boolean {
  return FARM.perksLive && perkAtLevel(id, farmLevelOf(state))
}

export interface FarmView {
  level: number
  xp: number
  /** XP at the start of this level and at the next one (null at level 10). */
  levelFrom: number
  levelTo: number | null
  pens: { capacity: number; used: number; next: FarmPen | null; canBuy: boolean; blocked: PenRefusal | null }
  perks: { perk: FarmPerk; unlocked: boolean }[]
}

/** Everything the farm card shows. */
export function farmView(state: GameState): FarmView {
  const level = farmLevelOf(state)
  const can = canBuyPen(state)
  return {
    level,
    xp: state.farm.xp,
    levelFrom: FARM.levelXp[level - 1] ?? 0,
    levelTo: FARM.levelXp[level] ?? null,
    pens: { capacity: penCapacity(state), used: state.ranchmates.length, next: nextPen(state), canBuy: can.ok, blocked: can.ok ? null : can.reason },
    perks: FARM_PERKS.map((perk) => ({ perk, unlocked: perkAtLevel(perk.id, level) })),
  }
}
