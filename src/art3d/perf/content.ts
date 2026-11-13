import {
  BackSide, Color, DoubleSide, Float32BufferAttribute, FrontSide, ShaderChunk, SphereGeometry, Group, HemisphereLight, DirectionalLight, InstancedMesh, Mesh, MeshBasicMaterial, MeshPhysicalMaterial,
  NoColorSpace, Object3D, PlaneGeometry, Scene, ShadowMaterial, SRGBColorSpace, Texture, TextureLoader, Vector2, Vector3, AdditiveBlending,
  CanvasTexture, Matrix4, Quaternion,
} from 'three'
import type { Camera, WebGLRenderer } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { ART } from '../../data/tuning.ts'

/**
 * Art 2.1 Performance check (docs/ART_2_DETAIL.md §6): what is drawn. The spike's game asset (public/models/perf/) with
 * the film look, built only from standard physical materials and lights so both renderers draw the same thing.
 */

const U = ART.ultra

/** The site root: the check is its own build under /perf/, the models sit with the game's. */
export const SITE = import.meta.env.BASE_URL.replace(/perf\/$/, '')
export const MODELS = `${SITE}models/perf/`

/** A part's film material: fur, eye lenses, fin membranes, fur cards, tuft locks, and props (rigid horns, rope, a bell). */
export type Kind = 'body' | 'eye' | 'fin' | 'card' | 'lock' | 'prop'
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

/** The maps a film material is built from: a part's colour map, and its normal and ORM maps when the file has them. */
export interface FilmTex {
  base: Texture
  normal: Texture | null
  orm: Texture | null
}

/**
 * A part's glow (the sidecar's `glow`; its mask is the ORM map's alpha): how strong, and a tint (linear RGB) or null
 * for the part's own base colour. Only a breed whose sidecar has `glow` gets one (an ORM without alpha can decode as 1).
 */
export interface FilmGlow {
  strength: number
  tint: readonly [number, number, number] | null
}

export interface FilmOptions {
  glow?: FilmGlow | null
  /** A look's own card edge fade (its sidecar's cards.edgeFade), instead of film.cardEdgeFade. */
  cardEdgeFade?: readonly [number, number] | null
  /** A look's own normal-map strength for its body and props (its sidecar's normal.scale), instead of film.normalScale. */
  normalScale?: number | null
  /** A look's own sheen on its body (its sidecar's body.sheen; 0 for stone), instead of film.furSheen. */
  bodySheen?: number | null
}

/** The glow's twinkle: the shared clock (seconds) and amplitude (0 with Reduce motion); setFilmClock each frame. */
export const FILM_TIME = { value: 0 }
export const FILM_TWINKLE = { value: U.film.glow.twinkleAmp as number }

export function setFilmClock(seconds: number, reduceMotion: boolean): void {
  FILM_TIME.value = seconds
  FILM_TWINKLE.value = reduceMotion ? 0 : U.film.glow.twinkleAmp
}

/** The brightness cap of a part (linear luminance, below the bloom threshold): only real glow blooms. */
export function maxLumOf(kind: Kind): number {
  const f = U.film
  return kind === 'fin' ? f.finMaxLum : kind === 'card' ? f.cardMaxLum : f.surfaceMaxLum
}

/**
 * The film material for one kind of part (ART_2_DETAIL §2.4): damp fur, glowing fins, soft cards.
 *
 * Runtime guards (the pilot's in-game review, ART_2_DETAIL §9.2-§9.3, and the first batch):
 * - **only glow blooms:** every part's lit brightness is capped below the bloom threshold (hue kept): fins (the ko
 *   fluke lit face-on by the key and the warm rims glowed white), fur cards (grazing-angle glints along the outline)
 *   and every other surface (Nimbusheep's white wool under the warm rims turned into a glowing peach blob);
 * - **glow:** with `opts.glow`, the ORM map's alpha is an emissive mask (base colour or tint × strength, twinkling
 *   ±`film.glow.twinkleAmp` per texel, still under Reduce motion); it is exempt from the cap, so it blooms;
 * - **hdrMax:** everything, glow included, stays under `film.hdrMax` (a glossy prop's highlight overflowed the
 *   half-float buffers and the bloom blacked out the frame);
 * - fur cards get less specular, and fade in only toward the outline.
 * The WebGPU view rebuilds these rules as node materials (viewGpu.ts); WebGL patches the shader here.
 */
export function filmMaterial(kind: Kind, tex: FilmTex, opts: FilmOptions = {}): MeshPhysicalMaterial {
  const f = U.film
  // the body and the props may take the look's own strength (a scaled hide wants more relief than fur)
  const ns = (kind === 'body' || kind === 'prop') && opts.normalScale ? opts.normalScale : f.normalScale
  const m = new MeshPhysicalMaterial({
    map: tex.base,
    normalMap: tex.normal,
    normalScale: new Vector2(ns, ns),
    aoMap: tex.orm,
    roughnessMap: tex.orm,
    roughness: f.furRoughness,
    metalness: 0,
    clearcoat: kind === 'fin' ? f.finCoat : kind === 'eye' ? f.eyeCoat : kind === 'card' ? 0 : f.furCoat,
    clearcoatRoughness: kind === 'eye' ? 0.05 : f.furCoatRoughness,
    // a prop is the body's material without the fur's sheen (hard horns, rope, a bell)
    // the body may take the look's own (a stone breed: none; absent: film.furSheen, as before)
    sheen: kind === 'fin' || kind === 'eye' || kind === 'prop' ? 0 : kind === 'card' ? f.cardSheen : kind === 'body' && typeof opts.bodySheen === 'number' ? opts.bodySheen : f.furSheen,
    // the sheen in the fur's own colour (each texel's), so it never tints a coat another hue
    sheenColor: new Color(f.sheenGain, f.sheenGain, f.sheenGain),
    sheenColorMap: tex.base,
    sheenRoughness: f.sheenRoughness,
    envMapIntensity: kind === 'eye' ? f.eyeEnv : kind === 'card' ? f.cardEnv : f.envIntensity,
    specularIntensity: kind === 'eye' ? f.eyeSpecular : kind === 'card' ? f.cardSpecular : kind === 'fin' ? f.finSpecular : 1,
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
  // the body's and the props' clearcoat per texel from the ORM map's B channel (matte horns stay matte)
  const coatMask = (kind === 'body' || kind === 'prop') && tex.orm ? f.coatFromOrm : null
  if (coatMask) {
    // any coat > 0 turns three's clearcoat on; the shader then takes the texel's own
    m.clearcoat = 1
    m.userData.coatMask = { gain: coatMask.gain, max: coatMask.max }
  }
  const maxLum = maxLumOf(kind)
  m.userData.maxLum = maxLum
  // no mirrors on a body or a prop: a hoof, pad or nose baked at roughness 0.05 read as chrome (film.minRoughness)
  const minRough = kind === 'body' || kind === 'prop' ? f.minRoughness : 0
  if (minRough > 0) m.userData.minRoughness = minRough
  m.userData.hdrMax = f.hdrMax
  // cards and the tuft read shared strip tiles: they never glow (the pipeline's notes)
  const glow = opts.glow && tex.orm && opts.glow.strength > 0 && kind !== 'card' && kind !== 'lock' ? opts.glow : null
  if (glow) m.userData.glow = { strength: glow.strength, tint: glow.tint }
  let edge: readonly [number, number] | null = null
  if (kind === 'card') {
    m.alphaTest = f.cardAlphaTest
    m.alphaToCoverage = true
    // the views turn coverage off without MSAA (view.ts setCoverage)
    m.userData.a2c = true
    // fins: a card fades out as it turns to face the camera, so cards only show where the coat meets the outline
    // (the WebGPU view rebuilds this as a node material with the same rule, viewGpu.ts)
    edge = opts.cardEdgeFade ?? f.cardEdgeFade
    m.userData.edgeFade = [edge[0], edge[1]]
    m.userData.coverageRamp = [f.cardCoverage[0], f.cardCoverage[1]]
  }
  // cards and the tuft take their colour from the vertex colours over a shared grey-white strip tile: their sheen gets
  // the vertex colour too (the tile alone laid a white veil over green or dark fur), half desaturated
  // (film.cardSheenSat) so a saturated coat doesn't turn into glossy shards
  const sheenByVertex = kind === 'card' || kind === 'lock'
  if (sheenByVertex) m.userData.sheenByVertex = f.cardSheenSat
  const g = f.glow
  m.onBeforeCompile = (sh) => {
    if (sheenByVertex) {
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <lights_physical_fragment>',
        `#include <lights_physical_fragment>
#if defined( USE_SHEEN ) && ( defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) )
  material.sheenColor *= mix( vec3( dot( vColor.rgb, vec3( 0.2126, 0.7152, 0.0722 ) ) ), vColor.rgb, ${f.cardSheenSat.toFixed(3)} );
#endif`,
      )
    }
    if (minRough > 0) {
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
  roughnessFactor = max( roughnessFactor, ${minRough.toFixed(3)} );`,
      )
    }
    if (coatMask) {
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <lights_physical_fragment>',
        `#include <lights_physical_fragment>
#ifdef USE_CLEARCOAT
  material.clearcoat = clamp( texture2D( roughnessMap, vRoughnessMapUv ).b * ${coatMask.gain.toFixed(3)}, 0.0, ${coatMask.max.toFixed(3)} );
#endif`,
      )
    }
    if (edge) {
      // the edge fade, then the strand's alpha: with MSAA it becomes coverage over a soft ramp (tapered tips fade, as in
      // Blender); three's own coverage would cut it hard at alphaTest. Without MSAA, a plain cut (views: setCoverage)
      const [lo, hi] = f.cardCoverage
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <alphatest_fragment>',
        `diffuseColor.a *= smoothstep( ${edge[0].toFixed(3)}, ${edge[1].toFixed(3)}, 1.0 - abs( dot( normalize( vNormal ), normalize( vViewPosition ) ) ) );
#ifdef ALPHA_TO_COVERAGE
  diffuseColor.a = smoothstep( ${lo.toFixed(3)}, ${hi.toFixed(3)}, diffuseColor.a );
  if ( diffuseColor.a <= 0.0 ) discard;
#else
  if ( diffuseColor.a < alphaTest ) discard;
#endif`,
      )
    }
    if (glow) {
      sh.uniforms.filmTime = FILM_TIME
      sh.uniforms.filmTwinkle = FILM_TWINKLE
      sh.uniforms.filmGlowStrength = { value: glow.strength }
      sh.uniforms.filmGlowTint = { value: new Vector3(...(glow.tint ?? [0, 0, 0])) }
      sh.fragmentShader = sh.fragmentShader
        .replace(
          '#include <common>',
          `#include <common>
uniform float filmTime;
uniform float filmTwinkle;
uniform float filmGlowStrength;
uniform vec3 filmGlowTint;`,
        )
        .replace(
          '#include <emissivemap_fragment>',
          `#include <emissivemap_fragment>
// the glow: the ORM map's alpha, twinkling slowly with a phase per texel cell
float filmPhase = fract( sin( dot( floor( vRoughnessMapUv * ${g.cells.toFixed(1)} ), vec2( 12.9898, 78.233 ) ) ) * 43758.5453 ) * 6.2831853;
vec3 filmGlow = ${glow.tint ? 'filmGlowTint' : 'diffuseColor.rgb'} * texture2D( roughnessMap, vRoughnessMapUv ).a * filmGlowStrength
  * ( 1.0 + filmTwinkle * sin( filmTime * ${(g.twinkleHz * 2 * Math.PI).toFixed(4)} + filmPhase ) );
totalEmissiveRadiance += filmGlow;`,
        )
    }
    // the cap on the lit surface (the linear brightness the bloom reads; hue kept), the glow added back on top, and
    // the half-float buffers' ceiling over all of it
    sh.fragmentShader = sh.fragmentShader.replace(
      '#include <opaque_fragment>',
      `{
  vec3 filmGlowPart = ${glow ? 'filmGlow' : 'vec3( 0.0 )'};
  vec3 filmLit = max( outgoingLight - filmGlowPart, vec3( 0.0 ) );
  filmLit *= min( 1.0, ${maxLum.toFixed(3)} / max( dot( filmLit, vec3( 0.2126, 0.7152, 0.0722 ) ), 1e-4 ) );
  outgoingLight = min( filmLit + filmGlowPart, vec3( ${f.hdrMax.toFixed(1)} ) );
}
#include <opaque_fragment>`,
    )
  }
  m.customProgramCacheKey = () => `film-${kind}-r${minRough}-${edge ? `fade${edge[0]}_${edge[1]}` : ''}-${maxLum}-${f.hdrMax}-${glow ? (glow.tint ? 'glow-tint' : 'glow') : ''}-${coatMask ? `coat${coatMask.gain}-${coatMask.max}` : ''}-${edge ? f.cardCoverage.join('_') : ''}`
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

export interface Studio { key: DirectionalLight; rim: DirectionalLight; rim2: DirectionalLight; hemi: HemisphereLight; ground: Mesh }

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
  const rim2 = new DirectionalLight(s.rim2.color, s.rim2.intensity)
  rim2.position.copy(dirFrom(s.rim2.azDeg, s.rim2.elDeg).multiplyScalar(reach * 4)).add(focus)
  rim2.target.position.copy(focus)
  const hemi = new HemisphereLight(s.sky, s.ground, s.hemi)
  const ground = new Mesh(new PlaneGeometry(reach * 8, reach * 8), new ShadowMaterial({ opacity: 0.22 }))
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  ground.userData.isHelper = true
  scene.add(key, key.target, rim, rim.target, rim2, rim2.target, hemi, ground)
  return { key, rim, rim2, hemi, ground }
}

/**
 * The rims light the subject's outline from behind as the camera sees it. Seen from behind (Battle 3D's behind camera,
 * a back view in the review) they faced the camera and lit the whole back at about 2.7 times the key: a flat, pale
 * plaster, dark wool turned pale grey (Nov 13). So each rim dims as the camera comes round to its side
 * (studio.rimFacing: full while the rim is behind the subject, which every front and three-quarter view keeps, down to
 * minPct of itself when it faces the camera). Horizontal directions from `focus`; call it whenever the camera moves.
 */
export function aimStudioRims(studio: Pick<Studio, 'rim' | 'rim2'>, eye: Vector3, focus: Vector3): void {
  const F = U.studio.rimFacing
  const cx = eye.x - focus.x
  const cz = eye.z - focus.z
  const cl = Math.hypot(cx, cz) || 1
  for (const [light, base] of [
    [studio.rim, U.studio.rim.intensity],
    [studio.rim2, U.studio.rim2.intensity],
  ] as const) {
    const lx = light.position.x - light.target.position.x
    const lz = light.position.z - light.target.position.z
    const d = (lx * cx + lz * cz) / ((Math.hypot(lx, lz) || 1) * cl)
    const t = Math.min(1, Math.max(0, (d - F.fromDot) / (F.toDot - F.fromDot)))
    const k = t * t * (3 - 2 * t)
    light.intensity = base * (1 - k * (1 - F.minPct / 100))
  }
}

/**
 * The film's world for reflections and room light (no files; prefiltered by the renderer): the Blender sheets' soft
 * grey dome, a touch darker below the horizon (ART.ultra.studio.world). It replaced three's RoomEnvironment, whose
 * white light panels turned every near-mirror texel into chrome or glass.
 */
export function studioEnvironmentScene(): Scene {
  const W = U.studio.world
  const scene = new Scene()
  const g = new SphereGeometry(50, 48, 24)
  const pos = g.getAttribute('position')
  const col: number[] = []
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / 50
    const k = W.strength * (y > 0 ? 1 : W.groundPct / 100 + (1 - W.groundPct / 100) * (1 + y))
    col.push(W.rgb[0] * k, W.rgb[1] * k, W.rgb[2] * k)
  }
  g.setAttribute('color', new Float32BufferAttribute(col, 3))
  scene.add(new Mesh(g, new MeshBasicMaterial({ vertexColors: true, side: BackSide })))
  return scene
}

/** The old name (the Performance check and the views call it). */
export const roomEnvironmentScene = studioEnvironmentScene

/**
 * The film tone map, GLSL (renderers set CustomToneMapping after installFilmToneMapping): three's Neutral, except that
 * its toe scales a dark colour (hue and saturation kept) instead of lowering every channel by one amount, blending into
 * Neutral's own between post.toeKeep's peaks (ART.ultra.post.toeKeep).
 */
export function filmToneGlsl(): string {
  const [lo, hi] = U.post.toeKeep
  return `vec3 CustomToneMapping( vec3 color ) {
  const float StartCompression = 0.8 - 0.04;
  const float Desaturation = 0.15;
  color *= toneMappingExposure;
  float x = min( color.r, min( color.g, color.b ) );
  float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  float pk = max( color.r, max( color.g, color.b ) );
  vec3 kept = color * max( pk - offset, 0.0 ) / max( pk, 1e-5 );
  color = mix( kept, color - offset, smoothstep( ${lo.toFixed(3)}, ${hi.toFixed(3)}, pk ) );
  float peak = max( color.r, max( color.g, color.b ) );
  if ( peak < StartCompression ) return color;
  float d = 1. - StartCompression;
  float newPeak = 1. - d * d / ( peak + d - StartCompression );
  color *= newPeak / peak;
  float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
  return mix( color, vec3( newPeak ), g );
}`
}

let filmToneInstalled = false

/** Put the film tone map in three's CustomToneMapping slot (once; WebGL shaders and the OutputPass read it). */
export function installFilmToneMapping(): void {
  if (filmToneInstalled) return
  const stub = 'vec3 CustomToneMapping( vec3 color ) { return color; }'
  const chunk = ShaderChunk as unknown as Record<string, string>
  if (chunk.tonemapping_pars_fragment?.includes(stub)) chunk.tonemapping_pars_fragment = chunk.tonemapping_pars_fragment.replace(stub, filmToneGlsl())
  filmToneInstalled = true
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
