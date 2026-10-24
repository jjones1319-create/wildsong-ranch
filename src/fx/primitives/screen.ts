import { Graphics } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import type { FxContext } from '../context.ts'
import { styleOf } from '../elements.ts'
import { FlashGate, shakeOffset } from '../quality.ts'
import { DONE, timed } from './helpers.ts'
import type { EffectHandle, FlashParams, HitstopParams, ImpactFrameParams, ShakeParams } from './types.ts'

/** #15 flash: a screen-wide tint, alpha capped (§24) and rate-limited to 3 a second; silently skipped otherwise. */
export function flash(ctx: FxContext, p: FlashParams): EffectHandle {
  const alpha = FlashGate.clampAlpha(Math.min(p.alpha ?? ctx.profile.flashAlpha, ctx.profile.flashAlpha))
  if (alpha <= 0 || !ctx.flashGate.allow(ctx.now)) return DONE
  const style = styleOf(p.element)
  const g = new Graphics()
  ctx.screen.addChild(g)
  const ms = p.ms ?? FX.flash.defaultMs
  return timed(
    ms,
    (prog) => {
      const cam = ctx.camera()
      g.clear()
      g.rect(0, 0, cam.width, cam.height).fill({ color: style.core, alpha: alpha * (1 - prog) })
    },
    () => g.destroy(),
  )
}

/** #16 shake: a decaying offset the arena applies to monsters and canvas together (0 under reduced motion). */
export function shake(ctx: FxContext, p: ShakeParams): EffectHandle {
  const amp = Math.min(ctx.profile.shakePx * 2, p.amplitudePx ?? ctx.profile.shakePx)
  if (amp <= 0) return DONE
  const ms = p.ms ?? FX.shake.durationMs
  let t = 0
  return timed(
    ms,
    (_prog, dt) => {
      t += dt
      const o = shakeOffset(t, amp, ms)
      ctx.addShake(o.dx, o.dy)
    },
    () => {},
  )
}

/** #17 hitstop: freeze the fx clock and the monsters' CSS animations for a moment (the simulation keeps going). */
export function hitstop(ctx: FxContext, p: HitstopParams): EffectHandle {
  const ms = p.ms ?? ctx.profile.hitstopMs
  if (ms > 0) ctx.hitstop(ms)
  return DONE
}

/** #18 impactFrame: one or two frames of a two-tone overlay on the arena (a DOM overlay, so it covers the monsters). */
export function impactFrame(ctx: FxContext, p: ImpactFrameParams): EffectHandle {
  if (ctx.profile.impactFrames === 'off') return DONE
  const frames = p.frames ?? FX.impactFrame.frames
  ctx.impactFrame(Math.round(frames * 16.7), styleOf(p.element).core)
  return DONE
}
