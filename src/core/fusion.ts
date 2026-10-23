import { BREED_BY_ID } from '../data/breeds.ts'
import { ITEM_BY_ID } from '../data/items.ts'
import { startersOf, techniquesOfBreed, TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { FREEZER, FUSION, SONGBOOK } from '../data/tuning.ts'
import { FAMILIES, STAT_KEYS, type BreedId, type Stats } from '../data/types.ts'
import { countOf } from './items.ts'
import { findStored, placeOnRanch, ranchBusy, recordInEncyclopedia } from './legacy.ts'
import { divRound } from './mathx.ts'
import { createMonster, gradeIndex, mixBreeds, rollLikes, zeroStats, type Monster, type TechniqueSlot } from './monster.ts'
import type { Rng } from './rng.ts'
import type { GameState } from './state.ts'
import { variantNameOf } from './variants.ts'

/**
 * GAME_DESIGN §15: Fusion at Dr. Pell's Lab. Outcome odds, compatibility, the baby's stats and
 * inheritance, catalysts, and the parents' move to the Memorial as Ancestors. Pure; integer math.
 */

export interface FusionOutcome {
  main: BreedId
  sub: BreedId
  /** Whole percent; the shown list sums to 100. */
  pct: number
}

type WeightMap = Map<BreedId, number>

function addW(map: WeightMap, id: BreedId, w: number): void {
  map.set(id, (map.get(id) ?? 0) + w)
}

/** Steps 1–5 of §15 "Outcome odds". */
export function fusionOutcomes(p1: Pick<Monster, 'mainBreed' | 'subBreed'>, p2: Pick<Monster, 'mainBreed' | 'subBreed'>, unlocked: readonly BreedId[], lineageSeal = false): FusionOutcome[] {
  const w = FUSION.mainWeights
  const mains: WeightMap = new Map()
  addW(mains, p1.mainBreed, w.p1Main * (lineageSeal ? FUSION.sealMultiplier : 1))
  addW(mains, p2.mainBreed, w.p2Main)
  addW(mains, p1.subBreed, w.p1Sub)
  addW(mains, p2.subBreed, w.p2Sub)
  const s = FUSION.subWeights
  const subs: WeightMap = new Map()
  addW(subs, p2.mainBreed, s.p2Main)
  addW(subs, p1.subBreed, s.p1Sub)
  addW(subs, p2.subBreed, s.p2Sub)
  addW(subs, p1.mainBreed, s.p1Main)
  // weight = mainW · subW · strength / 5: the divisor cancels in the normalization, so integers suffice.
  const raw: { main: BreedId; sub: BreedId; weight: number }[] = []
  for (const [main, mw] of mains) {
    if (!unlocked.includes(main)) continue
    for (const [sub, sw] of subs) raw.push({ main, sub, weight: mw * sw * BREED_BY_ID[main].strength })
  }
  const total = raw.reduce((a, r) => a + r.weight, 0)
  if (total === 0) return []
  const kept = raw
    .filter((r) => r.weight * 100 >= total * FUSION.minPct)
    .sort((a, b) => b.weight - a.weight || a.main.localeCompare(b.main) || a.sub.localeCompare(b.sub))
    .slice(0, FUSION.maxOutcomes)
  // Largest-remainder rounding so the shown percentages add up to exactly 100.
  const keptTotal = kept.reduce((a, r) => a + r.weight, 0)
  const scaled = kept.map((r) => ({ ...r, exact: (r.weight * 10000) / keptTotal }))
  const floors = scaled.map((r) => Math.floor(r.exact / 100))
  let remaining = 100 - floors.reduce((a, b) => a + b, 0)
  const order = scaled.map((r, i) => ({ i, rem: r.exact - floors[i]! * 100 })).sort((a, b) => b.rem - a.rem || a.i - b.i)
  for (const o of order) {
    if (remaining <= 0) break
    floors[o.i]! += 1
    remaining -= 1
  }
  return kept.map((r, i) => ({ main: r.main, sub: r.sub, pct: floors[i]! }))
}

/* ---------- compatibility ---------- */

/** Ranks 1–6 by value, highest first; ties go to the earlier stat. */
function rankByValue(values: Stats): Stats {
  const order = [...STAT_KEYS].sort((a, b) => values[b] - values[a] || STAT_KEYS.indexOf(a) - STAT_KEYS.indexOf(b))
  const out = zeroStats()
  order.forEach((k, i) => (out[k] = i + 1))
  return out
}

/** The baby breed's stats ranked by growth grade, ties broken by base stat. */
export function babyRanks(main: BreedId, sub: BreedId): Stats {
  const mix = mixBreeds(main, sub)
  const order = [...STAT_KEYS].sort((a, b) => gradeIndex(mix.grades[b]) - gradeIndex(mix.grades[a]) || mix.base[b] - mix.base[a] || STAT_KEYS.indexOf(a) - STAT_KEYS.indexOf(b))
  const out = zeroStats()
  order.forEach((k, i) => (out[k] = i + 1))
  return out
}

/** M (0–6): stats where the baby's rank equals either parent's rank. */
export function compatibility(p1: Pick<Monster, 'stats'>, p2: Pick<Monster, 'stats'>, main: BreedId, sub: BreedId): number {
  const r1 = rankByValue(p1.stats)
  const r2 = rankByValue(p2.stats)
  const rb = babyRanks(main, sub)
  let m = 0
  for (const k of STAT_KEYS) if (rb[k] === r1[k] || rb[k] === r2[k]) m += 1
  return m
}

export type CompatTier = 'low' | 'decent' | 'wonderful' | 'perfect'

export function compatTier(m: number): CompatTier {
  if (m >= FUSION.comment.perfect) return 'perfect'
  if (m >= FUSION.comment.wonderful) return 'wonderful'
  if (m >= FUSION.comment.decent) return 'decent'
  return 'low'
}

/* ---------- the baby ---------- */

/** K in percent, by the rarity of the chosen outcome. */
export function rarityK(pct: number): number {
  for (const [upTo, k] of FUSION.rarityK) if (pct <= upTo) return k
  return FUSION.rarityK[FUSION.rarityK.length - 1]![1]
}

/** The parents' trained gains (stat − that parent's breed base), blended 2:1 and never below 0; scaled ×div. */
function blendedOffsets3(p1: Monster, p2: Monster): Stats {
  const b1 = mixBreeds(p1.mainBreed, p1.subBreed).base
  const b2 = mixBreeds(p2.mainBreed, p2.subBreed).base
  const out = zeroStats()
  for (const k of STAT_KEYS) out[k] = Math.max(0, FUSION.offset.p1 * (p1.stats[k] - b1[k]) + FUSION.offset.p2 * (p2.stats[k] - b2[k]))
  return out
}

export interface CatalystEffect {
  stats: Stats
  lifespan: number
  lineageSeal: boolean
}

export function catalystEffect(itemId: string | null): CatalystEffect {
  const none: CatalystEffect = { stats: zeroStats(), lifespan: 0, lineageSeal: false }
  if (!itemId) return none
  const item = ITEM_BY_ID[itemId]
  if (!item || item.effect.kind !== 'catalyst') return none
  const stats = zeroStats()
  if (item.effect.stat) stats[item.effect.stat] = FUSION.shardStat
  return { stats, lifespan: item.effect.lifespan, lineageSeal: item.effect.lineageSeal }
}

/** The baby's stat offsets over its breed base: round(offset · P · K) + catalyst. */
export function babyStatOffsets(p1: Monster, p2: Monster, m: number, outcomePct: number, catalyst: CatalystEffect): Stats {
  const off3 = blendedOffsets3(p1, p2)
  const pPct = FUSION.pBasePct + FUSION.pPerMatchPct * m
  const kPct = rarityK(outcomePct)
  const out = zeroStats()
  for (const k of STAT_KEYS) out[k] = divRound(off3[k] * pPct * kPct, FUSION.offset.div * 100 * 100) + catalyst.stats[k]
  return out
}

/** §15 inheritance of techniques. The baby already knows its breed's starters. */
export function inheritedTechniques(baby: Monster, p1: Monster, p2: Monster): TechniqueSlot[] {
  const known = new Set(baby.techniques.map((t) => t.id))
  const out: TechniqueSlot[] = []
  if (baby.mainBreed === p1.mainBreed) {
    const learned = p1.techniques.filter((t) => TECHNIQUE_BY_ID[t.id] && TECHNIQUE_BY_ID[t.id]!.family !== 'Basic' && !known.has(t.id))
    const take = Math.floor((learned.length * FUSION.inherit.num) / FUSION.inherit.den)
    for (const t of learned.slice(0, take)) out.push({ ...t })
  } else {
    const kit = new Set(techniquesOfBreed(baby.mainBreed).map((t) => t.id))
    const pool = [...p1.techniques, ...p2.techniques]
    for (const fam of FAMILIES) {
      if (fam === 'Basic') continue
      const pick = pool.find((t) => kit.has(t.id) && !known.has(t.id) && TECHNIQUE_BY_ID[t.id]?.family === fam)
      if (pick) out.push({ ...pick })
    }
  }
  const room = Math.max(0, SONGBOOK.maxTechniques - baby.techniques.length)
  return out.slice(0, room)
}

export interface FusionResult {
  baby: Monster
  outcome: FusionOutcome
  compat: number
  tier: CompatTier
}

/** Builds the baby for a chosen outcome (the roll itself happens in `fuse`). */
export function makeBaby(p1: Monster, p2: Monster, outcome: FusionOutcome, catalyst: CatalystEffect, id: string, rng: Rng): FusionResult {
  const compat = compatibility(p1, p2, outcome.main, outcome.sub)
  const offsets = babyStatOffsets(p1, p2, compat, outcome.pct, catalyst)
  const likes = rollLikes(rng)
  const baby = createMonster({
    id,
    mainBreed: outcome.main,
    subBreed: outcome.sub,
    likes,
    offsets: { stats: offsets, lifespan: catalyst.lifespan, gutsRate: 0, nature: divRound(FUSION.blend.p1 * p1.nature + FUSION.blend.p2 * p2.nature, FUSION.blend.div) },
    generation: Math.max(p1.generation, p2.generation) + 1,
    parents: [p1.id, p2.id],
    name: variantNameOf({ mainBreed: outcome.main, subBreed: outcome.sub, variantId: null }),
  })
  baby.form = divRound(FUSION.blend.p1 * p1.form + FUSION.blend.p2 * p2.form, FUSION.blend.div)
  // Starters first (createMonster), then the inherited ones.
  const starters = new Set(startersOf(outcome.main).map((t) => t.id))
  baby.techniques = [...baby.techniques.filter((t) => starters.has(t.id) || TECHNIQUE_BY_ID[t.id]?.subQuirk), ...inheritedTechniques(baby, p1, p2)]
  return { baby, outcome, compat, tier: compatTier(compat) }
}

export type FuseRefusal = 'notFound' | 'sameMonster' | 'money' | 'freezerFull' | 'busy' | 'noOutcome' | 'noCatalyst'

export interface FuseOutput {
  state: GameState
  result: FusionResult | null
  placed: 'ranch' | 'freezer' | null
  refused: FuseRefusal | null
}

/**
 * Fuses two stored monsters: pays the fee, uses the catalyst, rolls the outcome by its percentage, builds the
 * baby and sends the parents to the Memorial as Ancestors. The baby goes to the ranch when it is empty,
 * otherwise to the Freezer.
 */
export function fuse(input: GameState, id1: string, id2: string, catalystId: string | null, babyId: string, rng: Rng): FuseOutput {
  const none = (refused: FuseRefusal): FuseOutput => ({ state: input, result: null, placed: null, refused })
  if (id1 === id2) return none('sameMonster')
  const s1 = findStored(input, id1)
  const s2 = findStored(input, id2)
  if (!s1 || !s2) return none('notFound')
  if (input.money < FUSION.fee) return none('money')
  if (catalystId && countOf(input.inventory, catalystId) <= 0) return none('noCatalyst')
  const toRanch = input.monster === null && !input.ended
  if (toRanch && ranchBusy(input)) return none('busy')
  // Two frozen parents free two slots; Elders free none. The baby needs one.
  const freed = (s1.where === 'freezer' ? 1 : 0) + (s2.where === 'freezer' ? 1 : 0)
  if (!toRanch && input.freezer.length - freed + 1 > FREEZER.slots) return none('freezerFull')
  const catalyst = catalystEffect(catalystId)
  const outcomes = fusionOutcomes(s1.monster, s2.monster, input.unlocked, catalyst.lineageSeal)
  if (outcomes.length === 0) return none('noOutcome')
  const state = structuredClone(input)
  state.money -= FUSION.fee
  if (catalystId) {
    state.inventory[catalystId] = (state.inventory[catalystId] ?? 0) - 1
    if (state.inventory[catalystId]! <= 0) delete state.inventory[catalystId]
  }
  const outcome = rng.weightedPick(outcomes, (o) => o.pct)
  const result = makeBaby(s1.monster, s2.monster, outcome, catalyst, babyId, rng)
  // Parents become Ancestors.
  for (const stored of [s1, s2]) {
    state.memorial.unshift({ monster: structuredClone(stored.monster), cause: 'fused', epitaph: '', week: state.week })
  }
  state.freezer = state.freezer.filter((m) => m.id !== id1 && m.id !== id2)
  state.elderGrove = state.elderGrove.filter((m) => m.id !== id1 && m.id !== id2)
  let placed: 'ranch' | 'freezer'
  if (toRanch) {
    placeOnRanch(state, result.baby)
    placed = 'ranch'
  } else {
    state.freezer.push(result.baby)
    recordInEncyclopedia(state, result.baby)
    placed = 'freezer'
  }
  return { state, result, placed, refused: null }
}

/** The names on a fused monster's family tree, looked up on this ranch (the Memorial, the Freezer, the Grove, the ranch). */
export function findRelative(state: GameState, id: string): Monster | null {
  return state.memorial.find((e) => e.monster.id === id)?.monster ?? findStored(state, id)?.monster ?? (state.monster?.id === id ? state.monster : null)
}
