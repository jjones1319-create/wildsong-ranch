import { HEAVY_DRILLS, LIGHT_DRILLS } from '../../data/drills.ts'
import { FOOD_IDS, type BreedId, type Difficulty, type FoodId, type Grades, type Stats } from '../../data/types.ts'
import { WEEKS_PER_YEAR } from '../calendar.ts'
import { addItems } from '../items.ts'
import { createMonster, loyaltyOf, rollLikes, totalStats, type Likes, type Monster } from '../monster.ts'
import { createRng } from '../rng.ts'
import { createGameState, type GameState } from '../state.ts'
import type { DrillOutcome } from '../training.ts'
import { allowedActions, runWeek, useItemInGame, type WeekAction, type WeekEvent, type WeekPolicy } from '../week.ts'

/**
 * Whole-life simulator for the §26 balance targets and the `npm run sim:life` tool.
 * It plays a scripted care policy week after week until the monster's life ends. Money is ignored
 * (items are conjured as needed) because the targets measure care, not the economy.
 */

export type PolicyName = 'Great' | 'Good' | 'OK' | 'Neglect'

export interface CarePolicy {
  name: string
  /** Rest when fatigue reaches this. */
  restAt: number
  /** Use stress items when stress reaches this (null = never). */
  stressItemAt: number | null
  /** 'tea' = one Calmleaf Tea (halves stress); 'sachets' = enough Lavender Sachets (−10 each) to clear it. */
  stressItem: 'tea' | 'sachets'
  food: 'liked' | 'neutral' | 'disliked'
  requests: 'accept' | 'half' | 'deny'
  /** Praise good outcomes and scold cheating; otherwise skip the prompt. */
  react: boolean
  /** Heavy drills only when fatigue is at most this; otherwise light drills. */
  heavyAtMostFatigue: number
}

/**
 * GAME_DESIGN §26 care policies. The doc fixes the rest and item thresholds, the food and the request habit;
 * the rest is our reading of a scripted player: praise good drills and scold cheating (except under Neglect),
 * clear stress with sachets, and use a heavy drill only right after a rest (fatigue at most restAt − 25).
 * This reading reproduces the doc's stat-total and outcome-rate targets closely.
 */
export const POLICIES: Record<PolicyName, CarePolicy> = {
  Great: { name: 'Great', restAt: 45, stressItemAt: 30, stressItem: 'sachets', food: 'liked', requests: 'accept', react: true, heavyAtMostFatigue: 20 },
  Good: { name: 'Good', restAt: 55, stressItemAt: 40, stressItem: 'sachets', food: 'liked', requests: 'accept', react: true, heavyAtMostFatigue: 30 },
  OK: { name: 'OK', restAt: 65, stressItemAt: 55, stressItem: 'sachets', food: 'neutral', requests: 'half', react: true, heavyAtMostFatigue: 40 },
  Neglect: { name: 'Neglect', restAt: 80, stressItemAt: null, stressItem: 'sachets', food: 'disliked', requests: 'deny', react: false, heavyAtMostFatigue: 55 },
}

export interface LifeSimOptions {
  breed: BreedId
  sub?: BreedId
  policy: PolicyName | CarePolicy
  seed: number
  difficulty?: Difficulty
  /** Override growth grades (to model "a Late bloomer with A/B grades"). */
  grades?: Partial<Grades>
  likes?: Likes
  /** Safety stop. */
  maxWeeks?: number
  /** Keep a one-line log per week. */
  weekly?: boolean
}

export interface YearSummary {
  year: number
  total: number
  stats: Stats
  fatigueAvg: number
  stressAvg: number
  loyalty: number
  outcomes: Record<DrillOutcome, number>
  drills: number
  rests: number
  breakdowns: number
}

export interface LifeReport {
  breed: BreedId
  sub: BreedId
  policy: string
  seed: number
  lifespanAtBirth: number
  weeksLived: number
  /** Weeks lived as a percentage of the lifespan at birth. */
  lifeLivedPct: number
  endedBy: 'passed' | 'retired' | 'limit'
  birthStats: Stats
  finalStats: Stats
  finalTotal: number
  finalLoyalty: number
  years: YearSummary[]
  outcomes: Record<DrillOutcome, number>
  drills: number
  rests: number
  plays: number
  journeys: number
  breakdowns: number
  illnesses: number
  requestsAccepted: number
  requestsDenied: number
  itemsUsed: number
  lines: string[]
}

const emptyOutcomes = (): Record<DrillOutcome, number> => ({ Great: 0, Success: 0, Cheat: 0, Fail: 0, Slacked: 0 })

function neutralFoodFor(m: Monster): FoodId {
  return FOOD_IDS.find((f) => f !== m.likes.food && f !== m.likes.dislikedFood && f !== 'turnips') ?? 'river-fish'
}

export function simulateLife(opts: LifeSimOptions): LifeReport {
  const policy = typeof opts.policy === 'string' ? POLICIES[opts.policy] : opts.policy
  const rng = createRng(opts.seed)
  const sub = opts.sub ?? opts.breed
  const likes = opts.likes ?? rollLikes(rng)
  const monster = createMonster({ id: `sim-${opts.seed}`, mainBreed: opts.breed, subBreed: sub, likes })
  if (opts.grades) Object.assign(monster.grades, opts.grades)
  let state: GameState = createGameState({ monster, difficulty: opts.difficulty ?? 'Standard' })
  state.foodChoice = policy.food === 'liked' ? monster.likes.food : policy.food === 'disliked' ? monster.likes.dislikedFood : neutralFoodFor(monster)

  const report: LifeReport = {
    breed: opts.breed,
    sub,
    policy: policy.name,
    seed: opts.seed,
    lifespanAtBirth: monster.lifespanTotal,
    weeksLived: 0,
    lifeLivedPct: 0,
    endedBy: 'limit',
    birthStats: { ...monster.stats },
    finalStats: { ...monster.stats },
    finalTotal: totalStats(monster.stats),
    finalLoyalty: loyaltyOf(monster),
    years: [],
    outcomes: emptyOutcomes(),
    drills: 0,
    rests: 0,
    plays: 0,
    journeys: 0,
    breakdowns: 0,
    illnesses: 0,
    requestsAccepted: 0,
    requestsDenied: 0,
    itemsUsed: 0,
    lines: [],
  }

  let lightIndex = 0
  let heavyIndex = 0
  let requestCounter = 0
  let year = { fatigue: 0, stress: 0, weeks: 0, outcomes: emptyOutcomes(), drills: 0, rests: 0, breakdowns: 0 }

  const weekPolicy: WeekPolicy = {
    food: () => state.foodChoice,
    request: () => {
      if (policy.requests === 'accept') return true
      if (policy.requests === 'deny') return false
      requestCounter += 1
      return requestCounter % 2 === 1
    },
    beforeAction: (s) => {
      const m = s.monster
      if (!m || policy.stressItemAt === null || m.stress < policy.stressItemAt) return s
      const item = policy.stressItem === 'tea' ? 'calmleaf-tea' : 'lavender-sachet'
      const qty = policy.stressItem === 'tea' ? 1 : Math.ceil(m.stress / 10)
      const stocked = { ...s, inventory: addItems(s.inventory, item, qty) }
      const r = useItemInGame(stocked, item, qty)
      if (r.used > 0) report.itemsUsed += r.used
      return r.state
    },
    action: (s): WeekAction => {
      const m = s.monster
      if (!m) return { kind: 'none' }
      const allowed = allowedActions(s)
      if (allowed.locked) return { kind: 'none' }
      if (allowed.restOnly || m.fatigue >= policy.restAt) return { kind: 'rest' }
      if (m.fatigue <= policy.heavyAtMostFatigue) {
        const heavy = HEAVY_DRILLS.filter((d) => !d.needsTrainingYard)
        const d = heavy[heavyIndex % heavy.length]!
        heavyIndex += 1
        return { kind: 'drill', drill: d.id }
      }
      const d = LIGHT_DRILLS[lightIndex % LIGHT_DRILLS.length]!
      lightIndex += 1
      return { kind: 'drill', drill: d.id }
    },
    reaction: (_s, r) => {
      if (!policy.react) return 'skip'
      return r.outcome === 'Cheat' || r.outcome === 'Slacked' ? 'scold' : 'praise'
    },
  }

  const maxWeeks = opts.maxWeeks ?? 2500
  while (!state.ended && state.week < maxWeeks) {
    const beforeWeek = state.week
    const r = runWeek(state, rng, weekPolicy)
    state = r.state
    tally(r.events)
    const m = state.monster!
    year.fatigue += m.fatigue
    year.stress += m.stress
    year.weeks += 1
    if (opts.weekly) report.lines.push(describeWeek(beforeWeek, r.events, m))
    if (state.week % WEEKS_PER_YEAR === 0 || state.ended) closeYear(m)
  }

  const final = state.monster!
  report.weeksLived = final.ageWeeks
  report.lifeLivedPct = Math.round((final.ageWeeks * 1000) / report.lifespanAtBirth) / 10
  report.endedBy = state.ended ?? 'limit'
  report.finalStats = { ...final.stats }
  report.finalTotal = totalStats(final.stats)
  report.finalLoyalty = loyaltyOf(final)
  return report

  function tally(events: WeekEvent[]) {
    for (const e of events) {
      if (e.kind === 'drill') {
        report.outcomes[e.result.outcome] += 1
        year.outcomes[e.result.outcome] += 1
        report.drills += 1
        year.drills += 1
      } else if (e.kind === 'rest') {
        report.rests += 1
        year.rests += 1
      } else if (e.kind === 'play') report.plays += 1
      else if (e.kind === 'journeyStart') report.journeys += 1
      else if (e.kind === 'request') {
        /* answered below */
      } else if (e.kind === 'requestDenied') report.requestsDenied += 1
      else if (e.kind === 'aging') {
        if (e.event.kind === 'breakdown') {
          report.breakdowns += 1
          year.breakdowns += 1
        }
        if (e.event.kind === 'illness') report.illnesses += 1
      }
    }
    const asked = events.filter((e) => e.kind === 'request').length
    const denied = events.filter((e) => e.kind === 'requestDenied').length
    report.requestsAccepted += asked - denied
  }

  function closeYear(m: Monster) {
    if (year.weeks === 0) return
    report.years.push({
      year: report.years.length + 1,
      total: totalStats(m.stats),
      stats: { ...m.stats },
      fatigueAvg: Math.round(year.fatigue / year.weeks),
      stressAvg: Math.round(year.stress / year.weeks),
      loyalty: loyaltyOf(m),
      outcomes: year.outcomes,
      drills: year.drills,
      rests: year.rests,
      breakdowns: year.breakdowns,
    })
    year = { fatigue: 0, stress: 0, weeks: 0, outcomes: emptyOutcomes(), drills: 0, rests: 0, breakdowns: 0 }
  }
}

function describeWeek(week: number, events: WeekEvent[], m: Monster): string {
  const parts: string[] = []
  for (const e of events) {
    if (e.kind === 'food') parts.push(`food ${e.food}${e.bored ? ' (bored)' : ''}`)
    if (e.kind === 'request') parts.push(`asks ${e.request.kind}`)
    if (e.kind === 'requestDenied') parts.push('denied')
    if (e.kind === 'item') parts.push(`item ${e.itemId}`)
    if (e.kind === 'drill') parts.push(`${e.result.drill} ${e.result.outcome}${Object.keys(e.result.gains).length ? ' ' + Object.entries(e.result.gains).map(([k, v]) => `${k}${v! >= 0 ? '+' : ''}${v}`).join(' ') : ''}`)
    if (e.kind === 'reaction') parts.push(e.reaction)
    if (e.kind === 'rest') parts.push('rest')
    if (e.kind === 'play') parts.push('play')
    if (e.kind === 'forcedRest') parts.push(`forced rest (${e.reason})`)
    if (e.kind === 'locked') parts.push(`away (${e.reason})`)
    if (e.kind === 'aging') {
      if (e.event.kind === 'breakdown') parts.push(`BREAKDOWN ${e.event.type}`)
      if (e.event.kind === 'illness') parts.push('SICK')
      if (e.event.kind === 'warning') parts.push(`warning ${e.event.which}`)
      if (e.event.kind === 'prime') parts.push('PRIME')
      if (e.event.kind === 'pastPrime') parts.push('past prime')
      if (e.event.kind === 'endOfLife') parts.push(`END (${e.event.how})`)
    }
  }
  return `wk ${String(week + 1).padStart(3)} | F${String(m.fatigue).padStart(3)} S${String(m.stress).padStart(3)} L${String(loyaltyOf(m)).padStart(3)} | total ${String(totalStats(m.stats)).padStart(4)} | ${parts.join(', ')}`
}

/** Average of a field over several seeds. */
export function averageReports(reports: LifeReport[]): { lifeLivedPct: number; finalTotal: number; outcomesPct: Record<DrillOutcome, number>; breakdowns: number; totalsByYear: number[] } {
  const n = reports.length
  const outcomes = emptyOutcomes()
  let drills = 0
  let life = 0
  let total = 0
  let breakdowns = 0
  const yearTotals: number[][] = []
  for (const r of reports) {
    life += r.lifeLivedPct
    total += r.finalTotal
    breakdowns += r.breakdowns
    drills += r.drills
    for (const k of Object.keys(outcomes) as DrillOutcome[]) outcomes[k] += r.outcomes[k]
    r.years.forEach((y, i) => {
      ;(yearTotals[i] ??= []).push(y.total)
    })
  }
  const outcomesPct = emptyOutcomes()
  for (const k of Object.keys(outcomes) as DrillOutcome[]) outcomesPct[k] = drills ? (outcomes[k] * 100) / drills : 0
  return {
    lifeLivedPct: life / n,
    finalTotal: total / n,
    outcomesPct,
    breakdowns: breakdowns / n,
    totalsByYear: yearTotals.map((ys) => ys.reduce((a, b) => a + b, 0) / ys.length),
  }
}
