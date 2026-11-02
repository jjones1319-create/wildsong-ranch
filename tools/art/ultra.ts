/**
 * Art 2.1 Ultra (docs/ART_2_DETAIL.md §5.1, §9 P1.1): build and ship one Ultra look.
 *
 *   node tools/art/ultra.ts <breed> [--blender] [--quick] [--stages build,bake,rig,clips,export] [--no-fail]
 *
 * --blender  first runs tools/blender/monsters/build_ultra.py headless (the given stages; default all but review),
 *            logging to tools/blender/out/<breed>-ultra/build.log
 * then, from tools/blender/out/<breed>-ultra/, writes public/models/monsters-ultra/:
 *   <breed>.glb                           skinned meshes + clips (deduplicated, resampled, quantised, meshopt)
 *   <breed>_{base,normal,orm}.{ktx2,webp} the 2048² body atlas (KTX2 = ETC1S everywhere, toktx; WebP for comparison)
 *   <breed>_<variant>_base.{ktx2,webp}    each variant's colour map on the same UVs (normal and ORM are shared)
 *   <breed>.json                          the sidecar, with `textures` and `budget` added
 * Exits 1 when an Ultra budget (§5.1) is broken, unless --no-fail.
 */
import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, inspect, meshopt, quantize, resample } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'
import { embedTextures, promoteColours, type Format } from './ultra-embed.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const OUT_DIR = join(ROOT, 'public', 'models', 'monsters-ultra')
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')
const TOKTX = 'C:\\Program Files\\KTX-Software\\bin\\toktx.exe'

/** ART_2_DETAIL §5.1, Ultra. */
export const ULTRA_BUDGET = { triangles: 100_000, cards: 6_000, cardLayers: 3, deformBones: 64, atlasPx: 2048, downloadBytes: 8 * 1024 * 1024 } as const

const WEBP_Q = { base: 85, normal: 92, orm: 85 } as const
/** ETC1S everywhere (ART_2_DETAIL §3.3: it looks the same as WebP, downloads about the same, and needs ~84% less GPU memory). */
const KTX_ARGS: Record<'base' | 'normal' | 'orm', string[]> = {
  base: ['--encode', 'etc1s', '--clevel', '4', '--qlevel', '255', '--assign_oetf', 'srgb', '--target_type', 'RGBA'],
  normal: ['--encode', 'etc1s', '--clevel', '5', '--qlevel', '255', '--assign_oetf', 'linear', '--target_type', 'RGB'],
  orm: ['--encode', 'etc1s', '--clevel', '4', '--qlevel', '255', '--assign_oetf', 'linear', '--target_type', 'RGB'],
}

export interface TexFile { ktx2: string; webp: string; px: number; ktx2Bytes: number; webpBytes: number }

function pngWidth(png: string): number {
  return readFileSync(png).readUInt32BE(16)
}

function encode(png: string, map: 'base' | 'normal' | 'orm', stem: string): TexFile {
  const webp = `${stem}.webp`
  const ktx2 = `${stem}.ktx2`
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, '-c:v', 'libwebp', '-quality', String(WEBP_Q[map]), '-compression_level', '6',
    ...(map === 'base' ? ['-pix_fmt', 'yuva420p'] : []), join(OUT_DIR, webp)])
  execFileSync(TOKTX, ['--t2', '--genmipmap', ...KTX_ARGS[map], join(OUT_DIR, ktx2), png])
  return { ktx2, webp, px: pngWidth(png), ktx2Bytes: statSync(join(OUT_DIR, ktx2)).size, webpBytes: statSync(join(OUT_DIR, webp)).size }
}

interface Side extends Record<string, unknown> {
  look: string
  variants: Record<string, Record<string, unknown>>
  build?: { cards?: { total: number; layers: number[] } }
}

export async function shipUltra(breed: string, look: string): Promise<{ problems: string[]; report: Record<string, unknown> }> {
  const src = join(ROOT, 'tools', 'blender', 'out', look)
  const srcGlb = join(src, `${look}.glb`)
  const srcJson = join(src, `${look}.json`)
  if (!existsSync(srcGlb) || !existsSync(srcJson)) throw new Error(`no ${srcGlb} / ${srcJson}: run the Blender stages first`)
  mkdirSync(OUT_DIR, { recursive: true })
  await MeshoptEncoder.ready
  await MeshoptDecoder.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  // textures: the body atlas and each variant's colour map (separate files, and embedded in the .glb below)
  const side = JSON.parse(readFileSync(srcJson, 'utf8')) as Side
  const body = {
    base: encode(join(src, 'atlas_base.png'), 'base', `${breed}_base`),
    normal: encode(join(src, 'atlas_normal.png'), 'normal', `${breed}_normal`),
    orm: encode(join(src, 'atlas_orm.png'), 'orm', `${breed}_orm`),
  }
  const textures: Record<string, Record<string, TexFile>> = { body }
  for (const vid of Object.keys(side.variants)) {
    const short = vid.replace(`-${breed}`, '')
    const png = join(src, `atlas_${short}.png`)
    if (!existsSync(png)) throw new Error(`no ${png}`)
    textures[vid] = { base: encode(png, 'base', `${breed}_${short}_base`) }
    side.variants[vid] = { ...side.variants[vid], textures: vid, holder: `__variant_${vid}` }
  }
  // one .glb per texture format: <breed>.glb (KTX2, KHR_texture_basisu) and <breed>.webp.glb (EXT_texture_webp)
  let doc = await io.read(srcGlb)
  let glb = new Uint8Array()
  const glbBytes: Record<Format, number> = { ktx2: 0, webp: 0 }
  for (const format of ['webp', 'ktx2'] as const) {
    doc = await io.read(srcGlb)
    const variantFiles = Object.fromEntries(Object.entries(textures).filter(([k]) => k !== 'body').map(([k, s]) => [k, s.base!]))
    if (!promoteColours(doc)) throw new Error('no _COLOR_BASE on the cards: re-export with build_ultra.py --stages export')
    embedTextures(doc, OUT_DIR, body, variantFiles, format)
    // no prune: it would drop the unused-looking UVs, tangents and colour sets
    await doc.transform(
      dedup(),
      resample({ tolerance: 5e-4 }),
      quantize({ quantizePosition: 14, quantizeNormal: 10, quantizeTexcoord: 12, quantizeColor: 8, quantizeWeight: 8 }),
      meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
    )
    glb = await io.writeBinary(doc)
    glbBytes[format] = glb.byteLength
    writeFileSync(join(OUT_DIR, format === 'ktx2' ? `${breed}.glb` : `${breed}.webp.glb`), glb)
  }
  const rep = inspect(doc)
  const triangles: Record<string, number> = {}
  let vertices = 0
  for (const m of rep.meshes.properties) {
    const key = m.name.replace(/\.\d+$/, '')
    triangles[key] = (triangles[key] ?? 0) + m.glPrimitives
    vertices += m.vertices
  }
  const totalTris = Object.values(triangles).reduce((a, b) => a + b, 0)
  const joints = doc.getRoot().listSkins().reduce((n, s) => Math.max(n, s.listJoints().length), 0)
  const animations = rep.animations.properties.map((a) => ({ name: a.name, seconds: Math.round(a.duration * 1000) / 1000, bytes: a.size }))
  const animationBytes = animations.reduce((n, a) => n + a.bytes, 0)
  const attrs: Record<string, string[]> = {}
  for (const mesh of doc.getRoot().listMeshes()) for (const p of mesh.listPrimitives()) attrs[mesh.getName()] = p.listSemantics()
  const sum = (sets: Record<string, TexFile>[], k: 'ktx2Bytes' | 'webpBytes') => sets.reduce((a, s) => a + Object.values(s).reduce((b, t) => b + t[k], 0), 0)
  const all = Object.values(textures)
  // the .glb carries everything (mesh, clips, the body atlas and the variant map): it is the whole download
  const download = {
    glb: glb.byteLength,
    glbKtx2: glbBytes.ktx2,
    glbWebp: glbBytes.webp,
    ktx2: { body: sum([body], 'ktx2Bytes'), variants: sum(all.slice(1), 'ktx2Bytes') },
    webp: { body: sum([body], 'webpBytes'), variants: sum(all.slice(1), 'webpBytes') },
  }
  const totalKtx2 = glbBytes.ktx2
  const totalWebp = glbBytes.webp
  const cards = side.build?.cards?.total ?? 0
  const layers = side.build?.cards?.layers?.length ?? 0
  const deformBones = joints
  const problems: string[] = []
  if (totalTris > ULTRA_BUDGET.triangles) problems.push(`${totalTris} triangles, over ${ULTRA_BUDGET.triangles}`)
  if (cards > ULTRA_BUDGET.cards) problems.push(`${cards} fur cards, over ${ULTRA_BUDGET.cards}`)
  if (layers > ULTRA_BUDGET.cardLayers) problems.push(`${layers} card layers, over ${ULTRA_BUDGET.cardLayers}`)
  if (deformBones > ULTRA_BUDGET.deformBones) problems.push(`${deformBones} joints, over ${ULTRA_BUDGET.deformBones}`)
  if (body.base.px > ULTRA_BUDGET.atlasPx) problems.push(`atlas ${body.base.px}², over ${ULTRA_BUDGET.atlasPx}²`)
  if (totalKtx2 > ULTRA_BUDGET.downloadBytes) problems.push(`KTX2 download ${(totalKtx2 / 1048576).toFixed(2)} MB, over 8 MB`)
  if (totalWebp > ULTRA_BUDGET.downloadBytes) problems.push(`WebP download ${(totalWebp / 1048576).toFixed(2)} MB, over 8 MB`)
  const files = (s: Record<string, TexFile>) => Object.fromEntries(Object.entries(s).map(([k, t]) => [k, { ktx2: t.ktx2, webp: t.webp, px: t.px }]))
  const budget = {
    triangles: totalTris,
    trianglesByMesh: triangles,
    vertices,
    cards,
    cardLayers: layers,
    joints,
    animations: animations.length,
    animationBytes,
    download: { ...download, totalKtx2, totalWebp },
    textures: Object.fromEntries(Object.entries(textures).map(([k, s]) => [k, Object.fromEntries(Object.entries(s).map(([m, t]) => [m, { px: t.px, ktx2: t.ktx2Bytes, webp: t.webpBytes }]))])),
    attributes: attrs,
    problems,
  }
  const out = {
    ...side,
    files: { glb: `${breed}.glb`, glbWebp: `${breed}.webp.glb` },
    textures: Object.fromEntries(Object.entries(textures).map(([k, s]) => [k, files(s)])),
    texturesNote: 'The .glb embeds everything with film-ready materials (KHR_texture_basisu, KHR_materials_clearcoat/sheen/specular; '
      + 'cards alphaMode MASK; a hidden __variant_<id> mesh per variant whose map is its colour atlas; for a variant also use COLOR_1 '
      + '(three: geometry attribute color_1) as the cards\' and tuft\'s colour). The same textures ship as separate files: '
      + 'KTX2 is ETC1S everywhere (three\'s KTX2Loader, transcoder in public/basis/); WebP is the fallback. Colour maps are sRGB with '
      + 'alpha in the bottom strip (the fur-card tiles); normal (tangent space, glTF TANGENT exported) and ORM (R AO, G roughness, B clearcoat mask) '
      + 'are linear and shared by every variant. Every mesh uses TEXCOORD_0; flipY = false.',
    budget,
  }
  writeFileSync(join(OUT_DIR, `${breed}.json`), JSON.stringify(out, null, 1) + '\n')
  return { problems, report: { glbBytes: glb.byteLength, totalTris, triangles, cards, joints, animations: animations.length, animationBytes, download, totalKtx2, totalWebp, attrs } }
}

function findBlender(): string {
  for (const c of [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe']) if (c && existsSync(c)) return c
  return 'blender'
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const [breed, ...rest] = process.argv.slice(2)
  if (!breed) {
    console.error('usage: node tools/art/ultra.ts <breed> [--blender] [--quick] [--stages build,bake,rig,clips,export] [--no-fail]')
    process.exit(1)
  }
  const look = `${breed}-ultra`
  if (rest.includes('--blender')) {
    const stages = rest.includes('--stages') ? rest[rest.indexOf('--stages') + 1]! : 'build,bake,rig,clips,export'
    const args = ['-b', '--factory-startup', '--python', join(ROOT, 'tools', 'blender', 'monsters', 'build_ultra.py'), '--', '--breed', `${breed}_ultra`, '--stages', stages]
    if (rest.includes('--quick')) args.push('--quick')
    const blender = findBlender()
    console.log(`${blender} ${args.join(' ')}`)
    const r = spawnSync(blender, args, { stdio: 'inherit', cwd: ROOT })
    if (r.status !== 0) {
      console.error(`Blender exited with ${r.status}; see tools/blender/out/${look}/build.log`)
      process.exit(r.status ?? 1)
    }
  }
  shipUltra(breed, look)
    .then(({ problems, report }) => {
      console.log(JSON.stringify(report, null, 1))
      for (const p of problems) console.log(`PROBLEM ${p}`)
      if (problems.length && !rest.includes('--no-fail')) process.exit(1)
    })
    .catch((e) => {
      console.error(e)
      process.exit(1)
    })
}
