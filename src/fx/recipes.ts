import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { BATTLE_FX, FX } from '../data/tuning.ts'
import type { FxEvent } from './bus.ts'
import { styleOf } from './elements.ts'
import type { IntensityProfile } from './quality.ts'
import type { PrimitiveCall } from './primitives/types.ts'

/**
 * V1's default recipe per element for each battle moment (VISUAL_V1_EFFECTS §3, §5 "immediate payoff"). Pure data:
 * an FxEvent in, a list of primitive calls (with delays) out. V2 replaces these with per-technique recipes.
 */

/** How long a ranged attack takes to reach the target (world units/s → ms), never shorter than the minimum. */
export function travelMs(fromX: number, toX: number): number {
  return Math.max(FX.projectile.minMs, Math.round((Math.abs(toX - fromX) / FX.projectile.speedUnitsPerSec) * 1000))
}

/** Melee effects land part-way through the lunge. */
export const MELEE_LAND_MS = Math.round(BATTLE_FX.lungeMs * 0.45)

export function recipeFor(ev: FxEvent, profile: IntensityProfile): PrimitiveCall[] {
  const s = styleOf(ev.element)
  const el = ev.element
  const str = Math.max(0, Math.min(1, ev.strength))
  const dir = ev.to.x >= ev.from.x ? 1 : -1
  const calls: PrimitiveCall[] = []
  switch (ev.kind) {
    case 'fire': {
      if (ev.ranged) {
        const ms = travelMs(ev.from.x, ev.to.x)
        calls.push({ name: 'projectile', params: { element: el, x: ev.from.x + dir * 70, y: ev.from.y, to: ev.to, durationMs: ms, strength: str, onArrive: 'spark' } })
        if (el === 'Lightning') calls.push({ name: 'glow', params: { element: el, x: ev.from.x, y: ev.from.y, radius: 90, durationMs: 220, strength: 0.6 } })
      } else {
        calls.push({ name: 'burst', params: { element: 'Physical', x: ev.from.x - dir * 30, y: -6, count: 10, speed: 150, spread: Math.PI * 0.8, dir: Math.PI / 2 + dir * 0.8, gravity: 600, lifeMs: 420, size: 10, strength: 0.5 } })
        calls.push({ name: 'glow', params: { element: el, x: ev.from.x + dir * 40, y: ev.from.y, radius: 80 + 60 * str, durationMs: 260, strength: str } })
        if (el === 'Fire') calls.push({ name: 'cone', params: { element: el, x: ev.from.x + dir * 70, y: ev.from.y, dir: dir > 0 ? 0 : Math.PI, durationMs: 260, strength: 0.6 } })
      }
      break
    }
    case 'hit':
    case 'crit': {
      const crit = ev.kind === 'crit'
      const delay = ev.techId && isRanged(ev.techId) ? travelMs(ev.from.x, ev.to.x) : MELEE_LAND_MS
      const strength = crit ? Math.max(0.75, str) : str
      calls.push({ name: 'impact', params: { element: el, x: ev.to.x - dir * 30, y: ev.to.y, strength, crit }, delayMs: delay })
      if (crit) calls.push({ name: 'ring', params: { element: el, x: ev.to.x, y: ev.to.y, radius: 170, durationMs: 420, strength }, delayMs: delay })
      switch (el) {
        case 'Water':
          calls.push({ name: 'splash', params: { element: el, x: ev.to.x - dir * 20, y: ev.to.y + 20, strength }, delayMs: delay })
          break
        case 'Earth':
          calls.push({ name: 'debris', params: { element: el, x: ev.to.x - dir * 20, y: ev.to.y, strength }, delayMs: delay })
          calls.push({ name: 'ring', params: { element: el, x: ev.to.x, y: 0, radius: 150, ground: true, durationMs: 400, strength }, delayMs: delay })
          break
        case 'Lightning':
          calls.push({ name: 'lightning', params: { element: el, x: ev.to.x - dir * 60, y: ev.to.y - 160, to: { x: ev.to.x, y: ev.to.y }, branches: true, strength }, delayMs: delay })
          if (profile.flashAlpha > 0) calls.push({ name: 'flash', params: { element: el, alpha: profile.flashAlpha * (crit ? 1 : 0.6), ms: FX.flash.defaultMs }, delayMs: delay })
          break
        case 'Ice':
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 16, chunky: true, gravity: 900, lifeMs: 800, strength }, delayMs: delay })
          calls.push({ name: 'mist', params: { element: el, x: ev.to.x, y: ev.to.y, count: 4, durationMs: 800, strength: 0.5 }, delayMs: delay })
          break
        case 'Fire':
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 14, strength }, delayMs: delay })
          calls.push({ name: 'mist', params: { element: el, x: ev.to.x, y: ev.to.y - 30, count: 3, durationMs: 700, strength: 0.4 }, delayMs: delay + 80 })
          break
        case 'Wind':
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 14, speed: 420, chunky: true, gravity: 200, strength }, delayMs: delay })
          break
        case 'Nature':
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 16, speed: 240, gravity: 260, lifeMs: 900, strength }, delayMs: delay })
          break
        case 'Light':
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 14, speed: 280, strength }, delayMs: delay })
          calls.push({ name: 'glow', params: { element: el, x: ev.to.x, y: ev.to.y, radius: 120, durationMs: 300, strength }, delayMs: delay })
          break
        case 'Dark':
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 14, inward: true, strength }, delayMs: delay })
          calls.push({ name: 'mist', params: { element: el, x: ev.to.x, y: ev.to.y, count: 4, durationMs: 900, strength: 0.6 }, delayMs: delay })
          break
        case 'Sound':
          calls.push({ name: 'ring', params: { element: el, x: ev.to.x, y: ev.to.y, radius: 140, count: 3, durationMs: 520, strength }, delayMs: delay })
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 8, speed: 200, gravity: -100, strength }, delayMs: delay })
          break
        default:
          calls.push({ name: 'burst', params: { element: el, x: ev.to.x, y: ev.to.y, count: 12, strength }, delayMs: delay })
          break
      }
      if (profile.shakePx > 0) calls.push({ name: 'shake', params: { amplitudePx: profile.shakePx * s.shake * (0.5 + strength * (crit ? 1 : 0.6)), ms: FX.shake.durationMs, element: el }, delayMs: delay })
      if (profile.hitstopMs > 0 && (crit || strength >= 0.75)) calls.push({ name: 'hitstop', params: { ms: Math.round(profile.hitstopMs * (crit ? 1 : 0.6)) }, delayMs: delay })
      if (profile.impactFrames === 'heavy' ? crit || strength >= 0.75 : profile.impactFrames === 'crits' && crit) calls.push({ name: 'impactFrame', params: { element: el }, delayMs: delay })
      if (crit && profile.flashAlpha > 0 && el !== 'Lightning') calls.push({ name: 'flash', params: { element: el, alpha: profile.flashAlpha * 0.7, ms: FX.flash.defaultMs }, delayMs: delay })
      break
    }
    case 'wither':
      calls.push({ name: 'glow', params: { element: 'Dark', x: ev.to.x, y: ev.to.y, radius: 90 + 60 * str, durationMs: 520, inward: true, strength: str }, delayMs: MELEE_LAND_MS })
      break
    case 'miss':
      calls.push({ name: 'mist', params: { element: el, x: ev.to.x - dir * 90, y: ev.to.y - 40, count: 3, durationMs: 520, drift: 90 * dir, strength: 0.3 }, delayMs: ev.techId && isRanged(ev.techId) ? travelMs(ev.from.x, ev.to.x) : MELEE_LAND_MS })
      break
    case 'ko':
      calls.push({ name: 'debris', params: { element: 'Physical', x: ev.from.x, y: -40, count: 14, strength: 1 } })
      calls.push({ name: 'ring', params: { element: 'Physical', x: ev.from.x, y: 0, radius: 200, ground: true, durationMs: 520, strength: 1 } })
      calls.push({ name: 'burst', params: { element: 'Light', x: ev.from.x, y: -150, count: 8, speed: 120, gravity: -60, lifeMs: 1200, size: 14, strength: 0.6 } })
      if (profile.shakePx > 0) calls.push({ name: 'shake', params: { amplitudePx: profile.shakePx, ms: FX.shake.durationMs } })
      break
    case 'special':
      calls.push({ name: 'glow', params: { element: 'Light', x: ev.from.x, y: ev.from.y, radius: 170, durationMs: 900, pulse: true, strength: 0.9 } })
      calls.push({ name: 'ring', params: { element: 'Light', x: ev.from.x, y: 0, radius: 220, ground: true, durationMs: 600, strength: 0.8 } })
      calls.push({ name: 'burst', params: { element: 'Light', x: ev.from.x, y: -20, count: 18, speed: 160, gravity: -220, spread: Math.PI * 0.7, dir: -Math.PI / 2, lifeMs: 900, strength: 0.8 } })
      break
    case 'push':
      calls.push({ name: 'ring', params: { element: 'Physical', x: ev.to.x, y: 0, radius: 160, ground: true, durationMs: 380, strength: 0.6 } })
      calls.push({ name: 'cone', params: { element: 'Physical', x: ev.to.x, y: -8, dir: dir > 0 ? 0 : Math.PI, durationMs: 220, halfAngle: 0.25, speed: 300, strength: 0.6 } })
      break
    case 'dash':
      calls.push({ name: 'trail', params: { element: 'Wind', x: ev.from.x, y: -30, to: { x: ev.from.x + dir * 120, y: -30 }, durationMs: 260, strength: 0.6 } })
      calls.push({ name: 'burst', params: { element: 'Physical', x: ev.from.x - dir * 40, y: -6, count: 8, speed: 140, spread: Math.PI * 0.6, dir: Math.PI / 2 + dir * 1.1, gravity: 500, lifeMs: 420, strength: 0.4 } })
      break
    case 'heal':
      calls.push({ name: 'burst', params: { element: 'Light', x: ev.from.x, y: -30, count: 16, speed: 90, gravity: -140, spread: Math.PI * 0.6, dir: -Math.PI / 2, lifeMs: 1100, size: 12, strength: 0.7 } })
      calls.push({ name: 'glow', params: { element: 'Nature', x: ev.from.x, y: -90, radius: 140, durationMs: 800, pulse: true, strength: 0.6 } })
      break
    case 'distract':
      break
    case 'travel':
      break
  }
  return calls
}

function isRanged(techId: string): boolean {
  return (TECHNIQUE_BY_ID[techId]?.range ?? 1) >= 3
}

/** The Effects Lab's "Combo" (fire cone → impact → shake). */
export function comboRecipe(x: number, dir: 1 | -1, profile: IntensityProfile): PrimitiveCall[] {
  const tx = x + dir * 360
  return [
    { name: 'cone', params: { element: 'Fire', x: x + dir * 60, y: -100, dir: dir > 0 ? 0 : Math.PI, durationMs: 600, strength: 1, haze: true } },
    { name: 'impact', params: { element: 'Fire', x: tx, y: -100, strength: 1, crit: true }, delayMs: 380 },
    { name: 'burst', params: { element: 'Fire', x: tx, y: -100, count: 20, strength: 1 }, delayMs: 380 },
    { name: 'shake', params: { amplitudePx: profile.shakePx, ms: FX.shake.durationMs }, delayMs: 380 },
    ...(profile.hitstopMs > 0 ? [{ name: 'hitstop', params: { ms: profile.hitstopMs }, delayMs: 380 } as PrimitiveCall] : []),
    ...(profile.impactFrames !== 'off' ? [{ name: 'impactFrame', params: { element: 'Fire' }, delayMs: 380 } as PrimitiveCall] : []),
  ]
}
