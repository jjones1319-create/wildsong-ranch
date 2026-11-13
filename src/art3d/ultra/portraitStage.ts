import {
  AddEquation,
  AnimationMixer,
  Box3,
  CanvasTexture,
  Color,
  CustomBlending,
  CustomToneMapping,
  DirectionalLight,
  Group,
  HemisphereLight,
  LoopOnce,
  LoopRepeat,
  Mesh,
  MeshBasicMaterial,
  OneFactor,
  PerspectiveCamera,
  PlaneGeometry,
  PMREMGenerator,
  Scene,
  SRGBColorSpace,
  Vector3,
  WebGLRenderer,
  ZeroFactor,
} from 'three'
import type { AnimationAction, AnimationClip, Material, Object3D, Texture } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { ULTRA_LOOKS, ultraHeightPct, type UltraId } from '../../art/ultraLooks.ts'
import { ART } from '../../data/tuning.ts'
import { art3dLost, art3dUnavailable } from '../../ui/store/artStore.ts'
import type { LightPreset } from '../materials.ts'
import { dirFrom, installFilmToneMapping, setFilmClock, studioEnvironmentScene } from '../perf/content.ts'
import { resolveClipName } from './clips.ts'
import { lapPlan, lapPose, liftAt, shadowAt, type FlightPlan, type FlyTimes } from './flight.ts'
import { blinkClipOf, flyTimesOf, loadUltraAsset, makeUltraModel, NO_AO_LAYER, wingspanOf, type UltraAsset, type UltraModel } from './ultraAsset.ts'

export { seededRandom } from '../faceCells.ts'

/**
 * Art 2.1 on the ranch (the owner's option A, Nov 12): the live portraits of the monsters with an Ultra look. One
 * shared WebGL canvas that hosts come and go from (a second host evicts the first, which shows its Classic drawing),
 * the film materials lit by the ranch's season and weather, no post effects (a 200 px box doesn't need them). It draws
 * only while its box is on screen and the page is shown; Lite loads the Lite copy at a lower pixel ratio and frame
 * rate; Reduce motion draws one still frame. A look that flies takes a lap when asked (flight.ts lapPlan).
 */

const R3 = ART.ranch3d
const S = ART.ultra.studio
const BASE = import.meta.env.BASE_URL

export interface UltraPortraitSpec {
  look: UltraId
  variant: string | null
  /** The loop it rests in (idle, or the mood's: idle_happy, idle_tired…). */
  clip: string
  /** Its turn toward the camera (degrees; mirrored portraits turn the other way). */
  yawDeg: number
  light: LightPreset
}

export interface UltraPortraitOptions {
  lite: boolean
  /** Reduce motion: one still frame (no clip time, no blinks, no laps). */
  still: boolean
  onReady?: () => void
  onFailed?: () => void
  onLost?: () => void
  onRestored?: () => void
  onEvicted?: () => void
}

export interface UltraPortraitStats {
  look: UltraId | null
  clip: string | null
  flies: boolean
  liftM: number
  lapping: boolean
  dpr: number
  drawing: boolean
}

export interface UltraPortraitHandle {
  readonly live: boolean
  show(spec: UltraPortraitSpec): void
  setLight(preset: LightPreset): void
  /** The loop to rest in. */
  setBase(clip: string): void
  /** An act: a one-shot that settles back into the base loop, or a loop for `seconds`. False if the file lacks it. */
  play(clip: string, seconds?: number): boolean
  /** Something other than the base loop is playing (an act or a lap). */
  busy(): boolean
  flies(): boolean
  /** Take off, fly a circle and land (false if it can't fly, is busy or is still). */
  flyLap(): boolean
  /** Its box is on screen (an IntersectionObserver's answer). */
  setVisible(on: boolean): void
  stats(): UltraPortraitStats
  release(): void
}

interface Shown {
  spec: UltraPortraitSpec
  asset: UltraAsset
  u: UltraModel
  root: Group
  mixer: AnimationMixer
  actions: Map<string, AnimationAction>
  current: string
  /** When the act playing settles back into the base loop (mixer seconds), or 0. */
  backAt: number
  blink: string | null
  nextBlink: number
  blinks: number
  fly: { times: FlyTimes; spanM: number } | null
  lap: FlightPlan | null
  lapStep: number
  lift: number
  /** The framing: the standing box's centre and size (m), fitted once. */
  centre: Vector3
  size: Vector3
}

/** A colour's brightness (linear luminance). */
function lum(hex: string): number {
  const c = new Color(hex)
  return Math.max(1e-3, 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b)
}

let blobTexture: CanvasTexture | null = null

function blob(): CanvasTexture {
  if (blobTexture) return blobTexture
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const g = c.getContext('2d')!
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32)
  r.addColorStop(0, 'rgba(30,26,20,1)')
  r.addColorStop(0.5, 'rgba(30,26,20,0.55)')
  r.addColorStop(1, 'rgba(30,26,20,0)')
  g.fillStyle = r
  g.fillRect(0, 0, 64, 64)
  blobTexture = new CanvasTexture(c)
  blobTexture.colorSpace = SRGBColorSpace
  return blobTexture
}

export class UltraPortraitStage {
  private static instance: UltraPortraitStage | null = null

  static get(): UltraPortraitStage {
    return (UltraPortraitStage.instance ??= new UltraPortraitStage())
  }

  private renderer: WebGLRenderer | null = null
  private canvas: HTMLCanvasElement | null = null
  private lite = false
  private environment: Texture | null = null
  private loader: GLTFLoader | null = null
  private readonly assets = new Map<string, Promise<UltraAsset>>()
  private readonly scene = new Scene()
  private readonly camera = new PerspectiveCamera(30, 1, 0.05, 60)
  private readonly key = new DirectionalLight(0xffffff, S.key.intensity)
  private readonly rim = new DirectionalLight(0xffffff, S.rim.intensity)
  private readonly rim2 = new DirectionalLight(0xffffff, S.rim2.intensity)
  private readonly hemi = new HemisphereLight(0xffffff, S.ground, S.hemi)
  private shadow: Mesh | null = null
  private host: { el: HTMLElement; opts: UltraPortraitOptions; handle: UltraPortraitHandle; visible: boolean } | null = null
  private shown: Shown | null = null
  private serial = 0
  private raf = 0
  private last = 0
  private now = 0
  private accum = 0
  private lost = false
  private sizeStamp = ''
  private idleTimer: ReturnType<typeof setTimeout> | null = null
  private readonly onVisibility = () => this.wake()

  private constructor() {
    // the cards (fur, tufts) sit on the AO-free layer: this camera draws them too
    this.camera.layers.enable(NO_AO_LAYER)
    this.scene.add(this.key, this.key.target, this.rim, this.rim.target, this.rim2, this.rim2.target, this.hemi)
  }

  /* -------------------------------------------------------------------------------------------- the renderer */

  private ensureRenderer(lite: boolean): boolean {
    if (this.renderer && this.lite === lite) return true
    if (this.renderer) this.destroyRenderer()
    try {
      const canvas = document.createElement('canvas')
      canvas.className = 'art3d-canvas'
      // MSAA (antialias) is what lets the fur cards use alpha to coverage; Lite draws them with a plain alpha test
      const r = new WebGLRenderer({ canvas, alpha: true, antialias: !lite, powerPreference: 'default', stencil: false })
      r.setClearColor(0x000000, 0)
      r.outputColorSpace = SRGBColorSpace
      installFilmToneMapping()
      r.toneMapping = CustomToneMapping
      r.toneMappingExposure = S.exposure
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
        this.wake()
        this.host?.opts.onRestored?.()
      })
      const pmrem = new PMREMGenerator(r)
      this.environment = pmrem.fromScene(studioEnvironmentScene(), 0.04).texture
      pmrem.dispose()
      const loader = new GLTFLoader()
      loader.setMeshoptDecoder(MeshoptDecoder)
      const ktx2 = new KTX2Loader().setTranscoderPath(`${BASE}basis/`)
      ;(ktx2 as unknown as { detectSupport(r: unknown): void }).detectSupport(r)
      loader.setKTX2Loader(ktx2)
      this.loader = loader
      this.renderer = r
      this.canvas = canvas
      this.lite = lite
      this.scene.environment = this.environment
      this.scene.environmentIntensity = S.environment
      return true
    } catch (e) {
      if (import.meta.env.DEV) console.warn('[ultra portrait] WebGL unavailable', e)
      art3dUnavailable.value = true
      return false
    }
  }

  private destroyRenderer(): void {
    this.stopLoop()
    this.drop()
    this.assets.clear()
    this.environment?.dispose()
    this.environment = null
    this.scene.environment = null
    this.renderer?.dispose()
    this.canvas?.remove()
    this.renderer = null
    this.canvas = null
    this.loader = null
  }

  /* -------------------------------------------------------------------------------------------- hosts */

  mount(el: HTMLElement, opts: UltraPortraitOptions): UltraPortraitHandle | null {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer)
      this.idleTimer = null
    }
    if (!this.ensureRenderer(opts.lite)) return null
    if (this.host) {
      const old = this.host
      this.detach()
      old.opts.onEvicted?.()
    }
    const canvas = this.canvas!
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none'
    el.appendChild(canvas)
    const handle = this.makeHandle()
    this.host = { el, opts, handle, visible: true }
    this.sizeStamp = ''
    document.addEventListener('visibilitychange', this.onVisibility)
    return handle
  }

  private detach(): void {
    this.stopLoop()
    document.removeEventListener('visibilitychange', this.onVisibility)
    this.drop()
    this.canvas?.remove()
    this.host = null
    this.idleTimer = setTimeout(() => {
      this.idleTimer = null
      if (!this.host) this.destroyRenderer()
    }, ART.stage.idleReleaseMs)
  }

  private makeHandle(): UltraPortraitHandle {
    const self = this
    const mine = () => self.host?.handle === handle
    const handle: UltraPortraitHandle = {
      get live() {
        return mine()
      },
      show: (spec) => {
        if (mine()) self.show(spec)
      },
      setLight: (preset) => {
        if (!mine() || !self.shown) return
        self.shown.spec = { ...self.shown.spec, light: preset }
        self.applyLight(preset)
        self.wake(true)
      },
      setBase: (clip) => {
        const s = self.shown
        if (!mine() || !s || s.spec.clip === clip) return
        s.spec = { ...s.spec, clip }
        if (!s.backAt && !s.lap) self.playOn(s, clip, true)
        self.wake(true)
      },
      play: (clip, seconds) => (mine() ? self.act(clip, seconds) : false),
      busy: () => !!self.shown && (self.shown.backAt > 0 || !!self.shown.lap),
      flies: () => !!self.shown?.fly,
      flyLap: () => (mine() ? self.startLap() : false),
      setVisible: (on) => {
        if (!mine()) return
        self.host!.visible = on
        self.wake()
      },
      stats: () => {
        const s = self.shown
        return { look: s?.spec.look ?? null, clip: s?.current || null, flies: !!s?.fly, liftM: +(s?.lift ?? 0).toFixed(3), lapping: !!s?.lap, dpr: self.renderer?.getPixelRatio() ?? 0, drawing: self.raf !== 0 }
      },
      release: () => {
        if (mine()) self.detach()
      },
    }
    return handle
  }

  /* -------------------------------------------------------------------------------------------- the monster */

  private load(id: UltraId): Promise<UltraAsset> {
    const k = `${id}|${this.lite}`
    let p = this.assets.get(k)
    if (!p) {
      p = loadUltraAsset(this.loader!, id, this.lite)
      p.catch(() => this.assets.delete(k))
      this.assets.set(k, p)
    }
    return p
  }

  private show(spec: UltraPortraitSpec): void {
    const s = this.shown
    if (s && s.spec.look === spec.look && s.spec.variant === spec.variant) {
      // the same monster: its turn, light and resting loop follow
      const turn = s.spec.yawDeg !== spec.yawDeg
      s.spec = spec
      if (turn) s.root.rotation.y = (spec.yawDeg * Math.PI) / 180
      this.applyLight(spec.light)
      if (!s.backAt && !s.lap) this.playOn(s, spec.clip, true)
      this.wake(true)
      return
    }
    const id = ++this.serial
    this.load(spec.look).then(
      (asset) => {
        if (id !== this.serial || !this.host) return
        this.drop()
        this.build(spec, asset)
        this.host.opts.onReady?.()
        this.wake(true)
      },
      (err: unknown) => {
        if (import.meta.env.DEV) console.warn('[ultra portrait] load failed', spec.look, err)
        if (id === this.serial) this.host?.opts.onFailed?.()
      },
    )
  }

  private build(spec: UltraPortraitSpec, asset: UltraAsset): void {
    const look = ULTRA_LOOKS[spec.look]
    const heightM = (ART.duel.monsterHeightM * (look ? ultraHeightPct(look) : 100)) / 100
    const u = makeUltraModel(asset, spec.variant, heightM)
    coverage(u.model, this.lite ? 0 : 4)
    const times = flyTimesOf(asset, asset.clips)
    const flyClip = asset.clips.find((c) => c.name === 'fly')
    const fly = times && flyClip ? { times, spanM: wingspanOf(u, asset.meta, flyClip) } : null
    const root = new Group()
    root.add(u.model)
    root.rotation.y = (spec.yawDeg * Math.PI) / 180
    this.scene.add(root)
    const mixer = new AnimationMixer(u.model)
    const actions = new Map<string, AnimationAction>()
    for (const c of asset.clips as AnimationClip[]) actions.set(c.name, mixer.clipAction(c))
    // the standing box, measured once at rest (the framing doesn't breathe with the clips)
    root.updateMatrixWorld(true)
    const box = new Box3()
    u.model.traverse((o) => {
      if ((o as Mesh).isMesh && o.visible) box.union(new Box3().setFromObject(o))
    })
    const size = box.isEmpty() ? new Vector3(u.size.width, u.size.height, u.size.front + u.size.back) : box.getSize(new Vector3())
    const centre = box.isEmpty() ? new Vector3(0, u.size.height / 2, 0) : box.getCenter(new Vector3())
    if (!this.shadow) {
      this.shadow = new Mesh(new PlaneGeometry(1, 1), new MeshBasicMaterial({ map: blob(), transparent: true, depthWrite: false, opacity: R3.shadow.opacity }))
      this.shadow.rotation.x = -Math.PI / 2
      this.shadow.renderOrder = -1
      this.shadow.layers.set(NO_AO_LAYER)
    }
    this.scene.add(this.shadow)
    const s: Shown = {
      spec, asset, u, root, mixer, actions, current: '', backAt: 0, blink: blinkClipOf(asset), nextBlink: this.now + 2.2, blinks: 0,
      fly, lap: null, lapStep: 0, lift: 0, centre, size,
    }
    this.shown = s
    this.applyLight(spec.light)
    this.playOn(s, spec.clip, true, 0)
    mixer.update(0)
    this.sizeStamp = ''
  }

  private drop(): void {
    const s = this.shown
    if (!s) return
    s.mixer.stopAllAction()
    this.scene.remove(s.root)
    for (const m of s.u.materials as Material[]) m.dispose()
    if (this.shadow) this.scene.remove(this.shadow)
    this.shown = null
  }

  private playOn(s: Shown, name: string, loop: boolean, fade = 0.25, rate = 1, offset = 0): boolean {
    const clip = resolveClipName((n) => s.actions.has(n), name)
    if (!clip) return false
    const next = s.actions.get(clip)!
    if (s.current === clip && loop) return true
    const prev = s.actions.get(s.current)
    next.reset()
    next.setLoop(loop ? LoopRepeat : LoopOnce, loop ? Infinity : 1)
    next.clampWhenFinished = !loop
    next.timeScale = rate
    next.time = offset
    next.enabled = true
    next.setEffectiveWeight(1)
    next.play()
    if (prev && prev !== next) prev.crossFadeTo(next, fade, false)
    s.current = clip
    return true
  }

  private act(name: string, seconds?: number): boolean {
    const s = this.shown
    if (!s || s.lap || this.host?.opts.still) return false
    const meta = s.asset.meta?.clips?.[name]
    const loop = meta?.loop !== false
    if (!this.playOn(s, name, loop)) return false
    const len = loop ? (seconds ?? meta?.seconds ?? 2) : (s.actions.get(s.current)?.getClip().duration ?? 1)
    s.backAt = s.mixer.time + len
    this.wake()
    return true
  }

  private startLap(): boolean {
    const s = this.shown
    if (!s?.fly || s.lap || s.backAt || this.host?.opts.still) return false
    s.lap = lapPlan(this.now, s.fly.times, s.u.size.height)
    s.lapStep = 0
    this.wake()
    return true
  }

  /* -------------------------------------------------------------------------------------------- light */

  /**
   * The season's and weather's mood (ART.light) on the film studio: the key, the sky fill and the rims take its colours,
   * and the key and the room's reflections dim with its brightness beside a clear day's (night is dark and blue, rain
   * grey and soft), within R3.mood's bounds.
   */
  private applyLight(preset: LightPreset): void {
    const L = ART.light[preset] ?? ART.light.day
    const day = ART.light.day
    const d = new Vector3(L.dir[0], L.dir[1], L.dir[2]).normalize()
    const k = (a: string, b: string) => Math.min(R3.mood.max, Math.max(R3.mood.min, lum(a) / lum(b)))
    this.key.color = new Color(L.key)
    this.key.intensity = S.key.intensity * k(L.key, day.key)
    this.key.position.copy(d).multiplyScalar(10)
    this.hemi.color = new Color(L.fill)
    this.scene.environmentIntensity = S.environment * k(L.fill, day.fill)
    this.rim.color = new Color(L.rim)
    this.rim.position.copy(dirFrom(S.rim.azDeg, S.rim.elDeg)).multiplyScalar(10)
    this.rim2.color = new Color(L.rim)
    this.rim2.position.copy(dirFrom(S.rim2.azDeg, S.rim2.elDeg)).multiplyScalar(10)
  }

  /* -------------------------------------------------------------------------------------------- frames */

  /** Draw while it should (its box shown, the page shown, not still), else stop; `once` draws a frame now regardless. */
  private wake(once = false): void {
    const h = this.host
    const should = !!h && h.visible && !document.hidden && !this.lost && !h.opts.still && !!this.shown
    if (should && !this.raf) {
      this.last = 0
      const tick = (t: number) => {
        this.raf = requestAnimationFrame(tick)
        this.frame(t)
      }
      this.raf = requestAnimationFrame(tick)
    } else if (!should) {
      this.stopLoop()
      if (once && h && !this.lost) this.render()
    }
  }

  private stopLoop(): void {
    if (this.raf) cancelAnimationFrame(this.raf)
    this.raf = 0
  }

  private frame(t: number): void {
    const dt = this.last ? Math.min(100, t - this.last) : 16.7
    this.last = t
    if (this.lite) {
      this.accum += dt
      if (this.accum < 1000 / R3.liteFps) return
      this.advance(this.accum / 1000)
      this.accum = 0
    } else this.advance(dt / 1000)
    this.render()
  }

  private advance(dt: number): void {
    const s = this.shown
    if (!s) return
    this.now += dt
    const lap = s.lap
    if (lap) {
      while (s.lapStep < lap.steps.length && this.now >= lap.steps[s.lapStep]!.at) {
        const st = lap.steps[s.lapStep++]!
        this.playOn(s, st.clip, st.loop, ART.duel.flight.fadeSec, st.rate, st.offset)
      }
      s.lift = liftAt(lap, this.now)
      if (this.now >= lap.end) {
        s.lap = null
        s.lift = 0
        this.playOn(s, s.spec.clip, true)
      }
    } else if (s.backAt && s.mixer.time >= s.backAt) {
      s.backAt = 0
      this.playOn(s, s.spec.clip, true)
    }
    if (s.blink && this.now >= s.nextBlink) {
      const b = s.actions.get(s.blink)!
      b.reset()
      b.setLoop(LoopOnce, 1)
      b.clampWhenFinished = false
      b.play()
      s.nextBlink = this.now + ART.gallery3d.blinkGapsSec[s.blinks++ % ART.gallery3d.blinkGapsSec.length]!
    }
    s.mixer.update(dt)
    setFilmClock(this.now, false)
  }

  private place(): void {
    const s = this.shown
    if (!s) return
    const yaw = (s.spec.yawDeg * Math.PI) / 180
    const q = s.lap ? lapPose(s.lap, this.now, (s.u.size.height * R3.flyLap.radiusPct) / 100) : { x: 0, z: 0, turn: 0, k: 0 }
    // the lap's offsets are in its own frame (x to its side, z toward the camera before its turn)
    const c = Math.cos(yaw)
    const sn = Math.sin(yaw)
    s.root.position.set(q.x * c + q.z * sn, s.lift, -q.x * sn + q.z * c)
    s.root.rotation.y = yaw + q.turn
    const sh = this.shadow
    if (sh) {
      const k = shadowAt(s.lift, s.u.size.height)
      sh.position.set(s.root.position.x, 0.004, s.root.position.z)
      sh.scale.set(((s.size.x * R3.shadow.widthPct) / 100) * 1.6 * k.scale, ((s.size.z * R3.shadow.depthPct) / 100) * 1.6 * k.scale, 1)
      ;(sh.material as MeshBasicMaterial).opacity = R3.shadow.opacity * k.opacity
    }
  }

  /** The portrait's camera: the standing body fills bodyPct of the box, its feet floorPct up from the bottom. */
  private aim(w: number, h: number): void {
    const s = this.shown
    if (!s) return
    const cam = this.camera
    cam.aspect = w / h
    const tanV = Math.tan((cam.fov * Math.PI) / 360)
    const viewH = Math.max(s.size.y, (s.size.x * 1.08) / cam.aspect) / (R3.bodyPct / 100)
    let d = viewH / 2 / tanV + s.size.z / 2
    const look = new Vector3(s.centre.x, viewH * (0.5 - R3.floorPct / 100), s.centre.z)
    // a lap: back off as it rises and circles, and follow it up a little
    if (s.lap && s.fly) {
      const peak = (s.u.size.height * R3.flyLap.peakPct) / 100
      const up = Math.min(1, s.lift / Math.max(1e-3, peak))
      const round = Math.sin(Math.PI * lapPose(s.lap, this.now, 1).k)
      const k = Math.max(up, round)
      d *= 1 + (R3.flyLap.zoomOut - 1) * k
      look.y += s.lift * 0.4 * k
    }
    const p = (R3.pitchDeg * Math.PI) / 180
    cam.position.set(look.x, look.y + Math.sin(p) * d, look.z + Math.cos(p) * d)
    cam.lookAt(look)
    cam.updateProjectionMatrix()
  }

  private render(): void {
    const r = this.renderer
    const h = this.host
    if (!r || !h || this.lost || !this.shown) return
    const w = Math.max(1, Math.round(h.el.clientWidth))
    const hh = Math.max(1, Math.round(h.el.clientHeight))
    const cap = this.lite ? R3.liteDprCap : R3.dprCap
    const stamp = `${w}x${hh}@${cap}`
    if (stamp !== this.sizeStamp) {
      this.sizeStamp = stamp
      r.setPixelRatio(Math.min(window.devicePixelRatio || 1, cap))
      r.setSize(w, hh, false)
    }
    this.place()
    this.aim(w, hh)
    r.render(this.scene, this.camera)
  }
}

/**
 * Alpha to coverage only with MSAA (perf/view.ts setCoverage, kept here so this chunk doesn't load the effect passes):
 * the fur cards carry userData.a2c. This canvas is see-through over the ranch's picture, so a card's partial alpha
 * must not overwrite the opaque body under it (the picture showed through as pale specks in the fur): its colour
 * replaces, its alpha only adds (the body stays opaque; the outline's own soft edge stays soft).
 */
function coverage(root: Object3D, msaa: number): void {
  root.traverse((o) => {
    const mat = (o as { material?: Material & { userData?: { a2c?: boolean }; alphaToCoverage: boolean } }).material
    if (!mat?.userData?.a2c) return
    const on = msaa > 0
    if (mat.alphaToCoverage !== on) {
      mat.alphaToCoverage = on
      mat.needsUpdate = true
    }
    mat.blending = CustomBlending
    mat.blendEquation = AddEquation
    mat.blendSrc = OneFactor
    mat.blendDst = ZeroFactor
    mat.blendEquationAlpha = AddEquation
    mat.blendSrcAlpha = OneFactor
    mat.blendDstAlpha = OneFactor
  })
}
