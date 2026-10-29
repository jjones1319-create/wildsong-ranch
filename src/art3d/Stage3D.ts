import { CanvasTexture, CircleGeometry, DirectionalLight, Mesh, MeshBasicMaterial, PerspectiveCamera, PlaneGeometry, Scene, ShadowMaterial, SRGBColorSpace, Vector3, WebGLRenderer } from 'three'
import { MODEL_LOOKS, type LookId } from '../art/models.ts'
import { ART } from '../data/tuning.ts'
import { art3dLost, art3dStats, art3dUnavailable } from '../ui/store/artStore.ts'
import { Actor, type ActorQuality, type PlayOptions } from './actor.ts'
import { cameraNumbers, portraitCamera, sameStageCamera, type StageCamera } from './arenaCamera.ts'
import { seededRandom } from './faceCells.ts'
import { acquireLook, disposeAllLooks, loadLook, releaseLook, type LookAsset } from './loader.ts'
import { lightRig, type LightPreset, type LightRig } from './materials.ts'
import type { ClipName, FaceName } from './types.ts'

/**
 * The one live 3D canvas (ART_2_PLAN §3.2 `Stage3D`): a single WebGLRenderer that hosts come and go from.
 * A screen mounts it into an element, describes its actors and camera, and either drives frames itself (the
 * arena's loop) or lets the stage run. A second live mount evicts the first (newest wins), so there is never
 * more than one 3D canvas from us. The renderer and model cache are freed a while after the last host leaves.
 */

export type QualityTier = keyof typeof ART.quality

export interface ActorSpec {
  id: string
  look: LookId
  variant: string | null
  stage: number
  face: FaceName
  /** Arena units. */
  x: number
  z?: number
  /** Degrees; 0 faces the camera. */
  yawDeg: number
  /** The loop to play while nothing else is playing. */
  clip?: ClipName
  sick?: number
  flash?: number
}

export interface MountOptions {
  quality: QualityTier
  manualClock?: boolean
  /** Still frames only (Reduce motion): no clip time, no blinks. */
  still?: boolean
  onReady?: (id: string) => void
  onLost?: () => void
  onRestored?: () => void
  onEvicted?: () => void
  onMarker?: (id: string, clip: ClipName, marker: string) => void
  seed?: number
}

export interface StageStats {
  fps: number
  tris: number
  drawCalls: number
  tier: QualityTier
  actors: number
}

export interface StageHandle {
  setCamera(c: StageCamera): void
  setActors(specs: ActorSpec[]): void
  play(id: string, clip: ClipName, o?: PlayOptions): boolean
  actor(id: string): Actor | null
  setLight(preset: LightPreset): void
  setTimeScale(k: number): void
  setPaused(on: boolean): void
  setHitstop(on: boolean): void
  /** Host-driven frames (the arena's loop). */
  frame(time: number): void
  /** Self-driven frames. */
  start(): void
  stop(): void
  /** Manual clock for the review scripts: advance and render. */
  step(ms: number): void
  glance(dx: number, dy: number, reach: number): void
  /** Draw one frame now (after a change while paused or still). */
  invalidate(): void
  stats(): StageStats
  readonly live: boolean
  release(): void
}

interface Slot {
  spec: ActorSpec
  actor: Actor | null
  loading: Promise<void> | null
  shadow: Mesh | null
  wanted: boolean
}

export interface PortraitRequest {
  look: LookId
  variant: string | null
  stage: number
  face: FaceName
  size: number
  yawDeg?: number
  clip?: ClipName
}

export function qualityFor(tier: QualityTier): ActorQuality & { dprCap: number; antialias: boolean; shadowMap: boolean } {
  const q = ART.quality[tier]
  return { outline: q.outline, springs: q.springs, outlinePx: q.outlinePx, dprCap: q.dprCap, antialias: q.antialias, shadowMap: q.shadowMap }
}

function blobTexture(): CanvasTexture {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const g = c.getContext('2d')!
  const grad = g.createRadialGradient(32, 32, 2, 32, 32, 32)
  grad.addColorStop(0, 'rgba(20,30,40,1)')
  grad.addColorStop(0.55, 'rgba(20,30,40,0.55)')
  grad.addColorStop(1, 'rgba(20,30,40,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 64, 64)
  const t = new CanvasTexture(c)
  t.colorSpace = SRGBColorSpace
  return t
}

export class Stage3D {
  private static instance: Stage3D | null = null

  static get(): Stage3D {
    return (Stage3D.instance ??= new Stage3D())
  }

  private renderer: WebGLRenderer | null = null
  private canvas: HTMLCanvasElement | null = null
  private rendererTier: QualityTier | null = null
  private readonly scene = new Scene()
  private readonly camera = new PerspectiveCamera(20, 1, 1, 5000)
  private readonly slots = new Map<string, Slot>()
  private host: { el: HTMLElement; opts: MountOptions; handle: StageHandle; cam: StageCamera | null; width: number; height: number } | null = null
  private rig: LightRig = lightRig('day')
  private rigPreset: LightPreset = 'day'
  private raf = 0
  private last = 0
  private paused = false
  private hitstop = false
  private timeScale = 1
  private liteAccum = 0
  private lost = false
  private idleTimer: ReturnType<typeof setTimeout> | null = null
  private blob: CanvasTexture | null = null
  private sun: DirectionalLight | null = null
  private catcher: Mesh | null = null
  private fps = 60
  private rng = seededRandom(1)
  private sizeStamp = ''
  private onVisibility = () => {
    if (!this.host) return
    if (document.hidden) this.stopLoop()
    else if (!this.host.opts.manualClock && this.selfDriven) this.startLoop()
  }
  private selfDriven = false

  // ------------------------------------------------------------------ renderer
  private ensureRenderer(tier: QualityTier): boolean {
    if (this.renderer && this.rendererTier === tier) return true
    if (this.renderer) this.destroyRenderer()
    const q = qualityFor(tier)
    try {
      const canvas = document.createElement('canvas')
      canvas.className = 'art3d-canvas'
      const r = new WebGLRenderer({ canvas, alpha: true, antialias: q.antialias, powerPreference: 'high-performance', stencil: false })
      r.setClearColor(0x000000, 0)
      r.outputColorSpace = SRGBColorSpace
      r.shadowMap.enabled = q.shadowMap
      r.setPixelRatio(Math.min(window.devicePixelRatio || 1, q.dprCap))
      canvas.addEventListener('webglcontextlost', (e) => {
        e.preventDefault()
        this.lost = true
        art3dLost.value = true
        this.stopLoop()
        this.host?.opts.onLost?.()
      })
      canvas.addEventListener('webglcontextrestored', () => {
        this.lost = false
        art3dLost.value = false
        if (this.host && this.selfDriven && !this.host.opts.manualClock) this.startLoop()
        this.host?.opts.onRestored?.()
      })
      this.renderer = r
      this.canvas = canvas
      this.rendererTier = tier
      if (!this.blob) this.blob = blobTexture()
      this.setupLights(q.shadowMap)
      return true
    } catch (e) {
      if (import.meta.env.DEV) console.warn('[art3d] WebGL unavailable', e)
      art3dUnavailable.value = true
      return false
    }
  }

  private setupLights(shadow: boolean): void {
    if (this.sun) {
      this.scene.remove(this.sun)
      this.sun.dispose()
      this.sun = null
    }
    if (this.catcher) {
      this.scene.remove(this.catcher)
      this.catcher.geometry.dispose()
      ;(this.catcher.material as ShadowMaterial).dispose()
      this.catcher = null
    }
    if (!shadow) return
    const sun = new DirectionalLight(0xffffff, 1)
    sun.castShadow = true
    sun.shadow.mapSize.set(512, 512)
    sun.shadow.camera.left = -400
    sun.shadow.camera.right = 400
    sun.shadow.camera.top = 400
    sun.shadow.camera.bottom = -400
    sun.shadow.camera.near = 10
    sun.shadow.camera.far = 2000
    sun.shadow.bias = -0.0005
    sun.shadow.radius = 4
    this.sun = sun
    this.scene.add(sun)
    this.scene.add(sun.target)
    const catcher = new Mesh(new PlaneGeometry(4000, 4000), new ShadowMaterial({ opacity: 0.22, transparent: true, depthWrite: false }))
    catcher.rotation.x = -Math.PI / 2
    catcher.position.y = 0.2
    catcher.receiveShadow = true
    this.catcher = catcher
    this.scene.add(catcher)
  }

  private destroyRenderer(): void {
    this.stopLoop()
    for (const id of [...this.slots.keys()]) this.dropSlot(id)
    this.setupLights(false)
    this.renderer?.dispose()
    this.canvas?.remove()
    this.renderer = null
    this.canvas = null
    this.rendererTier = null
    this.blob?.dispose()
    this.blob = null
  }

  // ------------------------------------------------------------------ hosts
  mount(el: HTMLElement, opts: MountOptions): StageHandle | null {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer)
      this.idleTimer = null
    }
    if (!this.ensureRenderer(opts.quality)) return null
    if (this.host) {
      const old = this.host
      if (import.meta.env.DEV) console.warn('[art3d] a second stage mounted; the first shows Classic')
      this.detachHost()
      old.opts.onEvicted?.()
    }
    this.rng = seededRandom(opts.seed ?? 1)
    const canvas = this.canvas!
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none'
    el.appendChild(canvas)
    const handle = this.makeHandle()
    this.host = { el, opts, handle, cam: null, width: 0, height: 0 }
    this.sizeStamp = ''
    this.selfDriven = false
    document.addEventListener('visibilitychange', this.onVisibility)
    return handle
  }

  private detachHost(): void {
    this.stopLoop()
    document.removeEventListener('visibilitychange', this.onVisibility)
    for (const id of [...this.slots.keys()]) this.dropSlot(id)
    this.canvas?.remove()
    this.host = null
    this.selfDriven = false
    this.paused = false
    this.hitstop = false
    this.timeScale = 1
    this.idleTimer = setTimeout(() => {
      this.idleTimer = null
      if (!this.host) {
        this.destroyRenderer()
        disposeAllLooks()
      }
    }, ART.stage.idleReleaseMs)
  }

  private makeHandle(): StageHandle {
    const self = this
    const handle: StageHandle = {
      get live() {
        return self.host?.handle === handle
      },
      setCamera: (c) => {
        if (self.host?.handle !== handle) return
        if (!sameStageCamera(self.host.cam, c)) {
          self.host.cam = { ...c }
          self.applyCamera()
        }
      },
      setActors: (specs) => {
        if (self.host?.handle === handle) self.syncActors(specs)
      },
      play: (id, clip, o) => {
        const a = self.slots.get(id)?.actor
        return a ? a.play(clip, o) : false
      },
      actor: (id) => self.slots.get(id)?.actor ?? null,
      setLight: (preset) => {
        if (preset !== self.rigPreset) {
          self.rigPreset = preset
          self.rig = lightRig(preset)
        }
      },
      setTimeScale: (k) => void (self.timeScale = k),
      setPaused: (on) => void (self.paused = on),
      setHitstop: (on) => void (self.hitstop = on),
      frame: (time) => {
        if (self.host?.handle === handle) self.frame(time)
      },
      start: () => {
        if (self.host?.handle !== handle) return
        self.selfDriven = true
        if (!self.host.opts.manualClock) self.startLoop()
      },
      stop: () => {
        self.selfDriven = false
        self.stopLoop()
      },
      step: (ms) => {
        if (self.host?.handle !== handle) return
        self.advance(ms)
        self.render()
      },
      glance: (dx, dy, reach) => {
        for (const s of self.slots.values()) s.actor?.glanceToward(dx, dy, reach)
      },
      invalidate: () => {
        if (self.host?.handle === handle) self.render()
      },
      stats: () => self.stats(),
      release: () => {
        if (self.host?.handle === handle) self.detachHost()
      },
    }
    return handle
  }

  // ------------------------------------------------------------------ actors
  private syncActors(specs: ActorSpec[]): void {
    const seen = new Set<string>()
    for (const spec of specs) {
      seen.add(spec.id)
      let slot = this.slots.get(spec.id)
      if (slot && (slot.spec.look !== spec.look)) {
        this.dropSlot(spec.id)
        slot = undefined
      }
      if (!slot) {
        slot = { spec, actor: null, loading: null, shadow: null, wanted: true }
        this.slots.set(spec.id, slot)
        this.loadSlot(slot)
      } else {
        slot.spec = spec
        slot.wanted = true
        if (slot.actor) this.applySpec(slot)
      }
    }
    for (const id of [...this.slots.keys()]) if (!seen.has(id)) this.dropSlot(id)
  }

  private loadSlot(slot: Slot): void {
    const id = slot.spec.id
    const look = slot.spec.look
    acquireLook(look)
    slot.loading = loadLook(look)
      .then((asset) => {
        if (!slot.wanted || this.slots.get(id) !== slot || !this.host) return
        this.makeActor(slot, asset)
      })
      .catch((e) => {
        if (import.meta.env.DEV) console.warn('[art3d] load failed', look, e)
      })
      .finally(() => {
        slot.loading = null
      })
  }

  private makeActor(slot: Slot, asset: LookAsset): void {
    const q = qualityFor(this.rendererTier ?? 'high')
    const host = this.host!
    const actor = new Actor(asset, {
      quality: { outline: q.outline, springs: q.springs, outlinePx: q.outlinePx },
      variant: slot.spec.variant,
      stage: slot.spec.stage,
      face: slot.spec.face,
      rng: this.rng,
      events: { onMarker: (clip, marker) => host.opts.onMarker?.(slot.spec.id, clip, marker) },
    })
    slot.actor = actor
    this.scene.add(actor.root)
    if (this.blob) {
      const shadow = new Mesh(new CircleGeometry(1, 28), new MeshBasicMaterial({ map: this.blob, transparent: true, depthWrite: false, opacity: ART.stage.shadow.alpha }))
      shadow.rotation.x = -Math.PI / 2
      shadow.position.y = 0.5
      shadow.renderOrder = -2
      slot.shadow = shadow
      this.scene.add(shadow)
    }
    this.applySpec(slot)
    if (slot.spec.clip) actor.play(slot.spec.clip, { fade: 0 })
    else if (actor.hasClip('idle')) actor.play('idle', { fade: 0 })
    if (this.host?.width) actor.setResolution(this.host.width * (this.renderer?.getPixelRatio() ?? 1), this.host.height * (this.renderer?.getPixelRatio() ?? 1))
    actor.update(0, false)
    host.opts.onReady?.(slot.spec.id)
    if (!this.raf) this.render()
  }

  private applySpec(slot: Slot): void {
    const a = slot.actor
    if (!a) return
    const s = slot.spec
    if (a.variant !== s.variant) a.setVariant(s.variant)
    if (a.stage !== s.stage) a.setStage(s.stage)
    a.setFace(s.face)
    a.place(s.x, s.z ?? 0, s.yawDeg)
    a.setSick(s.sick ?? 0)
    a.setFlash(s.flash ?? 0)
    if (s.clip && a.clipName !== s.clip && this.isLoop(a, a.clipName)) a.play(s.clip)
  }

  private isLoop(a: Actor, name: ClipName | null): boolean {
    if (!name) return true
    return a.asset.meta.clips[name]?.loop !== false
  }

  private dropSlot(id: string): void {
    const slot = this.slots.get(id)
    if (!slot) return
    slot.wanted = false
    if (slot.actor) {
      this.scene.remove(slot.actor.root)
      slot.actor.dispose()
    }
    if (slot.shadow) {
      this.scene.remove(slot.shadow)
      slot.shadow.geometry.dispose()
      ;(slot.shadow.material as MeshBasicMaterial).dispose()
    }
    releaseLook(slot.spec.look)
    this.slots.delete(id)
  }

  // ------------------------------------------------------------------ frames
  private startLoop(): void {
    if (this.raf || this.lost) return
    this.last = 0
    const tick = (time: number) => {
      this.raf = requestAnimationFrame(tick)
      this.frame(time)
    }
    this.raf = requestAnimationFrame(tick)
  }

  private stopLoop(): void {
    if (this.raf) cancelAnimationFrame(this.raf)
    this.raf = 0
  }

  private frame(time: number): void {
    const dt = this.last ? Math.min(100, time - this.last) : 16.7
    this.last = time
    if (this.lost || !this.host) return
    if (this.rendererTier === 'lite') {
      this.liteAccum += dt
      if (this.liteAccum < 1000 / ART.stage.liteFpsCap) return
      const step = this.liteAccum
      this.liteAccum = 0
      this.advance(step)
    } else {
      this.advance(dt)
    }
    this.render()
    const inst = dt > 0 ? 1000 / dt : 60
    this.fps += (inst - this.fps) * 0.08
  }

  private advance(dt: number): void {
    if (this.paused) return
    const still = !!this.host?.opts.still
    const scaled = this.hitstop ? 0 : dt * this.timeScale
    for (const s of this.slots.values()) {
      if (!s.actor) continue
      s.actor.update(still ? 0 : scaled, !still)
      if (s.shadow) {
        const a = s.actor
        const h = a.asset.meta.restHeight * a.unitsPerMetre
        const lift = a.rootHeight()
        const w = h * ART.stage.shadow.widthFrac
        const d = h * ART.stage.shadow.depthFrac
        s.shadow.position.x = a.root.position.x
        s.shadow.position.z = a.root.position.z
        const k = Math.max(0.3, 1 - lift / Math.max(1, h * 0.6))
        s.shadow.scale.set(w * (0.6 + 0.4 * k), d * (0.6 + 0.4 * k), 1)
        ;(s.shadow.material as MeshBasicMaterial).opacity = ART.stage.shadow.alpha * k
      }
    }
  }

  private applyCamera(): void {
    const host = this.host
    const r = this.renderer
    if (!host || !r || !host.cam) return
    const c = host.cam
    const n = cameraNumbers(c)
    const cam = this.camera
    cam.fov = n.fovDeg
    cam.aspect = n.aspect
    cam.near = n.near
    cam.far = n.far
    cam.position.set(...n.position)
    cam.lookAt(new Vector3(...n.lookAt))
    cam.updateProjectionMatrix()
    const w = Math.max(1, Math.round(c.width))
    const h = Math.max(1, Math.round(c.height))
    const stamp = `${w}x${h}`
    if (stamp !== this.sizeStamp) {
      this.sizeStamp = stamp
      host.width = w
      host.height = h
      r.setSize(w, h, false)
      const pr = r.getPixelRatio()
      for (const s of this.slots.values()) s.actor?.setResolution(w * pr, h * pr)
    }
  }

  private render(): void {
    const r = this.renderer
    if (!r || !this.host || this.lost) return
    if (!this.host.cam) return
    this.camera.updateMatrixWorld()
    const view = this.camera.matrixWorldInverse
    for (const s of this.slots.values()) s.actor?.applyLight(this.rig, view)
    if (this.sun) {
      this.sun.position.copy(this.rig.dir).multiplyScalar(900)
      this.sun.target.position.set(0, 0, 0)
    }
    r.render(this.scene, this.camera)
    const info = r.info.render
    art3dStats.value = { fps: Math.round(this.fps), tris: info.triangles, drawCalls: info.calls, tier: this.rendererTier ?? 'high' }
  }

  stats(): StageStats {
    const info = this.renderer?.info.render
    let actors = 0
    for (const s of this.slots.values()) if (s.actor) actors++
    return { fps: Math.round(this.fps), tris: info?.triangles ?? 0, drawCalls: info?.calls ?? 0, tier: this.rendererTier ?? 'high', actors }
  }

  get isLost(): boolean {
    return this.lost
  }

  // ------------------------------------------------------------------ portraits
  /** Render one still of a look into a Blob, without touching the live host (ART_2_PLAN §3.3 cached portraits). */
  async renderPortrait(req: PortraitRequest, tier: QualityTier = 'high'): Promise<Blob | null> {
    if (!this.ensureRenderer(this.rendererTier ?? tier)) return null
    const r = this.renderer!
    let asset: LookAsset
    try {
      acquireLook(req.look)
      asset = await loadLook(req.look)
    } catch {
      releaseLook(req.look)
      return null
    }
    const q = qualityFor(this.rendererTier ?? tier)
    const scene = new Scene()
    const actor = new Actor(asset, { quality: { outline: q.outline, springs: false, outlinePx: q.outlinePx }, variant: req.variant, stage: req.stage, face: req.face, rng: seededRandom(5) })
    scene.add(actor.root)
    actor.place(0, 0, req.yawDeg ?? ART.portrait.yawDeg)
    actor.play(req.clip ?? 'idle', { fade: 0 })
    actor.update(0, false)
    const size = req.size
    const pr = r.getPixelRatio()
    const px = Math.round(size * pr)
    actor.setResolution(px, px)
    const sc = portraitCamera(size, MODEL_LOOKS[req.look].unitsPerMetre)
    const n = cameraNumbers(sc)
    const cam = new PerspectiveCamera(n.fovDeg, n.aspect, n.near, n.far)
    cam.position.set(...n.position)
    cam.lookAt(new Vector3(...n.lookAt))
    cam.updateMatrixWorld()
    actor.applyLight(this.rig, cam.matrixWorldInverse)
    if (this.blob) {
      const h = asset.meta.restHeight * actor.unitsPerMetre
      const shadow = new Mesh(new CircleGeometry(1, 28), new MeshBasicMaterial({ map: this.blob, transparent: true, depthWrite: false, opacity: ART.stage.shadow.alpha }))
      shadow.rotation.x = -Math.PI / 2
      shadow.position.y = 0.5
      shadow.scale.set(h * ART.stage.shadow.widthFrac, h * ART.stage.shadow.depthFrac, 1)
      scene.add(shadow)
    }
    // Draw through the canvas itself (an off-screen target would skip the sRGB output encoding and give a dark
    // picture): resize, render, capture the bitmap, then put the live host's frame straight back.
    const canvas = this.canvas!
    const host = this.host
    r.setRenderTarget(null)
    r.setSize(size, size, false)
    r.setClearColor(0x000000, 0)
    r.clear()
    r.render(scene, cam)
    const captured = new Promise<Blob | null>((resolve) => {
      canvas.toBlob((b) => {
        if (b && b.type === 'image/webp') resolve(b)
        else canvas.toBlob((p) => resolve(p), 'image/png')
      }, 'image/webp', 0.9)
    })
    actor.dispose()
    releaseLook(req.look)
    if (host && host.width) {
      r.setSize(host.width, host.height, false)
      this.render()
    }
    return captured
  }
}
