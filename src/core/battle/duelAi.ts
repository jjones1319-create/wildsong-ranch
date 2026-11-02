import { AI, BATTLE } from '../../data/tuning.ts'
import { divRound } from '../mathx.ts'
import type { Rng } from '../rng.ts'
import { leftIsOutward, roomBehindUnits } from './geometry.ts'
import type { BattleState, FighterState } from './types.ts'

/**
 * docs/BATTLE_3D.md §4: the duel brain, run after the range plan (ai.ts) for every AI or Auto fighter in a duel.
 * The plan still decides the gap and the techniques; this adds what only a ring has:
 * - **sidestepping**: against an incoming straight-line technique it may sidestep, with the tier's chance and after
 *   its reaction delay, which a high SPD shortens. Only a sidestep that starts inside the wind-up helps, so slow
 *   reactions (rookies, low SPD) rarely dodge the quick techniques; it helps but never replaces stats;
 * - **circling**: between techniques it now and then strafes round the opponent for a while, and when the ring's
 *   edge is close behind it, it always circles toward open ground.
 * Every random draw happens in duel mode only, so line battles are untouched.
 */

const NEVER = -100_000

/** The way to sidestep or circle so the fighter turns toward open ground (+1 left, −1 right). */
function towardOpenGround(f: FighterState, opp: FighterState): -1 | 1 {
  return leftIsOutward(f, opp) ? -1 : 1
}

export function decideDuel(state: BattleState, f: FighterState, opp: FighterState, rng: Rng): void {
  const D = AI.duel
  const tick = state.tick
  const p = opp.pending

  // 1. Sidestep: decide once per incoming straight-line technique.
  if (p && p.path === 'line' && f.aiSidestepFor !== p.fireTick) {
    f.aiSidestepFor = p.fireTick
    f.aiSidestepAt = NEVER
    const afford = f.guts >= BATTLE.duel.sidestep.cost + D.sidestepReserve && f.sidestepCooldown === 0
    if (afford && rng.chance(D.sidestepPct[f.tier])) {
      const r = D.sidestepReact[f.tier]
      const base = rng.nextInt(r.min, r.max)
      const spd = Math.min(f.stats.SPD, 999)
      f.aiSidestepAt = p.fireTick + Math.max(1, divRound(base * (D.reactSpdDiv - spd), D.reactSpdDiv))
    }
  }
  if (p && f.aiSidestepFor === p.fireTick && f.aiSidestepAt !== NEVER && tick >= f.aiSidestepAt) {
    // too late once it has landed; otherwise go (the engine checks guts and cooldown again)
    if (tick < p.landTick) f.wantSidestep = towardOpenGround(f, opp)
    f.aiSidestepAt = NEVER
  }

  // 2. Circling.
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
  if (tick < f.aiStrafeUntil) return
  f.strafeDir = rng.chance(D.circlePct) ? (rng.chance(50) ? 1 : -1) : 0
  f.aiStrafeUntil = tick + rng.nextInt(D.circleTicks.min, D.circleTicks.max)
}
