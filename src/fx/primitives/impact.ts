import { Graphics } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { easeOut, scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, ImpactParams } from './types.ts'

/** #7 impact: the hit spark: a white core flash, radial spikes in the element's colour, sparks and a small ring. */
export function impact(ctx: FxContext, p: ImpactParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const crit = p.crit ?? false
  const duration = FX.impact.durationMs * (crit ? 1.25 : 1)
  const spikes = FX.impact.spikes + (crit ? 4 : 0)
  const spikeLen = scaled(FX.impact.spikeLength, str) * (crit ? 1.35 : 1)
  const coreR = scaled(FX.impact.coreRadius, str) * (crit ? 1.3 : 1)
  const g = new Graphics()
  g.blendMode = 'add'
  ctx.shapes.addChild(g)
  const base = ctx.rng.range(0, Math.PI)
  const lens = Array.from({ length: spikes }, () => ctx.rng.range(0.55, 1))
  // Sparks fly out at once.
  const n = ctx.allowance(Math.round(scaled(14, str) * style.density) + (crit ? 6 : 0))
  for (let i = 0; i < n; i++) {
    const a = ctx.rng.range(0, Math.PI * 2)
    const v = scaled(300, str) * ctx.rng.range(0.4, 1)
    spawnParticle(ctx, { element: p.element, x: p.x, y: p.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, gravity: 500 * Math.max(0.2, style.gravity), drag: 0.8, lifeMs: 450 * ctx.rng.range(0.7, 1.2), size0: scaled(14, str), size1: 3, fadeFrom: 0.4, rotation: a, spin: ctx.rng.range(-8, 8) }, style)
  }
  if (crit) ctx.filters.rgbSplit(90, ctx.now)
  return timed(
    duration,
    (prog) => {
      g.clear()
      const e = easeOut(prog)
      const fade = (1 - prog) * (1 - prog)
      // Spikes: shoot out then retract from the centre.
      const outer = spikeLen * (0.2 + 0.8 * e)
      const inner = spikeLen * Math.max(0, e - 0.35) * 1.2
      for (let i = 0; i < spikes; i++) {
        const a = base + (i / spikes) * Math.PI * 2
        const l = lens[i]!
        g.moveTo(p.x + Math.cos(a) * inner * l, p.y + Math.sin(a) * inner * l)
        g.lineTo(p.x + Math.cos(a) * outer * l, p.y + Math.sin(a) * outer * l)
      }
      g.stroke({ width: Math.max(1.5, 7 * fade), color: style.ramp[1]!, alpha: 0.9 * fade, cap: 'round' })
      // Core: a bright disc that pops then shrinks.
      const r = coreR * (prog < 0.15 ? prog / 0.15 : 1 - (prog - 0.15) / 0.85)
      if (r > 0) {
        g.circle(p.x, p.y, r * 2).fill({ color: style.glow, alpha: 0.4 * fade })
        g.circle(p.x, p.y, r).fill({ color: style.core, alpha: 0.95 * Math.min(1, fade * 1.6) })
      }
      // A thin ring that races out.
      const rr = coreR * 0.5 + spikeLen * 0.9 * e
      g.circle(p.x, p.y, rr).stroke({ width: Math.max(1, 4 * fade), color: style.core, alpha: 0.6 * fade })
    },
    () => g.destroy(),
  )
}
