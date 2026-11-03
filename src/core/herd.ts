import { DRILL_BY_ID } from '../data/drills.ts'
import { FOOD_BY_ID } from '../data/foods.ts'
import { fill } from '../data/text/format.ts'
import { LEGACY_TEXT } from '../data/text/legacy.ts'
import { FARM, HERD, UPGRADES } from '../data/tuning.ts'
import type { FoodId } from '../data/types.ts'
import { availability, endOfWeekTick, type AgingEvent } from './aging.ts'
import { fadeBond, keepsakeStress } from './bond.ts'
import { dateOf, seasonOf } from './calendar.ts'
import { hasPerk } from './farm.ts'
import { applyMonthlyFood } from './food.ts'
import { charmValue } from './items.ts'
import { signatureAtPrime } from './journey.ts'
import { pruneFriendshipsMut, retireToMemorialMut } from './legacy.ts'
import { divRound } from './mathx.ts'
import { addCondition, type Monster } from './monster.ts'
import { isGoodOutcome } from './outcomes.ts'
import type { Rng } from './rng.ts'
import { learnTechnique } from './songbook.ts'
import type { GameState, Heartstone, MateLast, MateOrder, MateRestReason } from './state.ts'
import { applyReaction, playMonster, resolveDrill, restMonster } from './training.ts'

export { makeStar, setOrder, penToFreezer, freezerToPen, freeMonster, replaceRanchmate } from './herdMoves.ts'
export type { StarRefusal, OrderRefusal, MoveRefusal, FreeRefusal } from './herdMoves.ts'

/**
 * GAME_DESIGN §6.11 the herd (v16): ranch-mates live in pens beside the star. Each week they follow a standing
 * order (train a drill, rest or play), rest by themselves when they need it, earn half a drill's pay, eat the
 * month's food, age, reach Prime and learn their Signature, and pass away gently. The star's week is untouched:
 * the herd runs after it, from its own random stream (week.ts draws one number for it, only when there is a herd).
 */

/** One ranch-mate's week, for the summary and the herd strip's badges. */
export interface MateReport {
  id: string
  name: string
  last: MateLast
  /** The aging tick's events (illness, breakdowns, returns, warnings, Prime, the end of life…). */
  aging: AgingEvent[]
  /** The Signature learned at Prime this week. */
  signature: string | null
  /** Its life ended this week: it is on the Memorial wall now (and in the Elder Grove when it retired). */
  ended: 'passed' | 'retired' | null
  heartstone: Heartstone | null
  heartstoneLost: boolean
  /** Its half of the drill's pay, and the breakdown fees it cost. */
  pay: number
  fees: number
}

/** The news worth a line in the week summary (and a planner stop); everything else is a badge. */
export type MateNews = 'illness' | 'ranOff' | 'collapsed' | 'cameBack' | 'clinicBack' | 'prime' | 'signature' | 'w48' | 'w10' | 'passed' | 'retired'

export function mateNews(r: MateReport): MateNews[] {
  const out: MateNews[] = []
  for (const e of r.aging) {
    if (e.kind === 'illness') out.push('illness')
    else if (e.kind === 'breakdown') out.push(e.type === 'runAway' ? 'ranOff' : 'collapsed')
    else if (e.kind === 'returned' && e.from === 'missing') out.push('cameBack')
    else if (e.kind === 'returned' && e.from === 'clinic') out.push('clinicBack')
    else if (e.kind === 'prime') out.push('prime')
    else if (e.kind === 'warning' && e.which === 'w48') out.push('w48')
    else if (e.kind === 'warning' && e.which === 'w10') out.push('w10')
  }
  if (r.signature) out.push('signature')
  if (r.ended) out.push(r.ended)
  return out
}

/** Why this ranch-mate rests instead of following its order (null: it follows the order). */
export function autoRestReason(state: Pick<GameState, 'upgrades'>, m: Monster, order: MateOrder): MateRestReason | null {
  const a = availability(m)
  if (a.reason === 'sick' || a.reason === 'injured') return a.reason
  if (m.fatigue >= HERD.autoRest.fatigue) return 'tired'
  if (m.stress >= HERD.autoRest.stress) return 'stressed'
  if (order.kind === 'drill') {
    const drill = DRILL_BY_ID[order.drill]
    if (!drill || (drill.needsTrainingYard && !state.upgrades.trainingYard)) return 'noYard'
  }
  return null
}

/* ---------- the start of the week (no randomness) ---------- */

/** One ranch-mate's share of a month's food: the price, or FARM.feedShedPct of it with the Feed Shed. */
export function mateFoodPrice(state: Pick<GameState, 'farm'>, food: FoodId): number {
  const price = FOOD_BY_ID[food].price
  return hasPerk(state, 'feedShed') ? divRound(price * FARM.feedShedPct, 100) : price
}

/** The month's food bill for the whole ranch: the star and every ranch-mate (the food prompt's "Feeds N · total"). */
export function monthlyFoodCost(state: Pick<GameState, 'farm' | 'ranchmates' | 'monster'>, food: FoodId): { mouths: number; total: number } {
  const star = state.monster ? 1 : 0
  return { mouths: star + state.ranchmates.length, total: star * FOOD_BY_ID[food].price + state.ranchmates.length * mateFoodPrice(state, food) }
}

/** Month start: every ranch-mate eats the month's food (its own likes and dislikes apply). Returns what it cost. */
export function feedHerdMut(state: GameState): number {
  for (const r of state.ranchmates) r.monster = applyMonthlyFood(r.monster, state.foodChoice).monster
  return state.ranchmates.length * mateFoodPrice(state, state.foodChoice)
}

/** Every week: the Cozy Barn (and the Tide Pool in summer) calm the ranch-mates as they calm the star. */
export function calmHerdMut(state: GameState): void {
  const summer = seasonOf(dateOf(state.week).month) === 'Summer'
  for (const r of state.ranchmates) {
    if (state.upgrades.cozyBarn) r.monster.stress = addCondition(r.monster.stress, -UPGRADES.cozyBarnStress)
    if (state.upgrades.tidePool && summer) r.monster.stress = addCondition(r.monster.stress, -UPGRADES.tidePoolSummerStress)
  }
}

/* ---------- the end of the week ---------- */

/** One week of the ranch-mate's order (or its rest, or its time away). */
function actMut(state: GameState, m: Monster, order: MateOrder, rng: Rng): { monster: Monster; last: MateLast; pay: number } {
  const a = availability(m)
  if (a.locked) return { monster: m, last: { kind: 'away', reason: a.reason as 'missing' | 'clinic' | 'cocoon' }, pay: 0 }
  const bedding = { beddingBonus: charmValue(state.inventory, 'bedding') }
  if (order.kind === 'rest') return { monster: restMonster(m, bedding).monster, last: { kind: 'rest' }, pay: 0 }
  const why = autoRestReason(state, m, order)
  if (why) return { monster: restMonster(m, bedding).monster, last: { kind: 'autoRest', reason: why }, pay: 0 }
  if (order.kind === 'play') return { monster: playMonster(m).monster, last: { kind: 'play' }, pay: 0 }
  const r = resolveDrill(m, order.drill, rng, { trainingYard: state.upgrades.trainingYard })
  // Nobody is there to praise or scold a ranch-mate, unless the farm has a Farmhand (good drills get praised).
  const reaction = hasPerk(state, 'farmhand') && isGoodOutcome(r.result.outcome) ? 'praise' : 'skip'
  const pay = Math.floor((r.result.pay * HERD.payPct) / 100)
  return {
    monster: applyReaction(r.monster, r.result.outcome, reaction),
    last: { kind: 'drill', drill: order.drill, outcome: r.result.outcome, gains: r.result.gains, pay },
    pay,
  }
}

/**
 * The herd's week, after the star's (§6.11). For each ranch-mate, in pen order: its order (or a rest, or time away),
 * the bond boost fading, the aging tick (fees join the ranch's fee line), the keepsakes' calm, the Signature at
 * Prime, and at the end of its life a quiet move to the Memorial. Mutates `state` (money included); returns the
 * reports. Uses only `rng`, a sub-stream the caller seeded from the game's RNG.
 */
export function tickHerdMut(state: GameState, rng: Rng): MateReport[] {
  const reports: MateReport[] = []
  const calm = keepsakeStress(state.keepsakes)
  for (const mate of [...state.ranchmates]) {
    const acted = actMut(state, mate.monster, mate.order, rng)
    state.money += acted.pay
    const tick = endOfWeekTick(fadeBond(acted.monster), state.difficulty, rng)
    let m = tick.monster
    if (calm > 0 && m.stress > 0) m.stress = addCondition(m.stress, -calm)
    state.money -= tick.fees
    let signature: string | null = null
    if (tick.events.some((e) => e.kind === 'prime')) {
      const sig = signatureAtPrime(m)
      if (sig) {
        const learned = learnTechnique(m, sig.id)
        if (learned.status === 'learned') {
          m = learned.monster
          signature = sig.id
        }
      }
    }
    mate.monster = m
    mate.last = acted.last
    const end = tick.events.find((e) => e.kind === 'endOfLife')
    const report: MateReport = { id: m.id, name: m.name, last: acted.last, aging: tick.events, signature, ended: null, heartstone: null, heartstoneLost: false, pay: acted.pay, fees: tick.fees }
    if (end && end.kind === 'endOfLife') {
      state.ranchmates = state.ranchmates.filter((r) => r !== mate)
      const epitaph = fill(LEGACY_TEXT.farewell.epitaphDefault, { name: m.name, food: FOOD_BY_ID[m.likes.food].name })
      const kept = retireToMemorialMut(state, m, end.how, epitaph)
      report.ended = end.how
      report.heartstone = kept.heartstone
      report.heartstoneLost = kept.heartstoneLost
    }
    reports.push(report)
  }
  if (reports.some((r) => r.ended)) pruneFriendshipsMut(state)
  return reports
}
