/**
 * Art 2.1 Ultra (docs/ART_2_DETAIL.md §5.1, §9 P1.1): build and ship one Ultra look, for any breed.
 *
 *   node tools/art/ultra.ts <breed> [--blender] [--quick] [--stages build,bake,rig,clips,export] [--gpu] [--no-fail]
 *                                   [--atlas 2048] [--body-tris N] [--lite-only]
 *
 * --blender  first runs tools/blender/monsters/build_ultra.py headless (the given stages; default all but review),
 *            logging to tools/blender/out/<breed>-ultra/build.log. Bakes run on the CPU (the GPU is shared and
 *            slower here) unless --gpu.
 * then, from tools/blender/out/<breed>-ultra/, writes public/models/monsters-ultra/:
 *   <breed>.glb                           skinned meshes + clips + textures (KTX2; deduplicated, resampled, quantised, meshopt)
 *   <breed>.lite.glb                      the Lite copy: ≤ 12k triangles in all (the membranes kept to a quarter, props
 *                                         capped at 2.4k, the body takes the rest), no cards or tuft, 1024² WebP, the same skeleton
 *                                         and clips (≤ 1.5 MB; committed). --lite-only rebuilds just this from the last ship
 *   <breed>_{base,normal,orm}.{ktx2,webp} the 2048² body atlas (KTX2 = ETC1S everywhere, toktx; WebP for comparison)
 *   <breed>_<short>_base.{ktx2,webp}      each variant's colour map on the same UVs (normal and ORM are shared)
 *   <breed>.webp.glb                      the WebP comparison copy (local only)
 *   <breed>.json                          the sidecar, with `build` (the .glb's sha1, 10 hex: a cache-buster),
 *                                         `textures`, `budget` and `lite` added
 * Exits 1 when an Ultra or Lite budget is broken, unless --no-fail.
 * A grown form is its own look: `node tools/art/ultra.ts hearthwing-grown --blender` builds breeds/hearthwing_grown_ultra.py
 * (ID 'hearthwing-grown') and writes hearthwing-grown.{glb,json,lite.glb} beside the young form's files.
 * A coat without fur cards or tuft ships the same way: no lo_cards / lo_tuft in the .glb, nothing to promote.
 */
import { execFileSync, spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO, type Document } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, getGLPrimitiveCount, inspect, meshopt, quantize, resample, simplifyPrimitive, weldPrimitive } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer'
import { embedTextures, promoteColours, type Format } from './ultra-embed.ts'
import { DEFAULT_LAYOUT, padAtlas, type Layout } from './ultra-pad.ts'
import { lookOverlaps, UV_OVERLAP_MAX } from './ultra-uv.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const OUT_DIR = join(ROOT, 'public', 'models', 'monsters-ultra')
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')
const TOKTX = process.env.TOKTX ?? 'C:\\Program Files\\KTX-Software\\bin\\toktx.exe'

/** ART_2_DETAIL §5.1, Ultra. */
export const ULTRA_BUDGET = { triangles: 100_000, cards: 6_000, cardLayers: 3, deformBones: 64, atlasPx: 2048, downloadBytes: 8 * 1024 * 1024 } as const
/**
 * The Lite copy (low-end phones; ART_2_DETAIL §5.1): the whole model ≤ 12k triangles, no cards, locks or tuft, a 1024²
 * WebP atlas, the same rig and clips, ≤ 1.5 MB.
 */
export const LITE_BUDGET = { triangles: 12_000, cards: 0, atlasPx: 1024, downloadBytes: 1.5 * 1024 * 1024 } as const
/** Meshes the Lite copy leaves out (the fur's soft outline and the tuft). */
const LITE_DROP = ['lo_cards', 'lo_tuft']
/** The membranes (flat sheets) keep this share of their triangles in the Lite copy; the body takes what the budget has left. */
const LITE_MEMBRANE_SHARE = 0.25
/** Props (lo_props and every lo_props_<short>) stay as they are up to this many triangles in all; above it they are
 * simplified in proportion to fit it (a horned head and a rope can be thousands). */
const LITE_PROP_CAP = 0.2 * LITE_BUDGET.triangles

const WEBP_Q = { base: 85, normal: 92, orm: 85 } as const
/** libwebp throws away the colour under fully transparent texels (it has no `exact` switch in ffmpeg): a glow look's
 *  ORM, whose alpha is the glow mask (0 on ~97% of the atlas), shipped its AO and roughness wrecked in the WebP copies
 *  (Nov 8: Hearthwing grown's AO off by 53/255, a dark band across the throat on WebP phones). Every WebP with alpha is
 *  encoded with its alpha raised to at least 1/255, which keeps the colour and is invisible (the glow, the cards'
 *  alpha test). */
const WEBP_ALPHA_FLOOR = "format=rgba,lutrgb=a='max(val,1)'"
const LITE_WEBP_Q = { base: 78, normal: 84, orm: 76 } as const
/** A light blur on the Lite normal map before it shrinks: at 1024² the fine strand grooves are incompressible noise,
 *  so this saves ~20% of the map (Tumblefox 240 → 193 KB) without a visible loss. The Ultra maps are untouched. */
const LITE_NORMAL_BLUR = 1.5
/** ETC1S for the colour and ORM maps (ART_2_DETAIL §3.3: it looks the same as WebP, downloads about the same, and needs
 *  ~84% less GPU memory). The normal map is UASTC (RDO + zstd) at NORMAL_KTX_PX: ETC1S's 4×4 blocks showed as square
 *  steps on smooth and scaled skin (Hearthwing's head, the tail's cream underside). At 2048² UASTC would add 2–3 MB per
 *  look (Tumblefox past 8 MB); at 1024² it adds ~0.2 MB, and still measures closer to the 2048² source than ETC1S at
 *  2048² does (Nov 8: mean angular error Hearthwing 2.0° vs 3.1°, Puddlepup 3.4° vs 4.0°, p99 15° vs 25° and 23° vs
 *  27°; no block edges). The WebP copies keep the full size. */
const NORMAL_KTX_PX = 1024
const KTX_ARGS: Record<'base' | 'normal' | 'orm', string[]> = {
  base: ['--encode', 'etc1s', '--clevel', '4', '--qlevel', '255', '--assign_oetf', 'srgb', '--target_type', 'RGBA'],
  normal: ['--encode', 'uastc', '--uastc_quality', '2', '--uastc_rdo_l', '1.0', '--zcmp', '18', '--assign_oetf', 'linear', '--target_type', 'RGB'],
  orm: ['--encode', 'etc1s', '--clevel', '4', '--qlevel', '255', '--assign_oetf', 'linear', '--target_type', 'RGB'],
}

export interface TexFile { ktx2: string; webp: string; px: number; ktx2Bytes: number; webpBytes: number; ktx2Px?: number }

function pngWidth(png: string): number {
  return readFileSync(png).readUInt32BE(16)
}

function checkToktx(): void {
  if (!existsSync(TOKTX)) {
    throw new Error(`toktx (KTX-Software) is not at ${TOKTX}. Install KTX-Software 4.x for Windows x64 from `
      + 'https://github.com/KhronosGroup/KTX-Software/releases (it installs to C:\\Program Files\\KTX-Software), or set TOKTX=<path to toktx.exe>.')
  }
}

/** `alpha`: keep the map's alpha (the ORM's glow mask, for a breed whose sidecar has `glow`); the colour map always keeps it. */
function encode(png: string, map: 'base' | 'normal' | 'orm', stem: string, alpha = false): TexFile {
  const webp = `${stem}.webp`
  const ktx2 = `${stem}.ktx2`
  const keepsAlpha = map === 'base' || alpha
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, ...(keepsAlpha ? ['-vf', WEBP_ALPHA_FLOOR] : []), '-c:v', 'libwebp', '-quality', String(WEBP_Q[map]),
    '-compression_level', '6', ...(keepsAlpha ? ['-pix_fmt', 'yuva420p'] : []), join(OUT_DIR, webp)])
  const args = alpha ? KTX_ARGS[map].map((a) => (a === 'RGB' ? 'RGBA' : a)) : KTX_ARGS[map]
  const px = pngWidth(png)
  let src = png
  if (map === 'normal' && px > NORMAL_KTX_PX) {
    // the KTX2 normal map at NORMAL_KTX_PX (see KTX_ARGS); the WebP above keeps the full size
    src = `${png.replace(/\.png$/, '')}.ktx${NORMAL_KTX_PX}.png`
    execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, '-vf', `scale=${NORMAL_KTX_PX}:${NORMAL_KTX_PX}:flags=lanczos`, src])
  }
  execFileSync(TOKTX, ['--t2', '--genmipmap', ...args, join(OUT_DIR, ktx2), src])
  return { ktx2, webp, px, ktx2Bytes: statSync(join(OUT_DIR, ktx2)).size, webpBytes: statSync(join(OUT_DIR, webp)).size,
    ...(src !== png ? { ktx2Px: NORMAL_KTX_PX } : {}) }
}

/** A Lite texture: the padded atlas scaled down to `px`², WebP only (the Lite copy is for phones without KTX2 headroom). */
function encodeLite(png: string, map: 'base' | 'normal' | 'orm', dir: string, stem: string, px: number, alpha = false): { ktx2: string; webp: string; bytes: number } {
  const webp = `${stem}.webp`
  const blur = map === 'normal' ? `gblur=sigma=${LITE_NORMAL_BLUR},` : ''
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, '-vf', `${blur}scale=${px}:${px}:flags=lanczos${alpha ? `,${WEBP_ALPHA_FLOOR}` : ''}`, '-c:v', 'libwebp', '-quality', String(LITE_WEBP_Q[map]),
    '-compression_level', '6', '-pix_fmt', alpha ? 'yuva420p' : 'yuv420p', join(dir, webp)])
  return { ktx2: '', webp, bytes: statSync(join(dir, webp)).size }
}

interface VariantEntry extends Record<string, unknown> { atlas?: string }
interface Side extends Record<string, unknown> {
  look: string
  meshes?: Record<string, string>
  variants: Record<string, VariantEntry>
  buildStats?: { cards?: { total: number; layers: number[] } }
  build?: unknown
  atlas?: Layout
  /** A glow channel (build_ultra's glow pass): the ORM's alpha is the mask; emissive = base colour × mask × strength. */
  glow?: { strength: number; tint: string | null } | null
  /** Parts the Lite copy keeps (the recipe's LITE_KEEP, e.g. ['tuft'] for a signature ear tuft); default none. */
  liteKeep?: string[]
  /** The Lite copy's prop share (the recipe's LITE_PROPS_TRIS; default LITE_PROP_CAP, 2.4k), at most 60% of its triangles. */
  litePropsTris?: number
}

export const sha10 = (b: Uint8Array): string => createHash('sha1').update(b).digest('hex').slice(0, 10)

/**
 * Every vertex position and every node's transform in `doc` is a finite number; throws in words naming the meshes and
 * counts otherwise (a recipe's negative base to a fractional power gave Hearthwing's frills NaN positions: they would
 * have shipped). Read through getElement, so quantised positions count as a renderer reads them.
 */
export function assertFinite(doc: Document, what: string): void {
  const bad: string[] = []
  const el: number[] = []
  for (const mesh of doc.getRoot().listMeshes()) {
    let n = 0
    for (const p of mesh.listPrimitives()) {
      const pos = p.getAttribute('POSITION')
      if (!pos) continue
      for (let i = 0; i < pos.getCount(); i++) {
        pos.getElement(i, el)
        if (!el.every(Number.isFinite)) n++
      }
    }
    if (n) bad.push(`${mesh.getName()}: ${n} vertex positions`)
  }
  for (const node of doc.getRoot().listNodes()) {
    if (![...node.getTranslation(), ...node.getRotation(), ...node.getScale()].every(Number.isFinite)) bad.push(`node ${node.getName()}: its transform`)
  }
  if (bad.length) throw new Error(`${what} has NaN or infinite numbers (${bad.join('; ')}): look at the recipe's shapes (a negative number to a fractional power, a division by zero) and build again`)
}

function trianglesByMesh(doc: Document): Record<string, number> {
  const out: Record<string, number> = {}
  for (const node of doc.getRoot().listNodes()) {
    const mesh = node.getMesh()
    if (!mesh) continue
    const key = node.getName().replace(/\.\d+$/, '')
    out[key] = (out[key] ?? 0) + mesh.listPrimitives().reduce((n, p) => n + getGLPrimitiveCount(p), 0)
  }
  return out
}

/** Dispose of accessors nothing uses any more (after meshes are removed or simplified). */
function dropOrphanAccessors(doc: Document): void {
  for (const a of doc.getRoot().listAccessors()) if (a.listParents().every((p) => p.propertyType === 'Root')) a.dispose()
}

/** Remove the named mesh nodes (and their meshes) from a document. */
function dropMeshes(doc: Document, names: string[]): void {
  for (const node of doc.getRoot().listNodes()) {
    if (!names.includes(node.getName())) continue
    const mesh = node.getMesh()
    node.dispose()
    if (mesh && mesh.listParents().every((p) => p.propertyType === 'Root')) {
      for (const p of mesh.listPrimitives()) p.dispose()
      mesh.dispose()
    }
  }
  dropOrphanAccessors(doc)
}

/** Simplify one mesh to at most `target` triangles (meshoptimizer), raising the error limit until it gets there. */
function simplifyMesh(doc: Document, name: string, target: number): { from: number; to: number; error: number } {
  const node = doc.getRoot().listNodes().find((n) => n.getName() === name)
  const mesh = node?.getMesh()
  if (!mesh) throw new Error(`no ${name} in the .glb`)
  const count = () => mesh.listPrimitives().reduce((n, p) => n + getGLPrimitiveCount(p), 0)
  const from = count()
  if (from <= target) return { from, to: from, error: 0 }
  for (const p of mesh.listPrimitives()) weldPrimitive(p)
  let error = 0.002
  let ratio = (target / from) * 0.97
  for (let i = 0; i < 12 && count() > target; i++) {
    for (const p of mesh.listPrimitives()) simplifyPrimitive(p, { simplifier: MeshoptSimplifier, ratio: Math.min(1, ratio), error, lockBorder: false })
    const now = count()
    if (now > target) {
      // the next pass simplifies the mesh as it is now: aim for the rest of the way, with a looser error limit
      ratio = (target / now) * 0.97
      error = Math.min(1, error * 2.5)
    }
  }
  dropOrphanAccessors(doc)
  return { from, to: count(), error }
}

const COMPRESS = (doc: Document) => doc.transform(
  dedup(),
  resample({ tolerance: 5e-4 }),
  quantize({ quantizePosition: 14, quantizeNormal: 10, quantizeTexcoord: 12, quantizeColor: 8, quantizeWeight: 8 }),
  meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
)

export async function shipUltra(breed: string, look: string): Promise<{ problems: string[]; report: Record<string, unknown> }> {
  const src = join(ROOT, 'tools', 'blender', 'out', look)
  const srcGlb = join(src, `${look}.glb`)
  const srcJson = join(src, `${look}.json`)
  if (!existsSync(srcGlb) || !existsSync(srcJson)) throw new Error(`no ${srcGlb} / ${srcJson}: run the Blender stages first`)
  checkToktx()
  mkdirSync(OUT_DIR, { recursive: true })
  await MeshoptEncoder.ready
  await MeshoptDecoder.ready
  await MeshoptSimplifier.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  // textures: the body atlas and each variant's colour map (separate files, and embedded in the .glb below), padded
  // first (ultra-pad.ts: no black, zero-AO or zero-roughness texels next to an island or a card's alpha edge)
  const side = JSON.parse(readFileSync(srcJson, 'utf8')) as Side
  // the variant's atlas: the sidecar names it (atlas_<short>.png); older exports leave it to the id minus -<breed>
  const shortOf = (vid: string) => (side.variants[vid]?.atlas ?? `atlas_${vid.replace(`-${breed}`, '')}.png`).replace(/^atlas_|\.png$/g, '')
  const vids = Object.keys(side.variants)
  for (const vid of vids) if (!existsSync(join(src, `atlas_${shortOf(vid)}.png`))) throw new Error(`no atlas_${shortOf(vid)}.png in ${src}`)
  const padded = join(src, 'ship')
  mkdirSync(padded, { recursive: true })
  const glow = !!side.glow
  // the coverage mask (build_ultra's coverage pass), when the bake made one: texels no ray reached are filled too
  const pad = padAtlas(FFMPEG, src, padded, vids.map(shortOf), side.atlas ?? DEFAULT_LAYOUT, { ormAlpha: glow, coverage: join(src, 'atlas_coverage.png') })
  console.log(`padded the atlas: ${JSON.stringify(pad)} texels${glow ? ' (the ORM keeps its alpha: the glow mask)' : ''}`)
  // two faces sharing texels bake into the same pixels (build_ultra stops above UV_OVERLAP_MAX; builds before the
  // check didn't): a warning here, fixed by building again from the build stage (the packer repairs overlaps)
  const uvOverlaps = (await lookOverlaps(srcGlb)).filter((r) => r.texels > 0)
  for (const r of uvOverlaps) {
    const line = `uv overlap: ${r.mesh} has ${r.texels} texels claimed by two faces (${r.triangles} triangles)`
    if (r.texels > UV_OVERLAP_MAX) console.warn(`WARNING ${line}: they bake into the same pixels; rebuild from the build stage`)
    else console.log(line)
  }
  const body = {
    base: encode(join(padded, 'atlas_base.png'), 'base', `${breed}_base`),
    normal: encode(join(padded, 'atlas_normal.png'), 'normal', `${breed}_normal`),
    orm: encode(join(padded, 'atlas_orm.png'), 'orm', `${breed}_orm`, glow),
  }
  const textures: Record<string, Record<string, TexFile>> = { body }
  for (const vid of vids) {
    const short = shortOf(vid)
    textures[vid] = { base: encode(join(padded, `atlas_${short}.png`), 'base', `${breed}_${short}_base`) }
    const { atlas: _atlas, ...entry } = side.variants[vid]!
    side.variants[vid] = { ...entry, textures: vid, holder: `__variant_${vid}` }
  }
  const meshes = side.meshes ?? {}
  const hasColours = 'lo_cards' in meshes || 'lo_tuft' in meshes || !side.meshes
  // one .glb per texture format: <breed>.glb (KTX2, KHR_texture_basisu) and <breed>.webp.glb (EXT_texture_webp)
  let doc = await io.read(srcGlb)
  let glb = new Uint8Array()
  const glbBytes: Record<Format, number> = { ktx2: 0, webp: 0 }
  for (const format of ['webp', 'ktx2'] as const) {
    doc = await io.read(srcGlb)
    assertFinite(doc, srcGlb)
    const variantFiles = Object.fromEntries(Object.entries(textures).filter(([k]) => k !== 'body').map(([k, s]) => [k, s.base!]))
    if (!promoteColours(doc) && hasColours) throw new Error('no _COLOR_BASE on the cards: re-export with build_ultra.py --stages export')
    embedTextures(doc, OUT_DIR, body, variantFiles, format)
    // no prune: it would drop the unused-looking UVs, tangents and colour sets
    await COMPRESS(doc)
    assertFinite(doc, `${breed} (${format})`)
    glb = await io.writeBinary(doc)
    glbBytes[format] = glb.byteLength
    writeFileSync(join(OUT_DIR, format === 'ktx2' ? `${breed}.glb` : `${breed}.webp.glb`), glb)
  }
  const build = sha10(glb)
  const rep = inspect(doc)
  const triangles = trianglesByMesh(doc)
  let vertices = 0
  for (const m of rep.meshes.properties) vertices += m.vertices
  const totalTris = Object.values(triangles).reduce((a, b) => a + b, 0)
  const joints = doc.getRoot().listSkins().reduce((n, s) => Math.max(n, s.listJoints().length), 0)
  const animations = rep.animations.properties.map((a) => ({ name: a.name, seconds: Math.round(a.duration * 1000) / 1000, bytes: a.size }))
  const animationBytes = animations.reduce((n, a) => n + a.bytes, 0)
  const attrs: Record<string, string[]> = {}
  for (const mesh of doc.getRoot().listMeshes()) for (const p of mesh.listPrimitives()) attrs[mesh.getName()] = p.listSemantics()
  const sum = (sets: Record<string, TexFile>[], k: 'ktx2Bytes' | 'webpBytes') => sets.reduce((a, s) => a + Object.values(s).reduce((b, t) => b + t[k], 0), 0)
  const all = Object.values(textures)
  // the .glb carries everything (mesh, clips, the body atlas and the variant maps): it is the whole download
  const download = {
    glb: glb.byteLength,
    glbKtx2: glbBytes.ktx2,
    glbWebp: glbBytes.webp,
    ktx2: { body: sum([body], 'ktx2Bytes'), variants: sum(all.slice(1), 'ktx2Bytes') },
    webp: { body: sum([body], 'webpBytes'), variants: sum(all.slice(1), 'webpBytes') },
  }
  const totalKtx2 = glbBytes.ktx2
  const totalWebp = glbBytes.webp
  const stats = side.buildStats ?? (typeof side.build === 'object' && side.build ? side.build as Side['buildStats'] : undefined)
  const cards = stats?.cards?.total ?? 0
  const layers = stats?.cards?.layers?.length ?? 0
  const problems: string[] = []
  if (totalTris > ULTRA_BUDGET.triangles) problems.push(`${totalTris} triangles, over ${ULTRA_BUDGET.triangles}`)
  if (cards > ULTRA_BUDGET.cards) problems.push(`${cards} fur cards, over ${ULTRA_BUDGET.cards}`)
  if (layers > ULTRA_BUDGET.cardLayers) problems.push(`${layers} card layers, over ${ULTRA_BUDGET.cardLayers}`)
  if (joints > ULTRA_BUDGET.deformBones) problems.push(`${joints} joints, over ${ULTRA_BUDGET.deformBones}`)
  if (body.base.px > ULTRA_BUDGET.atlasPx) problems.push(`atlas ${body.base.px}², over ${ULTRA_BUDGET.atlasPx}²`)
  if (totalKtx2 > ULTRA_BUDGET.downloadBytes) problems.push(`KTX2 download ${(totalKtx2 / 1048576).toFixed(2)} MB, over 8 MB`)
  if (totalWebp > ULTRA_BUDGET.downloadBytes) problems.push(`WebP download ${(totalWebp / 1048576).toFixed(2)} MB, over 8 MB`)
  const lite = await shipLite(io, breed, srcGlb, padded, vids, shortOf, hasColours, glow, side.liteKeep ?? [], litePropCap(side))
  problems.push(...lite.problems.map((p) => `Lite: ${p}`))
  const files = (s: Record<string, TexFile>) => Object.fromEntries(Object.entries(s).map(([k, t]) => [k, { ktx2: t.ktx2, webp: t.webp, px: t.px, ...(t.ktx2Px ? { ktx2Px: t.ktx2Px } : {}) }]))
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
    textures: Object.fromEntries(Object.entries(textures).map(([k, s]) => [k, Object.fromEntries(Object.entries(s).map(([m, t]) => [m, { px: t.px, ...(t.ktx2Px ? { ktx2Px: t.ktx2Px } : {}), ktx2: t.ktx2Bytes, webp: t.webpBytes }]))])),
    attributes: attrs,
    problems,
  }
  const { build: _old, buildStats, ...rest } = side
  const out = {
    ...rest,
    build,
    buildStats: stats ?? buildStats,
    files: { glb: `${breed}.glb`, glbWebp: `${breed}.webp.glb`, lite: `${breed}.lite.glb` },
    textures: Object.fromEntries(Object.entries(textures).map(([k, s]) => [k, files(s)])),
    texturesNote: 'The .glb embeds everything with film-ready materials (KHR_texture_basisu, KHR_materials_clearcoat/sheen/specular; '
      + 'cards alphaMode MASK; a hidden __variant_<id> mesh per variant whose map is its colour atlas; for a variant also use its '
      + 'colorAttribute (COLOR_1, COLOR_2, …; three: geometry attribute color_1, color_2, …) as the cards\' and tuft\'s colour). The same textures ship as separate files: '
      + 'KTX2 is ETC1S everywhere (three\'s KTX2Loader, transcoder in public/basis/); WebP is the fallback. Colour maps are sRGB with '
      + 'alpha in the bottom strip (the fur-card tiles); normal (tangent space, glTF TANGENT exported) and ORM (R AO, G roughness, B clearcoat mask) '
      + 'are linear and shared by every variant. Every mesh uses TEXCOORD_0; flipY = false. `build` is the first 10 hex of the .glb\'s sha1 '
      + '(append it as ?v=<build> to bust caches); `lite` is the Lite copy (WebP textures embedded, EXT_texture_webp; no cards or tuft).',
    budget,
    lite: lite.entry,
  }
  writeFileSync(join(OUT_DIR, `${breed}.json`), JSON.stringify(out, null, 1) + '\n')
  return { problems, report: { build, glbBytes: glb.byteLength, totalTris, triangles, cards, joints, animations: animations.length, animationBytes, download, totalKtx2, totalWebp, attrs, uvOverlaps, lite: lite.entry } }
}

/** The Lite copy: <breed>.lite.glb from the same Blender export, its textures from the same padded atlas. */
/** The Lite props' triangle share: the recipe's LITE_PROPS_TRIS (sidecar litePropsTris) for prop-heavy breeds, else 2.4k. */
function litePropCap(side: Side): number {
  const v = side.litePropsTris
  return typeof v === 'number' && Number.isFinite(v) && v > 0 ? Math.min(v, 0.6 * LITE_BUDGET.triangles) : LITE_PROP_CAP
}

async function shipLite(io: NodeIO, breed: string, srcGlb: string, padded: string, vids: string[], shortOf: (v: string) => string, hasColours: boolean,
  glow = false, keep: string[] = [], propCap: number = LITE_PROP_CAP):
  Promise<{ problems: string[]; entry: Record<string, unknown> }> {
  const px = LITE_BUDGET.atlasPx
  const dir = join(padded, 'lite')
  mkdirSync(dir, { recursive: true })
  const body = {
    base: encodeLite(join(padded, 'atlas_base.png'), 'base', dir, `${breed}_lite_base`, px),
    normal: encodeLite(join(padded, 'atlas_normal.png'), 'normal', dir, `${breed}_lite_normal`, px),
    orm: encodeLite(join(padded, 'atlas_orm.png'), 'orm', dir, `${breed}_lite_orm`, px, glow),
  }
  const variantFiles = Object.fromEntries(vids.map((vid) => [vid, encodeLite(join(padded, `atlas_${shortOf(vid)}.png`), 'base', dir, `${breed}_lite_${shortOf(vid)}_base`, px)]))
  const doc = await io.read(srcGlb)
  if (!promoteColours(doc) && hasColours) throw new Error('no _COLOR_BASE on the cards: re-export with build_ultra.py --stages export')
  // a recipe's LITE_KEEP (sidecar liteKeep: 'tuft', 'cards') keeps that part; it counts in the 12k budget like the rest
  const drop = LITE_DROP.filter((n) => !keep.includes(n.replace(/^lo_/, '')))
  dropMeshes(doc, drop)
  // the whole model fits the budget: the eyes and the props stay as they are, the membranes keep a share, the body
  // takes the rest (less one triangle per variant holder, added with the textures)
  const before = trianglesByMesh(doc)
  const simplified: Record<string, { from: number; to: number; error: number }> = {}
  if (before.lo_fins) simplified.lo_fins = simplifyMesh(doc, 'lo_fins', Math.max(64, Math.round(before.lo_fins * LITE_MEMBRANE_SHARE)))
  const props = Object.keys(before).filter((n) => n === 'lo_props' || n.startsWith('lo_props_'))
  const propTris = props.reduce((a, n) => a + before[n]!, 0)
  if (propTris > propCap) for (const n of props) simplified[n] = simplifyMesh(doc, n, Math.max(32, Math.floor((before[n]! * propCap) / propTris)))
  const others = Object.entries(trianglesByMesh(doc)).filter(([n]) => n !== 'lo_body').reduce((a, [, v]) => a + v, 0)
  const bodyTarget = LITE_BUDGET.triangles - others - vids.length
  if (bodyTarget < 4000) console.warn(`lite: only ${bodyTarget} triangles left for the body (the eyes, membranes and props take ${others})`)
  simplified.lo_body = simplifyMesh(doc, 'lo_body', Math.max(1000, bodyTarget))
  for (const [n, s] of Object.entries(simplified)) console.log(`lite: ${n} ${s.from} → ${s.to} triangles (error limit ${s.error})`)
  embedTextures(doc, dir, body, variantFiles, 'webp')
  await COMPRESS(doc)
  assertFinite(doc, `${breed} Lite`)
  const glb = await io.writeBinary(doc)
  const file = `${breed}.lite.glb`
  writeFileSync(join(OUT_DIR, file), glb)
  const tris = trianglesByMesh(doc)
  const total = Object.values(tris).reduce((a, b) => a + b, 0)
  const joints = doc.getRoot().listSkins().reduce((n, s) => Math.max(n, s.listJoints().length), 0)
  const problems: string[] = []
  if (total > LITE_BUDGET.triangles) problems.push(`${total} triangles in all, over ${LITE_BUDGET.triangles}`)
  if (drop.some((n) => n in tris)) problems.push('still has cards or a tuft')
  if (glb.byteLength > LITE_BUDGET.downloadBytes) problems.push(`download ${(glb.byteLength / 1048576).toFixed(2)} MB, over ${(LITE_BUDGET.downloadBytes / 1048576).toFixed(1)} MB`)
  const entry = {
    file,
    build: sha10(glb),
    bytes: glb.byteLength,
    triangles: total,
    trianglesByMesh: tris,
    simplified: Object.fromEntries(Object.entries(simplified).map(([n, s]) => [n, { from: s.from, to: s.to }])),
    joints,
    animations: doc.getRoot().listAnimations().length,
    atlasPx: px,
    textureBytes: Object.values(body).reduce((n, t) => n + t.bytes, 0) + Object.values(variantFiles).reduce((n, t) => n + t.bytes, 0),
    note: 'The same skeleton, sockets and clips as the Ultra .glb; WebP textures embedded (EXT_texture_webp); no fur cards and no tuft; '
      + 'the body, the membranes (and props over 2.4k triangles) simplified so the whole model is at most 12k triangles.',
    problems,
  }
  return { problems, entry }
}

/**
 * Rebuild only the Lite copy from the last full ship's padded atlas (tools/blender/out/<look>/ship/) and the same
 * Blender export, and update the shipped sidecar's `lite`, `files.lite` and Lite problems. The Ultra .glb is untouched.
 */
export async function shipLiteOnly(breed: string, look: string): Promise<{ problems: string[]; report: Record<string, unknown> }> {
  const src = join(ROOT, 'tools', 'blender', 'out', look)
  const srcGlb = join(src, `${look}.glb`)
  const padded = join(src, 'ship')
  const outPath = join(OUT_DIR, `${breed}.json`)
  if (!existsSync(srcGlb) || !existsSync(join(padded, 'atlas_base.png')) || !existsSync(outPath)) {
    throw new Error(`--lite-only needs a full ship first (${srcGlb}, ${padded}/atlas_base.png and ${outPath})`)
  }
  const side = JSON.parse(readFileSync(join(src, `${look}.json`), 'utf8')) as Side
  const shortOf = (vid: string) => (side.variants[vid]?.atlas ?? `atlas_${vid.replace(`-${breed}`, '')}.png`).replace(/^atlas_|\.png$/g, '')
  const meshes = side.meshes ?? {}
  const hasColours = 'lo_cards' in meshes || 'lo_tuft' in meshes || !side.meshes
  await MeshoptEncoder.ready
  await MeshoptDecoder.ready
  await MeshoptSimplifier.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  const lite = await shipLite(io, breed, srcGlb, padded, Object.keys(side.variants), shortOf, hasColours, !!side.glow, side.liteKeep ?? [], litePropCap(side))
  const out = JSON.parse(readFileSync(outPath, 'utf8')) as { files?: Record<string, string>; budget: { problems: string[] }; lite?: unknown }
  out.files = { ...out.files, lite: `${breed}.lite.glb` }
  out.budget.problems = [...out.budget.problems.filter((p) => !p.startsWith('Lite: ')), ...lite.problems.map((p) => `Lite: ${p}`)]
  out.lite = lite.entry
  writeFileSync(outPath, JSON.stringify(out, null, 1) + '\n')
  return { problems: out.budget.problems, report: { lite: lite.entry } }
}

/**
 * The recipe module of a look: `tumblefox` → `tumblefox_ultra`; a grown form `hearthwing-grown` →
 * `hearthwing_grown_ultra` (tools/blender/monsters/breeds/RECIPE.md, grown forms). Its files are `<look>.*` all the same.
 */
/** Blender's output is passed through and watched: Cycles reports a material it can't compile ("out of SVM stack
 *  space, shader … too big") only in its log, bakes black and carries on, and the build exited 0 (Starhowl shipped
 *  black bodies). */
function runBlender(exe: string, args: string[]): Promise<{ status: number | null; svm: string[] }> {
  return new Promise((resolve) => {
    const p = spawn(exe, args, { stdio: ['ignore', 'pipe', 'pipe'], cwd: ROOT })
    const svm: string[] = []
    const carry = { out: '', err: '' }
    const watch = (key: 'out' | 'err', chunk: Buffer) => {
      ;(key === 'out' ? process.stdout : process.stderr).write(chunk)
      const lines = (carry[key] + chunk.toString()).split(/\r?\n/)
      carry[key] = lines.pop() ?? ''
      for (const line of lines) if (/out of SVM stack space|Shader graph:.*too big/i.test(line)) svm.push(line.trim())
    }
    p.stdout.on('data', (c: Buffer) => watch('out', c))
    p.stderr.on('data', (c: Buffer) => watch('err', c))
    p.on('close', (status) => {
      for (const rest of [carry.out, carry.err]) if (/out of SVM stack space|Shader graph:.*too big/i.test(rest)) svm.push(rest.trim())
      resolve({ status, svm })
    })
  })
}

export const recipeModule = (look: string): string => `${look.replace(/-/g, '_')}_ultra`

function findBlender(): string {
  for (const c of [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe']) if (c && existsSync(c)) return c
  return 'blender'
}

function flagValue(rest: string[], name: string): string | undefined {
  const i = rest.indexOf(name)
  return i >= 0 ? rest[i + 1] : undefined
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const [breed, ...rest] = process.argv.slice(2)
  if (!breed || breed.startsWith('--')) {
    console.error('usage: node tools/art/ultra.ts <breed> [--blender] [--quick] [--stages build,bake,rig,clips,export] [--gpu] [--no-fail] [--atlas 2048] [--body-tris N] [--lite-only]')
    process.exit(1)
  }
  const look = `${breed}-ultra`
  if (rest.includes('--blender')) {
    const stages = flagValue(rest, '--stages') ?? 'build,bake,rig,clips,export'
    // --python-exit-code: an uncaught Python error exits non-zero (Blender's default is 0: a failed build looked done)
    const args = ['-b', '--factory-startup', '--python-exit-code', '1', '--python', join(ROOT, 'tools', 'blender', 'monsters', 'build_ultra.py'), '--', '--breed', recipeModule(breed), '--stages', stages]
    if (rest.includes('--quick')) args.push('--quick')
    if (!rest.includes('--gpu')) args.push('--cpu')
    for (const f of ['--atlas', '--body-tris']) {
      const v = flagValue(rest, f)
      if (v) args.push(f, v)
    }
    const blender = findBlender()
    console.log(`${blender} ${args.join(' ')}`)
    const r = await runBlender(blender, args)
    if (r.svm.length) {
      console.error(`Cycles could not compile a bake material (${r.svm[0]}), so that bake came out black. Too many per-pixel `
        + 'mark nodes in the body material: use fewer marks, or merge them with lib.marks.union.')
      process.exit(1)
    }
    if (r.status !== 0) {
      console.error(`Blender exited with ${r.status}; see tools/blender/out/${look}/build.log`)
      process.exit(r.status ?? 1)
    }
  }
  ;(rest.includes('--lite-only') ? shipLiteOnly(breed, look) : shipUltra(breed, look))
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
