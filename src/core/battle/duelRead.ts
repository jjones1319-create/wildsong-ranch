import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI } from '../../data/tuning.ts'
import { divRound } from '../mathx.ts'
import { roomBehindUnits } from './geometry.ts'
import type { BattleState, FighterState } from './types.ts'

/**
 * docs/BATTLE_3D.md §4.4–§4.5: what an AI fighter learns about its opponent during a duel, and the biases it draws.
 * It reads only last tick's events and the opponent's walking, so it never sees a same-tick decision. No random draws.
 */

const R = AI.duel.read
const H = AI.duel.herd

/** Called every tick in a duel for an AI or Auto fighter, busy or not. */
export function observeDuel(state: BattleState, f: FighterState, opp: FighterState): void {
  const last = state.tick - 1
  for (let i = state.log.length - 1; i >= 0; i--) {
    const e = state.log[i]!
    if (e.t < last) break
    if (e.t !== last) continue
    if (e.kind === 'fire') {
      if (e.side === opp.side) {
        const range = TECHNIQUE_BY_ID[e.tech]?.range
        if (range) f.readBand[range] = (f.readBand[range] ?? 0) + 1
      } else if (e.path === 'line') f.readLineFires += 1
    } else if (e.kind === 'sidestep' && e.side === opp.side && f.pending?.path === 'line') f.readSidesteps += 1
  }
  f.readTicks += 1
  if (opp.moveDir === 1 || opp.dashTicks > 0) f.readAdvance += 1
  if (f.readTicks >= R.minTicks && f.readTicks % R.everyTicks === 0) refreshBias(state, f, opp)
}

/** It has seen enough of the opponent walking in to call it a rusher. */
export function rusherSeen(f: FighterState): boolean {
  return f.readTicks >= R.minTicks && f.readAdvance * 100 >= f.readTicks * R.rusher.sharePct
}

/** The opponent's back is near the fence and this fighter knows to use it (§4.5). */
export function canHerd(state: BattleState, f: FighterState, opp: FighterState): boolean {
  return f.sense >= H.minSense && roomBehindUnits(state, opp, f) < H.units
}

/** The biases, stronger with battle sense (a Rookie barely adjusts). */
function refreshBias(state: BattleState, f: FighterState, opp: FighterState): void {
  const b = f.duelBias
  if (!b) return
  const k = f.sense
  const S = R.sidestepper
  b.sweepPct = f.readLineFires >= S.minFires && f.readSidesteps * 100 >= f.readLineFires * S.sharePct ? 100 + divRound(S.sweepBonus * k, 100) : 100
  const fromRusher = rusherSeen(f) ? divRound(R.rusher.knockBonus * k, 100) : 0
  const fromHerding = canHerd(state, f, opp) ? divRound(H.knockBonus * k, 100) : 0
  b.knockPct = 100 + Math.max(fromRusher, fromHerding)
  let total = 0
  let top = 1
  for (let r = 1; r <= 4; r++) {
    total += f.readBand[r] ?? 0
    if ((f.readBand[r] ?? 0) > (f.readBand[top] ?? 0)) top = r
  }
  const F = R.favourite
  if (total >= F.minFires && (f.readBand[top] ?? 0) * 100 >= total * F.sharePct) {
    b.avoidBand = top
    b.avoidPct = 100 + divRound(F.avoidBonus * k, 100)
  } else {
    b.avoidBand = 0
    b.avoidPct = 100
  }
}
