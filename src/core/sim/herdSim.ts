import { HEAVY_DRILLS, LIGHT_DRILLS } from '../../data/drills.ts'
import type { BreedId, DrillId } from '../../data/types.ts'
import { isMonthStart, WEEKS_PER_YEAR } from '../calendar.ts'
import { newRanchmate } from '../creation.ts'
import { buyPen, farmLevelOf, farmWeek, nextPen, penCapacity } from '../farm.ts'
import { mateFoodPrice } from '../herd.ts'
import { addItems } from '../items.ts'
import { pruneFriendshipsMut } from '../legacy.ts'
import { createMonster, rollLikes, totalStats, type Monster } from '../monster.ts'
import { createRng, type Rng } from '../rng.ts'
import { createGameState, type GameState, type MateOrder } from '../state.ts'
import { allowedActions, runWeek, useItemInGame, type WeekAction, type WeekPolicy } from '../week.ts'

/**
 * GAME_DESIGN §26 the herd targets (v1.21.0): a whole ranch, week after week, with a Good-care star (lifeSim's Good
 * policy: rest at fatigue 55, Lavender Sachets from stress 40, liked food, accept requests, praise and scold) and
 * ranch-mates on standing orders. When the star's life ends a new one of the same breed steps in, and a ranch-mate
 * that passes is replaced on the same order, so the ranch keeps going. As in lifeSim, money is not a limit (items and
 * pens are conjured); the herd's own gold (half pay, food, fees) is counted for the report.
 */

export type MatePlan = 'light' | 'heavy' | 'rest' | 'play'

export interface HerdSimOptions {
  seed: number
  breed?: BreedId
  mateBreed?: BreedId
  /** The ranch-mates' standing order: a light drill, a heavy drill, rest or play. */
  mates: MatePlan
  /** Build each pen as soon as the farm level allows, and fill it with a new ranch-mate on the same order. */
  buyPens?: boolean
  /** Scripted achievements the sim doesn't play itself (cups, Journeys, ranks, expeditions), counted by the farm. */
  achievements?: boolean
  /** Run exactly this many weeks; without it, the run lasts until the first star and the first ranch-mate have ended. */
  weeks?: number
}

export interface HerdReport {
  seed: number
  /** The first star: life lived vs its lifespan at birth, its stat total at the end of each year, how it ended. */
  star: { lifeLivedPct: number; totalsByYear: number[] }
  /** Every ranch-mate life that ended during the run (the first one first), as % of its lifespan at birth. */
  mateLives: number[]
  /** The farm level at the end of each year. */
  farmLevelByYear: number[]
  /** The herd's own gold (half pay − food − breakdown fees) per ranch-mate per month (4 weeks). */
  netGoldPerMateMonth: number
  /** Star drills a training partner joined, and friendship tiers reached. */
  partnerDrills: number
  tiersReached: number
  weeks: number
}

/**
 * A typical active year of the things this sim doesn't play (an assumption for the farm-level target, not a game
 * number): cups won, Journeys, a breeder rank, and an expedition from year 2.
 */
export const TYPICAL_YEAR = { cupsWon: 5, journeys: 1, rank: 1, maxRank: 8, expeditions: 1 } as const

const ORDERS: Record<MatePlan, MateOrder> = {
  light: { kind: 'drill', drill: 'log-toss' as DrillId },
  heavy: { kind: 'drill', drill: 'plow-pull' as DrillId },
  rest: { kind: 'rest' },
  play: { kind: 'play' },
}

/** lifeSim's Good care, for the star. */
function goodCare(): WeekPolicy {
  let light = 0
  let heavy = 0
  return {
    food: (s) => s.foodChoice,
    request: () => true,
    beforeAction: (s) => {
      const m = s.monster
      if (!m || m.stress < 40) return s
      const qty = Math.ceil(m.stress / 10)
      return useItemInGame({ ...s, inventory: addItems(s.inventory, 'lavender-sachet', qty) }, 'lavender-sachet', qty).state
    },
    action: (s): WeekAction => {
      const m = s.monster
      if (!m) return { kind: 'none' }
      const allowed = allowedActions(s)
      if (allowed.locked) return { kind: 'none' }
      if (allowed.restOnly || m.fatigue >= 55) return { kind: 'rest' }
      if (m.fatigue <= 30) {
        const list = HEAVY_DRILLS.filter((d) => !d.needsTrainingYard)
        return { kind: 'drill', drill: list[heavy++ % list.length]!.id }
      }
      return { kind: 'drill', drill: LIGHT_DRILLS[light++ % LIGHT_DRILLS.length]!.id }
    },
    reaction: (_s, r) => (r.outcome === 'Cheat' || r.outcome === 'Slacked' ? 'scold' : 'praise'),
  }
}

function born(id: string, breed: BreedId, rng: Rng): Monster {
  return createMonster({ id, mainBreed: breed, likes: rollLikes(rng) })
}

/** One ranch's run (see HerdSimOptions). Deterministic for a seed. */
export function simulateRanch(opts: HerdSimOptions): HerdReport {
  const breed = opts.breed ?? 'puddlepup'
  const mateBreed = opts.mateBreed ?? breed
  const order = ORDERS[opts.mates]
  const setup = createRng(opts.seed * 7919 + 17)
  const rng = createRng(opts.seed)
  const birthLife = new Map<string, number>()
  let made = 0
  const newMonster = (b: BreedId) => {
    const m = born(`h${opts.seed}-${made++}`, b, setup)
    birthLife.set(m.id, m.lifespanTotal)
    return m
  }
  const firstStar = newMonster(breed)
  let state: GameState = createGameState({ monster: firstStar })
  state.foodChoice = firstStar.likes.food
  const addMate = () => state.ranchmates.push({ ...newRanchmate(newMonster(mateBreed)), order })
  addMate()
  const firstMate = state.ranchmates[0]!.monster.id

  const policy = goodCare()
  const report: HerdReport = { seed: opts.seed, star: { lifeLivedPct: 0, totalsByYear: [] }, mateLives: [], farmLevelByYear: [], netGoldPerMateMonth: 0, partnerDrills: 0, tiersReached: 0, weeks: 0 }
  let starDone = false
  let mateDone = false
  let gold = 0
  let mateWeeks = 0
  const going = () => (opts.weeks !== undefined ? state.week < opts.weeks : !starDone || !mateDone)
  while (going() && state.week < 2500) {
    if (isMonthStart(state.week)) gold -= state.ranchmates.length * mateFoodPrice(state, state.foodChoice)
    mateWeeks += state.ranchmates.length
    const r = runWeek(state, rng, policy)
    state = farmWeek(r.state).state
    for (const e of r.events) {
      if (e.kind === 'drill' && e.result.buddy) report.partnerDrills += 1
      if (e.kind === 'friends') report.tiersReached += e.news.length
      if (e.kind !== 'herd') continue
      for (const x of e.reports) {
        gold += x.pay - x.fees
        if (!x.ended) continue
        const m = state.memorial.find((entry) => entry.monster.id === x.id)?.monster
        if (m) report.mateLives.push(Math.round((m.ageWeeks * 1000) / birthLife.get(m.id)!) / 10)
        if (x.id === firstMate) mateDone = true
      }
    }
    // The sim reads each passing from the Memorial once; dropping it keeps the weekly copies of the state small.
    state.memorial = []
    state.heartstones = []
    const star = state.monster!
    if (!starDone && state.week % WEEKS_PER_YEAR === 0) report.star.totalsByYear.push(totalStats(star.stats))
    if (state.week % WEEKS_PER_YEAR === 0) report.farmLevelByYear.push(farmLevelOf(state))
    if (opts.achievements && state.week % WEEKS_PER_YEAR === 0) scriptYear(state, state.week / WEEKS_PER_YEAR)
    if (state.ended) {
      if (!starDone) {
        starDone = true
        report.star.lifeLivedPct = Math.round((star.ageWeeks * 1000) / birthLife.get(star.id)!) / 10
        if (state.week % WEEKS_PER_YEAR !== 0) report.star.totalsByYear.push(totalStats(star.stats))
      }
      const next = newMonster(breed)
      state = { ...state, monster: next, ended: null, foodChoice: next.likes.food }
      pruneFriendshipsMut(state)
    }
    while (state.ranchmates.length < penCapacity(state)) addMate()
    const pen = nextPen(state)
    if (opts.buyPens && pen && farmLevelOf(state) >= pen.level) {
      state = buyPen({ ...state, money: Math.max(state.money, pen.price) }).state
      addMate()
    }
  }
  report.weeks = state.week
  report.netGoldPerMateMonth = mateWeeks > 0 ? Math.round((gold * 4) / mateWeeks) : 0
  return report
}

/** The year's scripted achievements (TYPICAL_YEAR), counted by the farm's tally next week. */
function scriptYear(state: GameState, year: number): void {
  const t = TYPICAL_YEAR
  state.records.cupsWon += t.cupsWon
  state.journeysBySite[Object.keys(state.journeysBySite)[0] as keyof GameState['journeysBySite']] += t.journeys
  state.breeder.rank = Math.min(t.maxRank, state.breeder.rank + t.rank)
  if (year >= 2) state.records.expeditionsDone += t.expeditions
}
