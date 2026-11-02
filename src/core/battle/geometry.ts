import { BATTLE } from '../../data/tuning.ts'
import { clamp } from '../mathx.ts'
import type { BattleState, FighterState } from './types.ts'

/**
 * GAME_DESIGN §12.1 and docs/BATTLE_3D.md §2: where the fighters stand, in centi-units.
 *
 * - **Line mode** (the classic battle): everyone stands on one line through the arena (y = 0); every helper here
 *   reduces to the original 1-D arithmetic, so line battles replay bit for bit.
 * - **Duel mode** (Battle 3D): the ring is a disc of radius `halfWidth`; body centres stay within
 *   `halfWidth − bodyRadius`. The fighters always face each other: "forward/back" runs along the line between
 *   them and changes the gap exactly as in line mode; strafing circles the opponent at the current distance.
 *
 * Square roots and divisions are plain IEEE doubles (correctly rounded on every device) and every position is
 * rounded back to whole centi-units, so duel battles replay exactly too. No trigonometry.
 */

const CENTI = 100
/** The furthest a body centre may stand from the ring centre (line: from x = 0). */
export const WALL = (BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius) * CENTI
/** Bodies never overlap: the closest two centres may be. */
export const MIN_DIST = 2 * BATTLE.arena.bodyRadius * CENTI

export const isDuel = (state: BattleState): boolean => state.mode === 'duel'

/** Centre-to-centre distance in centi-units (exactly |dx| on the line). */
export function centreDist(a: FighterState, b: FighterState): number {
  const dx = b.x - a.x
  const dy = b.y - a.y
  if (dy === 0) return Math.abs(dx)
  return Math.round(Math.sqrt(dx * dx + dy * dy))
}

/** The unit vector from `f` toward `opp` (duel); +x when they stand on top of each other. */
export function towardUnit(f: FighterState, opp: FighterState): { ux: number; uy: number } {
  const dx = opp.x - f.x
  const dy = opp.y - f.y
  const d = Math.sqrt(dx * dx + dy * dy)
  if (d === 0) return { ux: f.side === 0 ? 1 : -1, uy: 0 }
  return { ux: dx / d, uy: dy / d }
}

/** Keeps a body centre inside the ring (duel). */
export function clampToRing(f: FighterState): void {
  const r2 = f.x * f.x + f.y * f.y
  if (r2 <= WALL * WALL) return
  const r = Math.sqrt(r2)
  // toward zero, so rounding can never leave it a fraction outside
  f.x = Math.trunc((f.x * WALL) / r)
  f.y = Math.trunc((f.y * WALL) / r)
}

/** Never closer than two body radii: steps `f` back out along the line from `opp` (duel). */
function keepApart(f: FighterState, opp: FighterState): void {
  const dx = f.x - opp.x
  const dy = f.y - opp.y
  const d = Math.sqrt(dx * dx + dy * dy)
  if (d >= MIN_DIST) return
  if (d === 0) {
    f.x = opp.x + (f.side === 0 ? -MIN_DIST : MIN_DIST)
    return
  }
  f.x = opp.x + Math.round((dx * MIN_DIST) / d)
  f.y = opp.y + Math.round((dy * MIN_DIST) / d)
}

/** Duel: moves `f` by `d` centi-units along the line toward `opp` (negative = away), inside the ring, never through `opp`. */
export function moveAlongAxis(f: FighterState, opp: FighterState, d: number): void {
  const { ux, uy } = towardUnit(f, opp)
  let step = d
  if (step > 0) step = Math.min(step, Math.max(0, centreDist(f, opp) - MIN_DIST))
  f.x += Math.round(step * ux)
  f.y += Math.round(step * uy)
  clampToRing(f)
  keepApart(f, opp)
  clampToRing(f)
}

/**
 * Duel: strafes `f` by `s` centi-units sideways (+ = to its left as it faces `opp`), then sets the distance back
 * to what it was, so the move circles the opponent and the gap does not change.
 */
export function strafeAround(f: FighterState, opp: FighterState, s: number): void {
  const before = centreDist(f, opp)
  const { ux, uy } = towardUnit(f, opp)
  // left of the facing direction (ux, uy) is (−uy, ux)
  const px = f.x + Math.round(-uy * s)
  const py = f.y + Math.round(ux * s)
  const dx = px - opp.x
  const dy = py - opp.y
  const d = Math.sqrt(dx * dx + dy * dy)
  if (d === 0) return
  f.x = opp.x + Math.round((dx * before) / d)
  f.y = opp.y + Math.round((dy * before) / d)
  clampToRing(f)
  keepApart(f, opp)
  clampToRing(f)
}

/** Duel: a sidestep's move this tick, `s` centi-units straight sideways (+ = left), inside the ring. */
export function sidestepMove(f: FighterState, opp: FighterState, s: number): void {
  const { ux, uy } = towardUnit(f, opp)
  f.x += Math.round(-uy * s)
  f.y += Math.round(ux * s)
  clampToRing(f)
  keepApart(f, opp)
  clampToRing(f)
}

/** Duel: the direction a knocked-back fighter slides, away from `from`, in thousandths. */
export function slideVector(target: FighterState, from: FighterState): { vx: number; vy: number } {
  const { ux, uy } = towardUnit(from, target)
  return { vx: Math.round(ux * 1000), vy: Math.round(uy * 1000) }
}

/** Duel: one tick of a slide along (vx, vy)/1000. */
export function slideStep(f: FighterState, opp: FighterState, perTick: number): void {
  f.x += Math.round((perTick * f.slideVX) / 1000)
  f.y += Math.round((perTick * f.slideVY) / 1000)
  clampToRing(f)
  keepApart(f, opp)
  clampToRing(f)
}

/** Line: the original wall clamp. */
export function clampLine(x: number): number {
  return clamp(x, -WALL, WALL)
}

/** Whole units of room behind `f` (away from `opp`) before the wall or ring edge. */
export function roomBehindUnits(state: BattleState, f: FighterState, opp: FighterState): number {
  if (!isDuel(state)) return BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius - Math.floor(Math.abs(f.x) / CENTI)
  // the ray from f straight away from opp, to the ring edge: |p + t·w| = WALL with w = −toward
  const { ux, uy } = towardUnit(f, opp)
  const wx = -ux
  const wy = -uy
  const pw = f.x * wx + f.y * wy
  const disc = pw * pw - (f.x * f.x + f.y * f.y - WALL * WALL)
  const t = disc <= 0 ? 0 : -pw + Math.sqrt(disc)
  return Math.floor(Math.max(0, t) / CENTI)
}

/**
 * Duel: how far (centi-units) `p` stands from the line of a technique aimed from `a` at `d` (the attacker's and the
 * defender's centres when it was fired). A straight-line technique misses when the defender is farther than its
 * path's half-width (docs/BATTLE_3D.md §3).
 */
export function offsetFromAim(ax: number, ay: number, dx: number, dy: number, px: number, py: number): number {
  const lx = dx - ax
  const ly = dy - ay
  const len = Math.sqrt(lx * lx + ly * ly)
  if (len === 0) return Math.round(Math.sqrt((px - dx) * (px - dx) + (py - dy) * (py - dy)))
  return Math.round(Math.abs(lx * (py - ay) - ly * (px - ax)) / len)
}

/** Which way is "left" of `f` relative to the ring centre: +1 when its left points away from the centre. */
export function leftIsOutward(f: FighterState, opp: FighterState): boolean {
  const { ux, uy } = towardUnit(f, opp)
  return -uy * f.x + ux * f.y > 0
}
