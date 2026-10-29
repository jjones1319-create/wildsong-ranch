/**
 * Art 2.0 (ART_2_PLAN §3.1, §3.6): take a look's raw Blender export from tools/blender/out/<look>/ and write the
 * shipped files into public/models/monsters/: the .glb (deduplicated, pruned, animation keys resampled, vertex
 * attributes quantised, meshopt-compressed) and the sidecar .json with the budget report added.
 *
 *   node tools/art/optimize.ts <look> [--no-fail]
 *
 * Exits 1 when a §3.6 budget is broken (unless --no-fail): ≤ 700 KB, ≤ 12,000 triangles, ≤ 64 joints,
 * base colour ≤ 1024², every texture WebP.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, inspect, meshopt, prune, quantize, resample } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const OUT_DIR = join(ROOT, 'public', 'models', 'monsters')

export const BUDGET = { bytes: 700 * 1024, triangles: 12_000, joints: 64, baseColorPx: 1024, glowPx: 512, facePx: 512, variantBytes: 250 * 1024 } as const

export interface BudgetReport {
  bytes: number
  triangles: number
  vertices: number
  joints: number
  textures: { name: string; mime: string; width: number; height: number; bytes: number }[]
  animations: { name: string; seconds: number; keyframes: number; bytes: number }[]
  animationBytes: number
  problems: string[]
}

export async function optimizeLook(look: string): Promise<BudgetReport> {
  const srcDir = join(ROOT, 'tools', 'blender', 'out', look)
  const srcGlb = join(srcDir, `${look}.glb`)
  const srcJson = join(srcDir, `${look}.json`)
  if (!existsSync(srcGlb) || !existsSync(srcJson)) throw new Error(`no ${srcGlb} / ${srcJson}: run the Blender build first`)
  await MeshoptEncoder.ready
  await MeshoptDecoder.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  const doc = await io.read(srcGlb)
  await doc.transform(
    dedup(),
    prune({ keepLeaves: true, keepAttributes: false, keepIndices: false }),
    resample({ tolerance: 5e-4 }),
    quantize({ quantizePosition: 14, quantizeNormal: 10, quantizeTexcoord: 12, quantizeColor: 8, quantizeWeight: 8 }),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
  )
  const glb = await io.writeBinary(doc)
  const rep = inspect(doc)
  let triangles = 0
  let vertices = 0
  for (const m of rep.meshes.properties) {
    triangles += m.glPrimitives
    vertices += m.vertices
  }
  const skins = doc.getRoot().listSkins()
  const joints = skins.reduce((n, s) => Math.max(n, s.listJoints().length), 0)
  const textures = rep.textures.properties.map((t) => ({ name: t.name, mime: t.mimeType, width: t.resolution ? Number(t.resolution.split('x')[0]) : 0, height: t.resolution ? Number(t.resolution.split('x')[1]) : 0, bytes: t.size }))
  const animations = rep.animations.properties.map((a) => ({ name: a.name, seconds: Math.round(a.duration * 1000) / 1000, keyframes: a.keyframes, bytes: a.size }))
  const animationBytes = animations.reduce((n, a) => n + a.bytes, 0)
  const problems: string[] = []
  if (glb.byteLength > BUDGET.bytes) problems.push(`glb is ${(glb.byteLength / 1024).toFixed(0)} KB, over ${BUDGET.bytes / 1024} KB`)
  if (triangles > BUDGET.triangles) problems.push(`${triangles} triangles, over ${BUDGET.triangles}`)
  if (joints > BUDGET.joints) problems.push(`${joints} joints, over ${BUDGET.joints}`)
  for (const t of textures) {
    if (t.mime !== 'image/webp') problems.push(`texture ${t.name} is ${t.mime}, not WebP`)
    const cap = /face/i.test(t.name) ? BUDGET.facePx : BUDGET.baseColorPx
    if (t.width > cap || t.height > cap) problems.push(`texture ${t.name} is ${t.width}×${t.height}, over ${cap}`)
  }
  const report: BudgetReport = { bytes: glb.byteLength, triangles, vertices, joints, textures, animations, animationBytes, problems }
  mkdirSync(OUT_DIR, { recursive: true })
  writeFileSync(join(OUT_DIR, `${look}.glb`), glb)
  const side = JSON.parse(readFileSync(srcJson, 'utf8')) as Record<string, unknown>
  side.budget = { bytes: report.bytes, triangles, vertices, joints, textures, animationBytes }
  writeFileSync(join(OUT_DIR, `${look}.json`), JSON.stringify(side, null, 1) + '\n')
  return report
}

function printReport(look: string, r: BudgetReport): void {
  console.log(`${look}: ${(r.bytes / 1024).toFixed(0)} KB · ${r.triangles} tris · ${r.vertices} verts · ${r.joints} joints · animations ${(r.animationBytes / 1024).toFixed(0)} KB`)
  for (const t of r.textures) console.log(`  texture ${t.name}: ${t.mime} ${t.width}×${t.height} ${(t.bytes / 1024).toFixed(0)} KB`)
  const anims = [...r.animations].sort((a, b) => b.bytes - a.bytes)
  for (const a of anims.slice(0, 6)) console.log(`  anim ${a.name}: ${a.seconds}s ${a.keyframes} keys ${(a.bytes / 1024).toFixed(1)} KB`)
  for (const p of r.problems) console.log(`  PROBLEM ${p}`)
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const [look, ...rest] = process.argv.slice(2)
  if (!look) {
    console.error('usage: node tools/art/optimize.ts <look> [--no-fail]')
    process.exit(1)
  }
  optimizeLook(look)
    .then((r) => {
      printReport(look, r)
      if (r.problems.length && !rest.includes('--no-fail')) process.exit(1)
    })
    .catch((e) => {
      console.error(e)
      process.exit(1)
    })
}
