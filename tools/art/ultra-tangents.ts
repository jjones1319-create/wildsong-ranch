/**
 * Zero-length tangents (Nov 15): a sliver triangle (a decimation-protection step) can export a tangent of length 0.
 * It is finite, so assertFinite passes it, but one visible zero tangent blanks the review's raw-material frame and can
 * give black bloom frames on renderers without a guard (Bloatoad's builder found one each in six shipped looks).
 * `repairTangents` rebuilds every tangent shorter than TANGENT_MIN: from the UV direction across the triangles around
 * it, made perpendicular to the vertex normal; else from its neighbours' tangents; else any perpendicular to the
 * normal. The w sign (the bitangent's handedness) is kept. NaN and infinite tangents are left alone (assertFinite still
 * refuses them). Used by tools/art/ultra.ts on every Ultra and Lite output and by tools/art/ultra-fix-tangents.ts on
 * shipped files.
 */
import type { Accessor, Document, Primitive } from '@gltf-transform/core'

/** A tangent whose xyz is shorter than this is rebuilt (a real one is unit length; 10-bit quantising keeps it ≥ 0.99). */
export const TANGENT_MIN = 1e-3

type V3 = [number, number, number]

const len = (v: V3) => Math.hypot(v[0], v[1], v[2])
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

/** Any unit vector perpendicular to n. */
export function perpendicular(n: V3): V3 {
  const a: V3 = Math.abs(n[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]
  const d = dot(a, n)
  const t: V3 = [a[0] - n[0] * d, a[1] - n[1] * d, a[2] - n[2] * d]
  const l = len(t)
  return [t[0] / l, t[1] / l, t[2] / l]
}

/**
 * Rebuild the short tangents of one primitive, in place, on plain arrays (positions and normals 3 a vertex, UVs 2 or
 * none, tangents 4, indices or none for a plain triangle list). Returns the vertices it repaired.
 */
export function rebuildTangents(pos: ArrayLike<number>, nrm: ArrayLike<number> | null, uv: ArrayLike<number> | null,
  tan: { length: number; [i: number]: number }, indices: ArrayLike<number> | null, min = TANGENT_MIN): number[] {
  const count = Math.floor(tan.length / 4)
  const bad = new Set<number>()
  for (let i = 0; i < count; i++) {
    const t: V3 = [tan[4 * i]!, tan[4 * i + 1]!, tan[4 * i + 2]!]
    if (t.every(Number.isFinite) && len(t) < min) bad.add(i)
  }
  if (!bad.size) return []
  const fromUv = new Map<number, V3>()
  const fromNbr = new Map<number, { t: V3; w: number }>()
  const P = (i: number): V3 => [pos[3 * i]!, pos[3 * i + 1]!, pos[3 * i + 2]!]
  const tris = indices ? indices.length / 3 : count / 3
  for (let f = 0; f < tris; f++) {
    const vs = indices ? [indices[3 * f]!, indices[3 * f + 1]!, indices[3 * f + 2]!] : [3 * f, 3 * f + 1, 3 * f + 2]
    if (!vs.some((v) => bad.has(v))) continue
    let T: V3 | null = null
    if (uv) {
      const [a, b, c] = vs as [number, number, number]
      const e1 = sub(P(b), P(a))
      const e2 = sub(P(c), P(a))
      const du1 = uv[2 * b]! - uv[2 * a]!, dv1 = uv[2 * b + 1]! - uv[2 * a + 1]!
      const du2 = uv[2 * c]! - uv[2 * a]!, dv2 = uv[2 * c + 1]! - uv[2 * a + 1]!
      const det = du1 * dv2 - du2 * dv1
      if (Math.abs(det) > 1e-12) {
        const t: V3 = [(e1[0] * dv2 - e2[0] * dv1) / det, (e1[1] * dv2 - e2[1] * dv1) / det, (e1[2] * dv2 - e2[2] * dv1) / det]
        const l = len(t)
        if (l > 1e-12 && Number.isFinite(l)) T = [t[0] / l, t[1] / l, t[2] / l]
      }
    }
    for (const v of vs) {
      if (!bad.has(v)) continue
      if (T) {
        const acc = fromUv.get(v) ?? [0, 0, 0]
        fromUv.set(v, [acc[0] + T[0], acc[1] + T[1], acc[2] + T[2]])
      }
      for (const o of vs) {
        if (o === v || bad.has(o)) continue
        const t: V3 = [tan[4 * o]!, tan[4 * o + 1]!, tan[4 * o + 2]!]
        if (!t.every(Number.isFinite)) continue
        const acc = fromNbr.get(v) ?? { t: [0, 0, 0] as V3, w: 0 }
        fromNbr.set(v, { t: [acc.t[0] + t[0], acc.t[1] + t[1], acc.t[2] + t[2]], w: acc.w || Math.sign(tan[4 * o + 3]!) })
      }
    }
  }
  const out: number[] = []
  for (const v of [...bad].sort((a, b) => a - b)) {
    let n: V3 = nrm ? [nrm[3 * v]!, nrm[3 * v + 1]!, nrm[3 * v + 2]!] : [0, 0, 1]
    const nl = len(n)
    n = nl > 1e-6 && Number.isFinite(nl) ? [n[0] / nl, n[1] / nl, n[2] / nl] : [0, 0, 1]
    let t: V3 | null = null
    for (const c of [fromUv.get(v), fromNbr.get(v)?.t]) {
      if (!c) continue
      const d = dot(c, n)
      const o: V3 = [c[0] - n[0] * d, c[1] - n[1] * d, c[2] - n[2] * d]
      const l = len(o)
      if (l > 1e-6) {
        t = [o[0] / l, o[1] / l, o[2] / l]
        break
      }
    }
    t ??= perpendicular(n)
    // keep the w sign; a zero w takes a neighbour's, else +1
    const w0 = tan[4 * v + 3]!
    const w = w0 < 0 ? -1 : w0 > 0 ? 1 : (fromNbr.get(v)?.w || 1)
    tan[4 * v] = t[0]
    tan[4 * v + 1] = t[1]
    tan[4 * v + 2] = t[2]
    tan[4 * v + 3] = w
    out.push(v)
  }
  return out
}

function read(acc: Accessor, size: number): Float64Array {
  const n = acc.getCount()
  const out = new Float64Array(n * size)
  const el: number[] = []
  for (let i = 0; i < n; i++) {
    acc.getElement(i, el)
    for (let k = 0; k < size; k++) out[i * size + k] = el[k] ?? 0
  }
  return out
}

/** Short tangents per mesh (a report: nothing changes). */
export function shortTangents(doc: Document, min = TANGENT_MIN): Record<string, number> {
  const out: Record<string, number> = {}
  const el: number[] = []
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const p of mesh.listPrimitives()) {
      const tan = p.getAttribute('TANGENT')
      if (!tan) continue
      for (let i = 0; i < tan.getCount(); i++) {
        tan.getElement(i, el)
        const t: V3 = [el[0]!, el[1]!, el[2]!]
        if (t.every(Number.isFinite) && len(t) < min) out[mesh.getName()] = (out[mesh.getName()] ?? 0) + 1
      }
    }
  }
  return out
}

function repairPrimitive(p: Primitive, min: number): number {
  const tanAcc = p.getAttribute('TANGENT')
  const posAcc = p.getAttribute('POSITION')
  if (!tanAcc || !posAcc) return 0
  const tan = read(tanAcc, 4)
  const nrmAcc = p.getAttribute('NORMAL')
  const uvAcc = p.getAttribute('TEXCOORD_0')
  const idx = p.getIndices()
  const fixed = rebuildTangents(read(posAcc, 3), nrmAcc ? read(nrmAcc, 3) : null, uvAcc ? read(uvAcc, 2) : null, tan,
    idx ? idx.getArray() : null, min)
  // write back only the repaired elements: every other tangent (and every other accessor) stays as it was
  for (const v of fixed) tanAcc.setElement(v, [tan[4 * v]!, tan[4 * v + 1]!, tan[4 * v + 2]!, tan[4 * v + 3]!])
  return fixed.length
}

/** Rebuild every short tangent in the document; returns the count per mesh (empty when there were none). */
export function repairTangents(doc: Document, min = TANGENT_MIN): Record<string, number> {
  const out: Record<string, number> = {}
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const p of mesh.listPrimitives()) {
      const k = repairPrimitive(p, min)
      if (k) out[mesh.getName()] = (out[mesh.getName()] ?? 0) + k
    }
  }
  return out
}

/** "lo_body 1, lo_props 2" for a log line ('' when nothing was repaired). */
export function describeRepairs(r: Record<string, number>): string {
  return Object.entries(r).map(([m, k]) => `${m} ${k}`).join(', ')
}
