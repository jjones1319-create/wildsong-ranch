import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { DONE, scaled, spawnParticle, strengthOf } from './helpers.ts'
import type { DebrisParams, EffectHandle } from './types.ts'

/** #13 debris: chunky pieces (rocks, ice, coins, leaves) thrown out that fall, bounce on the floor and settle. */
export function debris(ctx: FxContext, p: DebrisParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const n = ctx.allowance(Math.round(scaled(p.count ?? FX.debris.count, str)))
  const size = scaled(p.size ?? FX.debris.size, str)
  for (let i = 0; i < n; i++) {
    const a = -Math.PI / 2 + ctx.rng.range(-1.3, 1.3)
    const v = scaled(FX.debris.speed, str) * ctx.rng.range(0.5, 1.1)
    spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-20, 20), y: p.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, gravity: FX.debris.gravity * Math.max(0.6, style.gravity), drag: 0.98, lifeMs: FX.debris.lifeMs * ctx.rng.range(0.7, 1.1), size0: size * ctx.rng.range(0.6, 1.4), size1: size * 0.8, fadeIn: 0, fadeFrom: 0.75, rotation: ctx.rng.range(0, Math.PI * 2), spin: ctx.rng.range(-9, 9), frame: style.debris, additive: false, bounce: FX.debris.bounce }, style)
  }
  // A puff of dust where it all came from.
  const dust = ctx.allowance(3)
  for (let i = 0; i < dust; i++) {
    spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-20, 20), y: p.y, vx: ctx.rng.range(-50, 50), vy: ctx.rng.range(-60, -10), gravity: -10, drag: 0.6, lifeMs: 700, size0: size * 2, size1: size * 5, fadeIn: 0.15, fadeFrom: 0.4, frame: style.puff, additive: false, alpha: 0.5 }, style)
  }
  return DONE
}
