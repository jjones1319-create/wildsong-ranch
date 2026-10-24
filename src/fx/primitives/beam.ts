import { Graphics } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { scaled, strengthOf, timed } from './helpers.ts'
import type { BeamParams, EffectHandle } from './types.ts'

/** #5 beam: an instant line from A to B with a wide glow, a mid pass and a bright core, its edge trembling. */
export function beam(ctx: FxContext, p: BeamParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const width = scaled(p.width ?? FX.beam.width, str)
  const duration = p.durationMs ?? FX.beam.durationMs
  const jitter = p.jitter ?? FX.beam.jitter
  const g = new Graphics()
  g.blendMode = 'add'
  ctx.shapes.addChild(g)
  const dx = p.to.x - p.x
  const dy = p.to.y - p.y
  const len = Math.hypot(dx, dy) || 1
  const nx = -dy / len
  const ny = dx / len
  const segments = 10
  let shimmer = 0
  const offsets = new Float32Array(segments + 1)
  const reroll = () => {
    for (let i = 1; i < segments; i++) offsets[i] = ctx.rng.range(-jitter, jitter)
  }
  reroll()
  return timed(
    duration,
    (prog, dt) => {
      shimmer += dt
      if (shimmer > 40) {
        shimmer = 0
        reroll()
      }
      // Grow in fast, hold, then thin out.
      const env = prog < 0.12 ? prog / 0.12 : prog > 0.55 ? 1 - (prog - 0.55) / 0.45 : 1
      const reach = Math.min(1, prog / 0.1)
      g.clear()
      const passes: [number, number, number][] = [
        [width * 2.6 * env, 0.22, style.glow],
        [width * 1.3 * env, 0.6, style.ramp[1]!],
        [width * 0.45 * env + 1, 1, style.core],
      ]
      for (const [w, a, color] of passes) {
        g.moveTo(p.x, p.y)
        for (let i = 1; i <= segments; i++) {
          const t = (i / segments) * reach
          const o = offsets[i]! * (i === segments ? 0 : 1)
          g.lineTo(p.x + dx * t + nx * o, p.y + dy * t + ny * o)
        }
        g.stroke({ width: Math.max(1, w), color, alpha: a * env, cap: 'round', join: 'round' })
      }
      // A bright muzzle dot.
      g.circle(p.x, p.y, width * 1.1 * env).fill({ color: style.core, alpha: 0.9 * env })
    },
    () => g.destroy(),
  )
}
