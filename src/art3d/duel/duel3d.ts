import {
  AnimationMixer,
  CanvasTexture,
  CatmullRomCurve3,
  CircleGeometry,
  Color,
  CylinderGeometry,
  Group,
  LoopOnce,
  LoopRepeat,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  RingGeometry,
  SRGBColorSpace,
  Scene,
  ShadowMaterial,
  TorusGeometry,
  Vector3,
} from 'three'
import type { AnimationAction, Texture } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import type { BattleEvent, BattleState, FighterState, Side } from '../../core/battle/types.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { ART, BATTLE } from '../../data/tuning.ts'
import type { UltraId } from '../../art/ultraLooks.ts'
import { aimStudioRims, buildStudio, setFilmClock } from '../perf/content.ts'
import { createDynRes } from '../perf/dynres.ts'
import { createView, type Backend, type Level, type PerfView } from '../perf/view.ts'
import { resolveClipName } from '../ultra/clips.ts'
import { blinkClipOf, flyTimesOf, NO_AO_LAYER, loadUltraAsset, makeUltraModel, wingspanOf, type UltraAsset, type UltraKind, type UltraSize } from '../ultra/ultraAsset.ts'
import { flightPlan, flyKindOf, framedLift, hopPlan, landNow, liftAt, mouthShare, shadowAt, withPeak, type FlightPlan, type FlyTimes } from '../ultra/flight.ts'
import { duelFighters, duelLoads } from './fighters.ts'
import { lungeFor, lungeReach, type Lunge } from './attacks.ts'
import { AttackFx } from './attackFx.ts'
import { Telegraphs } from './telegraph.ts'
import { cineShot, flyShotInside } from './cineShot.ts'
import { isRangedTech } from './fxRecipe.ts'
import { duelPaced, duelWindup } from '../../core/battle/pace.ts'
import { pathOf } from '../../data/paths.ts'
import { bandNeed, sideFraming } from './framing.ts'
import { memoryMb, noteTextures } from './memory.ts'
import { createCrowd, type Crowd, type CrowdStats } from './crowd.ts'

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
const AT = ART.duel.attack
const FL = ART.duel.flight

export type DuelCamera = 'side' | 'behind'

/** The arenas (docs/BATTLE_3D.md §8): the Breeders' Guild arena and the Crown Amphitheatre for the big fights. */
export type ArenaId = 'guild' | 'crown'

export interface DuelOptions {
  canvas: HTMLCanvasElement
  /** Which arena (the Guild by default). */
  arena?: ArenaId
  /** The player's side (the camera keeps it on the left / follows it). */
  me: Side
  /** Each side's look (an Ultra registry look, src/art/ultraLooks.ts: a breed or a grown form; Puddlepup by default and for any other). */
  looks?: [UltraId, UltraId]
  /** Variant id per side (Songheart's palette), or null; a variant the breed's file doesn't hold shows its usual look. */
  variants: [string | null, string | null]
  lite: boolean
  reduceMotion: boolean
  /** Left-handed: sideways, the cards sit on the left, so the side camera frames the fight to their right. */
  leftHanded?: boolean
  /** Prefer WebGPU (the test measured it faster); falls back to WebGL. */
  backend?: Backend
  /** Speed multiplier of the battle (×1/×2/×4) for the clips. */
  speed: () => number
  /** The player's monster's Fame (0–100): how full the Guild arena's stands are (ART.duel.crowd). */
  crowdFame?: number
}

export interface DuelStats {
  backend: Backend
  fps: number
  dpr: number
  level: Level
  gpuMs: number | null
  cpuMs: number
  arena: ArenaId | 'stand-in'
  /** What the player's side is drawn from (the Ultra file, its Lite file, or Puddlepup's Art 2.0 file), and both sides'. */
  monster: UltraKind
  monsters: [UltraKind, UltraKind]
  looks: [UltraId, UltraId]
  /** Estimated GPU memory (textures, geometry, render targets) and Chrome's JS heap, in MB. */
  gpuMb: number
  heapMb: number | null
  /** The Guild arena's crowd (people, cut-outs, its draws, triangles and CPU ms), or null without it. */
  crowd: CrowdStats | null
  /** §7 the attack effects last frame: quads drawn, their draws (at most two) and CPU ms. */
  fx: { quads: number; draws: number; ms: number; zoom: number }
  /** Flight: whether each side's look flies, how high each is now (m) and each one's open wingspan (m, 0 if it can't fly). */
  flight: { flies: [boolean, boolean]; liftM: [number, number]; spanM: [number, number] }
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
  /** Refill the stands for another Fame (the test screen's chip). */
  setCrowdFame(fame: number): Promise<void>
  /** Review only (picture, not rules): show a technique fired by `side` that hits or misses as the duel would time it; returns the stage seconds until it lands. */
  preview(tech: string, side: Side, outcome: 'hit' | 'miss'): number
  /** Skip: every animation that would still play out ends now (a monster in the air lands at once). */
  settle(): void
  /** Review only: run the picture slower (1 = normal), and the stage clock (s). */
  setTimeScale(k: number): void
  clock(): number
  stats(): DuelStats
  dispose(): void
}

/* ---------------------------------------------------------------------------------------------- loading */

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

/** What tools/blender/arenas writes beside the arena (guild.json): the parts the runtime uses. */
interface ArenaInfo {
  ringRadius?: number
  /** How far from the centre a camera may stand before the stands or the wall (the Crown: 18.5 m); else the ring. */
  cameraRadius?: number
  sun?: { direction: [number, number, number] }
  flyIn?: { eye: [number, number, number]; target: [number, number, number]; t: number; fovDeg: number }[]
  runtime?: { shadowCatcher?: { node: string } }
  /** The crowd's seats (checked by crowd.ts). */
  seats?: unknown
}

interface Arena {
  root: Object3D
  anchors: Map<string, Object3D>
  kind: ArenaId | 'stand-in'
  info: ArenaInfo | null
}

const GROUND_ATLAS = /ring|apron|mid|far|sand|floor/

/**
 * An arena (docs/BATTLE_3D.md §8: models/arenas/<id>/), or a simple ring if it can't load. Its materials are unlit
 * with the light baked in, so the fighters' shadows fall on its invisible shadow_catcher disc instead.
 */
async function loadArena(loader: GLTFLoader, lite: boolean, id: ArenaId): Promise<Arena> {
  const dir = `${BASE}models/arenas/${id}/`
  const file = lite ? `${id}_lite.glb` : `${id}.glb`
  if (await exists(`${dir}${file}`)) {
    try {
      const [gltf, info] = await Promise.all([loader.loadAsync(`${dir}${file}`), fetchJson<ArenaInfo>(`${dir}${id}.json`)])
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
      return { root: gltf.scene, anchors, kind: id, info }
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
  /** Its measurements (metres): how far nose and tail reach, its width; and its sizes beside Puddlepup's. */
  size: UltraSize
  /** Its body length, nose reach and width as shares of Puddlepup's (ART.duel.reference): 1 for Puddlepup. */
  lenK: number
  frontK: number
  widthK: number
  rootSpeed: Record<string, number>
  impactAt: Record<string, number>
  /** The file's blink clip, if it has one. */
  blink: string | null
  /** When the next blink plays (the blink clip keys only the lids, so it layers over any clip). */
  nextBlink: number
  blinks: number
  /** §7: a melee lunge in progress, a hit's squash until this time, and when the current walking clip began. */
  lunge: Lunge | null
  squashUntil: number
  loopSince: number
  /** Flight (ultra/flight.ts): its flying clips' times and its open wings' span (m) when the look flies, else null. */
  fly: { times: FlyTimes; spanM: number } | null
  /** The flight (or hop) in progress, its next clip, and how high its feet are now (m). */
  flight: FlightPlan | null
  flyStep: number
  lift: number
  /** Where its fire leaves from in the air (its mouth socket, following the jaw), and its contact shadow. */
  mouth: Object3D | null
  shadow: Mesh
}

function makeActor(asset: UltraAsset, side: Side, variant: string | null, heightM: number): Actor {
  // the copy: film materials, the variant, the cards out of the AO pass and the shadows, fitted to its true height
  const u = makeUltraModel(asset, variant, heightM)
  const R = D.reference
  const lenK = (u.size.front + u.size.back) / R.lengthM
  const frontK = u.size.front / R.frontM
  const widthK = u.size.width / R.widthM
  // a look that flies (its sidecar lists the flying clips and its file holds them): measured with its wings open,
  // before it is placed
  const clips = asset.clips
  const times = flyTimesOf(asset, clips)
  const flyClip = clips.find((c) => c.name === 'fly')
  const fly = times && flyClip ? { times, spanM: (wingspanOf(u, asset.meta, flyClip) * (100 + FL.spanMarginPct)) / 100 } : null
  const root = new Group()
  const shadow = contactShadow(widthK, lenK)
  root.add(u.model, shadow)
  const mixer = new AnimationMixer(u.model)
  const actions = new Map<string, AnimationAction>()
  for (const clip of clips) actions.set(clip.name, mixer.clipAction(clip))
  const a: Actor = {
    side, root, model: u.model, mixer, actions, current: '', holdUntil: 0, oneShot: null, pos: new Vector3(), yaw: 0, height: heightM,
    size: u.size, lenK, frontK, widthK, rootSpeed: u.rootSpeed, impactAt: u.impactAt, blink: blinkClipOf(asset),
    nextBlink: 1.2 + side * 0.9, blinks: side * 2, lunge: null, squashUntil: 0, loopSince: 0,
    fly, flight: null, flyStep: 0, lift: 0, mouth: fly ? (u.model.getObjectByName('socket_mouth') ?? u.model.getObjectByName('jaw') ?? null) : null, shadow,
  }
  play(a, 'battle_idle', { loop: true })
  return a
}

function resolveClip(a: Actor, name: string): string | null {
  return resolveClipName((n) => a.actions.has(n), name)
}

function play(a: Actor, name: string, o: { loop: boolean; rate?: number; fade?: number; hold?: boolean; offset?: number }): void {
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
  // a flying clip may start part way in (the cast just before its release)
  const offset = Math.min(Math.max(0, o.offset ?? 0), next.getClip().duration)
  next.time = offset
  next.enabled = true
  next.setEffectiveWeight(1)
  next.play()
  if (prev && prev !== next) prev.crossFadeTo(next, o.fade ?? 0.15, false)
  a.current = clip
  a.oneShot = o.loop ? null : clip
  a.holdUntil = o.loop ? 0 : a.mixer.time + (next.getClip().duration - offset) / Math.max(0.05, Math.abs(next.timeScale)) - (o.hold ? 0 : 0.05)
}

/** Whether it is in a flight with its own clips (not a hop): hits then don't cut in (it stays in its flying pose). */
function flying(a: Actor): boolean {
  return !!a.flight && a.flight.steps.length > 0
}

/* ---------------------------------------------------------------------------------------------- effects */

let contactTexture: CanvasTexture | null = null

/**
 * A soft dark disc under the feet: the arena's floor is baked, so this is what makes a monster stand on it. Sized like
 * the monster: its width and length beside Puddlepup's.
 */
function contactShadow(widthK: number, lenK: number): Mesh {
  if (!contactTexture) {
    const c = document.createElement('canvas')
    c.width = c.height = 64
    const g = c.getContext('2d')!
    const r = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    r.addColorStop(0, 'rgba(40,28,18,1)')
    r.addColorStop(0.45, 'rgba(40,28,18,0.6)')
    r.addColorStop(1, 'rgba(40,28,18,0)')
    g.fillStyle = r
    g.fillRect(0, 0, 64, 64)
    contactTexture = new CanvasTexture(c)
    contactTexture.colorSpace = SRGBColorSpace
  }
  const mat = new MeshBasicMaterial({ map: contactTexture, transparent: true, opacity: D.contactShadow.opacity, depthWrite: false })
  const disc = new Mesh(new PlaneGeometry(D.contactShadow.sizeM * widthK, ((D.contactShadow.sizeM * D.contactShadow.depthPct) / 100) * lenK), mat)
  disc.rotation.x = -Math.PI / 2
  disc.position.y = 0.006
  disc.renderOrder = 1
  // see-through: the AO pass would draw its whole square
  disc.layers.set(NO_AO_LAYER)
  return disc
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
  const dpr = Math.min(o.lite ? 1.25 : D.dprStart, dprMax)
  const wantGpu = (o.backend ?? 'webgpu') === 'webgpu' && !o.lite && 'gpu' in navigator
  let view: PerfView | undefined = wantGpu ? await createView('webgpu', { canvas, width: w(), height: h(), dpr, cinematic: false, focus: 3 }).catch(() => undefined) : undefined
  if (!view) view = await createView('webgl', { canvas, width: w(), height: h(), dpr, cinematic: false, focus: 3 })
  const v = view!
  const scene = new Scene()
  const camera = new PerspectiveCamera(D.fov, w() / h(), 0.05, D.far)
  // the fur cards (and the see-through floor marks and effects) draw on a layer the AO pass's camera leaves out
  camera.layers.enable(NO_AO_LAYER)
  const loader = makeLoader(v.renderer)
  // each side's breed at its true size; two fighters of one breed share one download
  const fighters = duelFighters(o)
  const loads = new Map(duelLoads(fighters).map((id) => [id, loadUltraAsset(loader, id, o.lite)] as const))
  const [arena, assets] = await Promise.all([loadArena(loader, o.lite, o.arena ?? 'guild'), Promise.all(fighters.map((f) => loads.get(f.look)!))])
  const textures = new Set<Texture>()
  noteTextures(arena.root, textures)
  for (const asset of new Set(assets)) noteTextures(asset.scene, textures)
  scene.add(arena.root)
  // the Guild arena's living crowd (§8): its seats come with the arena (the stand-in has none); each battle's own seed
  // seats a different crowd and draws different breeds' boards
  const crowdSeed = D.crowd.seed + (getState()?.seed ?? 0)
  const makeCrowd = (fame: number) => (arena.kind !== 'stand-in' ? createCrowd(scene, arena.info, { fame, lite: o.lite, reduceMotion: o.reduceMotion, seed: crowdSeed }) : Promise.resolve(null))
  let crowd: Crowd | null = await makeCrowd(o.crowdFame ?? D.crowd.defaultFame)
  let ovation = false
  const studio = buildStudio(scene, v.environment, new Vector3(0, 0.5, 0), 8)
  // outdoors: a soft sky instead of the studio's grey (the Guild arena brings its own sky domes)
  scene.background = new Color(D.sky)
  studio.ground.visible = arena.kind === 'stand-in'
  const sun = arena.info?.sun?.direction
  if (sun) studio.key.position.set(sun[0], sun[1], sun[2]).normalize().multiplyScalar(32).add(studio.key.target.position)
  // every camera stays inside the fence (ART.duel.confine): the crowd stands start just past it
  const wallR = arena.info?.cameraRadius ?? (arena.info?.ringRadius ? arena.info.ringRadius - D.confine.wallMargin : Infinity)
  const actors: [Actor, Actor] = [makeActor(assets[0], 0, fighters[0].variant, fighters[0].heightM), makeActor(assets[1], 1, fighters[1].variant, fighters[1].heightM)]
  for (const a of actors) scene.add(a.root)
  // §7: every technique's effects (its element and shape), two draws from one pool; their sockets sized per monster
  const seeThroughFrom = scene.children.length
  const fx = new AttackFx(scene, { lite: o.lite, reduceMotion: o.reduceMotion, speed: o.speed })
  for (const a of actors) fx.setSize(a.side, a.frontK, a.widthK)
  // review only: a previewed technique's result, waiting for its landing (picture only; the rules never see it)
  const previews: { at: number; e: BattleEvent }[] = []
  // §7: a hit nudges the camera until this time (not with Reduce motion)
  let shakeUntil = 0
  // §7: the wind-up's quiet floor marks (a lane for a straight line, a ring for a sweep)
  const telegraphs = new Telegraphs(scene)
  // the effects' quads and the telegraphs are see-through: out of the AO pass (it would draw them whole)
  for (const c of scene.children.slice(seeThroughFrom)) c.traverse((x) => x.layers.set(NO_AO_LAYER))
  await v.init(scene, camera)
  // compile the materials' shaders now, so the entrance's first frames don't stall on it (where the renderer can)
  try {
    await (v.renderer as { compileAsync?: (s: Scene, c: PerspectiveCamera) => Promise<unknown> }).compileAsync?.(scene, camera)
  } catch {
    /* compiled on first use instead */
  }
  // warm-up: draw the whole arena once from the fly-in's start (it sees all of it), so the texture uploads and first
  // draws happen behind the loading card instead of freezing the entrance's first frame (the Crown: about 7 s on the PC)
  const firstKey = arena.info?.flyIn?.[0]
  camera.position.set(...(firstKey?.eye ?? [0, 30, 60]))
  camera.lookAt(...(firstKey?.target ?? [0, 0, 0]))
  camera.updateMatrixWorld()
  for (let i = 0; i < D.warmupFrames; i++) {
    v.render()
    await new Promise((r) => setTimeout(r, 0))
  }
  if (o.lite) v.setLevel('no-msaa')
  const dyn = createDynRes(v, { lite: o.lite, dprStart: dpr, dprMax, size: () => ({ w: w(), h: h() }), fastDrop: D.fastDrop })

  let camMode: DuelCamera = 'side'
  let cine: { until: number; from: Vector3; look: Vector3; fov: number } | null = null
  const camPos = new Vector3(0, 3, 9)
  const camLook = new Vector3(0, 0.6, 0)
  let camFov: number = D.fov
  // the side camera's last distance, for the zoom hysteresis (§7)
  let lastSideD = 0
  // the side-on camera's fitting camera (reused every frame)
  const fitCam = new PerspectiveCamera(D.fov, 1, 0.05, D.far)
  /** The entrance's own clock (`t`, seconds): it follows real time, so a slow first frame can't stretch it. */
  let intro: { t: number; resolve: () => void; skip: boolean } | null = null
  let now = 0
  // review only: slow motion for the effects sheets (the battle itself is paused then)
  let timeScale = 1
  let last = performance.now()
  let raf = 0
  let disposed = false
  // the side the side-on camera sits on, fixed at the start so it never flips as they circle
  let sideSign = 1
  const frameTimes: number[] = []
  let cpuMs = 0

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
      // over the player's monster's back, at its size (a taller breed: further back and higher)
      const me = actors[o.me]
      const foe = actors[1 - o.me]!
      const k = me.height / D.monsterHeightM
      const lat = new Vector3(-u.z, 0, u.x).multiplyScalar(D.behind.side * k)
      // in a flight: up with it and back off its open wings; looking up at a flying opponent
      const upMe = framedLift(me.flight, me.lift)
      const upFoe = framedLift(foe.flight, foe.lift)
      const back = D.behind.back * k + (upMe > 0 && me.fly ? (me.fly.spanM * FL.camera.behindBackPct) / 100 : 0)
      return {
        pos: insideFence(a.clone().addScaledVector(u, -back).add(lat).add(new Vector3(0, D.behind.height * k + (upMe * FL.camera.behindRaisePct) / 100, 0))),
        look: b.clone().add(new Vector3(0, D.behind.lookY * (foe.height / D.monsterHeightM) + (upFoe * FL.camera.behindLookPct) / 100, 0)),
        fov: D.fov,
      }
    }
    // Side-on, framed for the screen's shape (framing.ts): upright, a three-quarter view turned toward the player's
    // monster; sideways, nearly square side-on. The distance is fitted every frame so both monsters sit in the clear
    // band of the screen (between the top bar and the cards upright; left of the cards sideways).
    void s
    const F = D.side
    const fr = sideFraming(camera.aspect)
    fr.elevationDeg = Math.max(D.arenaCamera.minElevationDeg, fr.elevationDeg + (arena.kind === 'crown' ? D.arenaCamera.crown.elevationAddDeg : 0))
    const n = new Vector3(-u.z, 0, u.x).multiplyScalar(sideSign)
    const yaw = (fr.yawDeg * Math.PI) / 180
    const flat = n.clone().multiplyScalar(Math.cos(yaw)).addScaledVector(u, -Math.sin(yaw)).normalize()
    const band = o.leftHanded ? { ...fr.band, left: -fr.band.right, right: -fr.band.left } : fr.band
    const centreX = (band.left + band.right) / 2
    const centreY = (band.top + band.bottom) / 2
    const right = new Vector3()
    const tMax = Math.tan(((D.confine.maxFov / 2) * Math.PI) / 180)
    // both monsters whole: feet and heads, front and back, each at its own size (bodyHalfM is Puddlepup's)
    // in a flight: its hover height and its open wings either side (held for the whole flight, so it settles once)
    const pts = ([[a, actors[o.me]], [b, actors[1 - o.me]!]] as const).flatMap(([p, act]) => {
      const up = framedLift(act.flight, act.lift)
      const body = [-1, 1].flatMap((k) => {
        const q = p.clone().addScaledVector(u, k * F.bodyHalfM * act.lenK)
        return [q, q.clone().add(new Vector3(0, act.height + up, 0))]
      })
      if (up <= 0 || !act.fly) return body
      const wing = new Vector3(-u.z, 0, u.x).multiplyScalar(act.fly.spanM / 2)
      const y = up + act.height * 0.6
      return [...body, p.clone().add(wing).setY(y), p.clone().sub(wing).setY(y)]
    })
    const dir = new Vector3()
    let t = 0
    let d = 0
    let look = mid.clone()
    fitCam.aspect = camera.aspect
    // how much bigger the view must be for every point to sit in the band, from distance d and lens t
    const need = (): number => {
      // aim off the middle so the pair sits in the band's centre rather than the screen's
      look = mid.clone().add(new Vector3(0, F.lookY - d * t * centreY, 0)).addScaledVector(right, -centreX * d * t * camera.aspect)
      fitCam.fov = (2 * Math.atan(t) * 180) / Math.PI
      fitCam.updateProjectionMatrix()
      fitCam.position.copy(look).addScaledVector(dir, d)
      fitCam.lookAt(look)
      fitCam.updateMatrixWorld()
      let m = 0
      for (const p of pts) {
        const q = p.clone().project(fitCam)
        m = Math.max(m, bandNeed(q.x, q.y, band))
      }
      return Math.min(1.6, Math.max(0.6, m))
    }
    for (let el = fr.elevationDeg; ; el += D.confine.raiseDeg) {
      const e = (el * Math.PI) / 180
      dir.copy(flat).multiplyScalar(Math.cos(e)).add(new Vector3(0, Math.sin(e), 0)).normalize()
      right.crossVectors(dir.clone().negate(), new Vector3(0, 1, 0)).normalize()
      t = Math.tan(((D.fov / 2) * Math.PI) / 180)
      d = F.base + dist * F.perGap
      for (let i = 0; i < 4; i++) d = Math.min(F.maxDist, Math.max(F.minDist, d * need()))
      const reach = reachInside(look, dir)
      if (d > reach) {
        // the crowd is behind: stay inside the fence and widen the lens; if that can't fit them, rise and try again
        t *= d / reach
        d = reach
        for (let i = 0; i < 3; i++) t = Math.min(tMax, t * need())
      }
      // a ring barrier inside the camera's floor (the Crown's): never stop just beyond it, where a post fills the
      // picture; back off past the strip (smaller monsters, still in the band)
      const ring = arena.info?.ringRadius
      if (ring && wallR > ring + D.barrierClearM) {
        const at = look.clone().addScaledVector(dir, d)
        const r = Math.sqrt(at.x * at.x + at.z * at.z)
        if (r > ring - D.barrierClearInM && r < ring + D.barrierClearM) d = Math.min(reach, Math.max(d, reachTo(look, dir, ring + D.barrierClearM)))
      }
      const fits = d < reach || need() <= 1.02
      // and never so low that a ring barrier's rope and posts cut across the picture (the Crown's)
      const highEnough = look.y + dir.y * d >= D.minCameraHeightM
      if ((fits && highEnough) || el >= fr.elevationDeg + D.confine.maxRaiseDeg) break
    }
    // §7: don't breathe in and out as they walk: come closer only for a big change (backing out is always at once)
    if (lastSideD > 0 && d < lastSideD && d * 100 > lastSideD * AT.zoomInPct && lastSideD <= reachInside(look, dir)) d = lastSideD
    lastSideD = d
    need()
    return { pos: look.clone().addScaledVector(dir, d), look, fov: (2 * Math.atan(t) * 180) / Math.PI }
  }

  /** How far the camera can back away from `from` along `dir` before it leaves the fence (horizontally), in metres. */
  function reachInside(from: Vector3, dir: Vector3): number {
    return reachTo(from, dir, wallR)
  }

  /** How far from `from` along `dir` the camera reaches radius R from the centre (horizontally), in metres. */
  function reachTo(from: Vector3, dir: Vector3, R: number): number {
    if (!Number.isFinite(R)) return Infinity
    const a = dir.x * dir.x + dir.z * dir.z
    const b = from.x * dir.x + from.z * dir.z
    const c = from.x * from.x + from.z * from.z - R * R
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

  /**
   * A cut to `attacker`: over its shoulder toward the target for a technique (§7: its effects in the shot; framed for
   * the screen's shape, cineShot.ts), else a low three-quarter on it (the KO).
   */
  function startCine(attacker: Actor, now: number, technique = false): void {
    if (!D.cine.enabled) return
    const opp = actors[1 - attacker.side]!
    const until = now + (o.reduceMotion ? D.cine.seconds * 0.7 : D.cine.seconds)
    if (technique) {
      // a flying attacker: the whole flier in the sky above the target (cineShot.ts flyShot); if that would stand
      // beyond the fence, it hovers lower (same timing) until a shot inside holds it
      const fl = attacker.flight
      if (fl?.kind === 'flight' && attacker.fly) {
        const f = flyShotInside(attacker.pos, opp.pos, camera.aspect, sideSign, insideFence, [attacker.height, opp.height], { liftM: fl.peakM, spanM: attacker.fly.spanM })
        if (f.liftM < fl.peakM) attacker.flight = withPeak(fl, f.liftM)
        cine = { until, from: f.shot.from, look: f.shot.look, fov: f.shot.fov }
        return
      }
      const shot = cineShot(attacker.pos, opp.pos, camera.aspect, sideSign, insideFence, [attacker.height, opp.height])
      cine = { until, from: shot.from, look: shot.look, fov: shot.fov }
      return
    }
    // the KO: a low three-quarter on the winner, at its size
    const k = attacker.height / D.monsterHeightM
    const u = opp.pos.clone().sub(attacker.pos).normalize()
    const n = new Vector3(-u.z, 0, u.x)
    const from = insideFence(attacker.pos.clone().addScaledVector(u, D.cine.ahead * k).addScaledVector(n, D.cine.side * k * sideSign).add(new Vector3(0, D.cine.height * k, 0)))
    cine = { until, from, look: attacker.pos.clone().add(new Vector3(0, (D.cine.lookPct / 100) * attacker.height + (attacker.lift * FL.camera.lookPct) / 100, 0)), fov: D.fov }
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
      const fwd = new Vector3(Math.sin(a.yaw), 0, Math.cos(a.yaw))
      // §7: a melee lunge carries the body across the gap to the target and back (picture only)
      const reach = a.lunge ? lungeReach(now, a.lunge) : 0
      if (a.lunge && now >= a.lunge.end) a.lunge = null
      // contactM is between two Puddlepups' noses: longer reaches meet further apart
      const foe = actors[(1 - a.side) as Side]
      const gap = Math.max(0, foe.pos.distanceTo(a.pos) - (AT.contactM * (a.frontK + foe.frontK)) / 2)
      a.root.position.copy(a.pos).addScaledVector(fwd, reach * gap)
      a.root.rotation.y = a.yaw
      // §7: a hit squashes the target for a moment
      const sq = a.squashUntil > now ? ((a.squashUntil - now) / AT.squashSec) * (AT.squashPct / 100) : 0
      a.root.scale.set(1 + sq * 0.66, 1 - sq, 1 + sq * 0.66)
      // flight (ultra/flight.ts): KO'd in the air it falls; the plan ends on the floor. Its shadow stays on the floor,
      // smaller and fainter the higher it is
      if (a.flight && f.hp <= 0 && a.flight.ease !== 'fall') a.flight = landNow(a.flight, now, FL.fallSec / Math.max(1, o.speed()), 'fall')
      if (a.flight && now >= a.flight.end) a.flight = null
      a.lift = a.flight ? liftAt(a.flight, now) : 0
      a.root.position.y += a.lift
      const sh = shadowAt(a.lift, a.height)
      a.shadow.position.y = (0.006 - a.lift) / Math.max(0.5, a.root.scale.y)
      a.shadow.scale.set(sh.scale, sh.scale, 1)
      ;(a.shadow.material as MeshBasicMaterial).opacity = D.contactShadow.opacity * sh.opacity
      // the clip
      const vel = a.pos.clone().sub(prev).divideScalar(Math.max(1e-3, dt))
      const left = new Vector3(fwd.z, 0, -fwd.x)
      const vf = vel.dot(fwd)
      const vl = vel.dot(left)
      const speed = Math.hypot(vf, vl)
      const busyOneShot = a.oneShot !== null && a.mixer.time < a.holdUntil
      if (f.hp <= 0) {
        if (a.current !== resolveClip(a, 'ko')) play(a, 'ko', { loop: false, hold: true })
      } else if (flying(a)) {
        // the flight's clips, each when its time comes (one whose time has partly passed starts that far in)
        const fl = a.flight!
        while (a.flyStep < fl.steps.length && now >= fl.steps[a.flyStep]!.at) {
          const st = fl.steps[a.flyStep++]!
          play(a, st.clip, { loop: st.loop, rate: st.rate, fade: FL.fadeSec, offset: st.offset + (now - st.at) * st.rate })
        }
      } else if (s.outcome && s.outcome.winner === a.side) {
        if (a.current !== resolveClip(a, 'win')) play(a, 'win', { loop: true })
      } else if (f.sidestepTicks > 0) {
        const name = f.sidestepDir > 0 ? 'sidestep_l' : 'sidestep_r'
        if (a.current !== resolveClip(a, name)) play(a, name, { loop: false, rate: o.speed() })
      } else if (!busyOneShot) {
        let name = 'battle_idle'
        let rate = 1
        if (f.dashTicks > 0) {
          name = 'dash'
          rate = o.speed()
        } else if (speed > 0.08) {
          const strafing = Math.abs(vl) > Math.abs(vf)
          name = strafing ? (vl > 0 ? 'strafe_l' : 'strafe_r') : vf >= 0 ? 'step_fwd' : 'step_back'
          const rs = a.rootSpeed[resolveClip(a, name) ?? ''] ?? 0
          rate = rs > 0 ? Math.min(2.4, Math.max(0.5, speed / rs)) : 1
        }
        // §7: walking clips hold a moment, so small back-and-forth steps don't flicker between them
        const want = resolveClip(a, name)
        if (want === a.current || a.oneShot !== null || name === 'dash' || now - a.loopSince >= AT.minLoopSec) {
          if (want !== a.current) a.loopSince = now
          play(a, name, { loop: true, rate })
        }
      }
      blink(a, f.hp > 0)
      a.mixer.update(dt)
    }
  }

  function blink(a: Actor, awake: boolean): void {
    const clip = a.blink ? a.actions.get(a.blink) : undefined
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
        const ranged = tech ? isRangedTech(tech) : false
        const clip = ranged ? 'cast' : 'strike'
        // time the clip so its impact lands with the engine's landing tick
        const windupSec = (((e.lands ?? e.t) - e.t) / BATTLE.ticksPerSecond) / Math.max(1, o.speed())
        const imp = a.impactAt[resolveClip(a, clip) ?? ''] ?? 0.4
        const rate = windupSec > 0.01 ? Math.min(2.6, Math.max(0.7, imp / windupSec)) : o.speed()
        // flight (ultra/flight.ts): a look that flies takes its Special and Signature into the air and hops its jab
        // (never with Reduce motion); every other look, and any move that can't fit a flight, as before
        const kind = a.fly && tech && !o.reduceMotion ? flyKindOf(tech.family, ranged) : null
        const speed = Math.max(1, o.speed())
        const hits = tech?.effect?.kind === 'multi' ? tech.effect.hits : 1
        const plan = kind === 'flight' && tech ? flightPlan({ now, windupSec, busySec: duelPaced(tech.anim) / BATTLE.ticksPerSecond / speed, hits, speed, heightM: a.height, times: a.fly!.times }) : null
        a.flight = plan
        a.flyStep = 0
        if (!plan) play(a, clip, { loop: false, rate })
        // §7: melee lunges across the gap; the technique's own effects (wind-up glow, projectile, wave) land with it
        if (!ranged) {
          a.lunge = lungeFor(now, windupSec)
          if (kind === 'hop') a.flight = hopPlan(a.lunge, a.height)
        }
        // in a flight the fire leaves its mouth on the cast's release, in the air
        const release = plan?.release ?? undefined
        if (tech) fx.fire(e.side, tech, now, windupSec, release)
        if (e.lands !== undefined && e.path) {
          const travel = release !== undefined ? Math.max(0.02, now + windupSec - release) : ranged ? AT.boltTravelSec : AT.lungeSec
          telegraphs.show(e.side, e.path, tech?.type === 'INT', fighterAt(s, e.side), fighterAt(s, (1 - e.side) as Side), now, windupSec, travel)
        }
        if (tech && (tech.family === 'Special' || tech.family === 'Signature')) {
          startCine(a, now, true)
          crowd?.cheer('big')
        }
      } else if (e.kind === 'hit') {
        const t = actors[e.target]
        const heavy = e.crit || e.damage * 8 >= s.fighters[e.target].maxHp
        // in the air it keeps its flying pose (the squash and the impact still show)
        if (s.fighters[e.target].hp > 0 && !flying(t)) play(t, heavy ? 'hit_heavy' : 'hit', { loop: false, rate: o.speed() })
        const tech = TECHNIQUE_BY_ID[e.tech]
        if (tech) fx.hit(e.side, tech, e.hitNo, e.of, e.crit, now)
        t.squashUntil = now + AT.squashSec
        if (!o.reduceMotion) shakeUntil = now + AT.shakeSec * (heavy ? 1.6 : 1)
        crowd?.cheer(heavy ? 'big' : 'small')
      } else if (e.kind === 'miss') {
        // §7: a miss whiffs past (no impact)
        const tech = TECHNIQUE_BY_ID[e.tech]
        if (tech) fx.miss(e.side, tech, e.hitNo, now)
      } else if (e.kind === 'sidestep') {
        fx.sidestep(e.side)
      } else if (e.kind === 'heal') {
        fx.healed(e.side, e.why, now)
      } else if (e.kind === 'ko') {
        startCine(actors[(1 - e.side) as Side], now)
        crowd?.cheer('huge')
      } else if (e.kind === 'fence') {
        // §4.5 knocked into the fence: a burst at its feet and a jolt
        const t = actors[e.side]
        fx.fenced(e.side, now)
        if (!flying(t)) play(t, 'hit_heavy', { loop: false, rate: o.speed() })
        crowd?.cheer('big')
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
    const k = actors[o.me].height / D.monsterHeightM
    const eye = me.clone().addScaledVector(u, -D.behind.back * k).add(new Vector3(-u.z, 0, u.x).multiplyScalar(D.behind.side * k)).add(new Vector3(0, D.behind.height * k, 0))
    const lastT = arena.info?.flyIn?.[arena.info.flyIn.length - 1]?.t ?? keys[keys.length - 1]!.t + 1
    keys.push({ eye: eye.toArray(), target: them.clone().add(new Vector3(0, D.behind.lookY * (actors[1 - o.me]!.height / D.monsterHeightM), 0)).toArray(), t: lastT, fovDeg: D.fov })
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

  const mouthAt = [new Vector3(), new Vector3()]
  let lastW = w()
  let lastH = h()
  function loop(): void {
    if (disposed) return
    raf = requestAnimationFrame(loop)
    const tNow = performance.now()
    const frameMs = tNow - last
    last = tNow
    const dt = Math.min(0.1, frameMs / 1000) * timeScale
    now += dt
    frameTimes.push(frameMs)
    if (frameTimes.length > 120) frameTimes.shift()
    if (w() !== lastW || h() !== lastH) {
      lastW = w()
      lastH = h()
      camera.aspect = lastW / lastH
      camera.updateProjectionMatrix()
      v.setSize(lastW, lastH, dyn.dpr())
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
          camFov += (cine.fov - camFov) * k
        } else {
          cine = null
          const k = 1 - Math.exp(-dt * (o.reduceMotion ? D.springReduced : D.spring))
          camPos.lerp(goal.pos, k)
          camLook.lerp(goal.look, k)
          camFov += (goal.fov - camFov) * k
        }
        camera.position.copy(camPos)
        if (now < shakeUntil) {
          // a short, fading jolt; picture only
          const k = ((shakeUntil - now) / AT.shakeSec) * AT.shakeM
          camera.position.x += Math.sin(now * 91) * k
          camera.position.y += Math.cos(now * 77) * k * 0.6
        }
        camera.lookAt(camLook)
        setFov(camFov)
      }
      // the win brings the stands to their feet (once per result)
      if (!!s.outcome !== ovation) {
        ovation = !!s.outcome
        if (ovation) crowd?.cheer('ovation')
      }
    }
    crowd?.update(dt, now, { x: (actors[0].pos.x + actors[1].pos.x) / 2, z: (actors[0].pos.z + actors[1].pos.z) / 2 })
    telegraphs.update(now)
    for (let i = previews.length - 1; i >= 0; i--) {
      if (previews[i]!.at > now) continue
      onEvents([previews[i]!.e])
      previews.splice(i, 1)
    }
    // in a flight the effects leave from its mouth (the socket follows the jaw), blended in as it climbs
    for (const a of actors) {
      const k = a.mouth ? mouthShare(a.flight, a.lift) : 0
      fx.setMouth(a.side, k > 0 ? a.mouth!.getWorldPosition(mouthAt[a.side]!) : null, k)
    }
    fx.update(now, camera, actors[0].root.position, actors[1].root.position, actors[0].height, actors[1].height)
    // the glow's twinkle (still with Reduce motion)
    setFilmClock(now, o.reduceMotion)
    // the rims stay behind the monsters as this camera sees them (a back view isn't lit face-on by them)
    aimStudioRims(studio, camera.position, camLook)
    v.render()
    cpuMs = performance.now() - c0
    // dynamic resolution (ART_2_DETAIL §3.6): resolution first, then effects; the monsters never change
    dyn.frame(frameMs)
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
      const p = a.pos.clone().add(new Vector3(0, a.height * 0.9 + a.lift, 0)).project(camera)
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
      return {
        backend: v.backend, fps: 1000 / avg, dpr: dyn.dpr(), level: dyn.level(), gpuMs: v.gpuMs(), cpuMs, arena: arena.kind,
        monster: assets[o.me].kind, monsters: [assets[0].kind, assets[1].kind], looks: [fighters[0].look, fighters[1].look],
        gpuMb: mem.gpu, heapMb: mem.heap, crowd: crowd?.stats() ?? null, fx: fx.stats(),
        flight: { flies: [!!actors[0].fly, !!actors[1].fly], liftM: [+actors[0].lift.toFixed(3), +actors[1].lift.toFixed(3)], spanM: [+(actors[0].fly?.spanM ?? 0).toFixed(2), +(actors[1].fly?.spanM ?? 0).toFixed(2)] },
      }
    },
    settle() {
      for (const a of actors) if (a.flight) a.flight = landNow(a.flight, now, FL.settleSec, 'soft')
    },
    setTimeScale(k) {
      timeScale = Math.max(0.02, Math.min(1, k))
    },
    clock: () => now,
    preview(id, side, outcome) {
      const s = getState()
      const t = TECHNIQUE_BY_ID[id]
      if (!s || !t) return 0
      const lands = s.tick + duelWindup(t.family)
      const of = t.effect?.kind === 'multi' ? t.effect.hits : 1
      const target = (1 - side) as Side
      onEvents([{ t: s.tick, kind: 'fire', side, tech: id, cost: 0, lands, path: pathOf(t) }])
      const at = now + (lands - s.tick) / BATTLE.ticksPerSecond / Math.max(1, o.speed())
      for (let hitNo = 1; hitNo <= of; hitNo++) {
        const e: BattleEvent = outcome === 'hit' ? { t: lands, kind: 'hit', side, target, tech: id, damage: 1, crit: false, wither: 0, hitNo, of } : { t: lands, kind: 'miss', side, target, tech: id, hitNo, of }
        previews.push({ at, e })
      }
      if (t.effect?.kind === 'heal') previews.push({ at, e: { t: lands, kind: 'heal', side, amount: 1, why: 'tech' } })
      return at - now
    },
    async setCrowdFame(fame) {
      const next = await makeCrowd(fame)
      crowd?.dispose()
      crowd = disposed ? (next?.dispose(), null) : next
    },
    dispose() {
      disposed = true
      cancelAnimationFrame(raf)
      crowd?.dispose()
      fx.dispose()
      telegraphs.dispose()
      v.dispose()
    },
  }
}

