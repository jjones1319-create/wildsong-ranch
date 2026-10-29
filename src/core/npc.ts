import { BREED_BY_ID } from '../data/breeds.ts'
import { techniquesOfBreed, UNIVERSAL_TECHNIQUES } from '../data/techniques.ts'
import { NPC, RANGES, SONGBOOK } from '../data/tuning.ts'
import { STAT_KEYS, type BreedId, type Family, type Personality, type Stats, type TournamentGrade } from '../data/types.ts'
import { clamp } from './mathx.ts'
import { createMonster, gradeFactor100, rollLikes, zeroStats, type Monster } from './monster.ts'
import { firstWeekOfStage } from './presets.ts'
import { createRng } from './rng.ts'

/**
 * GAME_DESIGN §13 generated opponents: stats spread by the breed's growth grades (weight 0.9 + gf, ±8 % noise)
 * to a total in the grade's band, a technique set by grade, loyalty and fame bands. Rivals, habits and
 * seeding by cup arrive with the tournaments (M5); the Battle Lab and the §26 balance tests use this now.
 */

export const NPC_GRADES = ['E', 'D', 'C', 'B', 'A', 'S', 'Crown', 'Legend'] as const
export type NpcGrade = (typeof NPC_GRADES)[number]

export function gradeForTotal(total: number): NpcGrade {
  for (const g of NPC_GRADES) if (total <= NPC.totals[g]![1]) return g
  return 'Legend'
}

function tournamentGradeOf(g: NpcGrade): TournamentGrade {
  return g === 'Crown' || g === 'Legend' ? 'S' : g
}

/** Spreads `total` over the six stats by integer weights, exactly, inside 1–999 (`NPC.statMax`). */
export function distributeTotal(weights: Stats, total: number): Stats {
  const target = clamp(total, RANGES.stat.min * 6, NPC.statMax * 6)
  const sumW = STAT_KEYS.reduce((s, k) => s + weights[k], 0)
  const out = zeroStats()
  let assigned = 0
  for (const k of STAT_KEYS) {
    out[k] = clamp(Math.floor((target * weights[k]) / sumW), RANGES.stat.min, NPC.statMax)
    assigned += out[k]
  }
  let rem = target - assigned
  for (let i = 0; rem !== 0 && i < 6000; i++) {
    const k = STAT_KEYS[i % STAT_KEYS.length]!
    if (rem > 0 && out[k] < NPC.statMax) {
      out[k] += 1
      rem -= 1
    } else if (rem < 0 && out[k] > RANGES.stat.min) {
      out[k] -= 1
      rem += 1
    }
  }
  return out
}

const FAMILY_ORDER: Family[] = ['Basic', 'Hit', 'Wither', 'Sharp', 'Heavy', 'Special', 'Chain', 'Signature']

export interface NpcOptions {
  breed: BreedId
  grade?: NpcGrade
  /** Overrides the grade's band; the grade for the technique set then follows the total. */
  total?: number
  seed: number
  personality?: Personality
  /** A boss also knows its Signature. */
  boss?: boolean
  name?: string
}

export function npcMonster(o: NpcOptions): Monster {
  const rng = createRng(o.seed)
  const breed = BREED_BY_ID[o.breed]
  const grade: NpcGrade = o.grade ?? (o.total !== undefined ? gradeForTotal(o.total) : 'E')
  const band = NPC.totals[grade]!
  const total = o.total ?? rng.nextInt(band[0], band[1])
  const m = createMonster({ id: `npc-${o.breed}-${o.seed}`, mainBreed: o.breed, likes: rollLikes(rng), name: o.name ?? breed.name })

  // Stats by growth-grade weights with personal noise, then an exact total.
  const weights = zeroStats()
  for (const k of STAT_KEYS) {
    const w = NPC.weightBase + gradeFactor100(m.grades[k])
    weights[k] = Math.max(1, w * (100 + rng.nextInt(-NPC.noisePct, NPC.noisePct)))
  }
  m.stats = distributeTotal(weights, total)

  // Techniques by grade (§13).
  const kit = techniquesOfBreed(o.breed)
  const families = new Set<Family>(['Basic'])
  const gi = NPC_GRADES.indexOf(grade)
  const firstOf = rng.pick(['Wither', 'Sharp'] as const)
  const otherOf: Family = firstOf === 'Wither' ? 'Sharp' : 'Wither'
  if (gi >= 1) families.add('Hit')
  if (gi >= 2) families.add(firstOf)
  if (gi >= 3) families.add('Heavy')
  if (gi >= 4) {
    families.add(otherOf)
    if (rng.chance(NPC.chainChancePct)) families.add('Chain')
  }
  if (gi >= 5) {
    families.add('Special')
    families.add('Chain')
  }
  const ids = kit.filter((t) => families.has(t.family)).sort((a, b) => FAMILY_ORDER.indexOf(a.family) - FAMILY_ORDER.indexOf(b.family)).map((t) => t.id)
  if (o.boss) ids.push(...kit.filter((t) => t.family === 'Signature').map((t) => t.id))
  if (gi >= NPC_GRADES.indexOf(NPC.universalFrom)) {
    const type = m.stats.POW >= m.stats.INT ? 'POW' : 'INT'
    const allowed = new Set<Family>(gi >= 5 ? ['Basic', 'Hit', 'Wither', 'Sharp', 'Heavy', 'Special'] : gi >= 4 ? ['Basic', 'Hit', 'Wither', 'Sharp'] : ['Basic', 'Hit'])
    const pool = UNIVERSAL_TECHNIQUES.filter((t) => t.type === type && allowed.has(t.family))
    const n = rng.nextInt(NPC.universal.min, NPC.universal.max)
    for (const t of rng.shuffle(pool).slice(0, n)) ids.push(t.id)
  }
  const unique = [...new Set(ids)].slice(0, SONGBOOK.maxTechniques)
  m.techniques = unique.map((id) => ({ id, uses: 0, level: 1 }))

  // Loyalty, fame, grade, nature, and an adult look.
  const loy = NPC.loyalty[grade]!
  const loyalty = rng.nextInt(loy[0], loy[1])
  m.spoil = loyalty
  m.fear = loyalty
  const fame = NPC.fame[grade]!
  m.fame = rng.nextInt(fame[0], fame[1])
  m.grade = tournamentGradeOf(grade)
  m.records.highestGrade = m.grade
  m.nature = rng.nextInt(-30, 30)
  m.ageWeeks = firstWeekOfStage(m, 5)
  return m
}
