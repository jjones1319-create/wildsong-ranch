import { FATIGUE_LABELS, LOYALTY_LABELS, STRESS_LABELS } from '../data/text/labels.ts'
import { BREAKDOWN, DIFFICULTY, EXPRESSION, ILLNESS, LABEL_BANDS, LIFESPAN, RANGES, STAGES, STRAIN } from '../data/tuning.ts'
import { STAT_KEYS, type Difficulty } from '../data/types.ts'
import { clamp } from './mathx.ts'
import { addCondition, isPrimeStage, loyaltyOf, stageOf, strainOf, weeksLeft, type Monster } from './monster.ts'
import type { Rng } from './rng.ts'
import { WEEKS_PER_YEAR } from './calendar.ts'
import { variantBirthdayRelief } from './variants.ts'

/** GAME_DESIGN §6.6 and §7: strain, illness, breakdowns, the weekly aging tick, warnings and labels. */

export type AgingEvent =
  | { kind: 'illness' }
  | { kind: 'breakdown'; type: 'runAway' | 'collapse'; fee: number }
  | { kind: 'returned'; from: 'missing' | 'clinic' | 'sick' | 'injured' | 'cocoon' }
  | { kind: 'warning'; which: 'quarterLife' | 'w48' | 'w10' }
  | { kind: 'prime' }
  | { kind: 'pastPrime' }
  | { kind: 'endOfLife'; how: 'passed' | 'retired' }
  /** CONTENT §12 Party Bloatoad: stress relief on a birthday. */
  | { kind: 'birthday'; relief: number }

/** §6.6 ladder: 0 below 80 strain; 80–124 → 1, 125–169 → 2, 170+ → 3 (Gentle caps at 1; Classic adds a step, cap 4). */
export function extraLifespanLoss(strain: number, difficulty: Difficulty = 'Standard'): number {
  if (strain < STRAIN.threshold) return 0
  const d = DIFFICULTY[difficulty]
  const base = 1 + Math.floor((strain - STRAIN.threshold) / STRAIN.step)
  return Math.min(d.strainCap, base + d.strainExtraStep)
}

/**
 * The proposed smooth rule (tuning STRAIN.mode = 'debt'): strain above the threshold piles up as debt, and every
 * `perWeek` points of debt cost one week of life. Gentle piles up half as fast, Classic a quarter faster.
 */
export function strainDebtStep(debt: number, strain: number, difficulty: Difficulty = 'Standard'): { debt: number; loss: number } {
  const d = DIFFICULTY[difficulty]
  const pct = difficulty === 'Gentle' ? STRAIN.debt.gentlePct : difficulty === 'Classic' ? STRAIN.debt.classicPct : 100
  const base = Math.max(0, strain - STRAIN.debt.threshold)
  const tail = STRAIN.debt.tailDiv + Math.max(0, strain - STRAIN.debt.tailFrom)
  const over = Math.floor((Math.floor((base * tail) / STRAIN.debt.tailDiv) * pct) / 100)
  let total = debt + over
  const loss = Math.min(d.strainCap, Math.floor(total / STRAIN.debt.perWeek))
  total -= loss * STRAIN.debt.perWeek
  return { debt: total, loss }
}

export interface TickResult {
  monster: Monster
  events: AgingEvent[]
  /** Lifespan weeks lost this week to strain, illness and breakdowns. */
  lifespanLost: number
  /** Gold owed for a breakdown (search fee or clinic). */
  fees: number
}

/**
 * The end-of-week tick (§3 step 6): age +1, strain loss, timers, illness check, breakdown check, warnings,
 * prime notices and the end of life. RNG order: illness (only at fatigue ≥ 90), breakdown trigger (only at
 * strain ≥ 200), breakdown type.
 */
export function endOfWeekTick(input: Monster, difficulty: Difficulty, rng: Rng): TickResult {
  const m = structuredClone(input)
  const events: AgingEvent[] = []
  let lifespanLost = 0
  let fees = 0
  const d = DIFFICULTY[difficulty]

  m.ageWeeks += 1
  const relief = variantBirthdayRelief(m)
  if (relief > 0 && m.ageWeeks % WEEKS_PER_YEAR === 0) {
    m.stress = addCondition(m.stress, -relief)
    events.push({ kind: 'birthday', relief })
  }
  let strainLoss: number
  if (STRAIN.mode === 'debt') {
    const step = strainDebtStep(m.status.strainDebt, strainOf(m), difficulty)
    m.status.strainDebt = step.debt
    strainLoss = step.loss
  } else {
    strainLoss = extraLifespanLoss(strainOf(m), difficulty)
  }
  m.lifespanTotal = clamp(m.lifespanTotal - strainLoss, RANGES.lifespan.min, RANGES.lifespan.max)
  lifespanLost += strainLoss

  for (const k of STAT_KEYS) {
    const left = m.status.tonics[k]
    if (left === undefined) continue
    if (left <= 1) delete m.status.tonics[k]
    else m.status.tonics[k] = left - 1
  }
  const tickDown = (key: 'sickWeeks' | 'injuredWeeks' | 'missingWeeks' | 'clinicWeeks' | 'cocoonWeeks', from: AgingEvent & { kind: 'returned' } extends infer R ? (R extends { from: infer F } ? F : never) : never) => {
    if (m.status[key] > 0) {
      m.status[key] -= 1
      if (m.status[key] === 0) events.push({ kind: 'returned', from })
    }
  }
  tickDown('sickWeeks', 'sick')
  tickDown('injuredWeeks', 'injured')
  tickDown('missingWeeks', 'missing')
  tickDown('clinicWeeks', 'clinic')
  tickDown('cocoonWeeks', 'cocoon')

  if (m.status.sickWeeks === 0 && m.fatigue >= ILLNESS.fatigueMin && rng.chance(ILLNESS.chancePct)) {
    m.status.sickWeeks = ILLNESS.weeks
    m.lifespanTotal = clamp(m.lifespanTotal - ILLNESS.lifespanLoss, RANGES.lifespan.min, RANGES.lifespan.max)
    lifespanLost += ILLNESS.lifespanLoss
    events.push({ kind: 'illness' })
  }

  if (m.status.missingWeeks === 0 && m.status.clinicWeeks === 0 && strainOf(m) >= BREAKDOWN.strainMin && rng.chance(d.breakdownPct)) {
    if (rng.chance(50)) {
      const r = BREAKDOWN.runAway
      m.status.missingWeeks = r.weeks
      m.fatigue = r.fatigueAfter
      m.stress = r.stressAfter
      m.spoil = addCondition(m.spoil, r.spoil)
      m.fear = addCondition(m.fear, r.fear)
      fees += r.fee
      events.push({ kind: 'breakdown', type: 'runAway', fee: r.fee })
    } else {
      const c = BREAKDOWN.collapse
      m.status.clinicWeeks = c.weeks
      m.fatigue = c.fatigueAfter
      m.stress = c.stressAfter
      m.lifespanTotal = clamp(m.lifespanTotal - c.lifespanLoss, RANGES.lifespan.min, RANGES.lifespan.max)
      lifespanLost += c.lifespanLoss
      fees += c.fee
      events.push({ kind: 'breakdown', type: 'collapse', fee: c.fee })
    }
  }

  if (m.ageWeeks >= m.lifespanTotal) {
    events.push({ kind: 'endOfLife', how: d.endOfLife === 'retire' ? 'retired' : 'passed' })
    return { monster: m, events, lifespanLost, fees }
  }

  const left = weeksLeft(m)
  if (!m.status.warnedQuarterLife && left * 100 <= LIFESPAN.warnAtRemainingPct * m.lifespanTotal) {
    m.status.warnedQuarterLife = true
    events.push({ kind: 'warning', which: 'quarterLife' })
  }
  if (!m.status.warned48 && left <= LIFESPAN.warnAtWeeksLeft[0]!) {
    m.status.warned48 = true
    events.push({ kind: 'warning', which: 'w48' })
  }
  if (!m.status.warned10 && left <= LIFESPAN.warnAtWeeksLeft[1]!) {
    m.status.warned10 = true
    events.push({ kind: 'warning', which: 'w10' })
  }
  const stage = stageOf(m)
  if (!m.status.announcedPrime && isPrimeStage(stage)) {
    m.status.announcedPrime = true
    events.push({ kind: 'prime' })
  }
  if (!m.status.announcedPastPrime && stage >= STAGES.pastPrime) {
    m.status.announcedPastPrime = true
    events.push({ kind: 'pastPrime' })
  }
  return { monster: m, events, lifespanLost, fees }
}

/** Which actions a monster's condition allows this week. */
export function availability(m: Monster): { locked: boolean; restOnly: boolean; reason: 'missing' | 'clinic' | 'cocoon' | 'sick' | 'injured' | null } {
  if (m.status.missingWeeks > 0) return { locked: true, restOnly: false, reason: 'missing' }
  if (m.status.clinicWeeks > 0) return { locked: true, restOnly: false, reason: 'clinic' }
  if (m.status.cocoonWeeks > 0) return { locked: true, restOnly: false, reason: 'cocoon' }
  if (m.status.sickWeeks > 0) return { locked: false, restOnly: true, reason: 'sick' }
  if (m.status.injuredWeeks > 0) return { locked: false, restOnly: true, reason: 'injured' }
  return { locked: false, restOnly: false, reason: null }
}

function bandIndex(value: number, upperBounds: readonly number[]): number {
  for (let i = 0; i < upperBounds.length; i++) if (value <= upperBounds[i]!) return i
  return upperBounds.length
}

export function fatigueLabel(fatigue: number): string {
  return FATIGUE_LABELS[bandIndex(fatigue, LABEL_BANDS.fatigue)]!
}
export function stressLabel(stress: number): string {
  return STRESS_LABELS[bandIndex(stress, LABEL_BANDS.stress)]!
}
export function loyaltyLabel(loyalty: number): string {
  return LOYALTY_LABELS[bandIndex(loyalty, LABEL_BANDS.loyalty)]!
}

export type ExpressionCue = 'droopy' | 'sweat' | 'sparkle' | 'sick' | 'grin'

/** §6.6 expression cues, in display priority order. */
export function expressionCues(m: Monster): ExpressionCue[] {
  const cues: ExpressionCue[] = []
  if (m.status.sickWeeks > 0) cues.push('sick')
  if (m.fatigue >= EXPRESSION.droopyFatigue) cues.push('droopy')
  if (m.stress >= EXPRESSION.sweatStress) cues.push('sweat')
  if (loyaltyOf(m) >= EXPRESSION.sparkleLoyalty) cues.push('sparkle')
  if (m.nature <= EXPRESSION.grinNature) cues.push('grin')
  return cues
}
