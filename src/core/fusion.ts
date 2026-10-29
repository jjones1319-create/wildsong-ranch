import { BREED_BY_ID } from '../data/breeds.ts'
import { BREED_KINDS, FUSION_RECIPES, FUSION_RULES } from '../data/fusionRecipes.ts'
import { ITEM_BY_ID } from '../data/items.ts'
import { startersOf, techniquesOfBreed, TECHNIQUE_BY_ID, UNIVERSAL_TECHNIQUES } from '../data/techniques.ts'
import { FREEZER, FUSION, SONGBOOK } from '../data/tuning.ts'
import { BREED_IDS, FAMILIES, STAT_KEYS, type BreedId, type Grades, type Kind, type Stats, type TraitId } from '../data/types.ts'
import { cyrb53 } from './hash.ts'
import { countOf } from './items.ts'
import { findStored, placeOnRanch, ranchBusy, recordInEncyclopedia } from './legacy.ts'
import { divRound } from './mathx.ts'
import { createMonster, gradeIndex, mixBreeds, rollLikes, stepGrade, trainedOf, traitOf, zeroStats, type Monster, type TechniqueSlot } from './monster.ts'
import type { Rng } from './rng.ts'
import type { GameState } from './state.ts'
import { variantNameOf } from './variants.ts'

/**
 * GAME_DESIGN §15: Fusion at Dr. Pell's Lab. Outcome odds (the parents' breeds and two surprises), compatibility,
 * the baby's stats and inheritance, catalysts, found recipes, and the parents' move to the Memorial as
 * Ancestors. The baby is always one whole breed. Pure; integer math.
 */

export type OutcomeSource = 'p1' | 'p2' | 'both' | 'surprise'

export interface FusionOutcome {
  /** The baby's breed (main and sub alike). */
  breed: BreedId
  /** Whole percent; the list sums to 100. */
  pct: number
  /** Whose breed it is: the first parent's, the second's, both (same breed), or a surprise. */
  source: OutcomeSource
  /** A surprise's found-recipe key (`a+b>breed`); null for the parents' breeds. */
  key: string | null
}

/* ---------- surprises (CONTENT §2.3) ---------- */

/** The unordered pair: the two main breeds sorted, e.g. `coilfang+galeheron`. */
export function pairKey(a: BreedId, b: BreedId): string {
  return a < b ? `${a}+${b}` : `${b}+${a}`
}

/** A found recipe: `coilfang+galeheron>hearthwing`. */
export function findKey(a: BreedId, b: BreedId, result: BreedId): string {
  return `${pairKey(a, b)}>${result}`
}

export interface SurpriseScore {
  breed: BreedId
  score: number
}

/** Every candidate surprise for a pair, best first: unlocked breeds other than the parents, scored by kinds. */
export function surpriseScores(a: BreedId, b: BreedId, unlocked: readonly BreedId[]): SurpriseScore[] {
  const pair = pairKey(a, b)
  const ka = BREED_KINDS[a]
  const kb = BREED_KINDS[b]
  const recipes = new Set(FUSION_RECIPES.filter((r) => pairKey(r.a, r.b) === pair).map((r) => r.makes))
  const ruleKinds: Kind[] = FUSION_RULES.filter((r) => (ka.includes(r.a) && kb.includes(r.b)) || (ka.includes(r.b) && kb.includes(r.a))).map((r) => r.makes)
  const w = FUSION.surprise
  const scored: (SurpriseScore & { tie: number })[] = []
  for (const id of BREED_IDS) {
    if (id === a || id === b || !unlocked.includes(id)) continue
    const kc = BREED_KINDS[id]
    let score = recipes.has(id) ? w.recipe : 0
    for (const k of ruleKinds) if (kc.includes(k)) score += w.rule
    if (kc.some((k) => ka.includes(k)) && kc.some((k) => kb.includes(k))) score += w.sharesBoth
    for (const k of kc) if (ka.includes(k) || kb.includes(k)) score += w.sharedKind
    scored.push({ breed: id, score, tie: cyrb53(`${pair}>${id}`) })
  }
  scored.sort((x, y) => y.score - x.score || x.tie - y.tie || (x.breed < y.breed ? -1 : 1))
  return scored.map(({ breed, score }) => ({ breed, score }))
}

/** The pair's surprises, best first (two, or fewer when there are not enough candidates). */
export function fusionSurprises(a: BreedId, b: BreedId, unlocked: readonly BreedId[]): BreedId[] {
  return surpriseScores(a, b, unlocked)
    .slice(0, FUSION.odds.surprises.length)
    .map((s) => s.breed)
}

/** Largest-remainder rounding: whole percents that add up to exactly 100 (ties go to the earlier row). */
function toPercents(weights: readonly number[]): number[] {
  const total = weights.reduce((a, b) => a + b, 0)
  if (total <= 0) return weights.map(() => 0)
  const floors = weights.map((w) => Math.floor((w * 100) / total))
  let remaining = 100 - floors.reduce((a, b) => a + b, 0)
  const order = weights.map((w, i) => ({ i, rem: (w * 100) % total })).sort((a, b) => b.rem - a.rem || a.i - b.i)
  for (const o of order) {
    if (remaining <= 0) break
    floors[o.i]! += 1
    remaining -= 1
  }
  return floors
}

/** §15 "Outcome odds": the first parent's breed, the second's and the two surprises; locked breeds drop out. */
export function fusionOutcomes(p1: Pick<Monster, 'mainBreed'>, p2: Pick<Monster, 'mainBreed'>, unlocked: readonly BreedId[], lineageSeal = false): FusionOutcome[] {
  const odds = FUSION.odds
  const rows: { breed: BreedId; weight: number; source: OutcomeSource; key: string | null }[] = []
  const addParent = (breed: BreedId, weight: number, source: OutcomeSource) => {
    if (!unlocked.includes(breed)) return
    const same = rows.find((r) => r.breed === breed)
    if (same) {
      same.weight += weight
      same.source = 'both'
    } else rows.push({ breed, weight, source, key: null })
  }
  addParent(p1.mainBreed, odds.p1 * (lineageSeal ? FUSION.sealMultiplier : 1), 'p1')
  addParent(p2.mainBreed, odds.p2, 'p2')
  fusionSurprises(p1.mainBreed, p2.mainBreed, unlocked).forEach((breed, i) => {
    rows.push({ breed, weight: odds.surprises[i]!, source: 'surprise', key: findKey(p1.mainBreed, p2.mainBreed, breed) })
  })
  const pcts = toPercents(rows.map((r) => r.weight))
  return rows.map((r, i) => ({ breed: r.breed, pct: pcts[i]!, source: r.source, key: r.key })).filter((o) => o.pct > 0)
}

/** Whether this ranch has bred this outcome before (the parents' breeds always count as known). */
export function outcomeKnown(o: FusionOutcome, finds: readonly string[]): boolean {
  return o.key === null || finds.includes(o.key)
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

/** The parents' trained gains (trained points − that parent's breed base; sweets don't pass on), blended 2:1, never below 0; ×div. */
function blendedOffsets3(p1: Monster, p2: Monster): Stats {
  const b1 = mixBreeds(p1.mainBreed, p1.subBreed).base
  const b2 = mixBreeds(p2.mainBreed, p2.subBreed).base
  const out = zeroStats()
  for (const k of STAT_KEYS) out[k] = Math.max(0, FUSION.offset.p1 * (trainedOf(p1, k) - b1[k]) + FUSION.offset.p2 * (trainedOf(p2, k) - b2[k]))
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

/**
 * The head start from the parents: round(offset · P · K), but never more than 10 % (`FUSION.headStartMaxPct`) of
 * the better parent's trained points in that stat (the owner's rule, v1.11).
 */
export function headStartFrom(p1: Monster, p2: Monster, m: number, outcomePct: number): Stats {
  const off3 = blendedOffsets3(p1, p2)
  const pPct = FUSION.pBasePct + FUSION.pPerMatchPct * m
  const kPct = rarityK(outcomePct)
  const out = zeroStats()
  for (const k of STAT_KEYS) {
    const limit = Math.floor((Math.max(trainedOf(p1, k), trainedOf(p2, k)) * FUSION.headStartMaxPct) / 100)
    out[k] = Math.min(divRound(off3[k] * pPct * kPct, FUSION.offset.div * 100 * 100), limit)
  }
  return out
}

/** The baby's stat offsets over its breed base: the parents' head start + catalyst. */
export function babyStatOffsets(p1: Monster, p2: Monster, m: number, outcomePct: number, catalyst: CatalystEffect): Stats {
  const head = headStartFrom(p1, p2, m, outcomePct)
  const out = zeroStats()
  for (const k of STAT_KEYS) out[k] = head[k] + catalyst.stats[k]
  return out
}

/** §15 (v1.11): one step up in a stat when the better parent's grade there beats the baby breed's own, never past it. */
export function inheritedGrades(p1: Pick<Monster, 'grades'>, p2: Pick<Monster, 'grades'>, breed: BreedId): Grades {
  const grades = { ...mixBreeds(breed, breed).grades }
  for (const k of STAT_KEYS) {
    const best = Math.max(gradeIndex(p1.grades[k]), gradeIndex(p2.grades[k]))
    if (best > gradeIndex(grades[k])) grades[k] = stepGrade(grades[k], 1)
  }
  return grades
}

/**
 * §15 (v1.11): the second trait. The first of the first parent's breed trait, the second's, then their own inherited
 * traits, that isn't the baby's own (Hungry Grub's cocoon is Nibblegrub's alone, so it never passes on).
 */
export function inheritedTraitFor(p1: Pick<Monster, 'mainBreed' | 'inheritedTrait'>, p2: Pick<Monster, 'mainBreed' | 'inheritedTrait'>, breed: BreedId): TraitId | null {
  const own = BREED_BY_ID[breed].trait
  const candidates = [traitOf(p1), traitOf(p2), p1.inheritedTrait, p2.inheritedTrait]
  return candidates.find((t): t is TraitId => t !== null && t !== undefined && t !== own && !FUSION.notInherited.includes(t)) ?? null
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
    // §10.5: universal techniques count as part of every breed's kit.
    const kit = new Set([...techniquesOfBreed(baby.mainBreed), ...UNIVERSAL_TECHNIQUES].map((t) => t.id))
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
  /** A surprise this ranch had never bred from this pair before. */
  newFind: boolean
  /** The stat points the parents gave as a head start (catalysts not included). */
  headStart: Stats
}

/** Builds the baby for a chosen outcome (the roll itself happens in `fuse`). The baby is one whole breed. */
export function makeBaby(p1: Monster, p2: Monster, outcome: FusionOutcome, catalyst: CatalystEffect, id: string, rng: Rng): FusionResult {
  const breed = outcome.breed
  const compat = compatibility(p1, p2, breed, breed)
  const headStart = headStartFrom(p1, p2, compat, outcome.pct)
  const offsets = babyStatOffsets(p1, p2, compat, outcome.pct, catalyst)
  const likes = rollLikes(rng)
  const baby = createMonster({
    id,
    mainBreed: breed,
    subBreed: breed,
    likes,
    offsets: { stats: offsets, lifespan: catalyst.lifespan, gutsRate: 0, nature: divRound(FUSION.blend.p1 * p1.nature + FUSION.blend.p2 * p2.nature, FUSION.blend.div) },
    generation: Math.max(p1.generation, p2.generation) + 1,
    parents: [p1.id, p2.id],
    name: variantNameOf({ mainBreed: breed, subBreed: breed, variantId: null }),
  })
  baby.form = divRound(FUSION.blend.p1 * p1.form + FUSION.blend.p2 * p2.form, FUSION.blend.div)
  // v1.11: better grades and a second trait from the parents.
  baby.grades = inheritedGrades(p1, p2, breed)
  baby.inheritedTrait = inheritedTraitFor(p1, p2, breed)
  // Starters first (createMonster), then the inherited ones.
  const starters = new Set(startersOf(breed).map((t) => t.id))
  baby.techniques = [...baby.techniques.filter((t) => starters.has(t.id) || TECHNIQUE_BY_ID[t.id]?.subQuirk), ...inheritedTechniques(baby, p1, p2)]
  return { baby, outcome, compat, tier: compatTier(compat), newFind: false, headStart }
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
  if (outcome.key !== null && !state.fusionFinds.includes(outcome.key)) {
    state.fusionFinds.push(outcome.key)
    result.newFind = true
  }
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
