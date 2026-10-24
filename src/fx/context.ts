import type { Container } from 'pixi.js'
import type { FxCamera } from './camera.ts'
import type { ParticleLayer } from './emitter.ts'
import type { FilterRig } from './filters.ts'
import type { PrimitiveCall } from './primitives/types.ts'
import type { FlashGate, IntensityProfile, QualityBudget } from './quality.ts'
import type { FxRng } from './rng.ts'
import type { Atlas } from './textures.ts'

/** What the arena DOM does for the layer: the three effects that have to move or tint the monsters themselves. */
export interface FxHooks {
  shake(dx: number, dy: number): void
  hitstop(on: boolean): void
  /** `color` is a CSS colour for the two-tone overlay. */
  impactFrame(on: boolean, color: string): void
}

/** Everything a primitive may touch. Primitives never reach the renderer or the DOM directly. */
export interface FxContext {
  /** World-space containers (arena units; the layer scales them with the camera). Shapes sit between the two particle banks. */
  world: Container
  shapes: Container
  /** Screen-space container in CSS pixels (flash). */
  screen: Container
  particles: ParticleLayer
  atlas: Atlas
  rng: FxRng
  filters: FilterRig
  flashGate: FlashGate
  readonly budget: QualityBudget
  readonly profile: IntensityProfile
  /** The fx clock in ms (scaled by playback speed, frozen by pause). */
  readonly now: number
  camera(): FxCamera
  /** How many particles an effect may spawn right now for a wish of `n`. */
  allowance(n: number): number
  addShake(dx: number, dy: number): void
  hitstop(ms: number): void
  impactFrame(ms: number, color: number): void
  /** Fire another primitive (a projectile's landing, a cone's haze). */
  fire(call: PrimitiveCall): void
}
