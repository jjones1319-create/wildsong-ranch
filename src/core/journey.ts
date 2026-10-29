import { JOURNEY_SITE_BY_ID } from '../data/journeys.ts'
import { TECHNIQUE_BY_ID, techniquesOfBreed } from '../data/techniques.ts'
import { JOURNEY, SIGNATURE, TRAIT_EFFECTS } from '../data/tuning.ts'
import { TOURNAMENT_GRADES, type JourneySiteId, type Stats, type Technique } from '../data/types.ts'
import { clamp, divRound } from './mathx.ts'
import { addCondition, addTrained, gradeFactor100, gradeIndex, hasTrait, loyaltyOf, stageFactor100, stageOf, type Monster } from './monster.ts'
import { npcMonster } from './npc.ts'
import type { Rng } from './rng.ts'
import { isFull } from './songbook.ts'

/**
 * GAME_DESIGN §11: four weeks with a mentor. M1 covers the weekly check, the gains and the technique roll.
 * The Trial battle, mentor bond and sale months arrive with tournaments in M5.
 */

export interface JourneyProgress {
  site: JourneySiteId
  /** The next week to run, 1–4. 5 means finished. */
  weekNo: number
  successes: number
  /** At most one technique per Journey. */
  learned: string | null
  /** Technique that was earned but could not be added because the monster already knows 12. */
  pendingTechnique: string | null
  gains: Stats
  /** §7 Gentle: an Elder from the Grove mentors this Journey (+JOURNEY.technique.elderMentorPct). */
  elderMentor: boolean
}

export function startJourney(site: JourneySiteId, elderMentor = false): JourneyProgress {
  return { site, weekNo: 1, successes: 0, learned: null, pendingTechnique: null, gains: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }, elderMentor }
}

export function isJourneyDone(p: JourneyProgress): boolean {
  return p.weekNo > JOURNEY.weeks
}

export function isSiteOpen(site: JourneySiteId, month: number): boolean {
  return JOURNEY_SITE_BY_ID[site].openMonths.includes(month)
}

export function canEnterSite(m: Monster, site: JourneySiteId): { ok: true } | { ok: false; reason: 'grade' } {
  const gate = JOURNEY_SITE_BY_ID[site].gradeMin
  if (gate && TOURNAMENT_GRADES.indexOf(m.grade) < TOURNAMENT_GRADES.indexOf(gate)) return { ok: false, reason: 'grade' }
  return { ok: true }
}

/** Everything in the weekly score except the roll. */
export function journeyScoreBase(m: Monster, site: JourneySiteId, fatigue = m.fatigue): number {
  const s = JOURNEY.score
  const siteStat = JOURNEY_SITE_BY_ID[site].stat
  return (
    s.sitePerGrade * gradeIndex(m.grades[siteStat]) +
    s.lifPerGrade * gradeIndex(m.grades.LIF) +
    s.perStage * (stageOf(m) - 1) +
    Math.floor(m.fear / s.fearDivisor) -
    Math.floor(fatigue / s.fatigueDivisor)
  )
}

/** Exact success chance for a given week, by counting the rolls that pass the threshold. */
export function weekSuccessPct(m: Monster, site: JourneySiteId, weekNo: number, fatigue = m.fatigue): number {
  const base = journeyScoreBase(m, site, fatigue)
  const threshold = JOURNEY.thresholds[weekNo - 1]!
  const { min, max } = JOURNEY.score.roll
  let passing = 0
  for (let roll = min; roll <= max; roll++) if (base + roll >= threshold) passing++
  return (passing * 100) / (max - min + 1)
}

/** The Ledger forecast: all four weeks, assuming fatigue climbs by the weekly cost after each check. */
export function journeyForecast(m: Monster, site: JourneySiteId): number[] {
  const out: number[] = []
  for (let week = 1; week <= JOURNEY.weeks; week++) out.push(weekSuccessPct(m, site, week, m.fatigue + JOURNEY.fatiguePerWeek * (week - 1)))
  return out
}

/**
 * Site-family techniques of the main breed the monster has not learned, in table order; Chains only once their
 * base is Lv3. At Glacier Bastion a pure breed that missed its Signature at Prime can learn it (§10.4).
 */
export function techniqueCandidates(m: Monster, site: JourneySiteId): Technique[] {
  const family = JOURNEY_SITE_BY_ID[site].family
  const known = new Set(m.techniques.map((t) => t.id))
  const out: Technique[] = []
  for (const t of techniquesOfBreed(m.mainBreed)) {
    const learn = t.learn
    if (known.has(t.id)) continue
    if (learn.kind === 'signature') {
      if (site === 'glacier-bastion') out.push(t)
      continue
    }
    if (learn.kind !== 'journey' || learn.site !== site) continue
    if (t.family !== family && t.family !== 'Chain') continue
    if (learn.chainOf) {
      const chainOf = learn.chainOf
      const base = m.techniques.find((k) => k.id === chainOf)
      if (!base || base.level < 3) continue
    }
    out.push(t)
  }
  return out
}

/** reqScore = the listed stats + loyalty (§11); the Signature at Glacier Bastion needs DEF + its type stat (§10.4). */
export function requirementScore(m: Monster, tech: Technique): number {
  if (tech.learn.kind === 'signature') return m.stats.DEF + m.stats[tech.type]
  if (tech.learn.kind !== 'journey') return 0
  let total = loyaltyOf(m)
  for (const k of tech.learn.stats) total += m.stats[k]
  return total
}

/** The requirement, lowered by the mentor bond (§11: each Mentor's Charm of that site takes 50 off). */
export function requirementValue(tech: Technique, bondCharms = 0): number {
  const base = tech.learn.kind === 'signature' ? SIGNATURE.glacierRequirement : tech.learn.kind === 'journey' ? tech.learn.value : 0
  return Math.max(0, base - bondCharms * JOURNEY.bond.requirementDrop)
}

/** 0% below the requirement; 30% at it; +10% per 50 over; cap 90; +10 Quick Study; +10 Elder mentor. */
export function techniqueChancePct(m: Monster, tech: Technique, elderMentor = false, bondCharms = 0): number {
  const over = requirementScore(m, tech) - requirementValue(tech, bondCharms)
  if (over < 0) return 0
  const t = JOURNEY.technique
  let pct = Math.min(t.capPct, t.basePct + Math.floor(over / t.perPointsOver) * t.pctPerStep)
  if (hasTrait(m, 'quick-study')) pct += TRAIT_EFFECTS.quickStudyJourneyPct
  if (elderMentor) pct += t.elderMentorPct
  return pct
}

export type ChanceTier = 'notReady' | 'possible' | 'likely' | 'veryLikely'

export function chanceTier(pct: number): ChanceTier {
  if (pct <= 0) return 'notReady'
  if (pct < 50) return 'possible'
  if (pct < 80) return 'likely'
  return 'veryLikely'
}

export interface JourneyWeekResult {
  week: number
  success: boolean
  score: number
  gains: Partial<Stats>
  technique: string | null
  /** True when the technique was earned but the monster already knows 12 (the UI asks what to forget). */
  needsForget: boolean
}

/**
 * One Journey week. RNG order: the score roll, then (on success) the site-stat noise, then (if a candidate's
 * requirement is met and nothing was learned yet) the technique chance. Fatigue and stress are applied after the check.
 */
export function journeyWeek(input: Monster, progress: JourneyProgress, rng: Rng, elderMentor = false, bondCharms = 0): { monster: Monster; progress: JourneyProgress; result: JourneyWeekResult } {
  const m = structuredClone(input)
  const p = structuredClone(progress)
  const site = JOURNEY_SITE_BY_ID[p.site]
  const week = p.weekNo
  const score = journeyScoreBase(m, p.site) + rng.nextInt(JOURNEY.score.roll.min, JOURNEY.score.roll.max)
  const success = score >= JOURNEY.thresholds[week - 1]!
  const gains: Partial<Stats> = {}
  let technique: string | null = null
  let needsForget = false

  if (success) {
    p.successes += 1
    const stage = stageOf(m)
    const sf = stageFactor100(stage)
    const g = JOURNEY.gains
    // An S stat has its own, higher ceiling (v1.11).
    const siteGain = clamp(divRound(g.siteBase * gradeFactor100(m.grades[site.stat]) * sf, 100 * 100) + rng.nextInt(-1, 1), g.siteMin, m.grades[site.stat] === 'S' ? g.siteMaxS : g.siteMax)
    const lifGain = clamp(divRound(g.lifBase * gradeFactor100(m.grades.LIF) * sf, 100 * 100), g.lifMin, m.grades.LIF === 'S' ? g.lifMaxS : g.lifMax)
    const applyGain = (k: keyof Stats, amount: number) => {
      const added = addTrained(m, k, amount)
      gains[k] = (gains[k] ?? 0) + added
      p.gains[k] += added
    }
    applyGain(site.stat, siteGain)
    applyGain('LIF', lifGain)

    if (!p.learned) {
      const candidate = techniqueCandidates(m, p.site).find((t) => requirementScore(m, t) >= requirementValue(t, bondCharms))
      if (candidate && rng.chance(techniqueChancePct(m, candidate, elderMentor, bondCharms))) {
        p.learned = candidate.id
        technique = candidate.id
        if (isFull(m)) {
          needsForget = true
          p.pendingTechnique = candidate.id
        } else {
          m.techniques.push({ id: candidate.id, uses: 0, level: 1 })
        }
      }
    }
  }

  m.fatigue = addCondition(m.fatigue, JOURNEY.fatiguePerWeek)
  m.stress = addCondition(m.stress, JOURNEY.stressPerWeek)
  p.weekNo += 1
  return { monster: m, progress: p, result: { week, success, score, gains, technique, needsForget } }
}

export function techniqueName(id: string): string {
  return TECHNIQUE_BY_ID[id]?.name ?? id
}

/** The Mentor's Charm item of a site (§11 mentor bond). */
export function bondCharmId(site: JourneySiteId): string {
  return `mentor-charm-${site}`
}

/** Journey cost this month: half price in sale months (§11). */
export function journeyCost(saleMonths: readonly number[], month: number): number {
  return saleMonths.includes(month) ? JOURNEY.saleCost : JOURNEY.cost
}

/** Two distinct sale months for a year, rolled from the game's RNG in January. */
export function rollSaleMonths(rng: Rng): number[] {
  const months = rng.shuffle(Array.from({ length: 12 }, (_, i) => i + 1))
  return months.slice(0, JOURNEY.saleMonthsPerYear).sort((a, b) => a - b)
}

/** §10.4: a monster entering Prime with loyalty ≥ 60 learns its Signature (null when it can't right now). */
export function signatureAtPrime(m: Monster): Technique | null {
  if (loyaltyOf(m) < SIGNATURE.loyaltyMin) return null
  const sig = techniquesOfBreed(m.mainBreed).find((t) => t.family === 'Signature')
  if (!sig || m.techniques.some((t) => t.id === sig.id) || isFull(m)) return null
  return sig
}

/** The Trial opponent (§11): a wild monster of the site's breed at your grade, or one up half the time. */
export function trialOpponent(m: Monster, site: JourneySiteId, rng: Rng): Monster {
  const breed = JOURNEY_SITE_BY_ID[site].trialBreeds[0]
  const gi = TOURNAMENT_GRADES.indexOf(m.grade)
  const up = rng.chance(JOURNEY.trial.gradeUpPct) ? 1 : 0
  const grade = TOURNAMENT_GRADES[Math.min(TOURNAMENT_GRADES.length - 1, gi + up)]!
  return npcMonster({ breed, grade, seed: rng.nextU32(), name: `Wild ${JOURNEY_SITE_BY_ID[site].trialBreeds[0]}` })
}

/** The Trial's purse for a win: 600 × gradeIndex. */
export function trialReward(m: Monster): number {
  return JOURNEY.trial.rewardPerGrade * (TOURNAMENT_GRADES.indexOf(m.grade) + 1)
}
