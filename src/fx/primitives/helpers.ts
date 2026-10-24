import type { Element } from '../../data/types.ts'
import type { FxContext } from '../context.ts'
import { rampIndex, styleOf, type ElementStyle } from '../elements.ts'
import type { SpawnSpec } from '../sim.ts'
import type { EffectHandle } from './types.ts'

/** A primitive that did all its work on spawn (its particles live on in the sim). */
export const DONE: EffectHandle = { update: () => false, dispose() {} }

export function strengthOf(s: number | undefined): number {
  return Math.max(0, Math.min(1, s ?? 0.6))
}

/** Scale a default by strength: 0 → ×0.5, 0.6 → ×1, 1 → ×1.4. */
export function scaled(base: number, strength: number): number {
  return base * (0.5 + strength * 0.9)
}

export interface SpawnDefaults {
  element: Element
  x: number
  y: number
  vx?: number
  vy?: number
  gravity?: number
  drag?: number
  lifeMs?: number
  size0?: number
  size1?: number
  rotation?: number
  spin?: number
  fadeIn?: number
  fadeFrom?: number
  frame?: number
  ramp?: number
  additive?: boolean
  bounce?: number
  alpha?: number
}

/** Spawn one particle with the element's style filling in whatever the caller left out. */
export function spawnParticle(ctx: FxContext, d: SpawnDefaults, style: ElementStyle = styleOf(d.element)): boolean {
  const spec: SpawnSpec = {
    x: d.x,
    y: d.y,
    vx: d.vx ?? 0,
    vy: d.vy ?? 0,
    gravity: d.gravity ?? 0,
    drag: d.drag ?? 1,
    lifeMs: d.lifeMs ?? 600,
    size0: d.size0 ?? 10,
    size1: d.size1 ?? (d.size0 ?? 10) * 0.4,
    rotation: d.rotation ?? 0,
    spin: d.spin ?? 0,
    fadeIn: d.fadeIn ?? 0.05,
    fadeFrom: d.fadeFrom ?? 0.5,
    frame: d.frame ?? style.spark,
    ramp: d.ramp ?? rampIndex(d.element),
    seed: ctx.rng.next(),
    additive: (d.additive ?? style.additive) ? 1 : 0,
    bounce: d.bounce ?? 0,
    alpha: d.alpha ?? 1,
  }
  return ctx.particles.spawn(spec)
}

/** A handle that runs `step(progress, dtMs)` for `durationMs` then disposes. */
export function timed(durationMs: number, step: (p: number, dtMs: number) => void, dispose: () => void): EffectHandle {
  let t = 0
  let alive = true
  return {
    update(dt) {
      if (!alive) return false
      t += dt
      const p = Math.min(1, t / durationMs)
      step(p, dt)
      if (t >= durationMs) {
        alive = false
        dispose()
        return false
      }
      return true
    },
    dispose() {
      if (!alive) return
      alive = false
      dispose()
    },
  }
}

/** Smooth ease-out (fast start, gentle end). */
export function easeOut(p: number): number {
  return 1 - (1 - p) * (1 - p)
}

export function easeIn(p: number): number {
  return p * p
}

/** Point on a lobbed path from A to B at progress p (arc in world units, negative = up). */
export function arcPoint(ax: number, ay: number, bx: number, by: number, arc: number, p: number): { x: number; y: number } {
  return { x: ax + (bx - ax) * p, y: ay + (by - ay) * p - arc * 4 * p * (1 - p) }
}
