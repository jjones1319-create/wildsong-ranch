import type { Element } from '../data/types.ts'
import { FRAME, type FrameId } from './atlas.ts'

/**
 * VISUAL_V1_EFFECTS §4: the default look of every element. Each primitive reads its element's style for colours,
 * particle shapes, blend mode and a few flags, so "cone + Fire" is a flame breath and "cone + Water" a jet.
 */
export type ProjectileShape = 'orb' | 'lance' | 'blade' | 'boulder' | 'feather' | 'note' | 'drop' | 'shard' | 'bolt' | 'leaf'

export interface ElementStyle {
  /** Particle colour over a particle's life, bright to dim (0xRRGGBB). */
  ramp: readonly number[]
  /** The brightest colour: beam cores, impact flashes, screen flashes. */
  core: number
  /** Auras and glows. */
  glow: number
  /** Ground dust and smoke. */
  smoke: number
  additive: boolean
  spark: FrameId
  debris: FrameId
  puff: FrameId
  projectile: ProjectileShape
  /** Heat shimmer or underwater wobble around cones and glows. */
  haze: boolean
  /** Water splashes when a projectile lands. */
  splashOnLand: boolean
  /** Bursts pull inward instead of out (Dark). */
  inward: boolean
  /** Multipliers on gravity, shake and particle count against the primitive defaults. */
  gravity: number
  shake: number
  density: number
  /** Trailing smoke / mist behind cones and projectiles. */
  trailSmoke: boolean
}

const S = (s: ElementStyle) => s

export const ELEMENT_STYLES: Readonly<Record<Element, ElementStyle>> = {
  Fire: S({ ramp: [0xfff6c4, 0xffc455, 0xff6d1f, 0x8a2f12], core: 0xfff8dc, glow: 0xff8c3a, smoke: 0x4a3a35, additive: true, spark: FRAME.ember, debris: FRAME.ember, puff: FRAME.puff, projectile: 'orb', haze: true, splashOnLand: false, inward: false, gravity: -0.35, shake: 1, density: 1.1, trailSmoke: true }),
  Water: S({ ramp: [0xf4feff, 0x8fe3f5, 0x34afd2, 0x1d6a8f], core: 0xf2fdff, glow: 0x5fd0ea, smoke: 0xa9dcea, additive: false, spark: FRAME.droplet, debris: FRAME.droplet, puff: FRAME.bubble, projectile: 'drop', haze: false, splashOnLand: true, inward: false, gravity: 1.3, shake: 0.8, density: 1.1, trailSmoke: false }),
  Ice: S({ ramp: [0xffffff, 0xdbf6ff, 0x9bd8ff, 0x5f8fd0], core: 0xffffff, glow: 0xa8dcff, smoke: 0xd6ecf7, additive: true, spark: FRAME.shard, debris: FRAME.shard, puff: FRAME.flake, projectile: 'lance', haze: false, splashOnLand: false, inward: false, gravity: 1, shake: 0.9, density: 0.9, trailSmoke: true }),
  Lightning: S({ ramp: [0xffffff, 0xfff7b0, 0xa9e2ff, 0x4f7fe0], core: 0xffffff, glow: 0x9bd1ff, smoke: 0x6f7fa8, additive: true, spark: FRAME.spark, debris: FRAME.spark, puff: FRAME.softDot, projectile: 'bolt', haze: false, splashOnLand: false, inward: false, gravity: 0.4, shake: 1.1, density: 0.9, trailSmoke: false }),
  Wind: S({ ramp: [0xffffff, 0xedf8f1, 0xc5e6d6, 0x8fb9a9], core: 0xffffff, glow: 0xd8f2e6, smoke: 0xc9d9cf, additive: false, spark: FRAME.streak, debris: FRAME.leaf, puff: FRAME.puff, projectile: 'blade', haze: false, splashOnLand: false, inward: false, gravity: 0.15, shake: 0.6, density: 1, trailSmoke: false }),
  Earth: S({ ramp: [0xe3c391, 0xb3844f, 0x7f5733, 0x4a3320], core: 0xf5e2c0, glow: 0xc99a5a, smoke: 0xb39b7a, additive: false, spark: FRAME.rock, debris: FRAME.rock, puff: FRAME.puff, projectile: 'boulder', haze: false, splashOnLand: false, inward: false, gravity: 1.6, shake: 1.5, density: 1, trailSmoke: true }),
  Nature: S({ ramp: [0xf9ffd6, 0xb6ea72, 0x62b447, 0x2f6b2a], core: 0xf6ffe0, glow: 0x8ee36b, smoke: 0xa9cf8e, additive: false, spark: FRAME.petal, debris: FRAME.leaf, puff: FRAME.puff, projectile: 'leaf', haze: false, splashOnLand: false, inward: false, gravity: 0.5, shake: 0.7, density: 1, trailSmoke: false }),
  Light: S({ ramp: [0xffffff, 0xfff5cc, 0xffd66e, 0xd99b2e], core: 0xffffff, glow: 0xffe79a, smoke: 0xfff1cc, additive: true, spark: FRAME.star, debris: FRAME.star, puff: FRAME.softDot, projectile: 'orb', haze: false, splashOnLand: false, inward: false, gravity: -0.2, shake: 0.8, density: 1, trailSmoke: false }),
  Dark: S({ ramp: [0xe0c2ff, 0x9a66e6, 0x53308a, 0x1a1030], core: 0xead9ff, glow: 0x8352e0, smoke: 0x2a1a44, additive: false, spark: FRAME.softDot, debris: FRAME.puff, puff: FRAME.puff, projectile: 'orb', haze: false, splashOnLand: false, inward: true, gravity: -0.3, shake: 0.9, density: 1, trailSmoke: true }),
  Sound: S({ ramp: [0xffffff, 0xffd9f3, 0xe08fd0, 0x8d4fa3], core: 0xfff0fa, glow: 0xf0a4e0, smoke: 0xe9c6e4, additive: true, spark: FRAME.note, debris: FRAME.ring, puff: FRAME.ring, projectile: 'note', haze: false, splashOnLand: false, inward: false, gravity: -0.1, shake: 0.9, density: 0.8, trailSmoke: false }),
  Physical: S({ ramp: [0xffffff, 0xfff3dc, 0xdccbb0, 0x8f816e], core: 0xffffff, glow: 0xfff0d0, smoke: 0xc8b9a2, additive: false, spark: FRAME.spark, debris: FRAME.rock, puff: FRAME.puff, projectile: 'orb', haze: false, splashOnLand: false, inward: false, gravity: 1, shake: 1, density: 1, trailSmoke: false }),
}

/** Ramp index = position in this list (the particle sim stores a small integer per particle). */
export const RAMPS: readonly (readonly number[])[] = [...(Object.keys(ELEMENT_STYLES) as Element[]).map((e) => ELEMENT_STYLES[e].ramp), [0xffffff, 0xd8d8d8, 0x9a9a9a, 0x5a5a5a]]
/** A neutral grey ramp (dust, smoke) is the last one. */
export const SMOKE_RAMP = RAMPS.length - 1

export function rampIndex(element: Element): number {
  return (Object.keys(ELEMENT_STYLES) as Element[]).indexOf(element)
}

export function styleOf(element: Element): ElementStyle {
  return ELEMENT_STYLES[element]
}

export function hexCss(color: number, alpha = 1): string {
  const r = (color >> 16) & 255
  const g = (color >> 8) & 255
  const b = color & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
