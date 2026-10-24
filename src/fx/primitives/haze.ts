import { FX } from '../../data/tuning.ts'
import { FRAME } from '../atlas.ts'
import type { FxContext } from '../context.ts'
import { SMOKE_RAMP, styleOf } from '../elements.ts'
import { scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, HazeParams } from './types.ts'

/**
 * #11 haze: heat distortion (or an underwater wobble) over a region. With filters it is a displacement map;
 * without them (Lite) it falls back to faint translucent puffs drifting up, so the moment still reads.
 */
export function haze(ctx: FxContext, p: HazeParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const w = p.width ?? 220
  const h = p.height ?? 260
  const duration = p.durationMs ?? FX.haze.durationMs
  ctx.filters.addHaze(p.x - w / 2, p.y - h / 2, w, h, scaled(0.8, str), duration, ctx.now)
  let acc = 0
  return timed(
    duration,
    (prog, dt) => {
      // The fallback shimmer: very faint, slow, large puffs; also a nice complement when filters are on.
      acc += (dt * (ctx.filters.hasHaze ? 10 : 26)) / 1000
      let n = Math.floor(acc)
      acc -= n
      n = ctx.allowance(n)
      const env = prog > 0.7 ? (1 - prog) / 0.3 : 1
      for (let i = 0; i < n; i++) {
        spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-w / 2, w / 2), y: p.y + ctx.rng.range(-h / 4, h / 2), vx: ctx.rng.range(-15, 15), vy: ctx.rng.range(-70, -30), gravity: -30, drag: 0.9, lifeMs: 900, size0: 40, size1: 90, fadeIn: 0.3, fadeFrom: 0.5, frame: FRAME.puff, ramp: style.haze ? undefined : SMOKE_RAMP, additive: style.additive, alpha: 0.22 }, style)
      }
      void env
    },
    () => {},
  )
}
