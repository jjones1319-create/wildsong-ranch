import { BloomFilter } from 'pixi-filters/bloom'
import { RGBSplitFilter } from 'pixi-filters/rgb-split'
import { ShockwaveFilter } from 'pixi-filters/shockwave'
import { type Container, DisplacementFilter, type Filter, Sprite } from 'pixi.js'
import { FX } from '../data/tuning.ts'
import type { FxCamera } from './camera.ts'
import type { FilterLevel, IntensityProfile } from './quality.ts'
import type { Atlas } from './textures.ts'

/**
 * The few GPU filters the layer uses, shared so there is never more than one of each. The Quality tier decides
 * which exist at all ('all' / 'some' = bloom + shockwave / 'none'). The filters only bend what the canvas draws
 * (the monsters are DOM), so haze shows as shimmer on the flames and a translucent wobble, not on the fur.
 */
interface HazeRegion {
  x: number
  y: number
  w: number
  h: number
  strength: number
  until: number
}

export class FilterRig {
  private bloom: BloomFilter | null = null
  private shock: ShockwaveFilter | null = null
  private shockUntil = 0
  private split: RGBSplitFilter | null = null
  private splitUntil = 0
  private haze: DisplacementFilter | null = null
  private readonly hazeSprite: Sprite
  private readonly regions: HazeRegion[] = []
  private scroll = 0
  private readonly world: Container
  private readonly additive: Container
  private level: FilterLevel

  constructor(world: Container, additive: Container, atlas: Atlas, level: FilterLevel) {
    this.world = world
    this.additive = additive
    this.level = level
    this.hazeSprite = new Sprite(atlas.noise)
    this.hazeSprite.visible = false
    this.hazeSprite.renderable = false
    world.addChild(this.hazeSprite)
  }

  setLevel(level: FilterLevel, profile: IntensityProfile): void {
    this.level = level
    this.setBloom(profile)
    if (level === 'none') {
      this.regions.length = 0
      this.shockUntil = 0
      this.splitUntil = 0
    }
  }

  setBloom(profile: IntensityProfile): void {
    const want = this.level !== 'none' && profile.bloom !== 'off'
    if (!want) {
      this.additive.filters = []
      return
    }
    if (!this.bloom) this.bloom = new BloomFilter({ strength: 2, quality: 1 })
    this.bloom.strength = profile.bloom === 'high' ? 5 : 2.5
    this.additive.filters = [this.bloom]
  }

  get hasHaze(): boolean {
    return this.level === 'all'
  }

  /** Register a heat-haze / wobble region (world units) for `ms`. */
  addHaze(x: number, y: number, w: number, h: number, strength: number, ms: number, now: number): void {
    if (!this.hasHaze) return
    this.regions.push({ x, y, w, h, strength, until: now + ms })
  }

  shockwave(x: number, y: number, strength: number, now: number): void {
    if (this.level === 'none') return
    if (!this.shock) this.shock = new ShockwaveFilter({ amplitude: 20, wavelength: 90, brightness: 1.05, radius: 260, speed: 900 })
    this.shock.center = { x, y }
    this.shock.amplitude = 12 + 22 * strength
    this.shock.time = 0
    this.shockUntil = now + 320
  }

  rgbSplit(ms: number, now: number): void {
    if (this.level !== 'all') return
    if (!this.split) this.split = new RGBSplitFilter({ red: { x: -3, y: 0 }, green: { x: 0, y: 0 }, blue: { x: 3, y: 0 } })
    this.splitUntil = now + ms
  }

  /** Called once per frame with the fx clock, the real dt and the camera (the shockwave centre is in screen px). */
  update(now: number, dtMs: number, cam: FxCamera): void {
    const list: Filter[] = []
    // Haze: the displacement sprite covers the union of the live regions and scrolls upward like warm air.
    for (let i = this.regions.length - 1; i >= 0; i--) if (this.regions[i]!.until <= now) this.regions.splice(i, 1)
    if (this.regions.length > 0 && this.hasHaze) {
      if (!this.haze) this.haze = new DisplacementFilter({ sprite: this.hazeSprite, scale: FX.haze.strength })
      let x0 = Infinity
      let y0 = Infinity
      let x1 = -Infinity
      let y1 = -Infinity
      let strength = 0
      for (const r of this.regions) {
        x0 = Math.min(x0, r.x)
        y0 = Math.min(y0, r.y)
        x1 = Math.max(x1, r.x + r.w)
        y1 = Math.max(y1, r.y + r.h)
        strength = Math.max(strength, r.strength)
      }
      this.scroll += (dtMs / 1000) * FX.haze.scroll
      const s = this.hazeSprite
      s.visible = true
      s.position.set(x0, y0)
      s.width = Math.max(1, x1 - x0)
      s.height = Math.max(1, y1 - y0)
      // Scroll by moving the sprite's texture frame is not possible on a plain sprite, so nudge the sprite up
      // and down a little instead; the noise is tiled, so the edge stays neutral.
      s.y = y0 - (this.scroll % 1) * 12
      const px = FX.haze.strength * strength * cam.pxPerUnit * 2
      this.haze.scale.set(px, px * 1.6)
      list.push(this.haze)
    } else {
      this.hazeSprite.visible = false
    }
    if (this.shock && now < this.shockUntil) {
      this.shock.time += dtMs / 1000
      list.push(this.shock)
    }
    if (this.split && now < this.splitUntil) list.push(this.split)
    const current = this.world.filters
    if (list.length === 0) {
      if (current && (Array.isArray(current) ? current.length : 1) > 0) this.world.filters = []
    } else this.world.filters = list
  }

  clear(): void {
    this.regions.length = 0
    this.shockUntil = 0
    this.splitUntil = 0
    this.world.filters = []
    this.hazeSprite.visible = false
  }

  destroy(): void {
    this.clear()
    this.additive.filters = []
    this.bloom?.destroy()
    this.shock?.destroy()
    this.split?.destroy()
    this.haze?.destroy()
    this.hazeSprite.destroy()
  }
}
