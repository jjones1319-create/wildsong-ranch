/**
 * Art 2.1: UV overlap check for an Ultra look's meshes. Two faces whose UVs cover the same texels bake into the same
 * pixels (Tumblefox's belly and left front sock shared ~2.4k texels at 2048²: a cream/plum checker in every variant).
 *
 *   node tools/art/ultra-uv.ts <breed…> [--size 2048] [--shipped]
 *
 * Reads the raw Blender export (tools/blender/out/<breed>-ultra/<breed>-ultra.glb: float UVs, the geometry that
 * ships; --shipped reads public/models/monsters-ultra/<breed>.glb instead: quantised, meshopt-compressed) and counts,
 * per mesh, the texel centres two different triangles claim. tools/art/ultra.ts warns at ship time;
 * build_ultra.py repairs overlaps when it packs (lib/bake.py _repair_overlaps) and stops in words if any are left.
 */
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { NodeIO, type Accessor } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { MeshoptDecoder } from 'meshoptimizer'
import { fileURLToPath } from 'node:url'

const ROOT = join(fileURLToPath(import.meta.url), '..', '..', '..')

export interface UvOverlap { mesh: string; texels: number; triangles: number }

/** Texels two faces may share before it matters (a 2048 grid; slivers touching make a handful): build_ultra's UV_OVERLAP_MAX. */
export const UV_OVERLAP_MAX = 32

/**
 * Texel centres (a size × size grid over UV 0..1) claimed by two different triangles. Adjacent triangles of one island
 * never share a centre, so any count above a few is a real overlap.
 */
export function overlapTexels(uv: ArrayLike<number>, index: ArrayLike<number>, size = 2048): { texels: number; triangles: number } {
  const owner = new Int32Array(size * size).fill(-1)
  const hit = new Uint8Array(size * size)
  const bad = new Set<number>()
  let texels = 0
  for (let t = 0; t < index.length / 3; t++) {
    const a = index[3 * t]!, b = index[3 * t + 1]!, c = index[3 * t + 2]!
    const x0 = uv[2 * a]! * size, y0 = uv[2 * a + 1]! * size
    const x1 = uv[2 * b]! * size, y1 = uv[2 * b + 1]! * size
    const x2 = uv[2 * c]! * size, y2 = uv[2 * c + 1]! * size
    const area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if (Math.abs(area) < 1e-9) continue
    const s = area > 0 ? 1 : -1
    const minX = Math.max(0, Math.floor(Math.min(x0, x1, x2))), maxX = Math.min(size - 1, Math.ceil(Math.max(x0, x1, x2)))
    const minY = Math.max(0, Math.floor(Math.min(y0, y1, y2))), maxY = Math.min(size - 1, Math.ceil(Math.max(y0, y1, y2)))
    for (let y = minY; y <= maxY; y++) {
      const py = y + 0.5
      for (let x = minX; x <= maxX; x++) {
        const px = x + 0.5
        const w0 = s * ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py))
        const w1 = s * ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py))
        const w2 = s * ((x0 - px) * (y1 - py) - (x1 - px) * (y0 - py))
        if (w0 <= 0 || w1 <= 0 || w2 <= 0) continue
        const k = y * size + x
        if (owner[k]! >= 0 && owner[k] !== t) {
          if (!hit[k]) {
            hit[k] = 1
            texels++
          }
          bad.add(t)
          bad.add(owner[k]!)
        }
        owner[k] = t
      }
    }
  }
  return { texels, triangles: bad.size }
}

/** An accessor's values as floats (a quantised one denormalised, as a renderer reads it). */
function floats(a: Accessor): ArrayLike<number> {
  const arr = a.getArray()!
  if (!a.getNormalized() && arr instanceof Float32Array) return arr
  const n = a.getCount(), k = a.getElementSize(), out = new Float32Array(n * k), el: number[] = []
  for (let i = 0; i < n; i++) {
    a.getElement(i, el)
    for (let j = 0; j < k; j++) out[i * k + j] = el[j]!
  }
  return out
}

/** Every lo_* mesh of a .glb (a raw Blender export or a shipped look): its UV overlap (TEXCOORD_0, triangles). */
export async function lookOverlaps(glbPath: string, size = 2048): Promise<UvOverlap[]> {
  await MeshoptDecoder.ready
  const doc = await new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder }).read(glbPath)
  const out: UvOverlap[] = []
  for (const mesh of doc.getRoot().listMeshes()) {
    const name = mesh.getName()
    if (!name.startsWith('lo_') || name.startsWith('lo_cards') || name.startsWith('lo_tuft')) continue     // cards and the tuft share strip tiles by design
    for (const p of mesh.listPrimitives()) {
      const acc = p.getAttribute('TEXCOORD_0')
      const idx = p.getIndices()?.getArray()
      if (!acc || !idx) continue
      out.push({ mesh: name, ...overlapTexels(floats(acc), idx, size) })
    }
  }
  return out
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const args = process.argv.slice(2)
  const at = args.indexOf('--size')
  const size = at >= 0 ? Number(args[at + 1]) : 2048
  const breeds = args.filter((a, i) => !a.startsWith('--') && (at < 0 || i !== at + 1))
  const shipped = args.includes('--shipped')
  for (const b of breeds) {
    const glb = shipped ? join(ROOT, 'public', 'models', 'monsters-ultra', `${b}.glb`) : join(ROOT, 'tools', 'blender', 'out', `${b}-ultra`, `${b}-ultra.glb`)
    if (!existsSync(glb)) {
      console.log(`${b}: no ${glb}`)
      continue
    }
    const rows = await lookOverlaps(glb, size)
    console.log(`${b}: ${rows.map((r) => `${r.mesh} ${r.texels} texels (${r.triangles} triangles)`).join(', ')}`)
  }
}
