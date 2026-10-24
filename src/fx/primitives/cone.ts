import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { SMOKE_RAMP, styleOf } from '../elements.ts'
import { FRAME } from '../atlas.ts'
import { scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { ConeParams, EffectHandle } from './types.ts'

/** #2 cone: a continuous directional spray (flame breath, water jet, dust) with optional heat haze. */
export function cone(ctx: FxContext, p: ConeParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const duration = p.durationMs ?? FX.cone.durationMs
  const rate = scaled(p.ratePerSec ?? FX.cone.ratePerSec, str) * style.density
  const speed = scaled(p.speed ?? FX.cone.speed, str)
  const half = p.halfAngle ?? FX.cone.halfAngle
  const size = scaled(p.size ?? FX.cone.size, str)
  const reach = (speed * FX.cone.lifeMs) / 1000
  if (p.haze !== false && style.haze) {
    const w = reach * 0.9
    const x0 = Math.cos(p.dir) >= 0 ? p.x : p.x - w
    ctx.filters.addHaze(x0, p.y - reach * 0.5, w, reach * 0.8, str, duration + 200, ctx.now)
  }
  let acc = 0
  let smokeTick = 0
  return timed(
    duration,
    (prog, dt) => {
      // Ramp up quickly, trail off toward the end.
      const envelope = prog < 0.15 ? prog / 0.15 : prog > 0.75 ? (1 - prog) / 0.25 : 1
      acc += (rate * dt * envelope) / 1000
      let n = Math.floor(acc)
      acc -= n
      n = ctx.allowance(n)
      for (let i = 0; i < n; i++) {
        const a = p.dir + ctx.rng.range(-half, half) * ctx.rng.range(0.3, 1)
        const v = speed * ctx.rng.range(0.6, 1.05)
        spawnParticle(ctx, { element: p.element, x: p.x + ctx.rng.range(-6, 6), y: p.y + ctx.rng.range(-8, 8), vx: Math.cos(a) * v, vy: Math.sin(a) * v, gravity: FX.burst.gravity * style.gravity * 0.6, drag: FX.cone.drag, lifeMs: FX.cone.lifeMs * ctx.rng.range(0.7, 1.1), size0: size * 0.5, size1: size * 1.7, fadeIn: 0.08, fadeFrom: 0.45, spin: ctx.rng.range(-2, 2), rotation: a }, style)
      }
      if (style.trailSmoke && ++smokeTick % 3 === 0 && ctx.allowance(1) > 0) {
        const a = p.dir + ctx.rng.range(-half, half)
        spawnParticle(ctx, { element: p.element, x: p.x + Math.cos(a) * reach * 0.4, y: p.y + Math.sin(a) * reach * 0.4, vx: Math.cos(a) * speed * 0.25, vy: Math.sin(a) * speed * 0.25 - 60, gravity: -80, drag: 0.7, lifeMs: 900, size0: size * 1.2, size1: size * 3.2, fadeIn: 0.2, fadeFrom: 0.4, frame: FRAME.puff, ramp: SMOKE_RAMP, additive: false, spin: ctx.rng.range(-1, 1), alpha: 0.55 }, style)
      }
    },
    () => {},
  )
}
