import { STARTING_UNLOCKED } from '../data/breeds.ts'
import type { BreedId } from '../data/types.ts'
import { DASH } from '../data/tuning.ts'
import { clamp, divRound } from './mathx.ts'
import { createRng, scrambleSeed, type Rng } from './rng.ts'
import type { GameState } from './state.ts'

/**
 * CONTENT §13 Odd Jobs: Meadow Dash, a tap-to-run race against three rival monsters. Each heat is simulated
 * here in fixed ticks (1/50 s) with integer distances, so a race replays exactly in a test; the UI only runs the
 * clock, feeds in the taps and draws. Each tap adds speed (a little more with SPD), the speed fades each tick,
 * and the player has a top speed; the rivals run steady paces that rise every heat, with a small wobble, and
 * have no top speed, so every run ends. Win a heat to run the next; the run ends at the first heat not won.
 * 25G per heat won, no cap, once per in-game week; practice pays nothing but keeps the best.
 */

export interface DashRunner {
  /** Distance from the start (hundredths of a millimetre). */
  pos: number
  /** Distance per tick. */
  v: number
}

export interface DashHeat {
  heat: number
  tick: number
  /** The speed one tap adds to the player (SPD included). */
  boost: number
  /** Lane 0 is the player; lanes 1–3 are the rivals. */
  runners: readonly DashRunner[]
  /** Each lane's position before the last tick, for drawing between ticks. */
  prev: readonly number[]
  /** Each rival's target speed per wobble segment. */
  targets: readonly (readonly number[])[]
  /** The rivals' breeds, lanes 1–3. */
  breeds: readonly BreedId[]
  /** The lane that crossed the line first, or null while the heat runs. */
  winner: number | null
}

export interface DashHeatOptions {
  runSeed: number
  heat: number
  spd: number
  unlocked: readonly BreedId[]
  ownBreed: BreedId
  relaxed: boolean
}

export type DashRefusal = 'noMonster' | 'played'

const RIVALS = 3

function whole(n: number): number {
  return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0
}

/** Each heat of a run gets its own seed from the run's. */
export function dashHeatSeed(runSeed: number, heat: number): number {
  return scrambleSeed((runSeed + Math.imul(heat, 0x9e3779b9)) >>> 0)
}

/** SPD adds up to 25% to each tap, in proportion (SPD 999 → 25). */
export function dashSpdBonusPct(spd: number): number {
  return Math.floor((clamp(whole(spd), 0, 999) * DASH.spdBonusMaxPct) / 999)
}

export function dashTapBoost(spd: number): number {
  return divRound(DASH.tapBoost * (100 + dashSpdBonusPct(spd)), 100)
}

/** The three rivals' paces in taps per ten seconds: the lead's rises every heat; Relaxed slows them all. */
export function dashRivalRatesX10(heat: number, relaxed: boolean): number[] {
  const lead = DASH.rivalRateX10.start + DASH.rivalRateX10.perHeat * (Math.max(1, whole(heat)) - 1)
  return DASH.rivalPct.map((pct) => {
    const rate = divRound(lead * pct, 100)
    return relaxed ? divRound(rate * DASH.relaxedPct, 100) : rate
  })
}

/** The speed that steady tapping at `rateX10` taps per ten seconds settles at (with no SPD bonus). */
export function dashTargetSpeed(rateX10: number): number {
  return divRound(DASH.tapBoost * rateX10 * 100, 10 * DASH.ticksPerSecond * DASH.dragPct)
}

function draw<T>(rng: Rng, bag: T[]): T {
  return bag.splice(rng.nextInt(0, bag.length - 1), 1)[0]!
}

/** Three different rival breeds from the unlocked ones (never the player's own), topped up from the starters. */
export function dashRivalBreeds(rng: Rng, unlocked: readonly BreedId[], ownBreed: BreedId): BreedId[] {
  const pool = [...new Set(unlocked)].filter((b) => b !== ownBreed)
  const spare = STARTING_UNLOCKED.filter((b) => b !== ownBreed && !pool.includes(b))
  const out: BreedId[] = []
  while (out.length < RIVALS && pool.length > 0) out.push(draw(rng, pool))
  while (out.length < RIVALS && spare.length > 0) out.push(draw(rng, spare))
  return out
}

export function createDashHeat(o: DashHeatOptions): DashHeat {
  const heat = Math.max(1, whole(o.heat))
  const rng = createRng(dashHeatSeed(o.runSeed, heat))
  const breeds = dashRivalBreeds(rng, o.unlocked, o.ownBreed)
  const rates = dashRivalRatesX10(heat, o.relaxed)
  // Which lane gets the lead's pace is shuffled.
  const lanes = [0, 1, 2]
  const order = [draw(rng, lanes), draw(rng, lanes), draw(rng, lanes)]
  const segments = Math.ceil(DASH.maxTicks / DASH.wobble.everyTicks) + 2
  const targets = order.map((i) => {
    const base = dashTargetSpeed(rates[i]!)
    const out: number[] = []
    while (out.length < segments) {
      const w = rng.nextInt(-DASH.wobble.pct, DASH.wobble.pct)
      out.push(divRound(base * (100 + w), 100), divRound(base * (100 - w), 100))
    }
    return out
  })
  const runners = Array.from({ length: RIVALS + 1 }, () => ({ pos: 0, v: 0 }))
  return { heat, tick: 0, boost: dashTapBoost(o.spd), runners, prev: runners.map(() => 0), targets, breeds, winner: null }
}

/** The lane that crossed first this tick: compares when each crossed, not how far past it ended up. Ties go to the lower lane (the player). */
function firstAcross(prev: readonly number[], runners: readonly DashRunner[]): number | null {
  let best: number | null = null
  for (let i = 0; i < runners.length; i++) {
    const r = runners[i]!
    if (r.pos < DASH.track) continue
    if (best === null) {
      best = i
      continue
    }
    const b = runners[best]!
    const restI = DASH.track - prev[i]!
    const restB = DASH.track - prev[best]!
    // i crossed earlier when restI / moveI < restB / moveB.
    if (restI * (b.pos - prev[best]!) < restB * (r.pos - prev[i]!)) best = i
  }
  return best
}

function furthest(runners: readonly DashRunner[]): number {
  let best = 0
  for (let i = 1; i < runners.length; i++) if (runners[i]!.pos > runners[best]!.pos) best = i
  return best
}

/**
 * One tick: the taps add speed to the player (up to the top speed), the rivals move toward their pace, everyone
 * runs, the player's speed fades, and the first across the line wins. Returns a new heat; a finished heat is returned as is.
 */
export function stepDash(h: DashHeat, taps: number): DashHeat {
  if (h.winner !== null) return h
  const prev = h.runners.map((r) => r.pos)
  const runners = h.runners.map((r) => ({ ...r }))
  const player = runners[0]!
  player.v = Math.min(DASH.vMax, player.v + whole(taps) * h.boost)
  for (let i = 1; i < runners.length; i++) {
    const rival = runners[i]!
    const schedule = h.targets[i - 1]!
    const target = schedule[Math.min(Math.floor(h.tick / DASH.wobble.everyTicks), schedule.length - 1)]!
    const gap = target - rival.v
    const step = Math.min(Math.abs(gap), Math.max(1, divRound(Math.abs(gap) * DASH.dragPct, 100)))
    rival.v += Math.sign(gap) * step
  }
  for (const r of runners) r.pos += r.v
  player.v = Math.max(0, player.v - Math.max(1, divRound(player.v * DASH.dragPct, 100)))
  const tick = h.tick + 1
  let winner = firstAcross(prev, runners)
  if (winner === null && tick >= DASH.maxTicks) winner = furthest(runners)
  return { ...h, tick, runners, prev, winner }
}

export function canPlayDash(state: GameState): { ok: true } | { ok: false; reason: DashRefusal } {
  if (!state.monster || state.ended) return { ok: false, reason: 'noMonster' }
  if (state.dashWeek !== null && state.dashWeek === state.week) return { ok: false, reason: 'played' }
  return { ok: true }
}

/** 25G per heat won, with no cap. */
export function dashPay(heatsWon: number): number {
  return whole(heatsWon) * DASH.payPerHeat
}

export interface DashResult {
  state: GameState
  pay: number
  /** True when this run set a new best (most heats won). */
  newBest: boolean
  refused: DashRefusal | null
}

/** Settles a run: a paid play pays per heat won and stamps the week; practice only records the best. */
export function applyDash(input: GameState, heatsWon: number, practice: boolean): DashResult {
  if (!input.monster || input.ended) return { state: input, pay: 0, newBest: false, refused: 'noMonster' }
  if (!practice) {
    const can = canPlayDash(input)
    if (!can.ok) return { state: input, pay: 0, newBest: false, refused: can.reason }
  }
  const heats = whole(heatsWon)
  const state = structuredClone(input)
  let pay = 0
  if (!practice) {
    pay = dashPay(heats)
    state.money += pay
    state.dashWeek = state.week
  }
  const newBest = heats > state.dashBest
  if (newBest) state.dashBest = heats
  return { state, pay, newBest, refused: null }
}
