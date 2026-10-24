import { Container, WebGLRenderer } from 'pixi.js'
import { FX } from '../data/tuning.ts'
import { DEFAULT_CAMERA, sameCamera, worldTransform, type FxCamera } from './camera.ts'
import type { FxContext, FxHooks } from './context.ts'
import { ParticleLayer } from './emitter.ts'
import { FilterRig } from './filters.ts'
import { PRIMITIVES } from './primitives/index.ts'
import type { EffectHandle, PrimitiveCall } from './primitives/types.ts'
import { FlashGate, particleAllowance, type IntensityProfile, type QualityBudget } from './quality.ts'
import { createFxRng, type FxRng } from './rng.ts'
import { buildAtlas, type Atlas } from './textures.ts'

/**
 * VISUAL_V1_EFFECTS §3: the effects canvas. One WebGL renderer over the arena, a world container the camera
 * places every frame, two particle banks, a shapes container and a screen-space container. Effects advance on a
 * clock that follows the battle's playback speed, pauses with it, freezes for hit-stop, and sleeps when idle.
 */
export interface FxLayerOptions {
  host: HTMLElement
  budget: QualityBudget
  profile: IntensityProfile
  hooks?: Partial<FxHooks>
  seed?: number
  /** No animation frames of its own; `step(ms)` drives it (Playwright, tests). */
  manualClock?: boolean
  /** Called once per frame with the frame time (for Auto quality detection). */
  onFrame?: (frameMs: number) => void
}

export interface FxStats {
  fps: number
  particles: number
  effects: number
  awake: boolean
  tier: QualityBudget['tier']
  intensity: IntensityProfile['intensity']
}

interface Scheduled {
  at: number
  call: PrimitiveCall
}

const NO_HOOKS: FxHooks = { shake() {}, hitstop() {}, impactFrame() {} }

export class FxLayer {
  readonly canvas: HTMLCanvasElement
  private renderer: WebGLRenderer | null = null
  private readonly stage = new Container()
  private readonly world = new Container()
  private readonly shapes = new Container()
  private readonly screen = new Container()
  private atlas: Atlas | null = null
  private particles: ParticleLayer | null = null
  private filters: FilterRig | null = null
  private readonly rng: FxRng
  private readonly hooks: FxHooks
  private budget: QualityBudget
  private profile: IntensityProfile
  private cam: FxCamera = { ...DEFAULT_CAMERA }
  private readonly effects: EffectHandle[] = []
  private readonly queue: Scheduled[] = []
  private clock = 0
  private timeScale = 1
  private paused = false
  private hitstopUntil = 0
  private hitstopOn = false
  private impactUntil = 0
  private impactOn = false
  private shakeX = 0
  private shakeY = 0
  private shook = false
  private raf = 0
  private last = 0
  private lastActive = 0
  private awake = false
  private hidden = false
  private destroyed = false
  private fps = 60
  private readonly flashGate = new FlashGate()
  private readonly ctx: FxContext
  private readonly opts: FxLayerOptions

  constructor(opts: FxLayerOptions) {
    this.opts = opts
    this.rng = createFxRng(opts.seed ?? 1)
    this.hooks = { ...NO_HOOKS, ...opts.hooks }
    this.budget = opts.budget
    this.profile = opts.profile
    this.canvas = document.createElement('canvas')
    this.canvas.className = 'fx-canvas'
    this.canvas.setAttribute('aria-hidden', 'true')
    this.stage.addChild(this.world, this.screen)
    const self = this
    this.ctx = {
      world: this.world,
      shapes: this.shapes,
      screen: this.screen,
      get particles() {
        return self.particles!
      },
      get atlas() {
        return self.atlas!
      },
      rng: this.rng,
      get filters() {
        return self.filters!
      },
      flashGate: this.flashGate,
      get budget() {
        return self.budget
      },
      get profile() {
        return self.profile
      },
      get now() {
        return self.clock
      },
      camera: () => this.cam,
      allowance: (n) => particleAllowance(n, this.profile, this.budget, this.particles?.live ?? 0),
      addShake: (dx, dy) => {
        this.shakeX += dx
        this.shakeY += dy
      },
      hitstop: (ms) => {
        this.hitstopUntil = Math.max(this.hitstopUntil, this.clock + ms)
      },
      impactFrame: (ms, color) => {
        this.impactUntil = Math.max(this.impactUntil, this.clock + ms)
        if (!this.impactOn) {
          this.impactOn = true
          this.hooks.impactFrame(true, `#${color.toString(16).padStart(6, '0')}`)
        }
      },
      fire: (call) => this.fire(call),
    }
  }

  /** Creates the GPU resources. Resolves false when WebGL is unavailable (the arena then simply has no effects). */
  async init(): Promise<boolean> {
    try {
      const renderer = new WebGLRenderer()
      await renderer.init({
        canvas: this.canvas,
        width: Math.max(1, this.opts.host.clientWidth || DEFAULT_CAMERA.width),
        height: Math.max(1, this.opts.host.clientHeight || DEFAULT_CAMERA.height),
        backgroundAlpha: 0,
        antialias: false,
        resolution: this.budget.resolution,
        autoDensity: true,
        clearBeforeRender: true,
        powerPreference: 'high-performance',
        preferWebGLVersion: 2,
      })
      if (this.destroyed) {
        renderer.destroy()
        return false
      }
      this.renderer = renderer
      this.atlas = buildAtlas()
      this.particles = new ParticleLayer(this.atlas, FX.poolCapacity)
      this.particles.warm()
      this.world.addChild(this.particles.normal.container, this.shapes, this.particles.additive.container)
      this.filters = new FilterRig(this.world, this.particles.additive.container, this.atlas, this.budget.filters)
      this.filters.setBloom(this.profile)
      this.opts.host.appendChild(this.canvas)
      this.canvas.addEventListener('webglcontextlost', this.onContextLost)
      this.canvas.addEventListener('webglcontextrestored', this.onContextRestored)
      document.addEventListener('visibilitychange', this.onVisibility)
      this.applyCamera()
      this.render()
      return true
    } catch (err) {
      console.warn('[fx] WebGL unavailable; effects are off.', err)
      this.renderer = null
      return false
    }
  }

  get ready(): boolean {
    return this.renderer !== null
  }

  /* ---------- the arena talks to the layer ---------- */

  setCamera(cam: FxCamera): void {
    if (sameCamera(cam, this.cam)) return
    const resized = cam.width !== this.cam.width || cam.height !== this.cam.height
    this.cam = { ...cam }
    if (resized && this.renderer) this.renderer.resize(Math.max(1, cam.width), Math.max(1, cam.height))
    this.applyCamera()
  }

  setTimeScale(s: number): void {
    this.timeScale = Math.max(0, s)
  }

  setPaused(on: boolean): void {
    this.paused = on
    if (!on) this.wake()
  }

  setQuality(budget: QualityBudget): void {
    this.budget = budget
    this.renderer?.resize(Math.max(1, this.cam.width), Math.max(1, this.cam.height), budget.resolution)
    this.filters?.setLevel(budget.filters, this.profile)
  }

  setIntensity(profile: IntensityProfile): void {
    this.profile = profile
    this.filters?.setBloom(profile)
  }

  /** Fire a primitive now or after its delay (fx time, so ×2 playback halves the wait). */
  fire(call: PrimitiveCall): void {
    if (!this.renderer || this.destroyed) return
    if (call.delayMs && call.delayMs > 0) {
      this.queue.push({ at: this.clock + call.delayMs, call })
    } else this.spawn(call)
    this.wake()
  }

  fireAll(calls: readonly PrimitiveCall[]): void {
    for (const c of calls) this.fire(c)
  }

  /** Skip or leave: drop everything at once. */
  clear(): void {
    for (const e of this.effects) e.dispose()
    this.effects.length = 0
    this.queue.length = 0
    this.particles?.clear()
    this.filters?.clear()
    this.hitstopUntil = 0
    this.impactUntil = 0
    this.endHitstop()
    this.endImpact()
    this.shakeX = 0
    this.shakeY = 0
    this.hooks.shake(0, 0)
    this.render()
  }

  /** Manual clock: advance by `ms` in frame-sized slices and render (Playwright review, tests). */
  step(ms: number): void {
    let left = Math.max(0, ms)
    while (left > 0) {
      const slice = Math.min(FX.manualSliceMs, left)
      this.advance(slice)
      left -= slice
    }
    this.render()
  }

  stats(): FxStats {
    return { fps: Math.round(this.fps), particles: this.particles?.live ?? 0, effects: this.effects.length + this.queue.length, awake: this.awake, tier: this.budget.tier, intensity: this.profile.intensity }
  }

  destroy(): void {
    if (this.destroyed) return
    this.destroyed = true
    this.sleep()
    document.removeEventListener('visibilitychange', this.onVisibility)
    this.canvas.removeEventListener('webglcontextlost', this.onContextLost)
    this.canvas.removeEventListener('webglcontextrestored', this.onContextRestored)
    for (const e of this.effects) e.dispose()
    this.effects.length = 0
    this.queue.length = 0
    this.endHitstop()
    this.endImpact()
    this.hooks.shake(0, 0)
    this.filters?.destroy()
    this.particles?.destroy()
    this.atlas?.destroy()
    this.stage.destroy({ children: true })
    this.renderer?.destroy()
    this.renderer = null
    this.canvas.remove()
  }

  /* ---------- internals ---------- */

  private spawn(call: PrimitiveCall): void {
    try {
      const factory = PRIMITIVES[call.name] as (ctx: FxContext, params: unknown) => EffectHandle
      const h = factory(this.ctx, call.params)
      if (h.update(0)) this.effects.push(h)
    } catch (err) {
      console.warn('[fx] primitive failed', call.name, err)
    }
    this.lastActive = this.clock
  }

  private advance(realMs: number): void {
    if (this.paused) return
    const dt = Math.min(FX.maxFrameMs, realMs) * this.timeScale
    if (dt <= 0) return
    // Hit-stop: the clock creeps forward only to know when it ends; nothing else moves.
    if (this.clock < this.hitstopUntil) {
      if (!this.hitstopOn) {
        this.hitstopOn = true
        this.hooks.hitstop(true)
      }
      this.clock += dt
      if (this.clock >= this.hitstopUntil) this.endHitstop()
      return
    }
    this.clock += dt
    if (this.impactOn && this.clock >= this.impactUntil) this.endImpact()
    // Scheduled calls whose time has come.
    if (this.queue.length > 0) {
      for (let i = this.queue.length - 1; i >= 0; i--) {
        const s = this.queue[i]!
        if (s.at <= this.clock) {
          this.queue.splice(i, 1)
          this.spawn(s.call)
        }
      }
    }
    this.shakeX = 0
    this.shakeY = 0
    for (let i = this.effects.length - 1; i >= 0; i--) {
      if (!this.effects[i]!.update(dt)) this.effects.splice(i, 1)
    }
    this.particles?.update(dt)
    this.filters?.update(this.clock, dt, this.cam)
    if (this.shakeX !== 0 || this.shakeY !== 0) {
      this.hooks.shake(this.shakeX, this.shakeY)
      this.shook = true
    } else if (this.shook) {
      this.shook = false
      this.hooks.shake(0, 0)
    }
    if (this.effects.length > 0 || this.queue.length > 0 || (this.particles?.live ?? 0) > 0) this.lastActive = this.clock
  }

  private endHitstop(): void {
    if (this.hitstopOn) {
      this.hitstopOn = false
      this.hooks.hitstop(false)
    }
  }

  private endImpact(): void {
    if (this.impactOn) {
      this.impactOn = false
      this.hooks.impactFrame(false, '')
    }
  }

  private applyCamera(): void {
    const t = worldTransform(this.cam)
    this.world.position.set(t.x, t.y)
    this.world.scale.set(t.scale)
  }

  private render(): void {
    if (!this.renderer || this.destroyed) return
    try {
      this.renderer.render({ container: this.stage })
    } catch (err) {
      console.warn('[fx] render failed', err)
    }
  }

  private readonly frame = (time: number): void => {
    this.raf = 0
    if (this.destroyed || !this.awake) return
    const real = this.last ? time - this.last : 16.7
    this.last = time
    const frameMs = Math.min(FX.maxFrameMs, real)
    this.fps += (1000 / Math.max(1, frameMs) - this.fps) * FX.fpsSmoothing
    this.opts.onFrame?.(frameMs)
    this.advance(real)
    this.render()
    const idle = this.effects.length === 0 && this.queue.length === 0 && (this.particles?.live ?? 0) === 0 && this.clock - this.lastActive > FX.idleGraceMs && !this.hitstopOn
    if (idle || this.hidden) {
      this.sleep()
      return
    }
    this.raf = requestAnimationFrame(this.frame)
  }

  private wake(): void {
    if (this.opts.manualClock || this.awake || this.destroyed || this.hidden || !this.renderer) return
    this.awake = true
    this.last = 0
    this.lastActive = this.clock
    this.raf = requestAnimationFrame(this.frame)
  }

  private sleep(): void {
    this.awake = false
    if (this.raf) cancelAnimationFrame(this.raf)
    this.raf = 0
    this.last = 0
  }

  private readonly onVisibility = (): void => {
    this.hidden = document.visibilityState === 'hidden'
    if (this.hidden) this.sleep()
    else this.wake()
  }

  private readonly onContextLost = (e: Event): void => {
    e.preventDefault()
    this.sleep()
  }

  private readonly onContextRestored = (): void => {
    // Pixi re-creates GPU state lazily; drop what was mid-flight so nothing references stale buffers.
    for (const h of this.effects) h.dispose()
    this.effects.length = 0
    this.queue.length = 0
    this.particles?.clear()
    this.filters?.clear()
    this.wake()
  }
}
