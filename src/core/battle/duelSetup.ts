import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI, BATTLE } from '../../data/tuning.ts'
import { gapUnits } from './engine.ts'
import { bandOf } from './formulas.ts'
import { roomBehindUnits } from './geometry.ts'
import type { BattleState, FighterState } from './types.ts'

/**
 * docs/BATTLE_3D.md §4.9 set-ups you can see, after the plan has chosen where to walk (duel only, no random draws):
 * - **step back** for a moment after taking a hit, to reset;
 * - **dance** in and out at the edge of the intent's range before committing (a trickster's feint; with a sidestep
 *   ready it is a bait, see duelAi.ts), until the chance is clear or the dance ends;
 * - **press**: after landing a hit, step a little deeper into the range.
 * A punish in progress or a shot being fired this tick wins over all of these.
 */

const NEVER = -100_000
const H = AI.duel.human

/** The gap to aim for in a dance at the edge of band `b`: out of range on odd steps, just inside on even ones. */
function danceGap(b: number, out: boolean): number {
  const D = H.dance
  // Close to Mid dance across their outer edge; Far across its inner one (behind it there is only the fence)
  const edge = b <= 3 ? BATTLE.bandEnds[b - 1]! : BATTLE.bandEnds[2]!
  const outward = b <= 3 ? 1 : -1
  return edge + outward * (out ? D.depth : -D.depth)
}

function walkTo(f: FighterState, gap: number, want: number): void {
  f.moveDir = gap > want + AI.deadZone ? 1 : gap < want - AI.deadZone ? -1 : 0
}

export function setUp(state: BattleState, f: FighterState, opp: FighterState): void {
  const shot = f.shot
  if (!shot || f.wantFire || f.aiPunishAt !== NEVER) return
  const tick = state.tick
  const gap = gapUnits(state)
  const room = roomBehindUnits(state, f, opp)
  if (tick < shot.resetUntil) {
    // a step back, but not out of its own range: a brawler resets inside Close, a caster can give more ground
    const outer = BATTLE.bandEnds[f.aiTargetBand - 1]! - H.score.edgeUnits
    f.moveDir = room > AI.cornerUnits && gap < outer ? -1 : 0
    f.wantDash = false
    return
  }
  const intent = shot.intent ? TECHNIQUE_BY_ID[shot.intent] : undefined
  if (intent && tick < f.aiFeintUntil && shot.chanceAt === NEVER) {
    walkTo(f, gap, danceGap(intent.range, Math.floor((f.aiFeintUntil - tick) / H.dance.step) % 2 === 1))
    if (f.moveDir === -1 && room <= AI.cornerUnits) f.moveDir = 0
    f.wantDash = false
    return
  }
  if (tick < shot.pressUntil) {
    const b = f.aiTargetBand
    if (gap > Math.max(bandLo(b) + H.press.inset, f.aiSweet - H.press.depth) + AI.deadZone) f.moveDir = 1
  }
  // holding a shot it can fire from here: stay in range, a step inside the edges (it commits, it doesn't drift out)
  if (intent && bandOf(gap) === intent.range) {
    const inset = H.score.edgeUnits
    if (gap > BATTLE.bandEnds[intent.range - 1]! - inset) f.moveDir = 1
    else if (gap < bandLo(intent.range) + inset && room > AI.cornerUnits) f.moveDir = -1
    f.wantDash = false
  }
}

function bandLo(b: number): number {
  return b === 1 ? AI.stall.touchGap + 1 : BATTLE.bandEnds[b - 2]!
}
