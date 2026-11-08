import { AnimationMixer, Box3, Group, LoopOnce, LoopRepeat, PerspectiveCamera, Scene, Vector3 } from 'three'
import type { AnimationAction, Mesh, Object3D } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { ULTRA_LOOKS, ultraHeightPct, type UltraId } from '../../art/ultraLooks.ts'
import { ART } from '../../data/tuning.ts'
import { buildStudio, setFilmClock } from '../perf/content.ts'
import { createDynRes, type DynRes } from '../perf/dynres.ts'
import { createView, type Backend, type Level, type PerfView } from '../perf/view.ts'
import { GALLERY_LOOPS, resolveClipName, type GalleryClip } from '../ultra/clips.ts'
import { blinkClipOf, NO_AO_LAYER, heldVariants, loadUltraAsset, makeUltraModel, type UltraAsset, type UltraKind, type UltraModel } from '../ultra/ultraAsset.ts'

/**
 * Lab → 3D Gallery: one finished Ultra breed on a turntable in the film look (the Art 2.1 renderer of Battle 3D and the
 * review sheets), its moves on buttons, its variants, and Puddlepup beside it at true scale. Drag turns it, a pinch or
 * the buttons zoom. Lite effects load the breed's Lite file.
 */

const G = ART.gallery3d
const BASE = import.meta.env.BASE_URL

export interface GalleryOptions {
  canvas: HTMLCanvasElement
  lite: boolean
  reduceMotion: boolean
  backend?: Backend
  /** Review captures: hold full quality at the phone's resolution (no dynamic resolution). */
  fixedQuality?: boolean
}

export interface GalleryShow {
  /** The look: a breed, or a grown form (`hearthwing-grown`). */
  look: UltraId
  variant: string | null
  /** Puddlepup beside it, both at true scale. */
  compare: boolean
}

export interface GalleryStats {
  backend: Backend
  fps: number
  dpr: number
  level: Level
  look: UltraId
  kind: UltraKind | null
  triangles: number
  /** The clip playing on the shown breed (after fallbacks), or null while loading. */
  clip: string | null
}

export interface Gallery3D {
  /** Show a breed (loads it once; resolves when it stands there). */
  show(s: GalleryShow): Promise<void>
  /** Play a move on the shown breed: idle and walk loop; the rest play once and settle back into idle. */
  play(clip: GalleryClip): void
  /** Review only: hold the shown breed in a move at a share of its length (0–1); null lets it play on. */
  pose(clip: GalleryClip | null, t?: number): void
  /** Turn the turntable (degrees) and tilt the camera (degrees). */
  turn(yawDeg: number, pitchDeg: number): void
  /** Zoom by a factor (>1 closer), or back to the fitted view with 0. */
  zoom(k: number): void
  /** The variants the shown breed's file really holds. */
  variants(): string[]
  stats(): GalleryStats
  /** A frame as a PNG data URL (review and tests). */
  snapshot(): string
  /** Dev and review only: the scene and camera. */
  inspect(): { scene: Scene; camera: PerspectiveCamera; view: PerfView }
  dispose(): void
}

interface Stand {
  look: UltraId
  asset: UltraAsset
  u: UltraModel
  root: Group
  mixer: AnimationMixer
  actions: Map<string, AnimationAction>
  current: string
  /** A one-shot's settle-back time (mixer seconds), or 0. */
  backAt: number
  blink: string | null
  nextBlink: number
  blinks: number
  triangles: number
}

function makeLoader(renderer: unknown): GLTFLoader {
  const loader = new GLTFLoader()
  loader.setMeshoptDecoder(MeshoptDecoder)
  const ktx2 = new KTX2Loader().setTranscoderPath(`${BASE}basis/`)
  ;(ktx2 as unknown as { detectSupport(r: unknown): void }).detectSupport(renderer)
  loader.setKTX2Loader(ktx2)
  return loader
}

function countTriangles(root: Object3D): number {
  let n = 0
  root.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh || !m.visible) return
    const g = m.geometry
    n += (g.index ? g.index.count : (g.attributes.position?.count ?? 0)) / 3
  })
  return Math.round(n)
}

export async function createGallery3D(o: GalleryOptions): Promise<Gallery3D> {
  const canvas = o.canvas
  const w = () => Math.max(1, canvas.clientWidth)
  const h = () => Math.max(1, canvas.clientHeight)
  const dprMax = Math.max(1, Math.min(o.lite ? G.liteDprMax : ART.ultra.scaling.dprMax, devicePixelRatio || 1))
  const dpr0 = o.fixedQuality ? dprMax : Math.min(o.lite ? G.liteDprStart : G.dprStart, dprMax)
  const wantGpu = (o.backend ?? 'webgpu') === 'webgpu' && !o.lite && 'gpu' in navigator
  let view: PerfView | undefined = wantGpu ? await createView('webgpu', { canvas, width: w(), height: h(), dpr: dpr0, cinematic: false, focus: 3 }).catch(() => undefined) : undefined
  if (!view) view = await createView('webgl', { canvas, width: w(), height: h(), dpr: dpr0, cinematic: false, focus: 3 })
  const v = view!
  const scene = new Scene()
  const camera = new PerspectiveCamera(G.fov, w() / h(), 0.05, 100)
  camera.layers.enable(NO_AO_LAYER)
  buildStudio(scene, v.environment, new Vector3(0, 0.5, 0), G.studioReachM)
  await v.init(scene, camera)
  if (o.lite) v.setLevel('no-msaa')
  const dyn: DynRes = createDynRes(v, { lite: o.lite, dprStart: dpr0, dprMax, size: () => ({ w: w(), h: h() }), fastDrop: ART.duel.fastDrop })
  if (o.fixedQuality) dyn.pause(Infinity)
  const loader = makeLoader(v.renderer)
  const assets = new Map<UltraId, Promise<UltraAsset>>()
  const load = (b: UltraId) => {
    let p = assets.get(b)
    if (!p) {
      p = loadUltraAsset(loader, b, o.lite)
      // a failed load can be tried again later
      p.catch(() => assets.delete(b))
      assets.set(b, p)
    }
    return p
  }

  let stands: Stand[] = []
  /** The turntable: the stands ride on it, a drag turns it. */
  const turntable = new Group()
  scene.add(turntable)
  let shown: GalleryShow | null = null
  let serial = 0
  let yaw: number = G.startYawDeg
  let pitch: number = G.pitchDeg
  let zoomK = 1
  const target = new Vector3(0, 0.5, 0)
  let fitDist = 3
  let now = 0
  let last = performance.now()
  const frames: number[] = []
  let raf = 0
  let disposed = false
  // review only: the shown breed held still in a pose
  let frozen = false

  function makeStand(asset: UltraAsset, id: UltraId, variant: string | null): Stand {
    const look = ULTRA_LOOKS[id]
    const heightM = (ART.duel.monsterHeightM * (look ? ultraHeightPct(look) : 100)) / 100
    const u = makeUltraModel(asset, variant, heightM)
    const root = new Group()
    root.add(u.model)
    const mixer = new AnimationMixer(u.model)
    const actions = new Map<string, AnimationAction>()
    for (const c of asset.clips) actions.set(c.name, mixer.clipAction(c))
    const s: Stand = { look: id, asset, u, root, mixer, actions, current: '', backAt: 0, blink: blinkClipOf(asset), nextBlink: G.blinkGapsSec[0]!, blinks: 1, triangles: countTriangles(u.model) }
    playOn(s, 'idle')
    return s
  }

  function playOn(s: Stand, name: string): void {
    const clip = resolveClipName((n) => s.actions.has(n), name)
    if (!clip) return
    const loop = GALLERY_LOOPS.has(name)
    const next = s.actions.get(clip)!
    const prev = s.actions.get(s.current)
    next.reset()
    next.setLoop(loop ? LoopRepeat : LoopOnce, loop ? Infinity : 1)
    next.clampWhenFinished = !loop
    next.enabled = true
    next.setEffectiveWeight(1)
    next.play()
    if (prev && prev !== next) prev.crossFadeTo(next, G.fadeSec, false)
    s.current = clip
    // a one-shot holds its last pose a moment (the ko longer), then settles back into idle
    s.backAt = loop ? 0 : s.mixer.time + next.getClip().duration + (name === 'ko' ? G.koHoldSec : G.holdSec)
  }

  function blinkOn(s: Stand): void {
    const a = s.blink ? s.actions.get(s.blink) : undefined
    if (!a) return
    a.reset()
    a.setLoop(LoopOnce, 1)
    a.clampWhenFinished = false
    a.play()
    s.nextBlink = now + G.blinkGapsSec[s.blinks++ % G.blinkGapsSec.length]!
  }

  /**
   * Stands side by side on one turntable (the shown breed on the left, both facing the camera at yaw 0, a hand's gap
   * between their widths); the camera fitted snugly to what stands there now (the turntable's turn included). A drag
   * keeps the distance (no breathing); ⤢ and a new breed fit again.
   */
  function layout(): void {
    if (stands.length === 2) {
      const [a, b] = stands as [Stand, Stand]
      const sep = a.u.size.width / 2 + b.u.size.width / 2 + G.compareGapM
      a.root.position.set(-sep / 2, 0, 0)
      b.root.position.set(sep / 2, 0, 0)
    } else if (stands[0]) stands[0].root.position.set(0, 0, 0)
    turntable.rotation.y = (yaw * Math.PI) / 180
    turntable.updateMatrixWorld(true)
    const box = new Box3()
    for (const s of stands) {
      s.u.model.traverse((o) => {
        if ((o as Mesh).isMesh && o.visible) box.union(new Box3().setFromObject(o))
      })
    }
    if (box.isEmpty()) return
    box.getCenter(target)
    const size = box.getSize(new Vector3())
    const tanV = Math.tan((G.fov * Math.PI) / 360)
    const tanH = tanV * camera.aspect
    // its width and height in the lens, backed off by part of its depth (the near side looks bigger)
    fitDist = Math.max(((size.x / 2) * G.fitMargin) / tanH, ((size.y / 2) * G.fitMargin) / tanV) + ((size.z / 2) * G.fitDepthPct) / 100
  }

  function aim(): void {
    const d = fitDist / zoomK
    const p = (pitch * Math.PI) / 180
    camera.position.set(target.x, target.y + Math.sin(p) * d, target.z + Math.cos(p) * d)
    camera.lookAt(target)
    camera.updateMatrixWorld()
  }

  let lastW = w()
  let lastH = h()
  function loop(): void {
    if (disposed) return
    raf = requestAnimationFrame(loop)
    const t = performance.now()
    const frameMs = t - last
    last = t
    const dt = Math.min(0.1, frameMs / 1000)
    now += dt
    frames.push(frameMs)
    if (frames.length > 90) frames.shift()
    if (w() !== lastW || h() !== lastH) {
      lastW = w()
      lastH = h()
      camera.aspect = lastW / lastH
      camera.updateProjectionMatrix()
      v.setSize(lastW, lastH, dyn.dpr())
      layout()
    }
    for (const s of stands) {
      if (s.backAt && s.mixer.time >= s.backAt) playOn(s, 'idle')
      if (now >= s.nextBlink) blinkOn(s)
      if (!(frozen && s === stands[0])) s.mixer.update(dt)
    }
    aim()
    // the glow's twinkle (still with Reduce motion)
    setFilmClock(now, o.reduceMotion)
    v.render()
    dyn.frame(frameMs)
  }

  camera.aspect = w() / h()
  camera.updateProjectionMatrix()
  raf = requestAnimationFrame(loop)

  function clear(): void {
    for (const s of stands) {
      s.root.removeFromParent()
      s.mixer.stopAllAction()
      for (const m of s.u.materials) m.dispose()
    }
    stands = []
  }

  return {
    async show(next) {
      const id = ++serial
      const assetsNeeded = await Promise.all([load(next.look), next.compare ? load('puddlepup') : null])
      if (disposed || id !== serial) return
      clear()
      const main = makeStand(assetsNeeded[0], next.look, next.variant)
      main.nextBlink = now + G.blinkGapsSec[0]!
      stands = [main]
      if (assetsNeeded[1]) {
        const pal = makeStand(assetsNeeded[1], 'puddlepup', null)
        pal.nextBlink = now + G.blinkGapsSec[1]!
        stands.push(pal)
      }
      for (const s of stands) {
        turntable.add(s.root)
        v.prepare(s.root)
      }
      shown = next
      // a new monster (or pair) is fitted afresh
      zoomK = 1
      layout()
      aim()
      // the uploads and shader compiles of a new model aren't the phone's pace
      dyn.pause(ART.ultra.scaling.graceMs)
      // compile now, so the first frame of a new breed doesn't stall (where the renderer can)
      try {
        await (v.renderer as { compileAsync?: (s: Scene, c: PerspectiveCamera) => Promise<unknown> }).compileAsync?.(scene, camera)
      } catch {
        /* compiled on first use instead */
      }
    },
    pose(clip, t = 0.99) {
      const s = stands[0]
      frozen = clip !== null
      if (!s || !clip) return
      playOn(s, clip)
      const a = s.actions.get(s.current)
      if (!a) return
      // jump straight into the move (no cross-fade), at that moment
      s.mixer.stopAllAction()
      a.reset().play()
      a.time = Math.min(1, Math.max(0, t)) * a.getClip().duration
      s.backAt = 0
      s.mixer.update(0)
    },
    play(clip) {
      const s = stands[0]
      if (!s) return
      if (clip === 'blink') blinkOn(s)
      else playOn(s, clip)
    },
    turn(dYaw, dPitch) {
      yaw = (yaw + dYaw) % 360
      pitch = Math.min(G.pitchMaxDeg, Math.max(G.pitchMinDeg, pitch + dPitch))
      turntable.rotation.y = (yaw * Math.PI) / 180
    },
    zoom(k) {
      // ⤢ fits again to how it stands now
      if (k === 0) layout()
      zoomK = k === 0 ? 1 : Math.min(G.zoomMax, Math.max(G.zoomMin, zoomK * k))
    },
    variants: () => (stands[0] ? heldVariants(stands[0].asset) : []),
    stats() {
      const avg = frames.length ? frames.reduce((p, c) => p + c, 0) / frames.length : 16.7
      const s = stands[0]
      return { backend: v.backend, fps: 1000 / avg, dpr: dyn.dpr(), level: dyn.level(), look: shown?.look ?? 'puddlepup', kind: s?.asset.kind ?? null, triangles: s?.triangles ?? 0, clip: s?.current || null }
    },
    snapshot() {
      // drawn and read in one task (the drawing buffer is not kept between frames)
      aim()
      v.render()
      return v.readPixels()
    },
    inspect: () => ({ scene, camera, view: v }),
    dispose() {
      disposed = true
      cancelAnimationFrame(raf)
      clear()
      v.dispose()
    },
  }
}
