import {
  AdditiveBlending,
  AnimationMixer,
  Box3,
  BufferGeometry,
  CanvasTexture,
  CatmullRomCurve3,
  CircleGeometry,
  Color,
  CylinderGeometry,
  DoubleSide,
  Group,
  InstancedMesh,
  LoopOnce,
  LoopRepeat,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  Quaternion,
  RingGeometry,
  SRGBColorSpace,
  Scene,
  ShadowMaterial,
  TorusGeometry,
  Vector3,
} from 'three'
import type { AnimationAction, AnimationClip, Material, Texture } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js'
import type { BattleEvent, BattleState, FighterState, Side } from '../../core/battle/types.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { ART, BATTLE } from '../../data/tuning.ts'
import { buildStudio, filmMaterial, type Kind } from '../perf/content.ts'
import { createView, type Backend, type Level, type PerfView } from '../perf/view.ts'
import { memoryMb, noteTextures } from './memory.ts'

/**
 * docs/BATTLE_3D.md §6–§8: Battle 3D's picture. One film-look renderer (the Art 2.1 view: WebGPU where the phone has
 * it, WebGL otherwise, dynamic resolution), the Guild arena, two monsters with their clips, the wind-up telegraphs,
 * impact sparks, and the cameras (side-on, behind, cinematic cuts, the entrance fly-in). It only reads the engine's
 * state and events; the battle store steps the engine.
 *
 * Units: the engine's centi-units / 10,000 = metres (1 arena unit = 1 cm; the fence is at 6 m).
 */

const BASE = import.meta.env.BASE_URL
const TO_M = 1 / 10_000
const D = ART.duel

export type DuelCamera = 'side' | 'behind'

export interface DuelOptions {
  canvas: HTMLCanvasElement
  /** The player's side (the camera keeps it on the left / follows it). */
  me: Side
  /** Variant id per side (Songheart's palette), or null. */
  variants: [string | null, string | null]
  lite: boolean
  reduceMotion: boolean
  /** Prefer WebGPU (the test measured it faster); falls back to WebGL. */
  backend?: Backend
  /** Speed multiplier of the battle (×1/×2/×4) for the clips. */
  speed: () => number
}

export interface DuelStats {
  backend: Backend
  fps: number
  dpr: number
  level: Level
  gpuMs: number | null
  cpuMs: number
  arena: 'guild' | 'stand-in'
  monster: 'ultra' | 'art2'
  /** Estimated GPU memory (textures, geometry, render targets) and Chrome's JS heap, in MB. */
  gpuMb: number
  heapMb: number | null
}

export interface Duel3D {
  /** The entrance: fly-in, walk-on, face-off. Resolves when it ends or is skipped. */
  playIntro(): Promise<void>
  skipIntro(): void
  setCamera(mode: DuelCamera): void
  camera(): DuelCamera
  /** Raw engine events of the ticks just run (telegraphs, clips, sparks). */
  onEvents(events: readonly BattleEvent[]): void
  /** Where a fighter's chest is on screen, in CSS pixels (for floating numbers). */
  project(side: Side): { x: number; y: number } | null
  /**
   * The player's monster's forward (toward the opponent) and left directions as they look on screen, unit vectors in
   * CSS-pixel space (y down), so the stick means the same from any camera.
   */
  basisOnScreen(): { fwd: { x: number; y: number }; left: { x: number; y: number } }
  stats(): DuelStats
  dispose(): void
}

/* ---------------------------------------------------------------------------------------------- loading */

interface MonsterAsset {
  scene: Object3D
  clips: AnimationClip[]
  meta: { clips?: Record<string, { rootSpeed?: number; markers?: { name: string; t: number }[] }>; variants?: Record<string, { texture?: string }> } | null
  kind: 'ultra' | 'art2'
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url)
    return r.ok ? ((await r.json()) as T) : null
  } catch {
    return null
  }
}

async function exists(url: string): Promise<boolean> {
  try {
    const r = await fetch(url, { method: 'HEAD' })
    return r.ok
  } catch {
    return false
  }
}

function makeLoader(renderer: unknown): GLTFLoader {
  const loader = new GLTFLoader()
  loader.setMeshoptDecoder(MeshoptDecoder)
  const ktx2 = new KTX2Loader().setTranscoderPath(`${BASE}basis/`)
  ;(ktx2 as unknown as { detectSupport(r: unknown): void }).detectSupport(renderer)
  loader.setKTX2Loader(ktx2)
  return loader
}

async function loadMonster(loader: GLTFLoader, lite: boolean): Promise<MonsterAsset> {
  const ultra = !lite && (await exists(`${BASE}models/monsters-ultra/puddlepup.glb`))
  const dir = ultra ? 'models/monsters-ultra/' : 'models/monsters/'
  const gltf = await loader.loadAsync(`${BASE}${dir}puddlepup.glb`)
  const meta = await fetchJson<MonsterAsset['meta']>(`${BASE}${dir}puddlepup.json`)
  return { scene: gltf.scene, clips: gltf.animations, meta, kind: ultra ? 'ultra' : 'art2' }
}

/** What tools/blender/arenas writes beside the arena (guild.json): the parts the runtime uses. */
interface ArenaInfo {
  ringRadius?: number
  sun?: { direction: [number, number, number] }
  flyIn?: { eye: [number, number, number]; target: [number, number, number]; t: number; fovDeg: number }[]
  runtime?: { shadowCatcher?: { node: string } }
}

interface Arena {
  root: Object3D
  anchors: Map<string, Object3D>
  kind: 'guild' | 'stand-in'
  info: ArenaInfo | null
}

const GROUND_ATLAS = /ring|apron|mid|far/

/**
 * The Guild arena (docs/BATTLE_3D.md §8), or a simple ring if it can't load. Its materials are unlit with the light
 * baked in, so the fighters' shadows fall on its invisible shadow_catcher disc instead.
 */
async function loadArena(loader: GLTFLoader, lite: boolean): Promise<Arena> {
  const dir = `${BASE}models/arenas/guild/`
  const file = lite ? 'guild_lite.glb' : 'guild.glb'
  if (await exists(`${dir}${file}`)) {
    try {
      const [gltf, info] = await Promise.all([loader.loadAsync(`${dir}${file}`), fetchJson<ArenaInfo>(`${dir}guild.json`)])
      const anchors = new Map<string, Object3D>()
      const catcher = info?.runtime?.shadowCatcher?.node ?? 'shadow_catcher'
      gltf.scene.traverse((o) => {
        if (/^(ring_center|spawn_[AB]|gate_[AB](_start)?|cam_fly_\d+)$/.test(o.name)) anchors.set(o.name, o)
        const m = o as Mesh
        if (!m.isMesh) return
        if (m.name.startsWith(catcher)) {
          m.material = new ShadowMaterial({ opacity: D.shadowOpacity })
          m.receiveShadow = true
          m.visible = true
          return
        }
        const mat = m.material as MeshBasicMaterial
        if (mat?.map && GROUND_ATLAS.test(mat.name)) mat.map.anisotropy = D.groundAnisotropy
      })
      return { root: gltf.scene, anchors, kind: 'guild', info }
    } catch {
      /* fall through to the stand-in */
    }
  }
  return { root: standInArena(), anchors: new Map(), kind: 'stand-in', info: null }
}

function standInArena(): Group {
  const g = new Group()
  const floor = new Mesh(new CircleGeometry(7.5, 64), new MeshStandardMaterial({ color: '#b48a5a', roughness: 0.95 }))
  floor.rotation.x = -Math.PI / 2
  floor.receiveShadow = true
  g.add(floor)
  const ring = new Mesh(new RingGeometry(6.15, 7.4, 64), new MeshStandardMaterial({ color: '#8c6a44', roughness: 1 }))
  ring.rotation.x = -Math.PI / 2
  ring.position.y = 0.005
  g.add(ring)
  const post = new CylinderGeometry(0.07, 0.09, 1.0, 10)
  const wood = new MeshStandardMaterial({ color: '#6e4a2c', roughness: 0.85 })
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2
    const p = new Mesh(post, wood)
    p.position.set(Math.cos(a) * 6.3, 0.5, Math.sin(a) * 6.3)
    p.castShadow = true
    g.add(p)
  }
  const rope = new Mesh(new TorusGeometry(6.3, 0.025, 6, 96), new MeshStandardMaterial({ color: '#c9b48a', roughness: 0.9 }))
  rope.rotation.x = Math.PI / 2
  rope.position.y = 0.82
  g.add(rope)
  const grass = new Mesh(new CircleGeometry(40, 48), new MeshStandardMaterial({ color: '#7fae5e', roughness: 1 }))
  grass.rotation.x = -Math.PI / 2
  grass.position.y = -0.01
  g.add(grass)
  return g
}

/* ---------------------------------------------------------------------------------------------- actors */

const FALLBACK: Record<string, string[]> = {
  strafe_l: ['strafe_l', 'walk', 'step_fwd'],
  strafe_r: ['strafe_r', 'walk', 'step_fwd'],
  sidestep_l: ['sidestep_l', 'hop', 'dash'],
  sidestep_r: ['sidestep_r', 'hop', 'dash'],
  battle_idle: ['battle_idle', 'idle'],
}

interface Actor {
  side: Side
  root: Group
  model: Object3D
  mixer: AnimationMixer
  actions: Map<string, AnimationAction>
  current: string
  /** A one-shot holds until this time (seconds of mixer time); hits and KO cut in. */
  holdUntil: number
  oneShot: string | null
  /** Displayed position (smoothed) and yaw. */
  pos: Vector3
  yaw: number
  height: number
  rootSpeed: Record<string, number>
  impactAt: Record<string, number>
  /** When the next blink plays (the blink clip keys only the lids, so it layers over any clip). */
  nextBlink: number
  blinks: number
}

function makeActor(asset: MonsterAsset, side: Side, variant: string | null): Actor {
  const model = cloneSkinned(asset.scene)
  // fit to about 1 m tall at the head (the monsters' metres), standing on y = 0
  const box = new Box3().setFromObject(model)
  const h = Math.max(0.01, box.max.y - box.min.y)
  const scale = D.monsterHeightM / h
  model.scale.setScalar(scale)
  model.position.y = -box.min.y * scale
  const variantMap = new Map<string, Texture>()
  model.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh) return
    m.castShadow = true
    m.frustumCulled = false
    // Art 2.0 files carry each variant's texture on a hidden mesh named __variant_<id>
    const vm = /^__variant_(.+)$/.exec(m.name)
    if (vm) {
      const map = (m.material as MeshStandardMaterial).map
      if (map) variantMap.set(vm[1]!, map)
      m.visible = false
    }
  })
  const variantBase = variant ? (variantMap.get(variant) ?? null) : null
  if (asset.kind === 'ultra') {
    // Art 2.1: the film materials of the spike (ART_2_DETAIL §3.4), rebuilt from the file's own maps by part, so the
    // cards get their edge fade and the eyes their own gloss; glTF can't carry those
    model.traverse((o) => {
      const m = o as Mesh
      if (!m.isMesh || !m.visible) return
      const kind = filmKindOf(m.name)
      const mat = m.material as MeshStandardMaterial
      if (!kind || !mat?.map) return
      const orm = mat.roughnessMap ?? mat.aoMap ?? mat.map
      const base = variantBase && kind !== 'eye' ? variantBase : mat.map
      m.material = filmMaterial(kind, { base, normal: mat.normalMap ?? mat.map, orm, bytes: 0 })
      // a variant's cards and tufts take their colour from the second vertex-colour set (the model's notes)
      if (variantBase && (kind === 'card' || kind === 'lock') && m.geometry.getAttribute('color_1')) m.geometry = withColourSet(m.geometry, 'color_1')
    })
  } else if (variantBase) {
    model.traverse((o) => {
      const m = o as Mesh
      if (!m.isMesh || !m.visible) return
      const mat = m.material as MeshStandardMaterial
      if (mat?.map && !/eye|face/i.test(m.name)) {
        const c = mat.clone()
        c.map = variantBase
        m.material = c
      }
    })
  }
  const root = new Group()
  root.add(model)
  const mixer = new AnimationMixer(model)
  const actions = new Map<string, AnimationAction>()
  for (const clip of asset.clips) actions.set(clip.name, mixer.clipAction(clip))
  const rootSpeed: Record<string, number> = {}
  const impactAt: Record<string, number> = {}
  for (const [name, c] of Object.entries(asset.meta?.clips ?? {})) {
    // the file's root speeds are in the model's metres: scale them like the model
    rootSpeed[name] = (c.rootSpeed ?? 0) * scale
    const imp = c.markers?.find((m) => m.name === 'impact' || m.name === 'release')
    if (imp) impactAt[name] = imp.t
  }
  const a: Actor = { side, root, model, mixer, actions, current: '', holdUntil: 0, oneShot: null, pos: new Vector3(), yaw: 0, height: D.monsterHeightM, rootSpeed, impactAt, nextBlink: 1.2 + side * 0.9, blinks: side * 2 }
  play(a, 'battle_idle', { loop: true })
  return a
}

/** A geometry sharing every buffer with `src`, but reading its vertex colours from another set. */
function withColourSet(src: BufferGeometry, set: string): BufferGeometry {
  const g = new BufferGeometry()
  for (const [k, a] of Object.entries(src.attributes)) g.setAttribute(k, a)
  g.setAttribute('color', src.getAttribute(set))
  g.setIndex(src.index)
  for (const gr of src.groups) g.addGroup(gr.start, gr.count, gr.materialIndex)
  g.boundingBox = src.boundingBox
  g.boundingSphere = src.boundingSphere
  return g
}

/** The film material kind of an Ultra model's part, by its mesh name (tools/blender: lo_body, lo_cards, …). */
function filmKindOf(name: string): Kind | null {
  if (/^lo_card/.test(name)) return 'card'
  if (/^lo_tuft|^lo_lock/.test(name)) return 'lock'
  if (/^lo_eye/.test(name)) return 'eye'
  if (/^lo_fin/.test(name)) return 'fin'
  if (/^lo_(body|paw)/.test(name)) return 'body'
  return null
}

function resolveClip(a: Actor, name: string): string | null {
  for (const n of FALLBACK[name] ?? [name]) if (a.actions.has(n)) return n
  return a.actions.has(name) ? name : null
}

function play(a: Actor, name: string, o: { loop: boolean; rate?: number; fade?: number; hold?: boolean }): void {
  const clip = resolveClip(a, name)
  if (!clip) return
  const next = a.actions.get(clip)!
  if (a.current === clip && o.loop) {
    next.timeScale = o.rate ?? 1
    return
  }
  const prev = a.actions.get(a.current)
  next.reset()
  next.setLoop(o.loop ? LoopRepeat : LoopOnce, o.loop ? Infinity : 1)
  next.clampWhenFinished = !o.loop
  next.timeScale = o.rate ?? 1
  next.enabled = true
  next.setEffectiveWeight(1)
  next.play()
  if (prev && prev !== next) prev.crossFadeTo(next, o.fade ?? 0.15, false)
  a.current = clip
  a.oneShot = o.loop ? null : clip
  a.holdUntil = o.loop ? 0 : a.mixer.time + next.getClip().duration / Math.max(0.05, Math.abs(next.timeScale)) - (o.hold ? 0 : 0.05)
}

/* ---------------------------------------------------------------------------------------------- effects */

interface Telegraph {
  mesh: Mesh
  born: number
  landAt: number
}

/** A round, soft-edged glow for the sparks (a flat square reads as a pixel, not a spark). */
function softDot(): CanvasTexture {
  const c = document.createElement('canvas')
  c.width = c.height = 32
  const g = c.getContext('2d')!
  const r = g.createRadialGradient(16, 16, 0, 16, 16, 16)
  r.addColorStop(0, 'rgba(255,255,255,1)')
  r.addColorStop(0.3, 'rgba(255,236,190,0.75)')
  r.addColorStop(1, 'rgba(255,200,120,0)')
  g.fillStyle = r
  g.fillRect(0, 0, 32, 32)
  const t = new CanvasTexture(c)
  t.colorSpace = SRGBColorSpace
  return t
}

class Sparks {
  readonly mesh: InstancedMesh
  private live: { at: Vector3; v: Vector3; born: number }[] = []
  private readonly m = new Matrix4()
  private readonly q = new Quaternion()
  private readonly s = new Vector3()
  private readonly max: number
  constructor(scene: Scene, max = 160) {
    this.max = max
    const mat = new MeshBasicMaterial({ color: '#ffd89a', map: softDot(), transparent: true, blending: AdditiveBlending, depthWrite: false, side: DoubleSide })
    this.mesh = new InstancedMesh(new PlaneGeometry(0.07, 0.07), mat, max)
    this.mesh.frustumCulled = false
    this.mesh.count = 0
    scene.add(this.mesh)
  }
  burst(at: Vector3, n: number, now: number, seed: number): void {
    for (let i = 0; i < n; i++) {
      // a fixed spread per index (no randomness: the picture repeats exactly with the battle)
      const a = (i * 2.399963 + seed) % (Math.PI * 2)
      const up = 0.6 + ((i * 7919) % 97) / 97
      this.live.push({ at: at.clone(), v: new Vector3(Math.cos(a) * 1.4, up * 1.6, Math.sin(a) * 1.4), born: now })
    }
    if (this.live.length > this.max) this.live.splice(0, this.live.length - this.max)
  }
  update(now: number, camera: PerspectiveCamera): void {
    this.live = this.live.filter((p) => now - p.born < 0.45)
    this.q.copy(camera.quaternion)
    this.live.forEach((p, i) => {
      const t = now - p.born
      const pos = p.at.clone().addScaledVector(p.v, t).add(new Vector3(0, -2.2 * t * t, 0))
      const k = 1 - t / 0.45
      this.s.setScalar(0.6 + 1.6 * k)
      this.m.compose(pos, this.q, this.s)
      this.mesh.setMatrixAt(i, this.m)
    })
    this.mesh.count = this.live.length
    this.mesh.instanceMatrix.needsUpdate = true
  }
}

/* ---------------------------------------------------------------------------------------------- the stage */

/** Engine (x, y) → three (x, 0, −y): mirrored so the engine's "left" (+side) is the monster's own left on screen. */
function worldOf(f: FighterState): Vector3 {
  return new Vector3(f.x * TO_M, 0, -f.y * TO_M)
}

export async function createDuel3D(o: DuelOptions, getState: () => BattleState | null): Promise<Duel3D> {
  const canvas = o.canvas
  const w = () => Math.max(1, canvas.clientWidth)
  const h = () => Math.max(1, canvas.clientHeight)
  const dprMax = Math.max(1, Math.min(o.lite ? 1.5 : ART.ultra.scaling.dprMax, devicePixelRatio || 1))
  let dpr = Math.min(o.lite ? 1.25 : D.dprStart, dprMax)
  const wantGpu = (o.backend ?? 'webgpu') === 'webgpu' && !o.lite && 'gpu' in navigator
  let view: PerfView | undefined = wantGpu ? await createView('webgpu', { canvas, width: w(), height: h(), dpr, cinematic: false, focus: 3 }).catch(() => undefined) : undefined
  if (!view) view = await createView('webgl', { canvas, width: w(), height: h(), dpr, cinematic: false, focus: 3 })
  const v = view!
  const scene = new Scene()
  const camera = new PerspectiveCamera(D.fov, w() / h(), 0.05, D.far)
  const loader = makeLoader(v.renderer)
  const [arena, asset] = await Promise.all([loadArena(loader, o.lite), loadMonster(loader, o.lite)])
  const textures = new Set<Texture>()
  noteTextures(arena.root, textures)
  noteTextures(asset.scene, textures)
  scene.add(arena.root)
  const studio = buildStudio(scene, v.environment, new Vector3(0, 0.5, 0), 8)
  // outdoors: a soft sky instead of the studio's grey (the Guild arena brings its own sky domes)
  scene.background = new Color(D.sky)
  studio.ground.visible = arena.kind === 'stand-in'
  const sun = arena.info?.sun?.direction
  if (sun) studio.key.position.set(sun[0], sun[1], sun[2]).normalize().multiplyScalar(32).add(studio.key.target.position)
  // every camera stays inside the fence (ART.duel.confine): the crowd stands start just past it
  const wallR = arena.info?.ringRadius ? arena.info.ringRadius - D.confine.wallMargin : Infinity
  const actors: [Actor, Actor] = [makeActor(asset, 0, o.variants[0]), makeActor(asset, 1, o.variants[1])]
  for (const a of actors) scene.add(a.root)
  const sparks = new Sparks(scene)
  const telegraphs: Telegraph[] = []
  await v.init(scene, camera)
  // compile the materials' shaders now, so the entrance's first frames don't stall on it (where the renderer can)
  try {
    await (v.renderer as { compileAsync?: (s: Scene, c: PerspectiveCamera) => Promise<unknown> }).compileAsync?.(scene, camera)
  } catch {
    /* compiled on first use instead */
  }
  if (o.lite) v.setLevel('no-msaa')

  let camMode: DuelCamera = 'side'
  let cine: { until: number; from: Vector3; look: Vector3 } | null = null
  const camPos = new Vector3(0, 3, 9)
  const camLook = new Vector3(0, 0.6, 0)
  let camFov: number = D.fov
  // the side-on camera's fitting camera (reused every frame)
  const fitCam = new PerspectiveCamera(D.fov, 1, 0.05, D.far)
  /** The entrance's own clock (`t`, seconds): it follows real time, so a slow first frame can't stretch it. */
  let intro: { t: number; resolve: () => void; skip: boolean } | null = null
  let now = 0
  let last = performance.now()
  let raf = 0
  let disposed = false
  // the side the side-on camera sits on, fixed at the start so it never flips as they circle
  let sideSign = 1
  const frameTimes: number[] = []
  let cpuMs = 0
  let missSecond = 0
  let framesSecond = 0
  let secondStart = performance.now()
  let calmSince = performance.now()
  let levelIndex = o.lite ? ART.ultra.levels.indexOf('no-msaa') : 0

  const fighterAt = (s: BattleState, side: Side) => worldOf(s.fighters[side])

  function chooseSideSign(s: BattleState): void {
    const a = fighterAt(s, o.me)
    const b = fighterAt(s, (1 - o.me) as Side)
    const u = b.clone().sub(a).normalize()
    const n = new Vector3(-u.z, 0, u.x)
    // the camera at mid + n·d looks along −n; screen-right is (−n) × up; the player's monster must be on the left
    const right = n.clone().negate().cross(new Vector3(0, 1, 0))
    sideSign = a.clone().sub(a.clone().add(b).multiplyScalar(0.5)).dot(right) < 0 ? 1 : -1
  }

  function targetCamera(s: BattleState): { pos: Vector3; look: Vector3; fov: number } {
    const a = actors[o.me].pos
    const b = actors[1 - o.me]!.pos
    const mid = a.clone().add(b).multiplyScalar(0.5)
    const u = b.clone().sub(a)
    const dist = Math.max(0.01, u.length())
    u.divideScalar(dist)
    if (camMode === 'behind') {
      const lat = new Vector3(-u.z, 0, u.x).multiplyScalar(D.behind.side)
      return {
        pos: insideFence(a.clone().addScaledVector(u, -D.behind.back).add(lat).add(new Vector3(0, D.behind.height, 0))),
        look: b.clone().add(new Vector3(0, D.behind.lookY, 0)),
        fov: D.fov,
      }
    }
    // Side-on, made for a tall phone: turned toward the player's monster and looking down a little, so the line between
    // them runs diagonally up the screen (the player near, bottom left); the distance is fitted every frame so both
    // monsters sit in the clear band between the top bar and the technique panel.
    void s
    const F = D.side
    const n = new Vector3(-u.z, 0, u.x).multiplyScalar(sideSign)
    const yaw = (F.yawDeg * Math.PI) / 180
    const flat = n.clone().multiplyScalar(Math.cos(yaw)).addScaledVector(u, -Math.sin(yaw)).normalize()
    const band = F.band
    const centreY = (band.top + band.bottom) / 2
    const tMax = Math.tan(((D.confine.maxFov / 2) * Math.PI) / 180)
    // both monsters whole: feet and heads, front and back
    const up = new Vector3(0, D.monsterHeightM, 0)
    const pts = [a, b].flatMap((p) => [-1, 1].flatMap((k) => [p.clone().addScaledVector(u, k * F.bodyHalfM), p.clone().addScaledVector(u, k * F.bodyHalfM).add(up)]))
    const dir = new Vector3()
    let t = 0
    let d = 0
    let look = mid.clone()
    fitCam.aspect = camera.aspect
    // how much bigger the view must be for every point to sit in the band, from distance d and lens t
    const need = (): number => {
      // aim below the middle so the pair sits in the band's centre rather than the screen's
      look = mid.clone().add(new Vector3(0, F.lookY - d * t * centreY, 0))
      fitCam.fov = (2 * Math.atan(t) * 180) / Math.PI
      fitCam.updateProjectionMatrix()
      fitCam.position.copy(look).addScaledVector(dir, d)
      fitCam.lookAt(look)
      fitCam.updateMatrixWorld()
      let m = 0
      for (const p of pts) {
        const q = p.clone().project(fitCam)
        m = Math.max(m, Math.abs(q.x) / band.x, q.y > centreY ? (q.y - centreY) / (band.top - centreY) : (centreY - q.y) / (centreY - band.bottom))
      }
      return Math.min(1.6, Math.max(0.6, m))
    }
    for (let el = F.elevationDeg; ; el += D.confine.raiseDeg) {
      const e = (el * Math.PI) / 180
      dir.copy(flat).multiplyScalar(Math.cos(e)).add(new Vector3(0, Math.sin(e), 0)).normalize()
      t = Math.tan(((D.fov / 2) * Math.PI) / 180)
      d = F.base + dist * F.perGap
      for (let i = 0; i < 4; i++) d = Math.min(F.maxDist, Math.max(F.minDist, d * need()))
      const reach = reachInside(mid, dir)
      if (d <= reach) break
      // the crowd is behind: stay inside the fence and widen the lens; if that can't fit them, rise and try again
      t *= d / reach
      d = reach
      for (let i = 0; i < 3; i++) t = Math.min(tMax, t * need())
      if (need() <= 1.02 || el >= F.elevationDeg + D.confine.maxRaiseDeg) break
    }
    need()
    return { pos: look.clone().addScaledVector(dir, d), look, fov: (2 * Math.atan(t) * 180) / Math.PI }
  }

  /** How far the camera can back away from `from` along `dir` before it leaves the fence (horizontally), in metres. */
  function reachInside(from: Vector3, dir: Vector3): number {
    if (!Number.isFinite(wallR)) return Infinity
    const a = dir.x * dir.x + dir.z * dir.z
    const b = from.x * dir.x + from.z * dir.z
    const c = from.x * from.x + from.z * from.z - wallR * wallR
    const disc = b * b - a * c
    if (a < 1e-6 || disc < 0) return Infinity
    return Math.max(0.6, (-b + Math.sqrt(disc)) / a)
  }

  /** A camera position pulled back inside the fence (horizontally), for the behind and cinematic cameras. */
  function insideFence(p: Vector3): Vector3 {
    const r = Math.hypot(p.x, p.z)
    if (r > wallR) {
      p.x *= wallR / r
      p.z *= wallR / r
    }
    return p
  }

  function startCine(attacker: Actor, now: number): void {
    if (!D.cine.enabled) return
    const opp = actors[1 - attacker.side]!
    const u = opp.pos.clone().sub(attacker.pos).normalize()
    const n = new Vector3(-u.z, 0, u.x)
    const from = insideFence(attacker.pos.clone().addScaledVector(u, D.cine.ahead).addScaledVector(n, D.cine.side * sideSign).add(new Vector3(0, D.cine.height, 0)))
    cine = { until: now + (o.reduceMotion ? D.cine.seconds * 0.7 : D.cine.seconds), from, look: attacker.pos.clone().add(new Vector3(0, 0.55, 0)) }
  }

  function updateActors(s: BattleState, dt: number): void {
    for (const a of actors) {
      const f = s.fighters[a.side]
      const opp = s.fighters[(1 - a.side) as Side]
      const target = worldOf(f)
      const prev = a.pos.clone()
      // smooth between 30 Hz ticks
      a.pos.lerp(target, 1 - Math.exp(-dt * 22))
      const face = worldOf(opp).sub(a.pos)
      a.yaw = Math.atan2(face.x, face.z)
      a.root.position.copy(a.pos)
      a.root.rotation.y = a.yaw
      // the clip
      const vel = a.pos.clone().sub(prev).divideScalar(Math.max(1e-3, dt))
      const fwd = new Vector3(Math.sin(a.yaw), 0, Math.cos(a.yaw))
      const left = new Vector3(fwd.z, 0, -fwd.x)
      const vf = vel.dot(fwd)
      const vl = vel.dot(left)
      const speed = Math.hypot(vf, vl)
      const busyOneShot = a.oneShot !== null && a.mixer.time < a.holdUntil
      if (f.hp <= 0) {
        if (a.current !== resolveClip(a, 'ko')) play(a, 'ko', { loop: false, hold: true })
      } else if (s.outcome && s.outcome.winner === a.side) {
        if (a.current !== resolveClip(a, 'win')) play(a, 'win', { loop: true })
      } else if (f.sidestepTicks > 0) {
        const name = f.sidestepDir > 0 ? 'sidestep_l' : 'sidestep_r'
        if (a.current !== resolveClip(a, name)) play(a, name, { loop: false, rate: o.speed() })
      } else if (!busyOneShot) {
        if (f.dashTicks > 0) play(a, 'dash', { loop: true, rate: o.speed() })
        else if (speed > 0.08) {
          const strafing = Math.abs(vl) > Math.abs(vf)
          const name = strafing ? (vl > 0 ? 'strafe_l' : 'strafe_r') : vf >= 0 ? 'step_fwd' : 'step_back'
          const rs = a.rootSpeed[resolveClip(a, name) ?? ''] ?? 0
          const rate = rs > 0 ? Math.min(2.4, Math.max(0.5, speed / rs)) : 1
          play(a, name, { loop: true, rate })
        } else play(a, 'battle_idle', { loop: true })
      }
      blink(a, f.hp > 0)
      a.mixer.update(dt)
    }
  }

  function blink(a: Actor, awake: boolean): void {
    const clip = a.actions.get('blink')
    if (!clip || !awake || now < a.nextBlink) return
    clip.reset()
    clip.setLoop(LoopOnce, 1)
    clip.clampWhenFinished = false
    clip.play()
    a.nextBlink = now + D.blinkGaps[a.blinks++ % D.blinkGaps.length]!
  }

  function onEvents(events: readonly BattleEvent[]): void {
    const s = getState()
    if (!s) return
    for (const e of events) {
      if (e.kind === 'fire') {
        const a = actors[e.side]
        const tech = TECHNIQUE_BY_ID[e.tech]
        const ranged = tech ? tech.type === 'INT' || tech.range >= 3 : false
        const clip = ranged ? 'cast' : 'strike'
        // time the clip so its impact lands with the engine's landing tick
        const windupSec = (((e.lands ?? e.t) - e.t) / BATTLE.ticksPerSecond) / Math.max(1, o.speed())
        const imp = a.impactAt[resolveClip(a, clip) ?? ''] ?? 0.4
        const rate = windupSec > 0.01 ? Math.min(2.6, Math.max(0.7, imp / windupSec)) : o.speed()
        play(a, clip, { loop: false, rate })
        if (e.lands !== undefined && e.path) addTelegraph(s, e.side, e.path, tech?.type === 'INT', e.lands)
        if (tech && (tech.family === 'Special' || tech.family === 'Signature')) startCine(a, now)
      } else if (e.kind === 'hit') {
        const t = actors[e.target]
        const heavy = e.crit || e.damage * 8 >= s.fighters[e.target].maxHp
        if (s.fighters[e.target].hp > 0) play(t, heavy ? 'hit_heavy' : 'hit', { loop: false, rate: o.speed() })
        sparks.burst(t.pos.clone().add(new Vector3(0, t.height * 0.55, 0)), heavy ? 28 : 16, now, e.t % 7)
      } else if (e.kind === 'ko') {
        startCine(actors[(1 - e.side) as Side], now)
      }
    }
  }

  function addTelegraph(s: BattleState, side: Side, path: 'line' | 'sweep', int: boolean, lands: number): void {
    const a = fighterAt(s, side)
    const b = fighterAt(s, (1 - side) as Side)
    const color = int ? D.telegraph.int : D.telegraph.pow
    const mat = new MeshBasicMaterial({ color, transparent: true, opacity: 0, depthWrite: false })
    let mesh: Mesh
    if (path === 'line') {
      const len = Math.max(0.2, a.distanceTo(b))
      mesh = new Mesh(new PlaneGeometry((BATTLE.duel.pathHalfWidth * 2) / 100, len), mat)
      mesh.rotation.x = -Math.PI / 2
      const mid = a.clone().add(b).multiplyScalar(0.5)
      mesh.position.set(mid.x, 0.02, mid.z)
      mesh.rotation.z = -Math.atan2(b.x - a.x, b.z - a.z)
    } else {
      mesh = new Mesh(new RingGeometry(0.45, 1.7, 48), mat)
      mesh.rotation.x = -Math.PI / 2
      mesh.position.set(b.x, 0.02, b.z)
    }
    scene.add(mesh)
    telegraphs.push({ mesh, born: now, landAt: now + (lands - s.tick) / BATTLE.ticksPerSecond / Math.max(1, o.speed()) })
  }

  function updateTelegraphs(): void {
    for (let i = telegraphs.length - 1; i >= 0; i--) {
      const t = telegraphs[i]!
      const mat = t.mesh.material as MeshBasicMaterial
      const k = (now - t.born) / Math.max(0.05, t.landAt - t.born)
      mat.opacity = k < 1 ? D.telegraph.opacity * Math.min(1, k * 1.5) : Math.max(0, D.telegraph.opacity * (1 - (now - t.landAt) / 0.2))
      if (k >= 1 && now - t.landAt > 0.2) {
        scene.remove(t.mesh)
        t.mesh.geometry.dispose()
        mat.dispose()
        telegraphs.splice(i, 1)
      }
    }
  }

  function setFov(f: number): void {
    if (Math.abs(camera.fov - f) < 0.01) return
    camera.fov = f
    camera.updateProjectionMatrix()
  }

  let flyCache: { eyes: CatmullRomCurve3; targets: CatmullRomCurve3; times: number[]; fovs: number[] } | null = null
  /**
   * The entrance camera path: the arena's (guild.json flyIn, times scaled to flySeconds), or a default arc. Its last
   * stop is always the face-off, framed like the behind camera from where the monsters really stand, so a tall phone
   * sees both.
   */
  function flyPath(s: BattleState): NonNullable<typeof flyCache> {
    if (flyCache) return flyCache
    type Key = { eye: readonly number[]; target: readonly number[]; t: number; fovDeg: number }
    const keys: Key[] = arena.info?.flyIn && arena.info.flyIn.length >= 3
      ? arena.info.flyIn.slice(0, -1)
      : [
          { eye: [-14, 9, 16], target: [0, 0.6, 0], t: 0, fovDeg: D.fov },
          { eye: [-6, 4.5, 9], target: [0, 0.6, 0], t: 1, fovDeg: D.fov },
        ]
    const me = fighterAt(s, o.me)
    const them = fighterAt(s, (1 - o.me) as Side)
    const u = them.clone().sub(me).normalize()
    const eye = me.clone().addScaledVector(u, -D.behind.back).add(new Vector3(-u.z, 0, u.x).multiplyScalar(D.behind.side)).add(new Vector3(0, D.behind.height, 0))
    const lastT = arena.info?.flyIn?.[arena.info.flyIn.length - 1]?.t ?? keys[keys.length - 1]!.t + 1
    keys.push({ eye: eye.toArray(), target: them.clone().add(new Vector3(0, D.behind.lookY, 0)).toArray(), t: lastT, fovDeg: D.fov })
    const v3 = (p: readonly number[]) => new Vector3(p[0], p[1], p[2])
    flyCache = {
      eyes: new CatmullRomCurve3(keys.map((k) => v3(k.eye)), false, 'centripetal'),
      targets: new CatmullRomCurve3(keys.map((k) => v3(k.target)), false, 'centripetal'),
      times: keys.map((k) => (k.t / (lastT || 1)) * D.intro.flySeconds),
      fovs: keys.map((k) => k.fovDeg),
    }
    return flyCache
  }

  /** A monster's way in: outside its gate, the gate, its start mark (or a short walk if the arena has no gates). */
  function walkPath(side: Side, end: Vector3): Vector3[] {
    const at = (n: string) => arena.anchors.get(n)?.getWorldPosition(new Vector3())
    const tag = side === 0 ? 'A' : 'B'
    const gate = at(`gate_${tag}`)
    const outside = at(`gate_${tag}_start`)
    if (gate) return outside ? [outside, gate, end] : [gate, end]
    return [new Vector3(end.x * 2.4, 0, end.z + (side === 0 ? 1.5 : -1.5)), end]
  }

  function updateIntro(s: BattleState, realDt: number): boolean {
    if (!intro) return false
    const step = Math.min(0.25, realDt)
    intro.t += step
    const t = intro.t
    const T = D.intro
    if (intro.skip || t >= T.seconds) {
      intro.resolve()
      intro = null
      return false
    }
    // the fly-in: along the arena's timed camera path, then held over the player's shoulder for the face-off
    const fly = flyPath(s)
    const ft = Math.min(t, T.flySeconds)
    let i = 0
    while (i < fly.times.length - 2 && ft > fly.times[i + 1]!) i++
    const span = Math.max(1e-3, fly.times[i + 1]! - fly.times[i]!)
    const f = Math.min(1, Math.max(0, (ft - fly.times[i]!) / span))
    const u = (i + f) / (fly.times.length - 1)
    camera.position.copy(fly.eyes.getPoint(u))
    camLook.copy(fly.targets.getPoint(u))
    camera.lookAt(camLook)
    camFov = fly.fovs[i]! + (fly.fovs[i + 1]! - fly.fovs[i]!) * f
    setFov(camFov)
    // the walk-on: from outside the gates, through them, to the start marks; then they face each other
    const raw = Math.max(0, Math.min(1, (t - T.walkFrom) / T.walkSeconds))
    const walk = raw * raw * (3 - 2 * raw)
    for (const a of actors) {
      const end = fighterAt(s, a.side)
      const path = walkPath(a.side, end)
      const len = path.reduce((n, p, j) => (j ? n + p.distanceTo(path[j - 1]!) : 0), 0)
      let left = walk * len
      let j = 1
      while (j < path.length - 1 && left > path[j]!.distanceTo(path[j - 1]!)) left -= path[j]!.distanceTo(path[j - 1]!), j++
      const seg = path[j]!.clone().sub(path[j - 1]!)
      a.pos.copy(path[j - 1]!).addScaledVector(seg.clone().normalize(), Math.min(left, seg.length()))
      a.root.position.copy(a.pos)
      const toward = raw < 1 ? seg : fighterAt(s, (1 - a.side) as Side).sub(end)
      a.root.rotation.y = Math.atan2(toward.x, toward.z)
      const speed = len / T.walkSeconds
      const rate = a.rootSpeed.walk ? Math.min(2, Math.max(0.6, speed / a.rootSpeed.walk)) : 1
      play(a, raw > 0 && raw < 1 ? 'walk' : 'battle_idle', { loop: true, rate: raw > 0 && raw < 1 ? rate : 1 })
      blink(a, true)
      a.mixer.update(step)
    }
    camPos.copy(camera.position)
    return true
  }

  function scale(frameMs: number): void {
    // dynamic resolution (ART_2_DETAIL §3.6): resolution first, then effects; the monsters never change
    const S = ART.ultra.scaling
    const budget = 1000 / S.targetFps
    framesSecond++
    if (frameMs > budget * S.missFactor) missSecond++
    const t = performance.now()
    if (t - secondStart < 1000) return
    const miss = missSecond / Math.max(1, framesSecond)
    secondStart = t
    missSecond = 0
    framesSecond = 0
    if (miss > S.missShareDown) {
      // most frames late (a slower phone at the start): take bigger steps so it recovers in a second or two
      const step = miss > D.fastDrop.missShare ? S.dprStepDown * D.fastDrop.stepMul : S.dprStepDown
      if (dpr - S.dprStepDown >= S.dprMin - 1e-6) {
        dpr = Math.max(S.dprMin, Math.round((dpr - step) * 100) / 100)
        v.setSize(w(), h(), dpr)
      } else if (levelIndex < ART.ultra.levels.length - 1) v.setLevel(ART.ultra.levels[++levelIndex]!)
      calmSince = t
    } else if (miss <= S.calmMissShare && t - calmSince > S.calmMsUp) {
      if (levelIndex > (o.lite ? ART.ultra.levels.indexOf('no-msaa') : 0)) v.setLevel(ART.ultra.levels[--levelIndex]!)
      else if (dpr + S.dprStepUp <= dprMax + 1e-6) {
        dpr = Math.round((dpr + S.dprStepUp) * 100) / 100
        v.setSize(w(), h(), dpr)
      }
      calmSince = t
    }
  }

  let lastW = w()
  let lastH = h()
  function loop(): void {
    if (disposed) return
    raf = requestAnimationFrame(loop)
    const tNow = performance.now()
    const frameMs = tNow - last
    last = tNow
    const dt = Math.min(0.1, frameMs / 1000)
    now += dt
    frameTimes.push(frameMs)
    if (frameTimes.length > 120) frameTimes.shift()
    if (w() !== lastW || h() !== lastH) {
      lastW = w()
      lastH = h()
      camera.aspect = lastW / lastH
      camera.updateProjectionMatrix()
      v.setSize(lastW, lastH, dpr)
    }
    const c0 = performance.now()
    const s = getState()
    if (s) {
      if (!updateIntro(s, frameMs / 1000)) {
        updateActors(s, dt)
        const goal = targetCamera(s)
        if (cine && now < cine.until) {
          const k = o.reduceMotion ? 1 - Math.exp(-dt * 4) : 1
          camPos.lerp(cine.from, k)
          camLook.lerp(cine.look, k)
          camFov += (D.fov - camFov) * k
        } else {
          cine = null
          const k = 1 - Math.exp(-dt * (o.reduceMotion ? D.springReduced : D.spring))
          camPos.lerp(goal.pos, k)
          camLook.lerp(goal.look, k)
          camFov += (goal.fov - camFov) * k
        }
        camera.position.copy(camPos)
        camera.lookAt(camLook)
        setFov(camFov)
      }
    }
    updateTelegraphs()
    sparks.update(now, camera)
    v.render()
    cpuMs = performance.now() - c0
    scale(frameMs)
  }

  const s0 = getState()
  if (s0) {
    chooseSideSign(s0)
    for (const a of actors) a.pos.copy(fighterAt(s0, a.side))
    const goal = targetCamera(s0)
    camPos.copy(goal.pos)
    camLook.copy(goal.look)
    camFov = goal.fov
    setFov(camFov)
  }
  raf = requestAnimationFrame(loop)

  return {
    playIntro() {
      return new Promise<void>((resolve) => {
        intro = { t: 0, resolve, skip: false }
      })
    },
    skipIntro() {
      if (intro) intro.skip = true
    },
    setCamera(mode) {
      camMode = mode
      cine = null
    },
    camera: () => camMode,
    onEvents,
    project(side) {
      const a = actors[side]
      const p = a.pos.clone().add(new Vector3(0, a.height * 0.9, 0)).project(camera)
      if (p.z > 1) return null
      return { x: ((p.x + 1) / 2) * w(), y: ((1 - p.y) / 2) * h() }
    },
    basisOnScreen() {
      const me = actors[o.me].pos
      const u = actors[1 - o.me]!.pos.clone().sub(me).setY(0).normalize()
      const left = new Vector3(u.z, 0, -u.x)
      const lift = new Vector3(0, 0.4, 0)
      const p0 = me.clone().add(lift).project(camera)
      const toScreen = (d: Vector3) => {
        const p = me.clone().add(lift).add(d).project(camera)
        const x = (p.x - p0.x) * w()
        const y = -(p.y - p0.y) * h()
        const len = Math.hypot(x, y) || 1
        return { x: x / len, y: y / len }
      }
      return { fwd: toScreen(u), left: toScreen(left) }
    },
    stats() {
      const avg = frameTimes.length ? frameTimes.reduce((p, c) => p + c, 0) / frameTimes.length : 16.7
      const mem = memoryMb(textures, scene, v.targetBytes())
      return { backend: v.backend, fps: 1000 / avg, dpr, level: ART.ultra.levels[levelIndex]!, gpuMs: v.gpuMs(), cpuMs, arena: arena.kind, monster: asset.kind, gpuMb: mem.gpu, heapMb: mem.heap }
    },
    dispose() {
      disposed = true
      cancelAnimationFrame(raf)
      for (const t of telegraphs) {
        t.mesh.geometry.dispose()
        ;(t.mesh.material as Material).dispose()
      }
      v.dispose()
    },
  }
}

