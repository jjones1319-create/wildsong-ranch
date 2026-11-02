/**
 * The Breeders' Guild arena (ART_2_PLAN §7.3): Blender build → what the phone downloads → review sheets.
 *
 *   npm run art:arena -- [--stages build,bake,export,review,ship,shots] [--quick]
 *
 * build…review   headless Blender (tools/blender/arenas/guild.py), logging to tools/blender/out/arena-guild/guild.log
 * ship           tools/blender/out/arena-guild/ → public/models/arenas/guild/: guild.glb and guild_lite.glb, each
 *                self-contained: unlit materials with their atlas embedded as KTX2 (ETC1S with mipmaps,
 *                KHR_texture_basisu), meshopt geometry; and guild.json (anchors, ring radius, fly-in, sun, the budget
 *                report with the WebP-equivalent sizes, the CC0 sources)
 * shots          the three.js viewer (art-review/arena-guild/viewer.html, copied from this folder) in Chrome on this PC's
 *                GPU, from the review cameras; then art-review/arena-guild/sheet.png beside the Cycles renders
 */
import { execFileSync, spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO, TextureInfo, type Document } from '@gltf-transform/core'
import { ALL_EXTENSIONS, KHRMaterialsUnlit, KHRTextureBasisu } from '@gltf-transform/extensions'
import { dedup, inspect, meshopt, prune, quantize } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'
import { chromium } from '@playwright/test'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..', '..')
const SRC = join(ROOT, 'tools', 'blender', 'out', 'arena-guild')
const TEX = join(SRC, 'tex')
const STAGE = join(SRC, 'encoded')
const PUB = join(ROOT, 'public', 'models', 'arenas', 'guild')
const REVIEW = join(ROOT, 'art-review', 'arena-guild')
const PORT = 5175
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')
const TOKTX = 'C:\\Program Files\\KTX-Software\\bin\\toktx.exe'
const IS_WIN = process.platform === 'win32'

/** The arena budgets (the owner's brief for this arena). */
export const BUDGET = { triangles: 150_000, drawCalls: 40, texturePx: 2048, fullBytes: 12 * 1024 * 1024, liteBytes: 3 * 1024 * 1024, litePx: 1024 } as const

const args = process.argv.slice(2)
const arg = (f: string) => (args.includes(f) ? args[args.indexOf(f) + 1] : undefined)
const stages = (arg('--stages') ?? 'build,bake,export,review,ship,shots').split(',')

function findBlender(): string {
  const c = [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'].filter((p): p is string => !!p)
  for (const p of c) if (existsSync(p)) return p
  return 'blender'
}

// ---------------------------------------------------------------------------- ship: the textures
const KTX_ARGS = ['--t2', '--genmipmap', '--encode', 'etc1s', '--clevel', '4', '--qlevel', '200', '--assign_oetf', 'srgb', '--target_type', 'RGB']

interface TexStat { px: [number, number]; ktx2: number; webp: number }

/** One baked atlas → KTX2 (ETC1S with mipmaps: what the glb embeds) and WebP (for the size comparison only). */
function encodeTexture(name: string): TexStat {
  const png = join(TEX, `${name}.png`)
  const ktx2 = join(STAGE, `${name}.ktx2`)
  const webp = join(STAGE, `${name}.webp`)
  execFileSync(TOKTX, [...KTX_ARGS, ktx2, png])
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, '-c:v', 'libwebp', '-quality', '84', '-compression_level', '6', webp])
  const head = readFileSync(png)
  return { px: [head.readUInt32BE(16), head.readUInt32BE(20)], ktx2: statSync(ktx2).size, webp: statSync(webp).size }
}

// ---------------------------------------------------------------------------- ship: the glb
interface MatInfo { atlas: string; texture: string; doubleSided: boolean }
interface Shipped { bytes: number; meshBytes: number; triangles: number; drawCalls: number; meshes: Record<string, number>; materials: Record<string, MatInfo> }

async function materialNames(raw: string): Promise<string[]> {
  const doc = await new NodeIO().registerExtensions(ALL_EXTENSIONS).read(join(SRC, raw))
  return doc.getRoot().listMaterials().map((m) => m.getName())
}

/** The raw Blender export → the shipped glb: unlit materials, each with its KTX2 atlas embedded (KHR_texture_basisu),
 * clamped and mipmapped; the shadow catcher stays invisible (a transparent disc the runtime may give a ShadowMaterial). */
async function shipGlb(raw: string, out: string): Promise<Shipped> {
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
    if (m.getName() === 'guild_shadow_catcher') {
      m.setBaseColorFactor([0, 0, 0, 0]).setAlphaMode('BLEND').setExtras({ shadowCatcher: true })
      continue
    }
    const tex = m.getName().replace(/^guild_/, '')
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
  await doc.transform(
    prune({ keepLeaves: true, keepAttributes: false }),
    dedup(),
    quantize({ quantizePosition: 16, quantizeTexcoord: 14, quantizeNormal: 10 }),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
  )
  const glb = await io.writeBinary(doc)
  writeFileSync(join(PUB, out), glb)
  const rep = inspect(doc)
  let triangles = 0
  let drawCalls = 0
  const meshes: Record<string, number> = {}
  for (const m of rep.meshes.properties) {
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
  const build = JSON.parse(readFileSync(join(SRC, 'guild_build.json'), 'utf8')) as Record<string, unknown>
  const tex: Record<string, TexStat> = {}
  for (const raw of ['guild_raw.glb', 'guild_lite_raw.glb']) {
    for (const name of await materialNames(raw)) {
      const t = name.replace(/^guild_/, '')
      if (t !== 'shadow_catcher' && !tex[t]) tex[t] = encodeTexture(t)
    }
  }
  const full = await shipGlb('guild_raw.glb', 'guild.glb')
  const lite = await shipGlb('guild_lite_raw.glb', 'guild_lite.glb')
  const webpOf = (set: Record<string, MatInfo>) => Object.values(set).reduce((a, m) => a + tex[m.texture.replace(/\.ktx2$/, '')]!.webp, 0)
  const row = (r: Shipped) => ({ triangles: r.triangles, drawCalls: r.drawCalls, downloadBytes: r.bytes, meshBytes: r.meshBytes, textureBytes: r.bytes - r.meshBytes, webpEquivalentBytes: r.meshBytes + webpOf(r.materials), meshes: r.meshes })
  const report = { full: row(full), lite: row(lite), textures: tex, budget: BUDGET }
  const problems: string[] = []
  if (full.triangles > BUDGET.triangles) problems.push(`full: ${full.triangles} triangles > ${BUDGET.triangles}`)
  if (full.drawCalls > BUDGET.drawCalls) problems.push(`full: ${full.drawCalls} draw calls > ${BUDGET.drawCalls}`)
  if (full.bytes > BUDGET.fullBytes) problems.push('full download over 12 MB')
  if (lite.bytes > BUDGET.liteBytes) problems.push('Lite download over 3 MB')
  for (const [n, t] of Object.entries(tex)) {
    const cap = n.includes('lite') ? BUDGET.litePx : BUDGET.texturePx
    if (t.px[0] > cap || t.px[1] > cap) problems.push(`${n} is ${t.px.join('×')}`)
  }
  const sidecar = {
    arena: 'guild',
    title: "The Breeders' Guild arena, Tunewick",
    ...build,
    files: { full: 'guild.glb', lite: 'guild_lite.glb' },
    materials: { full: full.materials, lite: lite.materials },
    runtime: {
      shading: 'Every material is KHR_materials_unlit (three: MeshBasicMaterial) with its KTX2 atlas embedded (KHR_texture_basisu: the GLTFLoader needs a KTX2Loader). The light is baked in, so scene lights and receiveShadow do not change the arena; light the fighters with a key along `sun.direction`.',
      hideForSideCamera: ['arena_near', 'lite_near'],
      shadowCatcher: { node: 'shadow_catcher', radius: 6.3, y: 0.004, note: "an invisible disc over the ring floor: give it a THREE.ShadowMaterial (opacity about 0.3) to show the fighters' shadows on the unlit floor" },
      sky: { radius: 400, centre: [0, 1.6, 0], note: 'two half-domes (sky_front looks toward -Z, the town; sky_back toward +Z): keep the camera far plane at 900 m or more' },
      anisotropy: 'set map.anisotropy to 4-8 on the ground atlases (ring, apron, mid, far) for the grazing battle view',
      flyIn: 'cam_fly_0 ... cam_fly_5: each node looks down its local -Z (three camera convention); `t` is seconds, `fovDeg` the vertical field of view; interpolate eye and target with a Catmull-Rom curve',
    },
    budget: report,
    problems,
  }
  writeFileSync(join(PUB, 'guild.json'), JSON.stringify(sidecar, null, 1) + '\n')
  const mb = (n: number) => (n / 1048576).toFixed(2) + ' MB'
  console.log(`full: ${full.triangles} tris, ${full.drawCalls} draws, ${mb(full.bytes)} (WebP equivalent ${mb(report.full.webpEquivalentBytes)})`)
  console.log(`lite: ${lite.triangles} tris, ${lite.drawCalls} draws, ${mb(lite.bytes)} (WebP equivalent ${mb(report.lite.webpEquivalentBytes)})`)
  for (const p of problems) console.log('PROBLEM', p)
}

// ---------------------------------------------------------------------------- shots
async function waitFor(url: string, ms: number): Promise<boolean> {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) {
    try {
      if ((await fetch(url)).ok) return true
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 400))
  }
  return false
}

function stopServer(p: ChildProcess): void {
  if (IS_WIN && p.pid) {
    try {
      execFileSync('taskkill', ['/PID', String(p.pid), '/F', '/T'], { stdio: 'ignore' })
    } catch {
      /* gone */
    }
  } else p.kill()
}

const SHOTS: { file: string; q: string }[] = [
  { file: 'three_battle', q: 'view=battle' },
  { file: 'three_shoulder', q: 'view=shoulder' },
  { file: 'three_establish', q: 'view=establish' },
  { file: 'three_lite_battle', q: 'view=battle&tier=lite' },
  { file: 'three_phone_battle', q: 'view=battle&w=412&h=560&dpr=2.5' },
  { file: 'three_fly0', q: 'view=fly0' },
]

async function shots(): Promise<Record<string, unknown>> {
  mkdirSync(REVIEW, { recursive: true })
  for (const f of ['viewer.html', 'viewer.js']) copyFileSync(join(HERE, f), join(REVIEW, f))
  const server = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', '--config', 'vite.perf.config.ts', '--port', String(PORT), '--strictPort'], { cwd: ROOT, stdio: 'ignore', shell: IS_WIN })
  const info: Record<string, unknown> = {}
  try {
    if (!(await waitFor(`http://localhost:${PORT}/wildsong-ranch/art-review/arena-guild/viewer.html`, 120_000))) throw new Error('the dev server did not start')
    const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'] })
    try {
      for (const s of SHOTS) {
        const page = await b.newPage({ viewport: { width: 1000, height: 1300 }, deviceScaleFactor: 1 })
        page.on('pageerror', (e) => console.error('page error:', e.message))
        page.on('console', (m) => {
          if (m.type() === 'error' || m.type() === 'warning') console.error('console:', m.text())
        })
        await page.goto(`http://localhost:${PORT}/wildsong-ranch/art-review/arena-guild/viewer.html?${s.q}`)
        await page.waitForFunction(() => (window as unknown as { __arena?: { ready: boolean } }).__arena?.ready === true, null, { timeout: 240_000 })
        const r = await page.evaluate(() => (window as unknown as { __arena: { shot(): { png: string; calls: number; triangles: number; textures: number; ms: number } } }).__arena.shot())
        writeFileSync(join(REVIEW, `${s.file}.png`), Buffer.from(r.png.slice(r.png.indexOf(',') + 1), 'base64'))
        info[s.file] = { calls: r.calls, triangles: r.triangles, textures: r.textures, ms: Math.round(r.ms * 10) / 10 }
        console.log('shot', s.file, JSON.stringify(info[s.file]))
        await page.close()
      }
      writeFileSync(join(REVIEW, 'shots.json'), JSON.stringify(info, null, 1) + '\n')
      writeFileSync(join(REVIEW, 'index.html'), sheetHtml(info))
      const sheet = await b.newPage({ viewport: { width: 1840, height: 1200 }, deviceScaleFactor: 1 })
      await sheet.goto(`http://localhost:${PORT}/wildsong-ranch/art-review/arena-guild/index.html`)
      await sheet.waitForLoadState('networkidle')
      await sheet.screenshot({ path: join(REVIEW, 'sheet.png'), fullPage: true })
      console.log('sheet', join(REVIEW, 'sheet.png'))
    } finally {
      await b.close()
    }
  } finally {
    stopServer(server)
  }
  return info
}

interface Row { triangles: number; drawCalls: number; downloadBytes: number; meshBytes: number; webpEquivalentBytes: number }

function sheetHtml(info: Record<string, unknown>): string {
  const side = JSON.parse(readFileSync(join(PUB, 'guild.json'), 'utf8')) as { budget: { full: Row; lite: Row }; problems: string[]; sources: { id: string; authors: string[] }[] }
  const mb = (n: number) => (n / 1048576).toFixed(2) + ' MB'
  const fig = (src: string, cap: string, w = 300) => (existsSync(join(REVIEW, src)) ? `<figure><img src="${src}" width="${w}"><figcaption>${cap}</figcaption></figure>` : `<figure><div class="miss" style="width:${w}px;height:${(w * 4) / 3}px"></div><figcaption>${cap} (missing)</figcaption></figure>`)
  const f = side.budget.full
  const l = side.budget.lite
  const shotInfo = (k: string) => {
    const s = info[k] as { calls?: number; triangles?: number } | undefined
    return s ? ` · ${s.calls} draws, ${(s.triangles ?? 0).toLocaleString()} tris drawn` : ''
  }
  return `<!doctype html><html><head><meta charset="utf-8"><title>Guild arena review</title><style>
body{margin:0;padding:16px 20px;background:#e4e6ea;font:14px/1.4 system-ui,Segoe UI,sans-serif;color:#1d2126;width:1800px}
h1{font-size:21px;margin:0 0 4px} h2{font-size:15px;margin:14px 0 6px} .row{display:flex;gap:10px;flex-wrap:wrap}
figure{margin:0;background:#fff;border-radius:8px;padding:6px;box-shadow:0 1px 2px #0002} figure img{display:block;border-radius:4px}
figcaption{font-size:12px;margin-top:4px;max-width:300px} .miss{background:#bbb;border-radius:4px}
table{border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 2px #0002} td,th{padding:4px 10px;border-bottom:1px solid #e4e6ea;text-align:left;font-size:13px} th{background:#f2f3f5}
</style></head><body>
<h1>The Breeders' Guild arena (Tunewick): Cycles reference beside the game's three.js render</h1>
<p>Grey capsules = 1 m stand-ins at spawn A (−2.4 m) and spawn B (+2.4 m). The game draws the arena unlit with its light baked in (one texture, one draw per atlas); three.js uses Neutral tone mapping, like the film look.</p>
<h2>1 · Battle camera, side-on (1.5 m high; the camera-side fence hidden)</h2>
<div class="row">${fig('cycles_battle.png', 'Cycles, the source scene path traced')}${fig('three_battle.png', 'three.js, Full' + shotInfo('three_battle'))}${fig('three_lite_battle.png', 'three.js, Lite' + shotInfo('three_lite_battle'))}${fig('shipped_lite_battle.png', 'Cycles, the Lite meshes and textures drawn unlit')}${fig('three_phone_battle.png', 'three.js at phone size (412 × 560 CSS px, 2.5×)', 220)}</div>
<h2>2 · Over spawn A's shoulder toward B · 3 · Establishing · fly-in start</h2>
<div class="row">${fig('cycles_shoulder.png', 'Cycles')}${fig('three_shoulder.png', 'three.js, Full' + shotInfo('three_shoulder'))}${fig('cycles_establish.png', 'Cycles')}${fig('three_establish.png', 'three.js, Full' + shotInfo('three_establish'))}${fig('three_fly0.png', 'three.js, cam_fly_0 (the fly-in starts here)')}</div>
<h2>Budgets (measured)</h2>
<table><tr><th></th><th>Triangles (≤ 150,000)</th><th>Draw calls (≤ 40)</th><th>Download (.glb, KTX2 inside)</th><th>of which mesh</th><th>Same with WebP textures</th></tr>
<tr><td>Full</td><td>${f.triangles.toLocaleString()}</td><td>${f.drawCalls}</td><td>${mb(f.downloadBytes)} (≤ 12 MB)</td><td>${mb(f.meshBytes)}</td><td>${mb(f.webpEquivalentBytes)}</td></tr>
<tr><td>Lite</td><td>${l.triangles.toLocaleString()}</td><td>${l.drawCalls}</td><td>${mb(l.downloadBytes)} (≤ 3 MB)</td><td>${mb(l.meshBytes)}</td><td>${mb(l.webpEquivalentBytes)}</td></tr></table>
<p>${side.problems.length ? 'Problems: ' + side.problems.join('; ') : 'Within every budget.'}</p>
<p style="color:#555">CC0 sources (Poly Haven): ${side.sources.map((s) => `${s.id} (${s.authors.join(', ')})`).join(' · ')}</p>
</body></html>`
}

// ---------------------------------------------------------------------------- main
async function main(): Promise<void> {
  const blenderStages = stages.filter((s) => ['build', 'bake', 'sky', 'export', 'review', 'preview'].includes(s))
  if (blenderStages.length) {
    const a = ['-b', '--factory-startup', '--python', join(HERE, 'guild.py'), '--', '--stages', blenderStages.join(',')]
    if (args.includes('--quick')) a.push('--quick')
    const blender = findBlender()
    console.log(`${blender} ${a.join(' ')}`)
    const r = spawnSync(blender, a, { stdio: 'inherit', cwd: ROOT })
    if (r.status !== 0) {
      console.error(`Blender exited with ${r.status}; see tools/blender/out/arena-guild/guild.log`)
      process.exit(r.status ?? 1)
    }
  }
  if (stages.includes('ship')) await ship()
  if (stages.includes('shots')) await shots()
  if (existsSync(REVIEW)) console.log('review files:', readdirSync(REVIEW).filter((f) => f.endsWith('.png')).join(', '))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
