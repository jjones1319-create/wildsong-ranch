import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { arcPoint, scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, TrailParams } from './types.ts'

/** #3 trail: a ribbon of fading particles left behind a point that travels from A to B. */
export function trail(ctx: FxContext, p: TrailParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const duration = p.durationMs ?? 300
  const width = scaled(p.width ?? FX.trail.size, str)
  const arc = p.arc ?? 0
  let acc = 0
  return timed(
    duration,
    (prog, dt) => {
      acc += (FX.trail.ratePerSec * dt) / 1000
      let n = Math.floor(acc)
      acc -= n
      n = ctx.allowance(n)
      for (let i = 0; i < n; i++) {
        const q = arcPoint(p.x, p.y, p.to.x, p.to.y, arc, Math.max(0, prog - (i / n) * (dt / duration)))
        spawnParticle(ctx, { element: p.element, x: q.x + ctx.rng.range(-width * 0.4, width * 0.4), y: q.y + ctx.rng.range(-width * 0.4, width * 0.4), vx: ctx.rng.range(-20, 20), vy: ctx.rng.range(-30, 10), gravity: 0, drag: 0.8, lifeMs: FX.trail.lifeMs, size0: width, size1: width * 0.2, fadeIn: 0, fadeFrom: 0.3, rotation: Math.atan2(p.to.y - p.y, p.to.x - p.x) }, style)
      }
    },
    () => {},
  )
}
