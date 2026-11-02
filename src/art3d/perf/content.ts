import {
  Color, DoubleSide, FrontSide, Group, HemisphereLight, DirectionalLight, InstancedMesh, Mesh, MeshBasicMaterial, MeshPhysicalMaterial,
  NoColorSpace, Object3D, PlaneGeometry, Scene, ShadowMaterial, SRGBColorSpace, Texture, TextureLoader, Vector2, Vector3, AdditiveBlending,
  CanvasTexture, Matrix4, Quaternion,
} from 'three'
import type { Camera, WebGLRenderer } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { ART } from '../../data/tuning.ts'

/**
 * Art 2.1 Performance check (docs/ART_2_DETAIL.md §6): what is drawn. The spike's game asset (public/models/perf/) with
 * the film look, built only from standard physical materials and lights so both renderers draw the same thing.
 */

const U = ART.ultra

/** The site root: the check is its own build under /perf/, the models sit with the game's. */
export const SITE = import.meta.env.BASE_URL.replace(/perf\/$/, '')
export const MODELS = `${SITE}models/perf/`

export type Kind = 'body' | 'eye' | 'fin' | 'card' | 'lock'
export interface TexSet { base: Texture; normal: Texture; orm: Texture; bytes: number }
/** Texture files: WebP, KTX2 (ETC1S colour and ORM, UASTC normals), or KTX2 with ETC1S normals too (the smallest). */
export type TexFormat = 'ktx2' | 'webp' | 'ktx2-etc1s'
export interface Assets {
  scene: Object3D
  body: TexSet
  cine: TexSet
  /** The performance stand-in's torso and tail (public/models/perf/standin.glb), when present. */
  standin: { scene: Object3D; tex: TexSet } | null
  format: TexFormat
  glbBytes: number
}

/** Anything three.js can render with: the WebGL renderer, or the WebGPU renderer (typed loosely, it lives in a lazy chunk). */
export type AnyRenderer = WebGLRenderer | { isWebGPURenderer: true; [k: string]: unknown }

async function fetchBytes(url: string): Promise<number> {
  try {
    const r = await fetch(url, { method: 'HEAD' })
    return Number(r.headers.get('content-length') ?? 0)
  } catch {
    return 0
  }
}

/** GPU bytes of a texture as it sits on the GPU (with its mipmaps): compressed formats are ~1 byte per pixel (ASTC 4×4,
 * BC7) or half that (ETC2 RGB, BC1); plain images are 4. */
export function gpuBytes(t: Texture): number {
  const img = t.image as { width?: number; height?: number } | undefined
  const w = img?.width ?? 0
  const h = img?.height ?? 0
  const compressed = (t as Texture & { isCompressedTexture?: boolean }).isCompressedTexture === true
  const bpp = compressed ? 1 : 4
  return Math.round(w * h * bpp * 1.333)
}

async function loadTexSet(renderer: AnyRenderer, prefix: string, format: TexFormat, channel: number): Promise<TexSet> {
  const names = ['base', 'normal', 'orm'] as const
  const out: Partial<Record<(typeof names)[number], Texture>> = {}
  let bytes = 0
  if (format !== 'webp') {
    // the renderer is initialised before this (WebGPU: await renderer.init()), so detectSupport can read its formats
    const ktx = new KTX2Loader().setTranscoderPath(`${SITE}basis/`).detectSupport(renderer as WebGLRenderer)
    for (const n of names) {
      const url = `${MODELS}${prefix}_${n}${format === 'ktx2-etc1s' && n === 'normal' ? '.etc1s' : ''}.ktx2`
      const t = await ktx.loadAsync(url)
      out[n] = t
      bytes += await fetchBytes(url)
    }
    ktx.dispose()
  } else {
    const tl = new TextureLoader()
    for (const n of names) {
      const url = `${MODELS}${prefix}_${n}.webp`
      const t = await tl.loadAsync(url)
      t.flipY = false
      t.colorSpace = n === 'base' ? SRGBColorSpace : NoColorSpace
      out[n] = t
      bytes += await fetchBytes(url)
    }
  }
  for (const n of names) {
    const t = out[n]!
    t.channel = channel
    t.anisotropy = 4
    t.needsUpdate = true
  }
  return { base: out.base!, normal: out.normal!, orm: out.orm!, bytes }
}

export async function loadAssets(renderer: AnyRenderer, format: TexFormat): Promise<Assets> {
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder)
  const gltf = await loader.loadAsync(`${MODELS}spike.glb`)
  const body = await loadTexSet(renderer, 'atlas', format, 0)
  const cine = await loadTexSet(renderer, 'cine', format, 1)
  gltf.scene.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh) return
    const n = m.name
    m.userData.kind = (/fins/.test(n) ? 'fin' : /cards/.test(n) ? 'card' : /tuft/.test(n) ? 'lock' : /eyes/.test(n) ? 'eye' : 'body') satisfies Kind
    m.userData.part = /paw/.test(n) ? 'paw' : 'head'
    m.userData.cineReady = /lo_body|lo_eyes|lo_fins/.test(n)
    // fur cards lie a few millimetres over the coat: their shadows would read as holes in it
    m.castShadow = m.userData.kind !== 'card'
    // a fin is a thin lit membrane: the head's shadow on it read as dirty smudges
    m.receiveShadow = m.userData.kind !== 'fin'
  })
  let standin: Assets['standin'] = null
  if ((await fetchBytes(`${MODELS}standin.glb`)) > 0) {
    const sg = await loader.loadAsync(`${MODELS}standin.glb`)
    sg.scene.traverse((o) => {
      const m = o as Mesh
      if (!m.isMesh) return
      m.userData.kind = (/cards/.test(m.name) ? 'card' : 'body') satisfies Kind
      m.userData.part = 'torso'
      m.userData.texSet = 'standin'
      m.castShadow = m.userData.kind !== 'card'
      // a fin is a thin lit membrane: the head's shadow on it read as dirty smudges
    m.receiveShadow = m.userData.kind !== 'fin'
    })
    standin = { scene: sg.scene, tex: await loadTexSet(renderer, 'standin', format, 0) }
  }
  return { scene: gltf.scene, body, cine, standin, format, glbBytes: await fetchBytes(`${MODELS}spike.glb`) }
}

/** The film material for one kind of part (ART_2_DETAIL §2.4): damp fur, glowing fins, soft cards. */
export function filmMaterial(kind: Kind, tex: TexSet): MeshPhysicalMaterial {
  const f = U.film
  const m = new MeshPhysicalMaterial({
    map: tex.base,
    normalMap: tex.normal,
    normalScale: new Vector2(f.normalScale, f.normalScale),
    aoMap: tex.orm,
    roughnessMap: tex.orm,
    roughness: f.furRoughness,
    metalness: 0,
    clearcoat: kind === 'fin' ? f.finCoat : kind === 'eye' ? f.eyeCoat : kind === 'card' ? 0 : f.furCoat,
    clearcoatRoughness: kind === 'eye' ? 0.05 : f.furCoatRoughness,
    sheen: kind === 'fin' || kind === 'eye' ? 0 : kind === 'card' ? f.cardSheen : f.furSheen,
    sheenColor: new Color(f.sheenColor),
    sheenRoughness: f.sheenRoughness,
    envMapIntensity: kind === 'eye' ? f.eyeEnv : f.envIntensity,
    specularIntensity: kind === 'eye' ? f.eyeSpecular : 1,
    // only the fins are two-sided: a fur card's back face gets a flipped normal and renders nearly black at the outline
    side: kind === 'fin' ? DoubleSide : FrontSide,
    vertexColors: kind === 'card' || kind === 'lock',
  })
  if (kind === 'fin') {
    // fake translucency: the membrane glows a little with its own colour (paler toward the edge, as painted)
    m.emissiveMap = tex.base
    m.emissive = new Color('#ffffff')
    m.emissiveIntensity = f.finGlow
  }
  if (kind === 'card') {
    m.alphaTest = f.cardAlphaTest
    m.alphaToCoverage = true
    // fins: a card fades out as it turns to face the camera, so cards only show where the coat meets the outline
    // (the WebGPU view rebuilds this as a node material with the same rule, viewGpu.ts)
    const [lo, hi] = f.cardEdgeFade
    m.userData.edgeFade = [lo, hi]
    m.onBeforeCompile = (sh) => {
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <alphatest_fragment>',
        `diffuseColor.a *= smoothstep( ${lo.toFixed(3)}, ${hi.toFixed(3)}, 1.0 - abs( dot( normalize( vNormal ), normalize( vViewPosition ) ) ) );
#include <alphatest_fragment>`,
      )
    }
    m.customProgramCacheKey = () => 'film-card-fin'
  }
  return m
}

export function applyFilm(root: Object3D, assets: Assets, cinematic: boolean): void {
  root.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh || m.userData.isHelper) return
    const kind = m.userData.kind as Kind
    const useCine = cinematic && m.userData.cineReady === true
    const set = m.userData.texSet === 'standin' && assets.standin ? assets.standin.tex : useCine ? assets.cine : assets.body
    m.material = filmMaterial(kind, set)
  })
}

/** Blender azimuth/elevation (0 = in front of the monster, 90 = its left side) → a three.js direction toward the light. */
export function dirFrom(azDeg: number, elDeg: number): Vector3 {
  const a = (azDeg * Math.PI) / 180
  const e = (elDeg * Math.PI) / 180
  return new Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), Math.cos(a) * Math.cos(e))
}

export interface Studio { key: DirectionalLight; rim: DirectionalLight; hemi: HemisphereLight; ground: Mesh }

/** The pictures' studio light, a soft shadow from the key, a shadow-catching floor and the grey backdrop. */
export function buildStudio(scene: Scene, environment: Texture | null, focus: Vector3, reach: number): Studio {
  const s = U.studio
  scene.background = new Color(s.background)
  scene.environment = environment
  scene.environmentIntensity = s.environment
  const key = new DirectionalLight(s.key.color, s.key.intensity)
  key.position.copy(dirFrom(s.key.azDeg, s.key.elDeg).multiplyScalar(reach * 4)).add(focus)
  key.target.position.copy(focus)
  key.castShadow = true
  key.shadow.mapSize.set(s.shadowMapPx, s.shadowMapPx)
  key.shadow.radius = s.shadowRadius
  // generous biases: the key light grazes the throat and chest, where a tight bias draws stripes of shadow acne
  key.shadow.bias = s.shadowBias
  key.shadow.normalBias = s.shadowNormalBias
  const cam = key.shadow.camera
  cam.left = -reach
  cam.right = reach
  cam.top = reach
  cam.bottom = -reach
  cam.near = 0.1
  cam.far = reach * 10
  const rim = new DirectionalLight(s.rim.color, s.rim.intensity)
  rim.position.copy(dirFrom(s.rim.azDeg, s.rim.elDeg).multiplyScalar(reach * 4)).add(focus)
  rim.target.position.copy(focus)
  const hemi = new HemisphereLight(s.sky, s.ground, s.hemi)
  const ground = new Mesh(new PlaneGeometry(reach * 8, reach * 8), new ShadowMaterial({ opacity: 0.22 }))
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  ground.userData.isHelper = true
  scene.add(key, key.target, rim, rim.target, hemi, ground)
  return { key, rim, hemi, ground }
}

/** A procedural environment for reflections (no files): three's RoomEnvironment scene, prefiltered by the renderer. */
export function roomEnvironmentScene(): Scene {
  return new RoomEnvironment()
}

/** Pick the part to show: 'head' (with fins, tuft and cards), 'paw', or 'all'. */
export function showPart(root: Object3D, part: 'head' | 'paw' | 'all'): void {
  root.traverse((o) => {
    if ((o as Mesh).isMesh && !o.userData.isHelper) o.visible = part === 'all' || o.userData.part === part
  })
}

// ----------------------------------------------------------------------------- the stand-in monster
/**
 * The performance stand-in (never shown as the monster): the spike's head, four copies of its front paw at the leg
 * positions and the torso from the spike file when present. It carries a whole monster's triangles, cards and pixels.
 */
export function standIn(assets: Assets): Group {
  const g = new Group()
  const src = assets.scene
  const head = new Group()
  const paw = new Group()
  for (const child of src.children) {
    const c = child.clone(true)
    if (c.userData.part === 'paw' || /paw/.test(c.name)) paw.add(c)
    else if (/torso|tail/.test(c.name)) g.add(c)
    else head.add(c)
  }
  g.add(head)
  if (assets.standin) g.add(assets.standin.scene.clone(true))
  // the spike's paw sits at the front-left leg (Blender x 0.15, y -0.19 → three x 0.15, z 0.19)
  for (const [x, z] of [[0, 0], [-0.3, 0], [0, -0.34], [-0.3, -0.34]] as const) {
    const p = paw.clone(true)
    p.position.set(x, 0, z)
    g.add(p)
  }
  return g
}

// ----------------------------------------------------------------------------- the effects stand-in (Flashy bursts)
function sparkTexture(): Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const g = c.getContext('2d')!
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
  grad.addColorStop(0, 'rgba(255,255,255,1)')
  grad.addColorStop(0.35, 'rgba(255,240,200,0.6)')
  grad.addColorStop(1, 'rgba(255,200,120,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 64, 64)
  const t = new CanvasTexture(c)
  t.colorSpace = SRGBColorSpace
  return t
}

export interface Bursts { mesh: InstancedMesh; update(t: number, camera: Camera): void }

/** Additive sparks bursting around the fighters on a loop: about the pixel cost of V1's Flashy effects. */
export function buildBursts(scene: Scene, centres: Vector3[], count = 480): Bursts {
  const mat = new MeshBasicMaterial({ map: sparkTexture(), transparent: true, depthWrite: false, blending: AdditiveBlending, color: new Color('#ffd9a0') })
  const mesh = new InstancedMesh(new PlaneGeometry(1, 1), mat, count)
  mesh.frustumCulled = false
  mesh.userData.isHelper = true
  scene.add(mesh)
  const seeds = Array.from({ length: count }, (_, i) => ({ c: centres[i % centres.length]!, a: (i * 2.399963) % (Math.PI * 2), b: ((i * 7919) % 97) / 97, ph: ((i * 104729) % 89) / 89 }))
  const m = new Matrix4()
  const q = new Quaternion()
  const s = new Vector3()
  const p = new Vector3()
  return {
    mesh,
    update(t: number, camera: Camera) {
      q.copy(camera.quaternion)
      for (let i = 0; i < count; i++) {
        const sd = seeds[i]!
        const life = (t * 0.8 + sd.ph) % 1
        const r = 0.15 + life * 0.9
        p.set(sd.c.x + Math.cos(sd.a) * r * (0.6 + sd.b), sd.c.y + 0.4 + Math.sin(sd.a * 1.7) * r * 0.5 + life * 0.3, sd.c.z + Math.sin(sd.a) * r * 0.4)
        const k = (1 - life) * 0.16
        s.set(k, k, k)
        m.compose(p, q, s)
        mesh.setMatrixAt(i, m)
      }
      mesh.instanceMatrix.needsUpdate = true
    },
  }
}
