import { Graphics } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { boltWithBranches, type Bolt } from './boltPath.ts'
import { scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, LightningParams } from './types.ts'

/** #10 lightning: a midpoint-displaced bolt with branches, drawn in up to three glow passes, flickering. */
export function lightning(ctx: FxContext, p: LightningParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const passes = ctx.budget.lightningPasses
  const g = new Graphics()
  g.blendMode = 'add'
  ctx.shapes.addChild(g)
  const roll = (): Bolt[] => boltWithBranches(p.x, p.y, p.to.x, p.to.y, ctx.rng, p.branches ?? true)
  let bolts = roll()
  let frames = 0
  let flickerOff = false
  const n = ctx.allowance(Math.round(scaled(10, str)))
  for (let i = 0; i < n; i++) {
    const a = ctx.rng.range(0, Math.PI * 2)
    const v = ctx.rng.range(80, 320)
    spawnParticle(ctx, { element: p.element, x: p.to.x, y: p.to.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, gravity: 300, drag: 0.8, lifeMs: 420, size0: 8, size1: 2, fadeFrom: 0.3 }, style)
  }
  return timed(
    FX.lightning.durationMs,
    (prog) => {
      frames += 1
      if (frames % FX.lightning.flickerFrames === 0) {
        bolts = roll()
        flickerOff = ctx.rng.next() < 0.25
      }
      g.clear()
      if (flickerOff && prog > 0.3) return
      const fade = prog < 0.15 ? 1 : 1 - (prog - 0.15) / 0.85
      const w = scaled(1, str)
      for (const b of bolts) {
        const draw = (width: number, color: number, alpha: number) => {
          g.moveTo(b.points[0]!, b.points[1]!)
          for (let i = 2; i < b.points.length; i += 2) g.lineTo(b.points[i]!, b.points[i + 1]!)
          g.stroke({ width: Math.max(1, width * b.weight), color, alpha: alpha * fade, cap: 'round', join: 'round' })
        }
        if (passes >= 3) draw(FX.lightning.glowWidth * 1.8 * w, style.glow, 0.18)
        if (passes >= 2) draw(FX.lightning.glowWidth * 0.8 * w, style.ramp[1]!, 0.5)
        draw(FX.lightning.coreWidth * w, style.core, 1)
      }
    },
    () => g.destroy(),
  )
}
