import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { DONE, scaled, spawnParticle, strengthOf } from './helpers.ts'
import type { BurstParams, EffectHandle } from './types.ts'

/** #1 burst: a one-shot radial spray of sparks, shards, droplets or petals (Dark pulls inward). */
export function burst(ctx: FxContext, p: BurstParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const n = ctx.allowance(Math.round(scaled(p.count ?? FX.burst.count, str) * style.density))
  const speed = scaled(p.speed ?? FX.burst.speed, str)
  const spread = p.spread ?? FX.burst.spread
  const centre = p.dir ?? -Math.PI / 2
  const gravity = (p.gravity ?? FX.burst.gravity) * style.gravity
  const life = p.lifeMs ?? FX.burst.lifeMs
  const size = scaled(p.size ?? FX.burst.size, str)
  const inward = p.inward ?? style.inward
  const frame = p.chunky ? style.debris : style.spark
  for (let i = 0; i < n; i++) {
    const a = centre + ctx.rng.range(-spread / 2, spread / 2)
    const v = speed * ctx.rng.range(0.45, 1)
    if (inward) {
      const r = ctx.rng.range(60, 140) * (0.6 + str)
      const sx = p.x + Math.cos(a) * r
      const sy = p.y + Math.sin(a) * r
      spawnParticle(ctx, { element: p.element, x: sx, y: sy, vx: -Math.cos(a) * v * 0.9, vy: -Math.sin(a) * v * 0.9, gravity: 0, drag: 0.6, lifeMs: life * 1.1, size0: size * 0.5, size1: size * 1.3, fadeIn: 0.15, fadeFrom: 0.6, frame, spin: ctx.rng.range(-3, 3) }, style)
    } else {
      spawnParticle(ctx, { element: p.element, x: p.x, y: p.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, gravity, drag: 0.85, lifeMs: life * ctx.rng.range(0.7, 1.15), size0: size * ctx.rng.range(0.7, 1.2), size1: size * 0.35, rotation: ctx.rng.range(0, Math.PI * 2), spin: ctx.rng.range(-6, 6), frame }, style)
    }
  }
  return DONE
}
