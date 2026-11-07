import type { Vector3 } from 'three'
import { ART } from '../../data/tuning.ts'
import { styleOf } from '../../fx/elements.ts'
import { CELL, type AttackFxRecipe } from './fxRecipe.ts'
import { FACE, FADE, noise } from './fxParticles.ts'
import { from, grow, many, part, puffs, ring, tint, type FxCtx } from './fxSpawn.ts'

/**
 * docs/BATTLE_3D.md §7: a miss, easy to see but not loud (the owner, Nov 3: "a missed projectile is easy to
 * overlook"). With the veer and dip of the projectile itself (fxParticles.ts, attackFx.ts), a whoosh of air rushes
 * past the target's side, and where the shot comes down a small puff of dust and a few of the element's bits fizzle out.
 * Solid shapes only (no flash), so it reads in sunlight without shouting.
 */

const M = ART.duel.fx.miss
const TAU = Math.PI * 2

/** A whoosh: a few streaks of air rushing on along the blow (`dir`) past `at`, beside the target. */
export function whoosh(c: FxCtx, r: AttackFxRecipe, at: Vector3, dir: Vector3, t0: number, S: number): void {
  for (let i = 0, n = many(c, M.streaks); i < n; i++) {
    const s = c.seed + 800 + i * 3
    const back = (noise(s) - 0.6) * 0.5 * S
    const p = grow(tint(from(part(c, CELL.streak, false, t0 + i * 0.03, 0.22 * c.q.life), at, dir.x * back, (noise(s + 1) - 0.5) * 0.4 * S, dir.z * back), 0xffffff, r.ramp[1]!, 0.9), 0.15 * S, 0.06 * S)
    const v = 4 + 2 * noise(s + 2)
    p.vx = dir.x * v
    p.vz = dir.z * v
    p.face = FACE.stretch
    p.stretch = 3.4
    p.fade = FADE.hold
  }
}

/**
 * Where a missed shot comes down (`at`, on the floor): a faint dust ring, a small puff (the element's own smoke turning
 * to dust; plain sand for a blow that only kicked the floor, `dust`), and a few of its bits fizzling out.
 */
export function fizzle(c: FxCtx, r: AttackFxRecipe, at: Vector3, t0: number, S: number, dust = false): void {
  const L = c.q.life
  const sand = styleOf('Earth').smoke
  ring(c, at, sand, false, 0.1 * S, 0.65 * S, t0, 0.32 * L).a = 0.65
  puffs(c, at, many(c, M.puffs), dust ? sand : r.smoke, sand, 0.65, 0.08 * S, 0.3 * S, t0, 0.55 * L, 0.35, 0.45, c.seed + 820)
  const k = r.look
  for (let i = 0, n = many(c, M.bits); i < n; i++) {
    const s = c.seed + 840 + i * 3
    const a = noise(s) * TAU
    const p = grow(tint(from(part(c, k.cell, false, t0, 0.42 * L), at, 0, 0.05, 0), r.ramp[1]!, r.ramp[2]!, 0.95), 0.075 * S, 0.035 * S)
    p.vx = Math.cos(a) * 0.7
    p.vz = Math.sin(a) * 0.7
    p.vy = 1.3 + 0.5 * noise(s + 1)
    p.g = 7
    p.rot = noise(s + 2) * TAU
    p.face = k.stretch ? FACE.stretch : FACE.camera
    p.stretch = k.stretch ? 1.8 : 1
    p.fade = FADE.hold
  }
}
