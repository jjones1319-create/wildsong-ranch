import { Graphics } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { easeOut, scaled, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, RingParams } from './types.ts'

/** #6 ring: an expanding ring (or a flattened ground shockwave) that thins and fades; several when `count` > 1. */
export function ring(ctx: FxContext, p: RingParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const radius = scaled(p.radius ?? FX.ring.radius, str)
  const thickness = scaled(p.thickness ?? FX.ring.thickness, str)
  const duration = p.durationMs ?? FX.ring.durationMs
  const count = Math.max(1, Math.min(4, p.count ?? 1))
  const squash = p.ground ? FX.ring.groundSquash : 1
  const g = new Graphics()
  g.blendMode = style.additive ? 'add' : 'normal'
  ctx.shapes.addChild(g)
  if (p.ground && ctx.budget.filters !== 'none') {
    const cam = ctx.camera()
    ctx.filters.shockwave((p.x - cam.centre) * cam.pxPerUnit + cam.width / 2, cam.height - cam.floorPx + p.y * cam.pxPerUnit, str, ctx.now)
  }
  const stagger = count > 1 ? 0.22 : 0
  return timed(
    duration * (1 + stagger * (count - 1)),
    (prog) => {
      g.clear()
      for (let i = 0; i < count; i++) {
        const local = (prog * (1 + stagger * (count - 1)) - stagger * i) / 1
        if (local <= 0 || local >= 1) continue
        const e = easeOut(local)
        const r = radius * (0.15 + 0.85 * e)
        const alpha = (1 - local) * (1 - local) * 0.95
        const w = Math.max(1.5, thickness * (1 - local * 0.7))
        g.ellipse(p.x, p.y, r, r * squash).stroke({ width: w, color: style.ramp[1]!, alpha })
        g.ellipse(p.x, p.y, r * 0.96, r * squash * 0.96).stroke({ width: Math.max(1, w * 0.4), color: style.core, alpha: alpha * 0.9 })
      }
    },
    () => g.destroy(),
  )
}
