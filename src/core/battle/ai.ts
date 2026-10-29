import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI, BATTLE } from '../../data/tuning.ts'
import type { PlanMode, Technique } from '../../data/types.ts'
import { divRound } from '../mathx.ts'
import type { Rng } from '../rng.ts'
import { currentBand, effectiveCost, gapUnits, previewDamage, previewHitTenths, speedPerTick } from './engine.ts'
import { bandCentre, hpPctTenths } from './formulas.ts'
import { traitFreeDash, traitImmovable, traitsAny } from './traits.ts'
import type { BattleEvent, BattleState, FighterState, TechniqueRef } from './types.ts'

/**
 * GAME_DESIGN §12.10 AI 2.0 (M10): the CPU brain, the player's Auto mode and the Battle Lab.
 *
 * Every 8–12 ticks (or at once on an event: got hit, the opponent fired, guts crossed a technique cost,
 * became cornered or touching, 20 s or 10 s left) the fighter makes a **range plan**: it scores each band by
 * its own offense there, the opponent's threat there, variety and travel, picks a target band with hysteresis,
 * a sweet spot inside it (away from the opponent's best band) and a goal technique. Between plans it walks to
 * the sweet spot with small footsies, pushes when stuck together or cornered, dashes in with a reason, and
 * fires after a reaction delay: the goal technique when affordable, a cheap poke when that does not delay the
 * goal, anything when sitting on 90+ guts. Tiers (rookie / skilled / expert), NPC personalities, the player's
 * Auto style and the situation modifiers only move the multipliers; the rules of what a monster *can* do are
 * the engine's. Integer math, the injected RNG only, nothing read from the opponent's same-tick decisions.
 */

const CENTI = 100
const TPS = BATTLE.ticksPerSecond
const NEVER = -100_000
const BLOCKED = -1_000_000_000
const HABIT_DASH_PCT = 20

interface Option {
  tech: Technique
  ref: TechniqueRef
  cost: number
  /** hit × (damage as % of the target's max HP + 0.35 · wither) + 0.05 · sharp, ×1000. */
  ev: number
  /** EV weighted by how affordable it is over a guts budget (§12.10): a cheap poke counts fully, a Heavy partly. */
  rate: number
  /** EV adjusted by the §12.10 value rules (own techniques only; the opponent's keep their EV). */
  value: number
}

/** What a tick needs to know about the match, computed once per decision. */
interface Situation {
  tick: number
  gap: number
  band: number
  touching: boolean
  roomBehind: number
  cornered: boolean
  secondsLeft: number
  ahead: boolean
  behind: boolean
  /** The opponent cannot afford any technique, or is busy, dawdling or stunned. */
  punishWindow: boolean
  /** The opponent cannot afford any technique at all, or is low on guts: my hits land harder and more often, so fire. */
  oppBroke: boolean
  /** Hit within the last second. */
  beingPunished: boolean
  aheadLate: boolean
  behindLate: boolean
}

export interface RangePlan {
  /** Per band 1–4 (index 0 unused). */
  offense: number[]
  threat: number[]
  score: number[]
  /** The best band by score, 0 when none is reachable. */
  best: number
  /** The opponent's strongest band by threat, 0 when it has none. */
  oppBest: number
}

interface Computed extends RangePlan {
  kit: Option[]
  oppKit: Option[]
  weakClose: boolean
  safe: boolean
}

/* ---------- expected value ---------- */

/** EV = hit · (damage as % of the opponent's max HP + 0.35 · wither) + 0.05 · sharp, ×1000. */
function evOf(state: BattleState, f: FighterState, opp: FighterState, tech: Technique, ref: TechniqueRef): number {
  const hit = previewHitTenths(state, f.side, tech.id)
  let term: number
  if (tech.force > 0) {
    const dmg = previewDamage(f, opp, tech, ref.forceBonus)
    term = divRound(dmg * 100 * 1000, opp.maxHp) + AI.ev.witherWeight * 10 * (tech.wither + ref.witherBonus)
  } else {
    const healPct = tech.effect?.kind === 'heal' ? tech.effect.pct : 0
    term = divRound(healPct * 1000 * (f.maxHp - f.hp), f.maxHp)
  }
  return divRound(hit * term, 1000) + AI.ev.sharpWeight * 10 * tech.sharp
}

/** Guts regenerated per second, ×1000. */
function regenK(f: FighterState): number {
  return divRound(TPS * 1000, Math.max(1, f.gutsRate))
}

/** Guts regenerated over `ticks`. */
function regenOver(f: FighterState, ticks: number): number {
  return Math.floor(ticks / Math.max(1, f.gutsRate))
}

function kitOf(state: BattleState, f: FighterState, opp: FighterState): Option[] {
  const out: Option[] = []
  const budget = regenK(f) * AI.score.budgetSec
  for (const ref of f.techniques) {
    const tech = TECHNIQUE_BY_ID[ref.id]
    if (!tech) continue
    const cost = effectiveCost(f, tech)
    const ev = evOf(state, f, opp, tech, ref)
    const rate = divRound(ev * Math.min(1000, divRound(budget, Math.max(1, cost))), 1000)
    out.push({ tech, ref, cost, ev, rate, value: ev })
  }
  return out
}

function cheapestCost(f: FighterState): number {
  let best = Infinity
  for (const ref of f.techniques) {
    const tech = TECHNIQUE_BY_ID[ref.id]
    if (tech) best = Math.min(best, effectiveCost(f, tech))
  }
  return best === Infinity ? 0 : best
}

/** Bit i set when technique i is affordable; a change means a cost was crossed (an event). */
function affordMask(f: FighterState): number {
  let mask = 0
  for (let i = 0; i < f.techniques.length && i < 30; i++) {
    const tech = TECHNIQUE_BY_ID[f.techniques[i]!.id]
    if (tech && f.guts >= effectiveCost(f, tech)) mask |= 1 << i
  }
  return mask
}

function punishWindowOf(opp: FighterState): boolean {
  return opp.guts < cheapestCost(opp) || opp.busyTicks > 0 || opp.dawdleTicks > 0 || opp.stunTicks > 0
}

function situationOf(state: BattleState, f: FighterState, opp: FighterState): Situation {
  const tick = state.tick
  const gap = gapUnits(state)
  const roomBehind = BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius - Math.floor(Math.abs(f.x) / CENTI)
  const secondsLeft = Math.floor((state.timerTicks - tick) / TPS)
  const mine = hpPctTenths(f.hp, f.maxHp)
  const theirs = hpPctTenths(opp.hp, opp.maxHp)
  const ahead = mine > theirs
  const behind = mine < theirs
  const late = f.tier !== 'rookie'
  return {
    tick,
    gap,
    band: currentBand(state),
    touching: gap <= AI.stall.touchGap,
    roomBehind,
    cornered: roomBehind < AI.cornerUnits,
    secondsLeft,
    ahead,
    behind,
    punishWindow: punishWindowOf(opp),
    oppBroke: opp.guts < cheapestCost(opp) || opp.guts <= AI.guts.oppLowGuts,
    beingPunished: tick - f.lastHitTakenTick <= AI.guts.punishedTicks,
    aheadLate: late && ahead && secondsLeft <= AI.situations.aheadLate.secondsLeft,
    behindLate: late && behind && secondsLeft <= AI.situations.behindLate.secondsLeft,
  }
}

/* ---------- the range plan ---------- */

/** The sweet spot inside band `b`: the edge farthest from the opponent's best band, or the centre. */
function sweetSpot(b: number, oppBest: number): number {
  const lo = b === 1 ? AI.stall.touchGap + 1 : BATTLE.bandEnds[b - 2]!
  const hi = BATTLE.bandEnds[b - 1]! - 1
  if (oppBest === 0 || oppBest === b) return Math.max(lo, bandCentre(b))
  return oppBest < b ? hi - AI.sweetSpotInset : lo + AI.sweetSpotInset
}

/**
 * Ticks to reach a gap of `want`, capped; null when it needs room behind me that I do not have (cornered) and
 * no push is coming. Backing away from a faster chaser costs extra: that band cannot be held.
 */
function travelTicks(f: FighterState, opp: FighterState, sit: Situation, b: number, want: number): number | null {
  let diff = want - sit.gap
  if (Math.abs(diff) <= AI.deadZone) return 0
  if (diff < 0) return Math.min(AI.score.travelCapTicks, divRound(-diff * CENTI, Math.max(1, speedPerTick(f, false))))
  const pushSoon = sit.touching && f.pushCooldown <= AI.stall.softTicks && !traitsAny(opp.traits, traitImmovable)
  // Backing off needs room: the band is out of reach when even its near edge is past the wall behind me.
  const lo = b === 1 ? 0 : BATTLE.bandEnds[b - 2]!
  if (lo - sit.gap > sit.roomBehind && !pushSoon) return null
  if (diff > sit.roomBehind) diff = Math.max(0, sit.roomBehind)
  let ticks = Math.min(AI.score.travelCapTicks, divRound(diff * CENTI, Math.max(1, speedPerTick(f, true))))
  // A chaser wants a closer band than this one (an AI), or has been walking in lately (a player on the pads).
  const chaser = opp.control === 'player' && !opp.auto ? sit.tick - opp.lastApproachTick <= AI.score.approachTicks : opp.prevTargetBand < b
  if (chaser && !pushSoon && !f.traits.includes('unshakable') && speedPerTick(f, true) <= speedPerTick(opp, false)) ticks += AI.score.unholdableTicks
  return ticks
}

/** The §12.10 value of one of my techniques right now (the EV with the attack-choice rules applied). */
function valueOf(state: BattleState, o: Option, f: FighterState, opp: FighterState, sit: Situation, threatNow: number, offenseMax: number, oppExpensive: boolean): number {
  const t = o.tech
  const p = AI.personalities[f.personality]
  const V = AI.value
  let v = o.ev
  if (t.family === 'Heavy' && f.guts < V.hitPref.gutsOverride && previewHitTenths(state, f.side, t.id) < V.hitPref.heavyHitBelowPct * 10) v = divRound(v * V.hitPref.heavyPct, 100)
  if (sit.punishWindow && t.force > 0) v = divRound(v * V.punishPct, 100)
  if (t.family === 'Wither') {
    if (opp.gutsRate >= V.starve.rateMin || oppExpensive) v = divRound(v * V.starve.witherPct, 100)
    v = divRound(v * p.witherBias, 100)
  }
  if (t.force === 0 && t.effect?.kind === 'heal') {
    const low = f.hp * 100 <= f.maxHp * V.heal.hpPctMax
    const quiet = threatNow <= divRound(offenseMax * V.heal.threatPct, 100)
    if (low && quiet) v = t.effect.pct * 1000
    if (f.traits.some((t) => t === 'blessed' || t === 'green-thumb')) v = divRound(v * V.heal.traitPct, 100)
  }
  if (sit.tick - (f.aiTechUsed[t.id] ?? NEVER) > AI.score.windowTicks) v = divRound(v * V.varietyPct, 100)
  if (f.habit === 'spamsWither' && t.family === 'Wither') v = divRound(v * V.habitBias, 100)
  if (f.habit === 'stealsGuts' && (t.effect?.kind === 'gutsSteal' || t.family === 'Wither')) v = divRound(v * V.habitBias, 100)
  return v
}

function computePlan(state: BattleState, f: FighterState, opp: FighterState, sit: Situation): Computed {
  const p = AI.personalities[f.personality]
  const st = AI.styles[f.style]
  const S = AI.situations
  const kit = kitOf(state, f, opp)
  const oppKit = kitOf(state, opp, f)

  // Multipliers: tier × personality × Auto style × situations (§12.10).
  let aggression = divRound(p.aggression * st.aggression, 100)
  let caution = f.tier === 'rookie' ? 0 : divRound(divRound(p.caution * st.caution, 100) * AI.score.threatWeight, 100)
  let safe = false
  if (f.tier !== 'rookie') {
    if (sit.aheadLate) {
      caution = divRound(caution * S.aheadLate.cautionPct, 100)
      safe = true
    }
    if (sit.behindLate) {
      aggression = divRound(aggression * S.behindLate.aggressionPct, 100)
      caution = divRound(caution * S.behindLate.cautionPct, 100)
    } else if (f.hp * 100 <= f.maxHp * S.lowHp.hpPctMax) caution = divRound(caution * S.lowHp.cautionPct, 100)
  }
  let heavyBand = 0
  if (f.tier === 'expert') {
    if (sit.punishWindow) caution = divRound(caution * S.punish.cautionPct, 100)
    if (opp.special && (opp.special.kind === 'valor' || opp.special.kind === 'clutch')) caution = divRound(caution * S.oppDamageUp.cautionPct, 100)
    if (f.special && (f.special.kind === 'valor' || f.special.kind === 'clutch')) aggression = divRound(aggression * S.ownDamageUp.aggressionPct, 100)
    let heavy: Option | null = null
    for (const o of oppKit) if (o.tech.family === 'Heavy' && (!heavy || o.ev > heavy.ev)) heavy = o
    if (heavy && opp.guts >= heavy.cost) heavyBand = heavy.tech.range
  }

  // Offense and threat per band (EV per second, best technique there; a bonus when affordable now).
  const offense = [0, 0, 0, 0, 0]
  const threat = [0, 0, 0, 0, 0]
  for (const o of kit) {
    const b = o.tech.range
    let r = f.guts >= o.cost ? divRound(o.rate * AI.score.affordNowPct, 100) : o.rate
    if (b === 4) r = divRound(r * divRound(p.farBias * st.farBias, 100), 100)
    if (b === 1) r = divRound(r * divRound(p.closeBias * st.closeBias, 100), 100)
    if (r > offense[b]!) offense[b] = r
  }
  let oppExpensiveBest = 0
  let oppBestEv = 0
  for (const o of oppKit) {
    const b = o.tech.range
    const r = opp.guts >= o.cost ? divRound(o.rate * AI.score.affordNowPct, 100) : o.rate
    if (r > threat[b]!) threat[b] = r
    if (o.ev > oppBestEv) {
      oppBestEv = o.ev
      oppExpensiveBest = o.cost
    }
  }
  let oppBest = 0
  for (let b = 1; b <= 4; b++) if (threat[b]! > (threat[oppBest] ?? 0)) oppBest = b
  let offenseMax = 0
  for (let b = 1; b <= 4; b++) offenseMax = Math.max(offenseMax, offense[b]!)

  // Values of my techniques (attack choice, §12.10).
  const oppExpensive = oppExpensiveBest >= AI.value.starve.expensiveCost
  for (const o of kit) o.value = valueOf(state, o, f, opp, sit, threat[sit.band] ?? 0, offenseMax, oppExpensive)

  // Band scores.
  const score = [BLOCKED, BLOCKED, BLOCKED, BLOCKED, BLOCKED]
  const kiting = sit.tick < f.aiKiteUntil
  for (let b = 1; b <= 4; b++) {
    if (offense[b]! <= 0) continue
    const travel = travelTicks(f, opp, sit, b, sweetSpot(b, oppBest))
    if (travel === null) continue
    // Variety: a bonus for a band unused lately, capped at a share of its own offense so a weak band is never chosen for variety alone.
    const varietyCap = Math.min(AI.score.varietyMax, divRound(offense[b]! * AI.score.varietyPct, 100))
    const variety = divRound(varietyCap * Math.min(AI.score.windowTicks, sit.tick - f.aiBandUsed[b]!), AI.score.windowTicks)
    let cautionHere = caution
    if (heavyBand === b) cautionHere = divRound(cautionHere * S.heavyReady.cautionPct, 100)
    let s = divRound(offense[b]! * aggression, 100) - divRound(threat[b]! * cautionHere, 100) + variety - travel * AI.score.travelWeight
    if (kiting && b > sit.band) s += AI.score.chillKiteBonus
    score[b] = s
  }
  let best = 0
  for (let b = 1; b <= 4; b++) if (score[b]! > BLOCKED && (best === 0 || score[b]! > score[best]!)) best = b
  return { offense, threat, score, best, oppBest, kit, oppKit, weakClose: threat[1]! > offense[1]!, safe }
}

/** The range plan as the AI sees it right now (pure; for tests and tools). */
export function rangePlan(state: BattleState, f: FighterState, opp: FighterState): RangePlan {
  const c = computePlan(state, f, opp, situationOf(state, f, opp))
  return { offense: c.offense, threat: c.threat, score: c.score, best: c.best, oppBest: c.oppBest }
}

/** Applies a fresh plan: target band (with hysteresis, habits and the tier's mistakes), sweet spot, goal technique. */
function applyPlan(f: FighterState, c: Computed, sit: Situation, rng: Rng): void {
  const tierCfg = AI.tiers[f.tier]
  let target = c.best
  const current = f.aiTargetBand
  if (sit.tick < f.aiMistakeUntil && c.score[current]! > BLOCKED) target = current
  else if (target !== 0 && current !== target && c.score[current]! > BLOCKED) {
    const margin = Math.max(AI.score.hysteresisMin, divRound(Math.abs(c.score[current]!) * AI.score.hysteresisPct, 100))
    if (c.score[target]! < c.score[current]! + margin) target = current
  }
  if (target === 0) {
    // Nothing reachable (cornered with only longer techniques): keep the closest band that has a technique.
    for (let b = sit.band; b >= 1 && target === 0; b--) if (c.offense[b]! > 0) target = b
    if (target === 0) for (let b = 1; b <= 4 && target === 0; b++) if (c.offense[b]! > 0) target = b
    if (target === 0) target = current
  }
  // A mistake: a random OK band instead of the best, kept for a few seconds so it reads as a choice, not a twitch.
  if (sit.tick >= f.aiMistakeUntil && rng.chance(tierCfg.mistakePct)) {
    const ok: number[] = []
    for (let b = 1; b <= 4; b++) if (c.score[b]! > BLOCKED && b !== target) ok.push(b)
    if (ok.length > 0) {
      target = rng.pick(ok)
      f.aiMistakeUntil = sit.tick + rng.nextInt(AI.tiers[f.tier].mistakeTicks.min, AI.tiers[f.tier].mistakeTicks.max)
    }
  }
  const opensFar = f.habit === 'opensFar' && !f.habitDone && c.offense[4]! > 0
  if (f.habit === 'walksClose' && c.offense[1]! > 0) target = 1
  if (opensFar) target = 4

  // The goal: the best-value technique at the target band that is affordable soon.
  const soon = f.guts + regenOver(f, AI.guts.goalHorizonTicks)
  let goal: Option | null = null
  for (const o of c.kit) {
    if (o.tech.range !== target || o.cost > soon) continue
    if (opensFar && o.tech.range !== 4) continue
    if (!goal || o.value > goal.value) goal = o
  }
  const goalId = goal ? goal.tech.id : null
  // A new target band cancels a technique waiting on its reaction delay; a new goal does not (the poke is still sound).
  if (target !== f.aiTargetBand) {
    f.aiFireTech = null
    f.aiFireAt = NEVER
  }
  f.aiTargetBand = target
  f.aiSweet = Math.min(sweetSpot(target, c.oppBest), sit.gap + Math.max(0, sit.roomBehind))
  f.aiGoal = goalId
  f.aiWeakClose = c.weakClose
  f.aiValues = {}
  for (const o of c.kit) f.aiValues[o.tech.id] = o.value
  f.aiNextThink = sit.tick + rng.nextInt(AI.replan.min, AI.replan.max)
}

/* ---------- the tick ---------- */

/** Sets the fighter's requests for this tick (move direction, push, dash, fire) and its plan icon. */
export function decideAi(state: BattleState, f: FighterState, opp: FighterState, rng: Rng, log: BattleEvent[]): void {
  const sit = situationOf(state, f, opp)
  const tick = sit.tick
  const band = sit.band
  const tierCfg = AI.tiers[f.tier]
  const p = AI.personalities[f.personality]
  const st = AI.styles[f.style]
  const habit = f.habit
  const modeBefore = f.aiMode
  const bandBefore = f.aiTargetBand

  // Events that force a re-plan.
  const afford = affordMask(f)
  const oppAfford = affordMask(opp)
  let clockMark = false
  for (const s of AI.clockMarks) if (tick === state.timerTicks - s * TPS) clockMark = true
  const event =
    f.hp < f.aiLastHp || opp.attacks !== f.aiLastOppAttacks || afford !== f.aiAfford || oppAfford !== f.aiOppAfford || (sit.touching && !f.aiLastTouching) || (sit.cornered && !f.aiLastCornered) || clockMark
  if (f.traits.includes('chill') && f.hits > f.aiLastHits) f.aiKiteUntil = tick + AI.situations.chillKiteTicks
  f.aiLastHits = f.hits
  let safe = sit.aheadLate
  if (tick >= f.aiNextThink || event) {
    const c = computePlan(state, f, opp, sit)
    applyPlan(f, c, sit, rng)
    safe = c.safe
    f.aiLastHp = f.hp
    f.aiLastOppAttacks = opp.attacks
    f.aiAfford = afford
    f.aiOppAfford = oppAfford
    f.aiLastTouching = sit.touching
    f.aiLastCornered = sit.cornered
  }
  const opensFar = habit === 'opensFar' && !f.habitDone && f.techniques.some((t) => TECHNIQUE_BY_ID[t.id]?.range === 4)

  // In-range, affordable options right now (habit filters apply).
  let inRange: Technique[] = []
  if (band <= 4) {
    for (const ref of f.techniques) {
      const tech = TECHNIQUE_BY_ID[ref.id]
      if (!tech || tech.range !== band || f.guts < effectiveCost(f, tech)) continue
      if (opensFar && tech.range !== 4) continue
      if (habit === 'banksForHeavy' && tech.family === 'Heavy' && f.guts < AI.value.habitBankGuts) continue
      inRange.push(tech)
    }
  }

  // 1. Movement: the sweet spot plus footsies, corner awareness, habits and Statue Pose.
  let desired = f.aiSweet
  if (habit === 'walksClose') desired = sweetSpot(1, 0)
  if (opensFar) desired = sweetSpot(4, 0)
  if (!f.traits.includes('statue-pose')) {
    if (tick >= f.aiFootsieNext) {
      f.aiFootsie = rng.nextInt(AI.footsie.amp.min, AI.footsie.amp.max) * (rng.chance(50) ? 1 : -1)
      f.aiFootsieNext = tick + rng.nextInt(AI.footsie.every.min, AI.footsie.every.max)
    }
    desired += f.aiFootsie
  }
  desired = Math.max(AI.stall.touchGap + 1, desired)
  let dir: -1 | 0 | 1 = sit.gap > desired + AI.deadZone ? 1 : sit.gap < desired - AI.deadZone ? -1 : 0
  if (habit === 'backsAway' && opp.prevMoveDir === 1 && band <= 3) dir = -1
  if (habit === 'pushesWhenTouching' && band === 1 && sit.gap > AI.stall.touchGap && f.pushCooldown === 0) dir = 1
  // Statue Pose: it holds its ground whenever it has something to fire from here (two still seconds earn the trait).
  if (f.traits.includes('statue-pose') && inRange.length > 0) dir = 0

  // 2. Push: stuck together, the weaker Close fighter, or my back near the wall; anti-stall.
  let push = false
  let stallFire = false
  const canPush = sit.touching && f.pushCooldown === 0
  const movable = !traitsAny(opp.traits, traitImmovable)
  const wantsRoom = f.aiTargetBand >= 2 || f.aiWeakClose || (sit.cornered && !f.traits.includes('unshakable'))
  if (canPush && movable && wantsRoom) push = true
  if (habit === 'pushesWhenTouching' && canPush) push = true
  // Caught at Close with nothing to fire there (or cornered): step in to touch, then shove to make room.
  if (wantsRoom && movable && band === 1 && !sit.touching && f.pushCooldown === 0 && (sit.cornered || inRange.length === 0)) dir = 1
  if (sit.touching && f.touchStreak > AI.stall.softTicks) {
    if (canPush && (wantsRoom || f.touchStreak > AI.stall.hardTicks)) push = true
    else if (sit.roomBehind > 0) dir = -1
    else stallFire = true
  }
  // Never walk backwards into the wall for more than half a second.
  if (dir === -1 && sit.roomBehind <= 0) {
    f.aiBackWall += 1
    if (f.aiBackWall > AI.backIntoWallTicks) dir = 0
  } else f.aiBackWall = 0
  f.moveDir = dir
  if (push) f.wantPush = true

  // 3. Dash in with a reason (Battering Ram: freely).
  const goal = f.aiGoal ? TECHNIQUE_BY_ID[f.aiGoal] : undefined
  const freeDash = traitsAny(f.traits, traitFreeDash)
  // Only dash when something can still be fired on arrival (the dash itself costs guts).
  let cheapestAtTarget = Infinity
  for (const ref of f.techniques) {
    const tech = TECHNIQUE_BY_ID[ref.id]
    if (tech && tech.range === f.aiTargetBand) cheapestAtTarget = Math.min(cheapestAtTarget, effectiveCost(f, tech))
  }
  const dashLeaves = freeDash ? f.guts : f.guts - BATTLE.dash.cost
  if (f.aiTargetBand < band && sit.gap >= BATTLE.dash.minGap && f.dashCooldown === 0 && dashLeaves >= cheapestAtTarget) {
    const goalCloser = goal ? band - goal.range : 0
    // A kiter (it wants more distance than I do) is caught fastest with a dash.
    const kiter = opp.prevTargetBand > f.aiTargetBand
    if (sit.punishWindow || (sit.behind && sit.secondsLeft <= AI.dash.behindSecondsLeft) || goalCloser >= AI.dash.goalBandsCloser || kiter || ((freeDash || st.dashFreely) && rng.chance(AI.dash.ramPct))) f.wantDash = true
  }
  if (habit === 'dashesBelowHalf' && f.hp * 2 < f.maxHp && band >= 2 && f.dashCooldown === 0 && rng.chance(HABIT_DASH_PCT)) f.wantDash = true

  // 4. Fire. Attacks are a scarce slot (the cooldown), so each one should be worth it: the goal when it is
  // affordable here; otherwise the best affordable technique in range when it is worth a good share of the
  // goal, or when the goal is far off anyway; always when sitting on 90+ guts, when the opponent is broke,
  // when being punished, or to break a stall. Otherwise save.
  const value = (id: string) => f.aiValues[id] ?? 0
  const goalCost = goal ? effectiveCost(f, goal) : 0
  let pick: Technique | null = null
  let saving = false
  if (f.aiCooldown === 0 && inRange.length > 0 && !(habit === 'waits99' && f.guts < AI.value.habitWaitGuts)) {
    const best = inRange.reduce((m, t) => (value(t.id) > value(m.id) ? t : m))
    if (f.tier === 'rookie') {
      if (f.guts >= AI.guts.rookieReserve) pick = best
    } else if (goal && goal.range === band && f.guts >= goalCost) pick = goal
    else if (f.guts >= AI.guts.spendAt || stallFire || sit.oppBroke || sit.beingPunished || !goal) pick = best
    else if (f.guts < AI.guts.pokeFloor) saving = true
    else {
      const horizon = divRound(AI.guts.horizonTicks * 100 * 100, p.saveBias * st.saveBias)
      const goalImminent = f.guts + regenOver(f, horizon) >= goalCost
      if (value(best.id) * 100 >= value(goal.id) * AI.guts.slotRatioPct || !goalImminent) pick = best
      else saving = true
    }
  } else if (goal && f.guts < goalCost) saving = true
  if (f.aiFireTech !== null && !inRange.some((t) => t.id === f.aiFireTech)) {
    f.aiFireTech = null
    f.aiFireAt = NEVER
  }
  if (pick && f.aiFireTech === null) {
    let chosen = pick
    if (inRange.length > 1 && rng.chance(tierCfg.mistakePct)) chosen = rng.pick(inRange)
    f.aiFireTech = chosen.id
    f.aiFireAt = tick + rng.nextInt(tierCfg.react.min, tierCfg.react.max)
  }
  if (f.aiFireTech !== null && tick >= f.aiFireAt) {
    const t = TECHNIQUE_BY_ID[f.aiFireTech]
    // A dash or a Wither may have cost guts since the decision: the reserve rules are checked again here.
    const held = (f.tier === 'rookie' && f.guts < AI.guts.rookieReserve) || (habit === 'waits99' && f.guts < AI.value.habitWaitGuts) || (habit === 'banksForHeavy' && t?.family === 'Heavy' && f.guts < AI.value.habitBankGuts)
    if (t && !held && t.range === band && f.guts >= effectiveCost(f, t) && f.aiCooldown === 0) {
      f.wantFire = t.id
      f.habitDone = true
      f.aiCooldown = divRound(rng.nextInt(tierCfg.cooldown.min, tierCfg.cooldown.max) * divRound(p.cooldownPct * st.cooldownPct, 100), 100)
      f.aiBandUsed[band] = tick
      f.aiTechUsed[t.id] = tick
    }
    f.aiFireTech = null
    f.aiFireAt = NEVER
  }

  // 5. The plan icon.
  let mode: PlanMode
  if (sit.punishWindow && (pick || f.wantDash)) mode = 'punish'
  else if (sit.cornered && f.aiTargetBand > band) mode = 'cornered'
  else if (push) mode = 'pushing'
  else if (safe) mode = 'safe'
  else if (saving) mode = 'saving'
  else if (f.aiTargetBand > band || dir === -1) mode = 'distance'
  else mode = 'pressing'
  // The urgent modes show at once; the calmer ones wait out the hold so the icon does not flicker.
  const urgent = mode === 'punish' || mode === 'pushing' || mode === 'cornered'
  if (mode !== modeBefore && (urgent || modeBefore === null || tick >= f.aiModeUntil)) {
    f.aiMode = mode
    f.aiModeUntil = tick + AI.modeHoldTicks
  }
  if (f.aiMode !== modeBefore || f.aiTargetBand !== bandBefore) log.push({ t: tick, kind: 'plan', side: f.side, band: f.aiTargetBand, mode: f.aiMode ?? mode })
}
