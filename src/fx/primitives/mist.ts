import { FX } from '../../data/tuning.ts'
import { FRAME } from '../atlas.ts'
import type { FxContext } from '../context.ts'
import { SMOKE_RAMP, styleOf } from '../elements.ts'
import { DONE, scaled, spawnParticle, strengthOf } from './helpers.ts'
import type { EffectHandle, MistParams } from './types.ts'

/** #14 mist: slow, large, translucent puffs (fog, steam, smoke) that drift and thin out. */
export function mist(ctx: FxContext, p: MistParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const n = ctx.allowance(Math.round(scaled(p.count ?? FX.mist.count, str)))
  const life = p.durationMs ?? FX.mist.lifeMs
  const drift = p.drift ?? 0
  const size = scaled(p.size ?? FX.mist.size, str)
  // Fire smoke and Earth dust go grey; coloured elements keep a pale tint.
  const grey = p.element === 'Fire' || p.element === 'Earth' || p.element === 'Physical'
  for (let i = 0; i < n; i++) {
    spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-size * 0.6, size * 0.6), y: p.y + ctx.rng.range(-size * 0.3, size * 0.3), vx: drift + ctx.rng.range(-FX.mist.drift, FX.mist.drift), vy: ctx.rng.range(-50, -15), gravity: -8, drag: 0.7, lifeMs: life * ctx.rng.range(0.7, 1.15), size0: size * 0.6, size1: size * 1.8, fadeIn: 0.25, fadeFrom: 0.45, rotation: ctx.rng.range(0, Math.PI * 2), spin: ctx.rng.range(-0.6, 0.6), frame: FRAME.puff, ramp: grey ? SMOKE_RAMP : undefined, additive: false, alpha: FX.mist.alpha + 0.12 * str }, style)
  }
  return DONE
}
