/**
 * The Crown Amphitheatre (Battle 3D's second arena): Blender build → what the phone downloads → review sheets.
 *
 *   npm run art:crown -- [--stages build,bake,export,review,ship,shots] [--quick] [--pub <dir>]
 *
 * build…review   headless Blender (tools/blender/arenas/crown.py), logging to tools/blender/out/arena-crown/crown.log
 * ship           tools/blender/out/arena-crown/ → public/models/arenas/crown/: crown.glb and crown_lite.glb (unlit
 *                materials with their atlas embedded as KTX2, ETC1S with mipmaps; meshopt geometry) and crown.json
 * shots          the three.js viewer in Chrome on this PC's GPU from the review cameras, then
 *                art-review/arena-crown/sheet.png beside the Cycles renders (crown_sheet.ts)
 * Adapted from guild.ts (left unchanged).
 */
import { execFileSync, spawn, spawnSync } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO, TextureInfo, type Document } from '@gltf-transform/core'
import { ALL_EXTENSIONS, KHRMaterialsUnlit, KHRTextureBasisu } from '@gltf-transform/extensions'
import { dedup, inspect, meshopt, prune, quantize } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'
import { RUNTIME, runShots, type Shipped } from './crown_sheet.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..', '..')
const SRC = join(ROOT, 'tools', 'blender', 'out', 'arena-crown')
const TEX = join(SRC, 'tex')
const STAGE = join(SRC, 'encoded')
const PUB_ARG = process.argv.includes('--pub') ? process.argv[process.argv.indexOf('--pub') + 1] : undefined
const PUB = PUB_ARG ? join(ROOT, PUB_ARG) : join(ROOT, 'public', 'models', 'arenas', 'crown')
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')
const TOKTX = 'C:\\Program Files\\KTX-Software\\bin\\toktx.exe'

/** The arena budgets (the owner's brief for this arena). */
export const BUDGET = { triangles: 150_000, drawCalls: 40, texturePx: 2048, fullBytes: 12 * 1024 * 1024, liteTriangles: 60_000, liteBytes: 4 * 1024 * 1024, litePx: 1024 } as const

const args = process.argv.slice(2)
const arg = (f: string) => (args.includes(f) ? args[args.indexOf(f) + 1] : undefined)
const stages = (arg('--stages') ?? 'build,bake,export,review,ship,shots').split(',')

function findBlender(): string {
  const c = [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'].filter((p): p is string => !!p)
  for (const p of c) if (existsSync(p)) return p
  return 'blender'
}

const KTX_ARGS = ['--t2', '--genmipmap', '--encode', 'etc1s', '--clevel', '4', '--qlevel', '200', '--assign_oetf', 'srgb', '--target_type', 'RGB']
interface TexStat { px: [number, number]; ktx2: number; webp: number }

function encodeTexture(name: string): TexStat {
  const png = join(TEX, `${name}.png`)
  const ktx2 = join(STAGE, `${name}.ktx2`)
  const webp = join(STAGE, `${name}.webp`)
  execFileSync(TOKTX, [...KTX_ARGS, ktx2, png])
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, '-c:v', 'libwebp', '-quality', '84', '-compression_level', '6', webp])
  const head = readFileSync(png)
  return { px: [head.readUInt32BE(16), head.readUInt32BE(20)], ktx2: statSync(ktx2).size, webp: statSync(webp).size }
}

interface MatInfo { atlas: string; texture: string; doubleSided: boolean }

async function materialNames(raw: string): Promise<string[]> {
  const doc = await new NodeIO().registerExtensions(ALL_EXTENSIONS).read(join(SRC, raw))
  return doc.getRoot().listMaterials().map((m) => m.getName())
}

/** The raw Blender export → the shipped glb: unlit materials with their KTX2 atlas embedded, clamped, mipmapped. */
async function shipGlb(raw: string, out: string): Promise<Shipped & { materials: Record<string, MatInfo> }> {
  await MeshoptEncoder.ready
  await MeshoptDecoder.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  const doc: Document = await io.read(join(SRC, raw))
  const unlit = doc.createExtension(KHRMaterialsUnlit)
  doc.createExtension(KHRTextureBasisu).setRequired(true)
  const materials: Record<string, MatInfo> = {}
  let texBytes = 0
  for (const m of doc.getRoot().listMaterials()) {
    const extras = m.getExtras() as { atlas?: string; doubleSided?: boolean }
    for (const t of [m.getBaseColorTexture(), m.getEmissiveTexture()]) if (t) t.dispose()
    m.setEmissiveFactor([0, 0, 0]).setRoughnessFactor(1).setMetallicFactor(0).setDoubleSided(!!extras.doubleSided)
    m.setExtension('KHR_materials_unlit', unlit.createUnlit())
    for (const ext of ['KHR_materials_specular', 'KHR_materials_emissive_strength', 'KHR_materials_ior']) m.setExtension(ext, null)
    if (m.getName() === 'crown_shadow_catcher') {
      m.setBaseColorFactor([0, 0, 0, 0]).setAlphaMode('BLEND').setExtras({ shadowCatcher: true })
      continue
    }
    const tex = m.getName().replace(/^crown_/, '')
    const bytes = readFileSync(join(STAGE, `${tex}.ktx2`))
    texBytes += bytes.byteLength
    const t = doc.createTexture(tex).setMimeType('image/ktx2').setImage(new Uint8Array(bytes))
    m.setBaseColorFactor([1, 1, 1, 1]).setBaseColorTexture(t)
    m.getBaseColorTextureInfo()!
      .setWrapS(TextureInfo.WrapMode.CLAMP_TO_EDGE)
      .setWrapT(TextureInfo.WrapMode.CLAMP_TO_EDGE)
      .setMinFilter(TextureInfo.MinFilter.LINEAR_MIPMAP_LINEAR)
      .setMagFilter(TextureInfo.MagFilter.LINEAR)
    materials[m.getName()] = { atlas: extras.atlas ?? tex, texture: `${tex}.ktx2`, doubleSided: !!extras.doubleSided }
    m.setExtras({ atlas: extras.atlas ?? tex })
  }
  await doc.transform(prune({ keepLeaves: true, keepAttributes: false }), dedup(), quantize({ quantizePosition: 16, quantizeTexcoord: 14, quantizeNormal: 10 }),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' }))
  const glb = await io.writeBinary(doc)
  writeFileSync(join(PUB, out), glb)
  let triangles = 0
  let drawCalls = 0
  const meshes: Record<string, number> = {}
  for (const m of inspect(doc).meshes.properties) {
    triangles += m.glPrimitives
    drawCalls += m.meshPrimitives
    meshes[m.name] = m.glPrimitives
  }
  console.log(`${out}: ${(glb.byteLength / 1048576).toFixed(2)} MB · ${triangles} tris · ${drawCalls} draw calls`)
  return { bytes: glb.byteLength, meshBytes: glb.byteLength - texBytes, triangles, drawCalls, meshes, materials }
}

async function ship(): Promise<void> {
  mkdirSync(PUB, { recursive: true })
  mkdirSync(STAGE, { recursive: true })
  const build = JSON.parse(readFileSync(join(SRC, 'crown_build.json'), 'utf8')) as Record<string, unknown>
  const tex: Record<string, TexStat> = {}
  for (const raw of ['crown_raw.glb', 'crown_lite_raw.glb']) {
    for (const name of await materialNames(raw)) {
      const t = name.replace(/^crown_/, '')
      if (t !== 'shadow_catcher' && !tex[t]) tex[t] = encodeTexture(t)
    }
  }
  const full = await shipGlb('crown_raw.glb', 'crown.glb')
  const lite = await shipGlb('crown_lite_raw.glb', 'crown_lite.glb')
  const webpOf = (set: Record<string, MatInfo>) => Object.values(set).reduce((a, m) => a + tex[m.texture.replace(/\.ktx2$/, '')]!.webp, 0)
  const row = (r: Shipped & { materials: Record<string, MatInfo> }) => ({ triangles: r.triangles, drawCalls: r.drawCalls, downloadBytes: r.bytes, meshBytes: r.meshBytes, textureBytes: r.bytes - r.meshBytes, webpEquivalentBytes: r.meshBytes + webpOf(r.materials), meshes: r.meshes })
  const report = { full: row(full), lite: row(lite), textures: tex, budget: BUDGET }
  const problems: string[] = []
  if (full.triangles > BUDGET.triangles) problems.push(`full: ${full.triangles} triangles > ${BUDGET.triangles}`)
  if (full.drawCalls > BUDGET.drawCalls) problems.push(`full: ${full.drawCalls} draw calls > ${BUDGET.drawCalls}`)
  if (full.bytes > BUDGET.fullBytes) problems.push('full download over 12 MB')
  if (lite.triangles > BUDGET.liteTriangles) problems.push(`lite: ${lite.triangles} triangles > ${BUDGET.liteTriangles}`)
  if (lite.bytes > BUDGET.liteBytes) problems.push('Lite download over 4 MB')
  for (const [n, t] of Object.entries(tex)) {
    const cap = n.includes('lite') ? BUDGET.litePx : BUDGET.texturePx
    if (t.px[0] > cap || t.px[1] > cap) problems.push(`${n} is ${t.px.join('×')}`)
  }
  const sidecar = {
    arena: 'crown',
    title: 'The Crown Amphitheatre',
    ...build,
    files: { full: 'crown.glb', lite: 'crown_lite.glb' },
    materials: { full: full.materials, lite: lite.materials },
    runtime: RUNTIME,
    budget: report,
    problems,
  }
  writeFileSync(join(PUB, 'crown.json'), sidecarText(sidecar))
  const mb = (n: number) => (n / 1048576).toFixed(2) + ' MB'
  console.log(`full: ${full.triangles} tris, ${full.drawCalls} draws, ${mb(full.bytes)} (WebP equivalent ${mb(report.full.webpEquivalentBytes)})`)
  console.log(`lite: ${lite.triangles} tris, ${lite.drawCalls} draws, ${mb(lite.bytes)} (WebP equivalent ${mb(report.lite.webpEquivalentBytes)})`)
  for (const p of problems) console.log('PROBLEM', p)
}

/** crown.json as text: indented, but the crowd's seats one per line. */
function sidecarText(sidecar: Record<string, unknown>): string {
  const seats = Array.isArray(sidecar.seats) ? (sidecar.seats as unknown[]) : []
  const text = JSON.stringify(sidecar, null, 1)
  return text.replace(/"seats": \[[\s\S]*?\n \]/, () => `"seats": [\n${seats.map((x) => '  ' + JSON.stringify(x)).join(',\n')}\n ]`) + '\n'
}

async function main(): Promise<void> {
  const blenderStages = stages.filter((s) => ['build', 'bake', 'sky', 'export', 'review', 'preview'].includes(s))
  if (blenderStages.length) {
    const a = ['-b', '--factory-startup', '--python', join(HERE, 'crown.py'), '--', '--stages', blenderStages.join(',')]
    if (args.includes('--quick')) a.push('--quick')
    const blender = findBlender()
    console.log(`${blender} ${a.join(' ')}`)
    const r = spawnSync(blender, a, { stdio: 'inherit', cwd: ROOT })
    if (r.status !== 0) {
      console.error(`Blender exited with ${r.status}; see tools/blender/out/arena-crown/crown.log`)
      process.exit(r.status ?? 1)
    }
  }
  if (stages.includes('ship')) await ship()
  if (stages.includes('shots')) {
    mkdirSync(join(ROOT, 'art-review', 'arena-crown'), { recursive: true })
    copyFileSync(join(HERE, 'crown_viewer.js'), join(ROOT, 'art-review', 'arena-crown', 'viewer.js'))
    await runShots(ROOT, PUB, { spawn, execFileSync })
  }
  const review = join(ROOT, 'art-review', 'arena-crown')
  if (existsSync(review)) console.log('review files:', readdirSync(review).filter((f) => f.endsWith('.png')).join(', '))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
