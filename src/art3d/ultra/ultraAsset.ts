import { AnimationClip, Box3, BufferGeometry, Mesh, MeshStandardMaterial, Object3D, Texture } from 'three'
import type { Material } from 'three'
import type { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js'
import { buildTagOf, ULTRA_LOOKS, ultraLook, versionedUrl, type UltraId, type UltraLook } from '../../art/ultraLooks.ts'
import type { BreedId } from '../../data/types.ts'
import { filmMaterial } from '../perf/content.ts'
import { ART } from '../../data/tuning.ts'
import { cardEdgeFadeOf, glowOf, normalScaleOf, partKind, partVisible, softFinsOf, variantOfPart } from './parts.ts'


/**
 * Art 2.1 Ultra models at runtime (docs/ART_2_DETAIL.md §3.4; Battle 3D and the Lab → 3D Gallery): load a registry
 * breed's file (or its Lite one), then make posed copies with the film materials, the variant's colours, the shadow
 * and AO layers the film renderer expects, fitted to a height in metres and measured for the cameras.
 */

const BASE = import.meta.env.BASE_URL

/** What the copy is drawn from: the Ultra file, its Lite file, or Puddlepup's Art 2.0 file. */
export type UltraKind = 'ultra' | 'ultra-lite' | 'art2'

/** The parts of a sidecar the runtime reads (tools/art/ultra.ts writes it; anything may be missing). */
export interface UltraMeta {
  heightUnits?: number
  clips?: Record<string, { loop?: boolean; hold?: boolean; seconds?: number; rootSpeed?: number; markers?: { name: string; t: number }[] }>
  /** Each variant's colour holder, its cards' colour set, and its own props (`lo_props_<short>`, hidden on other looks). */
  variants?: Record<string, { holder?: string; colorAttribute?: string; meshes?: string[] }>
  /** Mesh name → part kind (`lo_cards: "card"`). */
  meshes?: Record<string, string>
  face?: { blinkClip?: string }
  /** Present only when the breed glows: the ORM map's alpha × strength, on the base colour or the tint (parts.ts glowOf). */
  glow?: unknown
  /** `{ soft: true }`: the fins take received shadows (parts.ts softFinsOf). */
  fins?: unknown
  /** `{ edgeFade: [lo, hi] }`: where this look's fur cards fade in (parts.ts cardEdgeFadeOf). */
  cards?: unknown
  /** `{ scale }`: the body's and props' normal-map strength (parts.ts normalScaleOf). */
  normal?: unknown
  /** The 10-hex sha1 of the .glb (older sidecars: an object of build statistics). */
  build?: unknown
  /** The Lite copy (tools/art/ultra.ts): its file beside this one and its own build tag. */
  lite?: { file?: unknown; build?: unknown }
}

export interface UltraAsset {
  /** The look it is (a breed, or a grown form) and its breed. */
  look: UltraId
  breed: BreedId
  scene: Object3D
  clips: AnimationClip[]
  meta: UltraMeta | null
  kind: UltraKind
}

/**
 * The layer of what the AO pass must not see (its camera leaves it out, perf/view.ts): the fur cards' alpha-tested
 * quads, and in Battle 3D the soft contact shadows, floor telegraphs and effect quads (drawn whole in the AO's
 * normal pass, they darkened or lightened squares round the monsters). Main cameras enable it.
 */
export const NO_AO_LAYER = 1

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    // revalidated every time (a re-shipped model must update; the service worker serves it network-first)
    const r = await fetch(url, { cache: 'no-cache' })
    return r.ok ? ((await r.json()) as T) : null
  } catch {
    return null
  }
}

const DIR = (path: string) => path.slice(0, path.lastIndexOf('/') + 1)

/** The Ultra file, versioned by its sidecar's build tag (a re-shipped model gets a new URL, so a cached phone refetches it). */
async function loadUltra(loader: GLTFLoader, look: UltraLook, meta: UltraMeta): Promise<UltraAsset> {
  const gltf = await loader.loadAsync(versionedUrl(`${BASE}${look.glb}`, buildTagOf(meta)))
  return { look: look.id, breed: look.breed, scene: gltf.scene, clips: gltf.animations, meta, kind: 'ultra' }
}

/** The Lite copy: the file the sidecar's `lite` entry names (with its own build tag), else the registry's. */
async function loadLite(loader: GLTFLoader, look: UltraLook, meta: UltraMeta | null): Promise<UltraAsset> {
  const named = typeof meta?.lite?.file === 'string' && /^[\w.-]+\.glb$/.test(meta.lite.file) ? `${DIR(look.glb)}${meta.lite.file}` : look.lite.glb
  const tag = buildTagOf({ build: meta?.lite?.build }) ?? buildTagOf(meta)
  const gltf = await loader.loadAsync(versionedUrl(`${BASE}${named}`, tag))
  return { look: look.id, breed: look.breed, scene: gltf.scene, clips: gltf.animations, meta, kind: 'ultra-lite' }
}

/** The older model a registry breed falls back to when its Ultra files can't load (Puddlepup's Art 2.0 one). */
async function loadFallback(loader: GLTFLoader, look: UltraLook): Promise<UltraAsset> {
  if (!look.fallback) throw new Error(`${look.breed}: no fallback model`)
  const [gltf, meta] = await Promise.all([loader.loadAsync(`${BASE}${look.fallback.glb}`), fetchJson<UltraMeta>(`${BASE}${look.fallback.meta}`)])
  return { look: look.id, breed: look.breed, scene: gltf.scene, clips: gltf.animations, meta, kind: 'art2' }
}

/**
 * A registry look's model (a breed, or a grown form): the Ultra file, or with `lite` its Lite copy (the Ultra file if
 * it has none); either way its fallback model (Puddlepup's Art 2.0 one) if neither loads. A look outside the registry
 * loads Puddlepup.
 * The sidecar comes first (revalidated every time) for the build tags.
 */
export async function loadUltraAsset(loader: GLTFLoader, id: UltraId, lite: boolean): Promise<UltraAsset> {
  const look = ultraLook(id) ?? ULTRA_LOOKS.puddlepup!
  const meta = await fetchJson<UltraMeta>(`${BASE}${look.meta}`)
  try {
    if (!meta) throw new Error(`${look.meta} is missing`)
    if (lite) {
      try {
        return await loadLite(loader, look, meta)
      } catch {
        /* no Lite copy: the full one */
      }
    }
    return await loadUltra(loader, look, meta)
  } catch (err) {
    if (look.fallback) return loadFallback(loader, look)
    throw err
  }
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

/** A copy's measurements in metres once fitted: its height, how far its nose and tail reach from its feet, its width. */
export interface UltraSize {
  height: number
  front: number
  back: number
  width: number
}

export interface UltraModel {
  /** The copy, scaled and standing on y = 0, facing +z. */
  model: Object3D
  /** Model metres → metres. */
  scale: number
  size: UltraSize
  /** Clip root speeds in metres per second (the file's, scaled like the model). */
  rootSpeed: Record<string, number>
  /** Seconds into a clip at its `impact` or `release` marker. */
  impactAt: Record<string, number>
  /** The materials made for this copy (dispose them with it). */
  materials: Material[]
}

/** The variant an object belongs to only (itself or a parent group, up to the model's root), or null. */
function ownerOf(o: Object3D, root: Object3D, variants: UltraMeta['variants']): string | null {
  for (let p: Object3D | null = o; p && p !== root; p = p.parent) {
    const v = variantOfPart(p.name, variants)
    if (v !== null) return v
  }
  return null
}

/**
 * A posed copy of a loaded model for one fighter or one Gallery stand, `heightM` tall at its top: the variant holders
 * hidden, a variant's own props (`lo_props_<short>`) shown only with that variant, the Ultra parts in the film
 * materials (the variant's colour map on all but the eyes; its cards and tufts reading the variant's vertex colours),
 * cards on the AO-free layer and out of the shadows, fins out of the received shadows (as tools/art/ultra-viewer draws
 * them).
 */
export function makeUltraModel(asset: UltraAsset, variant: string | null, heightM: number): UltraModel {
  const model = cloneSkinned(asset.scene)
  const variantMap = new Map<string, Texture>()
  const film = asset.kind !== 'art2'
  const variants = asset.meta?.variants
  /** Parts one variant wears (a bell, a ribbon): left out of the measuring, so every look stands the same height. */
  const own = new Set<Object3D>()
  model.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh) return
    m.frustumCulled = false
    // each variant's colour map rides on a hidden mesh named __variant_<id>
    const vm = /^__variant_(.+)$/.exec(m.name)
    if (vm) {
      const map = (m.material as MeshStandardMaterial).map
      if (map) variantMap.set(vm[1]!, map)
      m.visible = false
      return
    }
    const owner = ownerOf(m, model, variants)
    if (owner !== null) {
      own.add(m)
      m.visible = partVisible(m.name, variant, variants) && owner === variant
    }
    m.castShadow = true
  })
  // fit to heightM at the top, standing on y = 0. Only the visible, always-worn parts count: the variant holders sit
  // half a metre below the feet, and counting them floated every monster off the floor
  model.updateMatrixWorld(true)
  const box = new Box3()
  model.traverse((o) => {
    if ((o as Mesh).isMesh && o.visible && !own.has(o)) box.union(new Box3().setFromObject(o))
  })
  if (box.isEmpty()) {
    box.min.set(-0.3, 0, -0.5)
    box.max.set(0.3, 1, 0.5)
  }
  const h = Math.max(0.01, box.max.y - box.min.y)
  const scale = heightM / h
  model.scale.setScalar(scale)
  model.position.y = -box.min.y * scale
  const size: UltraSize = { height: heightM, front: Math.max(0.05, box.max.z * scale), back: Math.max(0.05, -box.min.z * scale), width: Math.max(0.05, (box.max.x - box.min.x) * scale) }
  const variantBase = variant ? (variantMap.get(variant) ?? null) : null
  const colourSet = (variant ? asset.meta?.variants?.[variant]?.colorAttribute : undefined)?.toLowerCase() ?? 'color_1'
  // the glow channel, only when the sidecar says the breed glows (an ORM map without alpha can decode as 1)
  const glow = glowOf(asset.meta, ART.ultra.film.glow.maxStrength)
  const softFins = softFinsOf(asset.meta)
  const cardEdgeFade = cardEdgeFadeOf(asset.meta)
  const normalScale = normalScaleOf(asset.meta)
  const materials: Material[] = []
  model.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh || !m.visible) return
    const mat = m.material as MeshStandardMaterial
    if (film) {
      // Art 2.1: the film materials (ART_2_DETAIL §3.4), rebuilt from the file's own maps by part, so the cards get
      // their edge fade and the eyes their own gloss; glTF can't carry those
      const kind = partKind(m.name, asset.meta?.meshes)
      if (!kind || !mat?.map) return
      const base = variantBase && kind !== 'eye' ? variantBase : mat.map
      const made = filmMaterial(kind, { base, normal: mat.normalMap ?? null, orm: mat.roughnessMap ?? mat.aoMap ?? null }, { glow, cardEdgeFade, normalScale })
      m.material = made
      materials.push(made)
      // a variant's cards and tufts take their colour from the second vertex-colour set (the model's notes)
      if (variantBase && (kind === 'card' || kind === 'lock') && m.geometry.getAttribute(colourSet)) m.geometry = withColourSet(m.geometry, colourSet)
      // fur cards lie a few millimetres over the coat: their shadows read as holes in it, and the AO pass can't cut
      // them out (it would darken their whole quads); a fin is a thin lit membrane, the head's shadow on it smudged
      m.castShadow = kind !== 'card'
      m.receiveShadow = kind !== 'fin' || softFins
      if (kind === 'card') m.layers.set(NO_AO_LAYER)
    } else if (variantBase && mat?.map && !/eye|face/i.test(m.name)) {
      const c = mat.clone()
      c.map = variantBase
      m.material = c
      materials.push(c)
    }
  })
  const rootSpeed: Record<string, number> = {}
  const impactAt: Record<string, number> = {}
  for (const [name, c] of Object.entries(asset.meta?.clips ?? {})) {
    // the file's root speeds are in the model's metres: scale them like the model
    rootSpeed[name] = (c.rootSpeed ?? 0) * scale
    const imp = c.markers?.find((mk) => mk.name === 'impact' || mk.name === 'release')
    if (imp) impactAt[name] = imp.t
  }
  return { model, scale, size, rootSpeed, impactAt, materials }
}

/** The variants this loaded file really holds (a hidden __variant_<id> mesh each). */
export function heldVariants(asset: UltraAsset): string[] {
  const out: string[] = []
  asset.scene.traverse((o) => {
    const vm = /^__variant_(.+)$/.exec(o.name)
    if (vm && (o as Mesh).isMesh) out.push(vm[1]!)
  })
  return out
}

/** The blink clip's name in this file, if it has one (it keys only the lids, so it plays over any clip). */
export function blinkClipOf(asset: UltraAsset): string | null {
  const name = asset.meta?.face?.blinkClip ?? 'blink'
  return asset.clips.some((c) => c.name === name) ? name : null
}
