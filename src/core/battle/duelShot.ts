import { pathOf } from '../../data/paths.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI, BATTLE } from '../../data/tuning.ts'
import type { Technique } from '../../data/types.ts'
import { divRound } from '../mathx.ts'
import type { Rng } from '../rng.ts'
import type { DuelStyle } from './duelAi.ts'
import { bySense } from './duelSense.ts'
import { canFire, currentBand, effectiveCost, gapUnits, previewDamage, previewHitTenths } from './engine.ts'
import { roomBehindUnits } from './geometry.ts'
import { duelWindup } from './pace.ts'
import type { BattleState, DuelShot, FighterState } from './types.ts'

/**
 * docs/BATTLE_3D.md §4.9 AI 3.1, human qualities (v1.22). The range plan (ai.ts) still decides what to fire and paces
 * its shots; in the duel its shot becomes an **intent** that this layer releases when the moment is right:
 * - a shot score (the hit chance, plus the opponent's state, the spot in the band, value per guts, a better technique
 *   about to be affordable, and guts kept like a player), the situational part weighted by battle sense;
 * - a bar that patience lowers the longer it holds, so it never waits forever;
 * - a human reaction (with variance and the odd hesitation) from the moment a good chance appears;
 * - pressing after landing a hit and stepping back after taking one.
 * Holding never touches the plan's goal or its pacing, so the fire rate stays the plan's. Duel only.
 */

const NEVER = -100_000
const H = AI.duel.human

/** §4.3: the opponent can't sidestep or answer right now. */
export function isOpen(opp: FighterState): boolean {
  return (opp.busyTicks > 0 && opp.pending === null) || opp.stunTicks > 0 || opp.dawdleTicks > 0
}

/** Every decision tick, first: a gap in its decisions (busy, stunned, sidestepping) or a new band is a fresh look. */
export function look(state: BattleState, f: FighterState): void {
  const shot = f.shot
  if (!shot) return
  const band = currentBand(state)
  if (state.tick - shot.lastLook > 1 || band !== shot.steadyBand) {
    shot.steadyBand = band
    shot.steadySince = state.tick
    shot.chanceAt = NEVER
  }
  shot.lastLook = state.tick
}

function setIntent(shot: DuelShot, id: string, tick: number): void {
  const before = shot.intent ? TECHNIQUE_BY_ID[shot.intent] : undefined
  // patience carries over when the shot changes for one at the same range
  if (!before || before.range !== TECHNIQUE_BY_ID[id]?.range) shot.since = tick
  shot.intent = id
}

/** The plan released a shot: hold it as the intent (the plan's cooldown and goal stay as the plan set them). */
export function takeIntent(state: BattleState, f: FighterState, opp: FighterState, rng: Rng, style: DuelStyle): void {
  const shot = f.shot
  if (!shot || !f.wantFire) return
  const fresh = shot.intent === null
  setIntent(shot, f.wantFire, state.tick)
  f.wantFire = null
  shot.taken += 1
  if (!fresh || isOpen(opp)) return
  // a set-up before committing: dance in and out at the edge of its range (duelSetup.ts)
  const D = H.dance
  if ((style === 'trickster' || f.sense >= D.fromSense) && rng.chance(D.pct[style])) f.aiFeintUntil = state.tick + rng.nextInt(D.ticks.min, D.ticks.max)
}

/** A hit it landed may start a press; a hit it took may start a step back (the windows run from the hit). */
export function notice(f: FighterState, opp: FighterState, rng: Rng, style: DuelStyle): void {
  const shot = f.shot
  if (!shot) return
  if (opp.lastHitTakenTick > shot.hitSeen) {
    shot.hitSeen = opp.lastHitTakenTick
    if (rng.chance(H.press.pct[style])) shot.pressUntil = opp.lastHitTakenTick + H.press.ticks
  }
  if (f.lastHitTakenTick > shot.hurtSeen) {
    shot.hurtSeen = f.lastHitTakenTick
    const pct = divRound(H.reset.pct[style] * bySense(H.reset.senseSlow, 100, f.sense), 100)
    if (rng.chance(pct)) shot.resetUntil = f.lastHitTakenTick + rng.nextInt(H.reset.ticks.min, H.reset.ticks.max)
  }
}

/** A punish took the shot: the intent is spent. */
export function spendIntent(f: FighterState): void {
  if (!f.shot) return
  f.shot.intent = null
  f.shot.chanceAt = NEVER
}

function cheapest(f: FighterState): number {
  let c = Infinity
  for (const t of f.techniques) {
    const tech = TECHNIQUE_BY_ID[t.id]
    if (tech) c = Math.min(c, effectiveCost(f, tech))
  }
  return c
}

function canFinish(f: FighterState, opp: FighterState, tech: Technique): boolean {
  const ref = f.techniques.find((t) => t.id === tech.id)
  return tech.force > 0 && previewDamage(f, opp, tech, ref?.forceBonus ?? 0) >= opp.hp
}

/** The opponent is low on guts or has its back to the fence: a time to spend big. */
function spendBig(state: BattleState, f: FighterState, opp: FighterState): boolean {
  return opp.guts <= H.score.oppLowGuts || roomBehindUnits(state, opp, f) < AI.cornerUnits
}

/**
 * §4.9 guts like a player, asked by the plan (ai.ts) before it picks a shot in the duel: keep a sidestep and a punish
 * in hand (by battle sense) while the opponent can threaten, unless the opponent is open, low or cornered, the shot
 * can finish, its own guts are full or it is stuck in a stall. A gate on the pick, never a veto after it.
 */
export function maySpend(state: BattleState, f: FighterState, opp: FighterState, tech: Technique): boolean {
  const K = H.keep
  const want = BATTLE.duel.sidestep.cost + K.extra + divRound(cheapest(f) * K.punishPct, 100)
  const keep = divRound(want * bySense(K.slowPct, K.quickPct, f.sense), 100)
  if (f.guts - effectiveCost(f, tech) >= keep) return true
  return isOpen(opp) || opp.guts < cheapest(opp) || spendBig(state, f, opp) || canFinish(f, opp, tech) || f.guts >= H.score.fullGuts || f.touchStreak > AI.stall.softTicks
}

/** Standing near the band's edge: worse when the opponent is walking that way (it would step out of range). */
function edgeTerm(state: BattleState, opp: FighterState, band: number): number {
  const S = H.score
  const gap = gapUnits(state)
  const nearLo = band > 1 && gap - BATTLE.bandEnds[band - 2]! < S.edgeUnits
  const nearHi = BATTLE.bandEnds[band - 1]! - gap <= S.edgeUnits
  if ((nearLo && opp.prevMoveDir === 1) || (nearHi && opp.prevMoveDir === -1)) return -S.edgeLeaving
  return nearLo || nearHi ? -S.edge : 0
}

/** Value per guts against the best it can afford: a poor buy (an expensive, unlikely Heavy) waits for a better moment. */
function vpgTerm(f: FighterState, tech: Technique): number {
  const S = H.score
  const per = (id: string, cost: number) => divRound((f.aiValues[id] ?? 0) * 100, Math.max(1, cost))
  let best = 0
  for (const t of f.techniques) {
    const x = TECHNIQUE_BY_ID[t.id]
    if (!x || f.guts < effectiveCost(f, x)) continue
    best = Math.max(best, per(t.id, effectiveCost(f, x)))
  }
  if (best <= 0) return 0
  const ratio = divRound(per(tech.id, effectiveCost(f, tech)) * 100, best)
  return Math.max(S.vpgMin, divRound((ratio - 100) * S.vpgPct, 100))
}

/** A clearly better technique at the same range is a little regen away. */
function betterSoon(f: FighterState, tech: Technique): boolean {
  const S = H.score
  const v = f.aiValues[tech.id] ?? 0
  for (const t of f.techniques) {
    const x = TECHNIQUE_BY_ID[t.id]
    if (!x || x.range !== tech.range || t.id === tech.id) continue
    const c = effectiveCost(f, x)
    if (f.guts >= c || (f.aiValues[t.id] ?? 0) * 100 < v * S.betterPct) continue
    if (f.guts + Math.floor(S.betterSoonTicks / Math.max(1, f.gutsRate)) >= c) return true
  }
  return false
}

/** §4.9 how good this shot is right now (points, about percent): the hit chance plus the situation weighted by sense. */
export function shotScore(state: BattleState, f: FighterState, opp: FighterState, tech: Technique): number {
  const S = H.score
  let s = 0
  const open = isOpen(opp)
  if (open) s += S.open
  else if (opp.pending) s += S.oppWindup
  else if (pathOf(tech) === 'line') {
    if (opp.sidestepCooldown === 0 && opp.guts >= BATTLE.duel.sidestep.cost) {
      let pen = S.lineFresh + (duelWindup(tech.family) >= S.escapableWindup ? S.lineEscapable : 0)
      if (f.readLineFires > 0) pen += divRound(pen * S.sidestepSeenPct * Math.min(f.readSidesteps, f.readLineFires), 100 * f.readLineFires)
      s -= pen
    } else s += S.noDodge
  }
  s += edgeTerm(state, opp, tech.range)
  s += vpgTerm(f, tech)
  if (betterSoon(f, tech)) s -= S.betterSoon
  // guts like a player (the reserve itself is maySpend's): spend big on a broke or cornered opponent, or to finish
  const finish = canFinish(f, opp, tech)
  if (finish) s += S.finish
  if (spendBig(state, f, opp)) s += S.spendBig
  if (!finish && f.guts - effectiveCost(f, tech) < S.drainFloor) s -= S.drain
  if (f.guts >= S.fullGuts || f.touchStreak > AI.stall.softTicks) s += S.full
  const shot = f.shot
  if (shot && state.tick < shot.pressUntil) s += S.press
  if (shot && state.tick < shot.resetUntil) s -= S.reset
  return divRound(previewHitTenths(state, f.side, tech.id), 10) + divRound(s * bySense(H.weight.slow, H.weight.quick, f.sense), 100)
}

/** No bar at all: patience has run out and any shot goes. */
export const NO_BAR = -1_000

/** §4.9 the bar the shot must clear: by battle sense and style, lowered to the floor over its patience, then gone. */
export function shotThreshold(f: FighterState, held: number, style: DuelStyle): number {
  const st = H.styles[style]
  const t0 = bySense(H.threshold.slow, H.threshold.quick, f.sense) + st.threshold
  const patience = Math.max(1, divRound(bySense(H.patience.slow, H.patience.quick, f.sense) * st.patiencePct, 100))
  if (held >= patience) return NO_BAR
  return t0 - divRound((t0 - Math.min(t0, H.threshold.floor)) * Math.max(0, held), patience)
}

/** A clearly better technique at this range became affordable: the intent upgrades to it. */
function upgrade(state: BattleState, f: FighterState, opp: FighterState, shot: DuelShot): void {
  const v = f.aiValues[shot.intent!] ?? 0
  for (const t of f.techniques) {
    const tech = TECHNIQUE_BY_ID[t.id]
    if (!tech || t.id === shot.intent || !canFire(state, f, t.id) || !maySpend(state, f, opp, tech)) continue
    if ((f.aiValues[t.id] ?? 0) * 100 >= v * H.score.betterPct) setIntent(shot, t.id, state.tick)
  }
}

/** Release the intent when the moment is right, after a human reaction from when the chance appeared. */
export function judge(state: BattleState, f: FighterState, opp: FighterState, rng: Rng, style: DuelStyle): void {
  const shot = f.shot
  if (!shot || shot.intent === null || f.wantFire) return
  const tick = state.tick
  upgrade(state, f, opp, shot)
  const tech = TECHNIQUE_BY_ID[shot.intent]
  if (!tech || !canFire(state, f, shot.intent)) {
    shot.chanceAt = NEVER
    if (!tech || tick - shot.since > H.intentMaxTicks) {
      shot.intent = null
      shot.dropped += 1
    }
    return
  }
  // AI 3.0 patience: about to sidestep the opponent's technique, it dodges first
  const p = opp.pending
  if (f.sense >= AI.duel.punish.holdFromSense && p && f.aiSidestepFor === p.fireTick && f.aiSidestepAt !== NEVER) {
    shot.chanceAt = NEVER
    return
  }
  // while a live shot is held, the plan's next one waits for it (its cooldown pauses at the floor, never resets)
  f.aiCooldown = Math.max(f.aiCooldown, 2)
  const bar = shotThreshold(f, tick - shot.since, style)
  const score = shotScore(state, f, opp, tech)
  if (shot.chanceAt === NEVER) {
    if (score < bar) return
    const R = H.react
    let react = rng.nextInt(bySense(R.slow.min, R.quick.min, f.sense), bySense(R.slow.max, R.quick.max, f.sense))
    if (rng.chance(bySense(H.hesitate.slowPct, H.hesitate.quickPct, f.sense))) react += rng.nextInt(H.hesitate.ticks.min, H.hesitate.ticks.max)
    shot.chanceAt = tick + react
    // a clear chance: stop dancing and commit
    if (score >= bar + H.dance.commitAbove) f.aiFeintUntil = Math.min(f.aiFeintUntil, tick)
    return
  }
  if (score < bar - H.dropBelow) {
    shot.chanceAt = NEVER
    return
  }
  if (tick < shot.chanceAt) return
  f.wantFire = shot.intent
  shot.intent = null
  shot.chanceAt = NEVER
  shot.released += 1
}
