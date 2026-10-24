import type { Element } from '../../data/types.ts'
import type { ProjectileShape } from '../elements.ts'

/**
 * The 18 primitives' parameters (VISUAL_V1_EFFECTS §4). World units, y down with 0 on the floor, angles in
 * radians with 0 pointing right. `strength` (0..1) scales counts, sizes and durations around the defaults.
 * These are plain data so recipes can be built and tested without Pixi.
 */
export interface FxPointLike {
  x: number
  y: number
}

export interface BaseParams {
  element: Element
  x: number
  y: number
  strength?: number
}

export interface BurstParams extends BaseParams {
  count?: number
  speed?: number
  /** Total angle covered (2π = all around). */
  spread?: number
  /** Centre of the spread (default: straight up). */
  dir?: number
  gravity?: number
  lifeMs?: number
  size?: number
  /** Pull particles toward the centre instead of out. */
  inward?: boolean
  /** Use the element's debris shape instead of its spark. */
  chunky?: boolean
}

export interface ConeParams extends BaseParams {
  dir: number
  halfAngle?: number
  durationMs?: number
  ratePerSec?: number
  speed?: number
  size?: number
  /** Heat shimmer if the element allows it and the Quality tier has filters. */
  haze?: boolean
}

export interface TrailParams extends BaseParams {
  to: FxPointLike
  durationMs?: number
  width?: number
  /** Arc height for a lobbed path (0 = straight). */
  arc?: number
}

export interface ProjectileParams extends BaseParams {
  to: FxPointLike
  shape?: ProjectileShape
  arc?: number
  durationMs?: number
  size?: number
  /** What to draw on arrival (default: a small spark; the hit event brings the real impact). */
  onArrive?: 'none' | 'spark' | 'impact' | 'splash'
}

export interface BeamParams extends BaseParams {
  to: FxPointLike
  width?: number
  durationMs?: number
  jitter?: number
}

export interface RingParams extends BaseParams {
  radius?: number
  thickness?: number
  durationMs?: number
  /** A flattened ellipse on the floor (a shockwave) rather than an upright ring. */
  ground?: boolean
  /** Two or three rings one after another (Sound). */
  count?: number
}

export interface ImpactParams extends BaseParams {
  crit?: boolean
}

export interface SplashParams extends BaseParams {
  size?: number
}

export interface SheetParams extends BaseParams {
  width?: number
  height?: number
  durationMs?: number
  /** A wave that rises from the floor and curls toward `dir` (1 = right, −1 = left); otherwise a falling sheet. */
  rising?: boolean
  dir?: 1 | -1
}

export interface LightningParams extends BaseParams {
  to: FxPointLike
  branches?: boolean
}

export interface HazeParams extends BaseParams {
  width?: number
  height?: number
  durationMs?: number
  strength?: number
}

export interface GlowParams extends BaseParams {
  radius?: number
  durationMs?: number
  pulse?: boolean
  /** Shrinks into the point (a drain) instead of breathing. */
  inward?: boolean
}

export interface DebrisParams extends BaseParams {
  count?: number
  size?: number
}

export interface MistParams extends BaseParams {
  count?: number
  durationMs?: number
  drift?: number
  size?: number
}

export interface FlashParams {
  element: Element
  alpha?: number
  ms?: number
}

export interface ShakeParams {
  amplitudePx?: number
  ms?: number
  /** Element multiplier is applied by the recipe; this is the final request. */
  element?: Element
}

export interface HitstopParams {
  ms?: number
}

export interface ImpactFrameParams {
  element: Element
  frames?: number
}

export interface PrimitiveParamsMap {
  burst: BurstParams
  cone: ConeParams
  trail: TrailParams
  projectile: ProjectileParams
  beam: BeamParams
  ring: RingParams
  impact: ImpactParams
  splash: SplashParams
  sheet: SheetParams
  lightning: LightningParams
  haze: HazeParams
  glow: GlowParams
  debris: DebrisParams
  mist: MistParams
  flash: FlashParams
  shake: ShakeParams
  hitstop: HitstopParams
  impactFrame: ImpactFrameParams
}

export type PrimitiveName = keyof PrimitiveParamsMap
export const PRIMITIVE_NAMES: readonly PrimitiveName[] = ['burst', 'cone', 'trail', 'projectile', 'beam', 'ring', 'impact', 'splash', 'sheet', 'lightning', 'haze', 'glow', 'debris', 'mist', 'flash', 'shake', 'hitstop', 'impactFrame']

/** Screen-space primitives ignore the camera. */
export const SCREEN_SPACE: ReadonlySet<PrimitiveName> = new Set<PrimitiveName>(['flash', 'shake', 'hitstop', 'impactFrame'])

/** One scheduled primitive. */
export type PrimitiveCall = { [K in PrimitiveName]: { name: K; params: PrimitiveParamsMap[K]; delayMs?: number } }[PrimitiveName]

/** A live effect: advance by dt (true = still alive) and release everything. */
export interface EffectHandle {
  update(dtMs: number): boolean
  dispose(): void
}
