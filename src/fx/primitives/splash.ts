import { FX } from '../../data/tuning.ts'
import { FRAME } from '../atlas.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { DONE, scaled, spawnParticle, strengthOf } from './helpers.ts'
import type { EffectHandle, SplashParams } from './types.ts'

/** #8 splash: a crown of droplets thrown up and out, ripple rings on the ground and a puff of mist. */
export function splash(ctx: FxContext, p: SplashParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const size = scaled(p.size ?? FX.splash.size, str)
  const n = ctx.allowance(Math.round(scaled(FX.splash.drops, str)))
  for (let i = 0; i < n; i++) {
    // The crown: mostly upward, a few sideways.
    const a = -Math.PI / 2 + ctx.rng.range(-1.1, 1.1) * (i % 4 === 0 ? 1.4 : 1)
    const v = scaled(FX.splash.speed, str) * ctx.rng.range(0.4, 1)
    spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-14, 14), y: p.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, gravity: FX.splash.gravity, drag: 0.95, lifeMs: FX.splash.lifeMs * ctx.rng.range(0.7, 1.1), size0: size * ctx.rng.range(0.7, 1.3), size1: size * 0.5, fadeIn: 0, fadeFrom: 0.6, rotation: a + Math.PI / 2, spin: ctx.rng.range(-2, 2), frame: FRAME.droplet, bounce: 0.3 }, style)
  }
  const mist = ctx.allowance(4)
  for (let i = 0; i < mist; i++) {
    spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-20, 20), y: p.y - 10, vx: ctx.rng.range(-40, 40), vy: ctx.rng.range(-90, -30), gravity: -20, drag: 0.6, lifeMs: 900, size0: size * 3, size1: size * 7, fadeIn: 0.2, fadeFrom: 0.4, frame: FRAME.puff, additive: false, alpha: 0.45 }, style)
  }
  for (let i = 0; i < FX.splash.rings; i++) {
    ctx.fire({ name: 'ring', params: { element: p.element, x: p.x, y: Math.min(0, p.y + 60), radius: scaled(120, str) * (1 + i * 0.4), thickness: 6, ground: true, durationMs: 420, strength: str }, delayMs: i * 90 })
  }
  return DONE
}
