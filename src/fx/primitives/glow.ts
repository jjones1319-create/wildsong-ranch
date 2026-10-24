import { Sprite } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import { FRAME } from '../atlas.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { scaled, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, GlowParams } from './types.ts'

const CELL_PX = 64

/** #12 glow: a soft additive aura at a point: breathing (charging, specials) or shrinking inward (a drain). */
export function glow(ctx: FxContext, p: GlowParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const radius = scaled(p.radius ?? FX.glow.radius, str)
  const duration = p.durationMs ?? FX.glow.durationMs
  const pulse = p.pulse ?? false
  const inward = p.inward ?? false
  const outer = new Sprite(ctx.atlas.frames[FRAME.softDot]!)
  outer.anchor.set(0.5)
  outer.blendMode = 'add'
  outer.tint = style.glow
  const inner = new Sprite(ctx.atlas.frames[FRAME.softDot]!)
  inner.anchor.set(0.5)
  inner.blendMode = 'add'
  inner.tint = style.core
  outer.position.set(p.x, p.y)
  inner.position.set(p.x, p.y)
  ctx.shapes.addChild(outer, inner)
  const base = (radius * 2) / (CELL_PX * 0.7)
  return timed(
    duration,
    (prog) => {
      const env = prog < 0.2 ? prog / 0.2 : prog > 0.6 ? (1 - prog) / 0.4 : 1
      let s = base
      if (inward) s = base * (1.5 - 1.3 * prog)
      else if (pulse) s = base * (1 + 0.12 * Math.sin(prog * duration * 0.001 * FX.glow.pulseHz * Math.PI * 2))
      outer.scale.set(s)
      outer.alpha = FX.glow.alpha * env * (inward ? 0.6 + 0.4 * prog : 1)
      inner.scale.set(s * 0.45)
      inner.alpha = 0.7 * env
    },
    () => {
      outer.destroy()
      inner.destroy()
    },
  )
}
