import { existsSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { MODEL_LOOKS, MODELS } from '../art/models.ts'
import { BREED_BY_ID } from '../data/breeds.ts'
import { SECRET_BY_ID } from '../data/secrets.ts'
import { FACES, SOCKETS, STAR_CLIPS, type LookSidecar } from './types.ts'

/**
 * ART_2_PLAN §3.6 budgets and §5 clip contract, checked on the shipped files in public/models/monsters/.
 * The GLB's JSON chunk is parsed here directly (no three), so the test runs in plain Node.
 */

const BUDGET = { bytes: 700 * 1024, triangles: 12_000, joints: 64, texturePx: 1024, facePx: 512, variantBytes: 250 * 1024 }

interface GltfJson {
  nodes?: { name?: string; mesh?: number; skin?: number }[]
  meshes?: { name?: string; primitives: { indices?: number; mode?: number; attributes: Record<string, number> }[] }[]
  accessors?: { count: number }[]
  animations?: { name?: string }[]
  skins?: { joints: number[] }[]
  images?: { mimeType?: string; name?: string }[]
  extensionsUsed?: string[]
}

function glbJson(path: string): GltfJson {
  const buf = readFileSync(path)
  expect(buf.readUInt32LE(0)).toBe(0x46546c67) // 'glTF'
  expect(buf.readUInt32LE(4)).toBe(2)
  const len = buf.readUInt32LE(12)
  expect(buf.readUInt32LE(16)).toBe(0x4e4f534a) // JSON chunk
  return JSON.parse(buf.subarray(20, 20 + len).toString('utf8')) as GltfJson
}

function triangles(g: GltfJson): number {
  let n = 0
  for (const m of g.meshes ?? []) {
    for (const p of m.primitives) {
      const mode = p.mode ?? 4
      if (mode !== 4) continue
      const count = p.indices !== undefined ? g.accessors![p.indices]!.count : g.accessors![p.attributes.POSITION!]!.count
      n += count / 3
    }
  }
  return n
}

describe('shipped models (ART_2_PLAN §3.6, §5)', () => {
  const looks = Object.entries(MODEL_LOOKS)

  it('every registered look has its files and the sidecar matches the registry', () => {
    for (const [id, look] of looks) {
      const glb = join('public', look.file)
      const json = join('public', look.meta)
      expect(existsSync(glb), `${glb} exists`).toBe(true)
      expect(existsSync(json), `${json} exists`).toBe(true)
      const side = JSON.parse(readFileSync(json, 'utf8')) as LookSidecar
      expect(side.look).toBe(id)
      expect(side.heightUnits).toBe(look.unitsPerMetre)
      for (const v of look.variants) {
        expect(side.variants[v], `${id} ships variant ${v}`).toBeDefined()
        expect(SECRET_BY_ID[v]?.breed).toBeDefined()
      }
      for (const [breed, m] of Object.entries(MODELS)) {
        if (m.young === id || m.grown === id) expect(BREED_BY_ID[breed as keyof typeof BREED_BY_ID].art.plan).toBe(side.plan)
      }
    }
  })

  it('keeps every budget: bytes, triangles, joints, textures', () => {
    for (const [id, look] of looks) {
      const glb = join('public', look.file)
      const side = JSON.parse(readFileSync(join('public', look.meta), 'utf8')) as LookSidecar
      const bytes = statSync(glb).size
      expect(bytes, `${id} bytes`).toBeLessThanOrEqual(BUDGET.bytes)
      expect(side.budget, `${id} sidecar has the optimiser's report`).toBeDefined()
      expect(side.budget!.bytes).toBe(bytes)
      const g = glbJson(glb)
      const tris = triangles(g)
      expect(tris, `${id} triangles`).toBeLessThanOrEqual(BUDGET.triangles)
      expect(side.budget!.triangles).toBe(tris)
      const joints = Math.max(0, ...(g.skins ?? []).map((s) => s.joints.length))
      expect(joints, `${id} joints`).toBeLessThanOrEqual(BUDGET.joints)
      expect(joints).toBeGreaterThan(0)
      for (const img of g.images ?? []) expect(img.mimeType, `${id} image ${img.name}`).toBe('image/webp')
      for (const t of side.budget!.textures) {
        const cap = /face/i.test(t.name) ? BUDGET.facePx : BUDGET.texturePx
        expect(Math.max(t.width, t.height), `${id} texture ${t.name}`).toBeLessThanOrEqual(cap)
        if (Object.keys(side.variants).some((v) => t.name.includes(v))) expect(t.bytes, `${id} variant texture ${t.name}`).toBeLessThanOrEqual(BUDGET.variantBytes)
      }
      expect(g.extensionsUsed ?? []).toContain('EXT_meshopt_compression')
    }
  })

  it('has every ★ clip, with metadata, and every socket', () => {
    for (const [id, look] of looks) {
      const g = glbJson(join('public', look.file))
      const side = JSON.parse(readFileSync(join('public', look.meta), 'utf8')) as LookSidecar
      const names = new Set((g.animations ?? []).map((a) => a.name))
      for (const c of STAR_CLIPS) {
        expect(names.has(c), `${id} clip ${c} in the file`).toBe(true)
        const m = side.clips[c]
        expect(m, `${id} clip ${c} metadata`).toBeDefined()
        expect(m!.seconds).toBeGreaterThan(0)
        for (const f of m!.faces) expect([...FACES, 'neutral']).toContain(f.face)
      }
      for (const [, m] of Object.entries(side.clips)) if (m.rootSpeed > 0) expect(m.loop).toBe(true)
      const nodeNames = new Set((g.nodes ?? []).map((n) => n.name))
      for (const s of SOCKETS) {
        expect(nodeNames.has(s), `${id} socket ${s}`).toBe(true)
        expect(side.sockets[s]).toBeDefined()
      }
      for (const b of Object.values(side.bones)) expect(nodeNames.has(b), `${id} bone ${b}`).toBe(true)
      for (const sp of side.springs) for (const b of sp.chain) expect(nodeNames.has(b), `${id} spring bone ${b}`).toBe(true)
      for (const layer of side.face.layers) expect(nodeNames.has(`face_${layer}`), `${id} face patch ${layer}`).toBe(true)
      for (const face of FACES) expect(side.face.expressions[face], `${id} face ${face}`).toBeDefined()
      expect(side.face.sheet).toBeLessThanOrEqual(BUDGET.facePx)
    }
  })
})
