import { AnimationClip, Bone, Group, Mesh, MeshStandardMaterial, Object3D, SkinnedMesh, Texture } from 'three'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { clone as cloneSkeleton } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { MODEL_LOOKS, type LookId } from '../art/models.ts'
import { ART } from '../data/tuning.ts'
import type { LookSidecar } from './types.ts'

/**
 * Loads a look once (its .glb and sidecar .json), keeps it while something uses it, and hands out clones
 * (ART_2_PLAN §3.2 loader and cache). Failures are remembered briefly so a screen doesn't hammer a 404.
 */

export interface LookAsset {
  id: LookId
  scene: Group
  animations: AnimationClip[]
  meta: LookSidecar
  /** The base colour and each variant's texture, by the sidecar's names. */
  textures: Map<string, Texture>
  faceSheet: Texture | null
  bytes: number
}

export interface LookInstance {
  root: Object3D
  body: SkinnedMesh
  faces: Map<string, Mesh>
  sockets: Map<string, Object3D>
  bones: Map<string, Bone>
}

const loader = new GLTFLoader()
loader.setMeshoptDecoder(MeshoptDecoder)

const cache = new Map<LookId, Promise<LookAsset>>()
const refs = new Map<LookId, number>()
const failedAt = new Map<LookId, number>()
const idleTimers = new Map<LookId, ReturnType<typeof setTimeout>>()

function url(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`
}

export function loadLook(id: LookId): Promise<LookAsset> {
  const cached = cache.get(id)
  if (cached) return cached
  const failed = failedAt.get(id)
  if (failed !== undefined && Date.now() - failed < ART.stage.retryMs) return Promise.reject(new Error(`look ${id} failed recently`))
  const look = MODEL_LOOKS[id]
  const p = (async () => {
    const [meta, gltf] = await Promise.all([
      fetch(url(look.meta)).then((r) => {
        if (!r.ok) throw new Error(`${look.meta}: ${r.status}`)
        return r.json() as Promise<LookSidecar>
      }),
      loader.loadAsync(url(look.file)),
    ])
    const textures = new Map<string, Texture>()
    let faceSheet: Texture | null = null
    let bytes = 0
    gltf.scene.traverse((o) => {
      const m = o as Mesh
      if (!m.isMesh) return
      const mat = m.material as MeshStandardMaterial
      const map = mat?.map
      if (!map) return
      if (m.name.startsWith('__variant_')) {
        textures.set(m.name.replace('__variant_', ''), map)
        m.visible = false
      } else if (m.name.startsWith('face_')) {
        faceSheet ??= map
      } else if (m instanceof SkinnedMesh || (m as SkinnedMesh).isSkinnedMesh) {
        textures.set('base', map)
      }
    })
    for (const t of textures.values()) t.anisotropy = 4
    if (faceSheet) {
      const fs = faceSheet as Texture
      fs.anisotropy = 4
      fs.generateMipmaps = true
    }
    bytes = (meta.budget as { bytes?: number } | undefined)?.bytes ?? 0
    return { id, scene: gltf.scene, animations: gltf.animations, meta, textures, faceSheet, bytes }
  })()
  cache.set(id, p)
  p.catch(() => {
    cache.delete(id)
    failedAt.set(id, Date.now())
  })
  return p
}

/** Count a user; the asset stays loaded while the count is above zero (and a grace period after). */
export function acquireLook(id: LookId): void {
  refs.set(id, (refs.get(id) ?? 0) + 1)
  const t = idleTimers.get(id)
  if (t) {
    clearTimeout(t)
    idleTimers.delete(id)
  }
}

export function releaseLook(id: LookId): void {
  const n = (refs.get(id) ?? 1) - 1
  refs.set(id, Math.max(0, n))
  if (n <= 0) {
    const t = setTimeout(() => {
      idleTimers.delete(id)
      if ((refs.get(id) ?? 0) === 0) disposeLook(id)
    }, ART.stage.idleReleaseMs)
    idleTimers.set(id, t)
  }
}

export function disposeLook(id: LookId): void {
  const p = cache.get(id)
  cache.delete(id)
  if (!p) return
  void p.then((asset) => {
    asset.scene.traverse((o) => {
      const m = o as Mesh
      if (m.isMesh) {
        m.geometry.dispose()
        const mats = Array.isArray(m.material) ? m.material : [m.material]
        for (const mat of mats) (mat as MeshStandardMaterial).dispose()
      }
    })
    for (const t of asset.textures.values()) t.dispose()
    asset.faceSheet?.dispose()
  }, () => undefined)
}

export function disposeAllLooks(): void {
  for (const id of [...cache.keys()]) disposeLook(id)
}

/**
 * GLTFLoader strips dots, colons, slashes and brackets from node names (`face_white.L` → `face_whiteL`,
 * `ear.L.1` → `earL1`), so every lookup goes through the same rule.
 */
export function nodeName(name: string): string {
  return name.replace(/\s/g, '_').replace(/[\[\].:/]/g, '')
}

/** A fresh scene-graph copy with its own skeleton; materials are replaced by the actor, so they're not cloned.
 *  The maps are keyed by the sidecar's names (with dots), looked up through `nodeName`. */
export function instantiate(asset: LookAsset): LookInstance {
  const root = cloneSkeleton(asset.scene) as Object3D
  let body: SkinnedMesh | null = null
  const faces = new Map<string, Mesh>()
  const sockets = new Map<string, Object3D>()
  const bones = new Map<string, Bone>()
  const byNode = new Map<string, Object3D>()
  root.traverse((o) => {
    byNode.set(o.name, o)
    if ((o as Bone).isBone) bones.set(o.name, o as Bone)
    if (o.name.startsWith('socket_')) sockets.set(o.name, o)
    const m = o as Mesh
    if (!m.isMesh) return
    if (m.name.startsWith('__variant_')) {
      m.visible = false
      return
    }
    if (m.name.startsWith('face_')) {
      faces.set(m.name.slice('face_'.length), m)
      return
    }
    if ((m as SkinnedMesh).isSkinnedMesh) body = m as SkinnedMesh
  })
  if (!body) throw new Error(`look ${asset.id}: no skinned body in the file`)
  // re-key by the sidecar's names, so `faces.get('white.L')` and `bones.get('ear.L.1')` work
  for (const layer of asset.meta.face.layers) {
    const m = faces.get(nodeName(layer))
    if (m) faces.set(layer, m)
  }
  const wanted = new Set<string>([...Object.values(asset.meta.bones), ...asset.meta.springs.flatMap((s) => s.chain)])
  for (const name of wanted) {
    const b = bones.get(nodeName(name))
    if (b) bones.set(name, b)
  }
  for (const s of Object.keys(asset.meta.sockets)) {
    const o = byNode.get(nodeName(s))
    if (o) sockets.set(s, o)
  }
  return { root, body, faces, sockets, bones }
}
