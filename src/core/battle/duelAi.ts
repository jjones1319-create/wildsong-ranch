import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI, BATTLE } from '../../data/tuning.ts'
import { divRound } from '../mathx.ts'
import type { Rng } from '../rng.ts'
import { canFire, currentBand, effectiveCost } from './engine.ts'
import { herdDir, leftIsOutward, offsetFromAim, roomBehindUnits } from './geometry.ts'
import { canHerd, rusherSeen } from './duelRead.ts'
import { bySense } from './duelSense.ts'
import { setUp } from './duelSetup.ts'
import { isOpen, judge, look, notice, spendIntent, takeIntent } from './duelShot.ts'
import type { BattleState, FighterState } from './types.ts'

/**
 * docs/BATTLE_3D.md §4 AI 3.0: the duel brain, run after the range plan (ai.ts) for every AI or Auto fighter in a
 * duel that can act. The plan still decides the range and the techniques; this layer adds, scaled by battle sense:
 * sidesteps timed to the wind-up (§4.2), punishing openings (§4.3), the habits read in duelRead.ts (§4.4, through the
 * plan's values), the ring (§4.5), visible styles (§4.6) and a spoiled monster's bad habits (§4.7); and AI 3.1's
 * human qualities (§4.9, duelShot.ts and duelSetup.ts): the plan's shot is held as an intent and fired when the moment
 * is right, after a human reaction. Every random draw happens in duel mode only, so line battles are untouched.
 */

const NEVER = -100_000
const CENTI = 100
const D = AI.duel

export type DuelStyle = 'rusher' | 'trickster' | 'careful' | 'steady'

/** §4.6: CPU personalities and the player's Auto styles, as the four styles you can see. */
export function duelStyleOf(f: FighterState): DuelStyle {
  if (f.control === 'player') return f.style === 'aggressive' ? 'rusher' : f.style === 'defensive' ? 'careful' : 'steady'
  switch (f.personality) {
    case 'Aggressive':
    case 'Brawler':
      return 'rusher'
    case 'Trickster':
      return 'trickster'
    case 'Cautious':
    case 'Sniper':
      return 'careful'
    default:
      return 'steady'
  }
}

/** The way to sidestep or circle so the fighter turns toward open ground (+1 left, −1 right). */
function towardOpenGround(f: FighterState, opp: FighterState): -1 | 1 {
  return leftIsOutward(f, opp) ? -1 : 1
}

export function decideDuel(state: BattleState, f: FighterState, opp: FighterState, rng: Rng): void {
  const style = duelStyleOf(f)
  look(state, f)
  sidestep(state, f, opp, rng, style)
  // §4.9: the plan's shot becomes an intent; a punish fires at once; otherwise the intent waits for its moment
  takeIntent(state, f, opp, rng, style)
  notice(f, opp, rng, style)
  punish(state, f, opp, rng, style)
  finisher(state, f, opp, style)
  judge(state, f, opp, rng, style)
  showOff(state, f, rng)
  move(state, f, opp, rng, style)
}

/** §4.2: once per incoming straight-line technique, maybe sidestep after a reflex; below 35 sense, the odd flinch. */
function sidestep(state: BattleState, f: FighterState, opp: FighterState, rng: Rng, style: DuelStyle): void {
  const S = D.sidestep
  const p = opp.pending
  const afford = f.guts >= BATTLE.duel.sidestep.cost + D.sidestepReserve && f.sidestepCooldown === 0
  if (p && p.path === 'line' && f.aiSidestepFor !== p.fireTick) {
    f.aiSidestepFor = p.fireTick
    f.aiSidestepAt = NEVER
    const offLine = f.sense >= S.ignoreOffLineFrom && offsetFromAim(p.ax, p.ay, p.dx, p.dy, f.x, f.y) > BATTLE.duel.pathHalfWidth * CENTI
    // §4.9 a bait: dancing at the edge with a sidestep ready, it expects the attack
    const baiting = state.tick < f.aiFeintUntil && (style === 'trickster' || f.sense >= D.human.bait.fromSense)
    const pct = S.basePct + divRound(S.perSensePct * f.sense, 100) + (style === 'careful' ? S.carefulPct : 0) + (baiting ? D.human.bait.sidestepPct : 0)
    if (afford && !offLine && rng.chance(pct)) {
      const base = rng.nextInt(bySense(S.reactSlow.min, S.reactQuick.min, f.sense), bySense(S.reactSlow.max, S.reactQuick.max, f.sense))
      const spd = Math.min(f.stats.SPD, 999)
      f.aiSidestepAt = p.fireTick + Math.max(1, divRound(base * (D.reactSpdDiv - spd), D.reactSpdDiv))
    }
  }
  if (p && f.aiSidestepFor === p.fireTick && f.aiSidestepAt !== NEVER && state.tick >= f.aiSidestepAt) {
    // too late once it has landed; otherwise go (the engine checks guts and cooldown again)
    if (state.tick < p.landTick) f.wantSidestep = towardOpenGround(f, opp)
    f.aiSidestepAt = NEVER
    return
  }
  const F = D.flinch
  if (!p && afford && f.sense < F.below && state.tick % F.every === 0 && rng.chance(divRound((F.below - f.sense) * F.perPoint, 10))) {
    f.wantSidestep = rng.chance(50) ? 1 : -1
  }
}

/** The best technique it can fire this tick, by the plan's values. */
function bestReady(state: BattleState, f: FighterState): string | null {
  let best: string | null = null
  for (const t of f.techniques) {
    if (!canFire(state, f, t.id)) continue
    if (best === null || (f.aiValues[t.id] ?? 0) > (f.aiValues[best] ?? 0)) best = t.id
  }
  return best
}

/** §4.3: once per opening, maybe fire into it after a delay that battle sense shortens; a rusher dashes in to do it. */
function punish(state: BattleState, f: FighterState, opp: FighterState, rng: Rng, style: DuelStyle): void {
  const P = D.punish
  if (!isOpen(opp)) {
    f.aiOpeningSeen = NEVER
    f.aiPunishAt = NEVER
    return
  }
  if (f.aiOpeningSeen === NEVER) {
    f.aiOpeningSeen = state.tick
    f.aiPunishAt = rng.chance(divRound(P.perSensePct * f.sense, 100)) ? state.tick + bySense(P.slow, P.quick, f.sense) : NEVER
  }
  if (f.aiPunishAt === NEVER || state.tick < f.aiPunishAt) return
  const best = bestReady(state, f)
  if (best) {
    // §4.9 even a punish settles for a moment after arriving in range; it spends the intent the plan had
    if (f.shot && state.tick - f.shot.steadySince < bySense(D.human.punishSettle.slow, D.human.punishSettle.quick, f.sense)) {
      f.aiPunishAt = state.tick + 1
      return
    }
    f.wantFire = best
    f.aiPunishAt = NEVER
    spendIntent(f)
    return
  }
  // nothing ready here: head for the range of the best technique it can afford, and try again while it stays open
  const goal = bestAffordable(f)
  const band = currentBand(state)
  if (!goal) {
    f.aiPunishAt = NEVER
    return
  }
  f.moveDir = band > goal.range ? 1 : -1
  const dashIn = band > goal.range && f.dashTicks === 0 && (style === 'rusher' || f.sense >= P.dashFromSense)
  if (dashIn) f.wantDash = true
  f.aiPunishAt = state.tick + (dashIn ? P.dashRetry : 1)
}

/** The best technique it has the guts for, wherever it fires from. */
function bestAffordable(f: FighterState): { id: string; range: number } | null {
  let best: { id: string; range: number } | null = null
  for (const t of f.techniques) {
    const tech = TECHNIQUE_BY_ID[t.id]
    if (!tech || f.guts < effectiveCost(f, tech)) continue
    if (best === null || (f.aiValues[t.id] ?? 0) > (f.aiValues[best.id] ?? 0)) best = { id: t.id, range: tech.range }
  }
  return best
}

/** §4.6 careful: once the opponent is low, keep guts for the Special or Signature and fire it when in range. */
function finisher(state: BattleState, f: FighterState, opp: FighterState, style: DuelStyle): void {
  if (style !== 'careful' || opp.hp * 100 > opp.maxHp * D.styles.careful.finisherHpPct) return
  let fin: string | null = null
  for (const t of f.techniques) {
    const tech = TECHNIQUE_BY_ID[t.id]
    if (!tech || (tech.family !== 'Special' && tech.family !== 'Signature')) continue
    if (fin === null || tech.force > (TECHNIQUE_BY_ID[fin]?.force ?? 0)) fin = t.id
  }
  const finTech = fin ? TECHNIQUE_BY_ID[fin] : undefined
  if (!fin || !finTech || !f.shot || f.wantFire) return
  // §4.9 it becomes the intent (fired at the right moment, after a reaction) when it can be paid for, or when the
  // intent it has would leave too little for it
  const finCost = effectiveCost(f, finTech)
  const intent = f.shot.intent ? TECHNIQUE_BY_ID[f.shot.intent] : undefined
  if (f.shot.intent !== fin && (intent ? f.guts - effectiveCost(f, intent) < finCost : f.guts >= finCost)) {
    if (!intent) f.shot.since = state.tick
    f.shot.intent = fin
  }
  // with the guts in hand, walk to its range
  const band = currentBand(state)
  if (f.guts >= finCost && band !== finTech.range) f.moveDir = band > finTech.range ? 1 : -1
}

/** §4.7 a spoiled monster shows off: now and then its most forceful ready technique instead of the best one. */
function showOff(state: BattleState, f: FighterState, rng: Rng): void {
  if (!f.spoiled || !f.wantFire || !rng.chance(D.spoiled.showOffPct[f.spoiled])) return
  let flashy: string | null = null
  for (const t of f.techniques) {
    if (!canFire(state, f, t.id)) continue
    if (flashy === null || (TECHNIQUE_BY_ID[t.id]?.force ?? 0) > (TECHNIQUE_BY_ID[flashy]?.force ?? 0)) flashy = t.id
  }
  if (flashy) f.wantFire = flashy
}

/** Set-ups (§4.9), slacking (§4.7) and circling: away from the fence, herding the opponent to it (§4.5), or for a while. */
function move(state: BattleState, f: FighterState, opp: FighterState, rng: Rng, style: DuelStyle): void {
  const tick = state.tick
  setUp(state, f, opp)
  const Sp = D.spoiled
  if (f.spoiled && tick % Sp.slackEvery === 0 && rng.chance(Sp.slackPct[f.spoiled])) f.aiLazyUntil = tick + Sp.slackTicks
  if (tick < f.aiLazyUntil) {
    if (f.moveDir === 1) f.moveDir = 0
    f.wantDash = false
  }
  const T = D.styles.trickster

  if (roomBehindUnits(state, f, opp) < AI.cornerUnits) {
    f.strafeDir = towardOpenGround(f, opp)
    f.aiStrafeUntil = tick + D.circleTicks.min
    return
  }
  // Statue Pose is worth more standing still than circling
  if (f.traits.includes('statue-pose')) {
    f.strafeDir = 0
    return
  }
  if (canHerd(state, f, opp)) {
    f.strafeDir = herdDir(f, opp, D.herd.alignPct)
    return
  }
  if (tick < f.aiStrafeUntil) return
  const mul = style === 'rusher' ? D.styles.rusher.circlePct : style === 'trickster' ? T.circlePct : style === 'careful' ? D.styles.careful.circlePct : 100
  const pct = Math.min(95, divRound(D.circlePct * mul, 100) + (rusherSeen(f) ? D.read.rusher.circlePct : 0))
  f.strafeDir = rng.chance(pct) ? (rng.chance(50) ? 1 : -1) : 0
  const ticks = rng.nextInt(D.circleTicks.min, D.circleTicks.max)
  f.aiStrafeUntil = tick + (style === 'trickster' ? divRound(ticks, 2) : ticks)
}
