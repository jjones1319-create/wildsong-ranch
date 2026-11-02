import type { BufferGeometry, Material, Mesh, Object3D, Texture } from 'three'
import { gpuBytes } from '../perf/content.ts'

/**
 * docs/BATTLE_3D.md §8: a rough count of what the duel holds on the GPU. Textures are collected from the loaded
 * models before their materials are swapped for film materials (node materials hide their textures), so the loader
 * calls `noteTextures` on each glTF scene as it arrives.
 */
export function noteTextures(root: Object3D, into: Set<Texture>): void {
  root.traverse((o) => {
    const m = (o as Mesh).material as Material | Material[] | undefined
    for (const mat of m ? (Array.isArray(m) ? m : [m]) : []) {
      for (const v of Object.values(mat)) if (v && (v as Texture).isTexture) into.add(v as Texture)
    }
  })
}

/** Vertex and index bytes of every geometry under `root`; buffers shared between geometries count once. */
export function geometryBytes(root: Object3D): number {
  const arrays = new Set<{ byteLength: number }>()
  root.traverse((o) => {
    const g = (o as Mesh).geometry as BufferGeometry | undefined
    if (!g) return
    for (const a of Object.values(g.attributes)) arrays.add(a.array as unknown as { byteLength: number })
    if (g.index) arrays.add(g.index.array as unknown as { byteLength: number })
  })
  let n = 0
  for (const a of arrays) n += a.byteLength
  return n
}

/** Megabytes: textures (with mips), geometry, the view's render targets; and Chrome's JS heap when it tells. */
export function memoryMb(textures: Set<Texture>, root: Object3D, targetBytes: number): { gpu: number; heap: number | null } {
  let t = 0
  for (const tex of textures) t += gpuBytes(tex)
  const heap = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory
  return { gpu: (t + geometryBytes(root) + targetBytes) / 2 ** 20, heap: heap ? heap.usedJSHeapSize / 2 ** 20 : null }
}
