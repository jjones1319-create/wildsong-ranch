/**
 * Art 2.1 detail spike (docs/ART_2_DETAIL.md §7): turn the Blender spike into what the phone loads and draws, measure
 * it, and lay it beside the reference pictures.
 *
 *   node tools/art/spike-detail.ts [--no-encode] [--no-shots]
 *
 * 1. encode   tools/blender/out/spike-detail/ → public/models/perf/: the optimised .glb (meshopt), and the body atlas and
 *             the cinematic head set as WebP and as KTX2 (toktx: ETC1S colour and ORM; normals as UASTC + zstd and as
 *             ETC1S), plus half-size Lite WebP for the sizes
 * 2. shots    the Performance check page in shot mode (Vite dev server, vite.perf.config.ts) in Chrome on this PC's
 *             GPU: the film look with the Ultra effects, in the reference views and at phone thumbnail sizes
 * 3. sheet    art-review/detail-spike/index.html → sheet.png, with stats.json
 */
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, inspect, meshopt, quantize } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'
import { chromium, type Browser, type Page } from '@playwright/test'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const SRC = join(ROOT, 'tools', 'blender', 'out', 'spike-detail')
const PUB = join(ROOT, 'public', 'models', 'perf')
const OUT = join(ROOT, 'art-review', 'detail-spike')
const SHOTS = join(OUT, 'shots')
const LITE = join(OUT, 'lite')
const PORT = 5174
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')
const TOKTX = 'C:\\Program Files\\KTX-Software\\bin\\toktx.exe'
const IS_WIN = process.platform === 'win32'

const args = process.argv.slice(2)
const has = (f: string) => args.includes(f)

// ---------------------------------------------------------------------------- 1. encode
async function optimiseGlb(name = 'spike'): Promise<{ bytes: number; triangles: Record<string, number>; vertices: number }> {
  await MeshoptEncoder.ready
  await MeshoptDecoder.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  const doc = await io.read(join(SRC, `${name}.glb`))
  // no prune: the placeholder materials carry no textures, and prune would drop the tangents, the second UV set and the colours
  await doc.transform(dedup(), quantize({ quantizePosition: 14, quantizeNormal: 10, quantizeTexcoord: 12, quantizeColor: 8 }), meshopt({ encoder: MeshoptEncoder, level: 'medium' }))
  const glb = await io.writeBinary(doc)
  writeFileSync(join(PUB, `${name}.glb`), glb)
  const rep = inspect(doc)
  const triangles: Record<string, number> = {}
  let vertices = 0
  for (const m of rep.meshes.properties) {
    const key = m.name.replace(/\.\d+$/, '')
    triangles[key] = (triangles[key] ?? 0) + m.glPrimitives
    vertices += m.vertices
  }
  return { bytes: glb.byteLength, triangles, vertices }
}

const WEBP_Q = { base: 85, normal: 92, orm: 85 } as const
// The usual KTX2 mix: ETC1S (small) for colour and ORM, UASTC with strong RDO + zstd for normals (ETC1S breaks normals).
const KTX_ARGS: Record<'base' | 'normal' | 'orm', string[]> = {
  base: ['--encode', 'etc1s', '--clevel', '4', '--qlevel', '255', '--assign_oetf', 'srgb', '--target_type', 'RGBA'],
  normal: ['--encode', 'uastc', '--uastc_quality', '2', '--uastc_rdo_l', '4', '--uastc_rdo_d', '8192', '--zcmp', '22', '--assign_oetf', 'linear', '--target_type', 'RGB'],
  orm: ['--encode', 'etc1s', '--clevel', '4', '--qlevel', '255', '--assign_oetf', 'linear', '--target_type', 'RGB'],
}

interface TexStat { px: number; webp: number; ktx2: number; liteWebp: number; png: number }

function encodeSet(set: 'atlas' | 'cine' | 'standin'): Record<string, TexStat> {
  const out: Record<string, TexStat> = {}
  mkdirSync(LITE, { recursive: true })
  for (const map of ['base', 'normal', 'orm'] as const) {
    const png = join(SRC, `${set}_${map}.png`)
    const webp = join(PUB, `${set}_${map}.webp`)
    const ktx2 = join(PUB, `${set}_${map}.ktx2`)
    const lite = join(LITE, `${set}_${map}.webp`)
    const enc = (dst: string, scale: string) =>
      execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', png, '-vf', scale, '-c:v', 'libwebp', '-quality', String(WEBP_Q[map]), '-compression_level', '6', ...(map === 'base' ? ['-pix_fmt', 'yuva420p'] : []), dst])
    enc(webp, 'scale=iw:ih')
    enc(lite, 'scale=iw/2:ih/2:flags=lanczos')
    execFileSync(TOKTX, ['--t2', '--genmipmap', ...KTX_ARGS[map], ktx2, png])
    if (map === 'normal') execFileSync(TOKTX, ['--t2', '--genmipmap', '--encode', 'etc1s', '--clevel', '5', '--qlevel', '255', '--assign_oetf', 'linear', '--target_type', 'RGB', join(PUB, `${set}_normal.etc1s.ktx2`), png])
    out[map] = { px: readFileSync(png).readUInt32BE(16), webp: statSync(webp).size, ktx2: statSync(ktx2).size, liteWebp: statSync(lite).size, png: statSync(png).size }
  }
  return out
}

// ---------------------------------------------------------------------------- 2. the page
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

async function startServer(): Promise<ChildProcess> {
  const proc = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', '--config', 'vite.perf.config.ts', '--port', String(PORT), '--strictPort'], { cwd: ROOT, stdio: 'ignore', shell: IS_WIN })
  if (!(await waitFor(`http://localhost:${PORT}/wildsong-ranch/perf/index.html`, 90_000))) throw new Error('the perf dev server did not start')
  return proc
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

async function launch(): Promise<Browser> {
  return chromium.launch({
    channel: 'chrome',
    headless: true,
    args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox', '--enable-unsafe-webgpu'],
  })
}

async function openShotPage(b: Browser): Promise<Page> {
  const page = await b.newPage({ viewport: { width: 1300, height: 1300 }, deviceScaleFactor: 1 })
  page.on('pageerror', (e) => console.error('page error:', e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') console.error('console:', m.text())
  })
  await page.goto(`http://localhost:${PORT}/wildsong-ranch/perf/index.html?mode=shot`)
  await page.waitForFunction(() => (window as unknown as { __perf?: { ready: boolean } }).__perf?.ready === true, null, { timeout: 120_000 })
  return page
}

interface Shot { file: string; o: Record<string, unknown> }
const SHOT_LIST: Shot[] = [
  { file: 'cine_head_34', o: { view: 'head_34', cinematic: true } },
  { file: 'cine_head_front', o: { view: 'head_front', cinematic: true } },
  { file: 'cine_head_side', o: { view: 'head_side', cinematic: true } },
  { file: 'ultra_head_34', o: { view: 'head_34' } },
  { file: 'ultra_paw_34', o: { view: 'paw_34', part: 'paw' } },
  { file: 'webgpu_head_34', o: { view: 'head_34', cinematic: true, backend: 'webgpu' } },
  { file: 'webp_head_34', o: { view: 'head_34', cinematic: true, format: 'webp' } },
  { file: 'etc1s_head_34', o: { view: 'head_34', cinematic: true, format: 'ktx2-etc1s' } },
  { file: 'ultra_head_34_s64', o: { view: 'head_34', size: 64 } },
  { file: 'ultra_head_34_s100', o: { view: 'head_34', size: 100 } },
  { file: 'ultra_head_34_s200', o: { view: 'head_34', size: 200 } },
  { file: 'ultra_head_front_s64', o: { view: 'head_front', size: 64 } },
  { file: 'check_battle', o: { kind: 'battle', size: 700 } },
  { file: 'check_card', o: { kind: 'card', size: 700, cinematic: true } },
]

type ShotInfo = { triangles: number; cards: number; ok: boolean; error?: string }

async function shots(page: Page): Promise<Record<string, ShotInfo>> {
  mkdirSync(SHOTS, { recursive: true })
  const info: Record<string, ShotInfo> = {}
  for (const s of SHOT_LIST) {
    try {
      const r = await page.evaluate((o) => (window as unknown as { __perf: { shot(o: unknown): Promise<{ png: string; triangles: number; cards: number }> } }).__perf.shot(o), s.o)
      writeFileSync(join(SHOTS, `${s.file}.png`), Buffer.from(r.png.slice(r.png.indexOf(',') + 1), 'base64'))
      info[s.file] = { triangles: r.triangles, cards: r.cards, ok: true }
      console.log('shot', s.file, r.triangles, 'tris', r.cards, 'cards')
    } catch (e) {
      info[s.file] = { triangles: 0, cards: 0, ok: false, error: (e as Error).message.split('\n')[0] }
      console.warn('shot failed', s.file, info[s.file]!.error)
    }
  }
  return info
}

async function gpuInfo(page: Page): Promise<{ webgl: string; webgpu: string }> {
  return page.evaluate(async () => {
    const c = document.createElement('canvas')
    const gl = c.getContext('webgl2')
    const dbg = gl?.getExtension('WEBGL_debug_renderer_info')
    const webgl = gl ? String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)) : 'none'
    let webgpu = 'none'
    const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<{ info?: { vendor: string; architecture: string; description: string } } | null> } }).gpu
    if (gpu) {
      const a = await gpu.requestAdapter()
      webgpu = a ? `${a.info?.vendor ?? ''} ${a.info?.architecture ?? ''} ${a.info?.description ?? ''}`.trim() || 'adapter' : 'no adapter'
    }
    return { webgl, webgpu }
  })
}

// ---------------------------------------------------------------------------- 3. the sheet
const REF = '../../chatgpt/monsters/01-puddlepup/'
const IMG: Record<string, [number, number]> = { '1-hero.png': [1254, 1254], '2-turnaround.png': [1672, 941], '3-faces.png': [1448, 1086], '4-details.png': [1536, 1024] }
function crop(src: string, nat: [number, number], x: number, y: number, w: number, h: number, D: number): string {
  const s = D / Math.max(w, h)
  return `background:#8a8b8f url('${src}') no-repeat; background-size:${(nat[0] * s).toFixed(1)}px ${(nat[1] * s).toFixed(1)}px; background-position:${(-x * s).toFixed(1)}px ${(-y * s).toFixed(1)}px; width:${D}px; height:${D}px;`
}
const ref = (f: string, r: [number, number, number, number], cap: string, D: number) => `<figure><div class="img" style="${crop(REF + f, IMG[f]!, ...r, D)}"></div><figcaption>${cap}</figcaption></figure>`
const img = (src: string, cap: string, D: number) => `<figure><img src="${src}" width="${D}" height="${D}"><figcaption>${cap}</figcaption></figure>`
const kb = (n: number) => `${(n / 1024).toFixed(0)} KB`

interface Stats {
  build?: { tris?: Record<string, number>; cards?: { head?: number; paw?: number }; tuft_locks?: number }
  glb: { bytes: number; triangles: Record<string, number> }
  textures: Record<'atlas' | 'cine', Record<string, TexStat>> & { standin?: Record<string, TexStat> }
  standinGlb?: { bytes: number; triangles: Record<string, number> }
  shots?: Record<string, ShotInfo>
  gpu?: { webgl: string; webgpu: string }
  bench?: Record<string, unknown>[]
}

function benchTable(st: Stats): string {
  const rows = (st.bench ?? []).map((r) => {
    const x = r as { label: string; fps?: number; gpuMs?: number | null; triangles?: number; cards?: number; error?: string }
    return x.error ? `<tr><td>${x.label}</td><td colspan="3">${x.error}</td></tr>` : `<tr><td>${x.label}</td><td>${x.gpuMs == null ? 'n/a' : x.gpuMs.toFixed(2) + ' ms'}</td><td>${(x.fps ?? 0).toFixed(0)}</td><td>${(x.triangles ?? 0).toLocaleString()} / ${(x.cards ?? 0).toLocaleString()}</td></tr>`
  })
  return `<table><tr><th colspan="4">This PC's GPU (${st.gpu?.webgl ?? '?'}), 412 × 560 CSS px canvas: an indication only</th></tr><tr><th>Scene</th><th>GPU per frame</th><th>fps</th><th>triangles / cards</th></tr>${rows.join('')}</table>`
}

/** What the phone downloads by default: ETC1S colour, normal and ORM (the UASTC normals stay on this PC). */
const etc1sBytes = (set: 'atlas' | 'cine') =>
  statSync(join(PUB, `${set}_base.ktx2`)).size + statSync(join(PUB, `${set}_normal.etc1s.ktx2`)).size + statSync(join(PUB, `${set}_orm.ktx2`)).size

function sheetHtml(st: Stats): string {
  const D = 300
  const t = st.build?.tris ?? {}
  const tex = st.textures
  const sum = (set: 'atlas' | 'cine', k: keyof TexStat) => Object.values(tex[set]).reduce((a, x) => a + x[k], 0)
  const ok = (f: string) => st.shots?.[f]?.ok === true
  const tag = (s: string) => `<span class="tag">${s}</span>`
  const blank = (cap: string) => `<figure><div class="img" style="width:${D}px;height:${D}px"></div><figcaption>${cap}</figcaption></figure>`
  return `<!doctype html><html><head><meta charset="utf-8"><title>Art 2.1 detail spike, round 2</title><style>
body{margin:0;padding:18px 22px;background:#e4e6ea;font:14px/1.4 system-ui,Segoe UI,sans-serif;color:#1d2126;width:1900px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:18px 0 6px} p{margin:2px 0 8px;max-width:1820px}
.row{display:flex;gap:10px} figure{margin:0;background:#fff;border-radius:8px;padding:6px;box-shadow:0 1px 2px #0002}
figure img,.img{display:block;border-radius:4px;background:#8a8b8f} figcaption{font-size:12.5px;margin-top:5px;max-width:${D}px}
.small{display:flex;gap:14px;align-items:flex-end;background:#fff;border-radius:8px;padding:10px;box-shadow:0 1px 2px #0002}
table{border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 2px #0002} td,th{padding:4px 10px;border-bottom:1px solid #e4e6ea;text-align:left;font-size:13px} th{background:#f2f3f5}
.tag{display:inline-block;background:#1d6f69;color:#fff;border-radius:4px;padding:0 6px;font-size:12px;margin-right:4px}.cols{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
</style></head><body>
<h1>Art 2.1 detail spike, round 2: Puddlepup's head and front paw at the Ultra targets</h1>
<p>Every render is the game's own three.js (r186) on this PC's GPU: the film look with the Ultra effects (soft key-light shadows, ambient occlusion, bloom, colour grading, 4× MSAA), no outlines. ${tag('cinematic')} is the head on its own ${tex.cine.base?.px ?? 2048}² texture set (Monster Card, cutscenes); ${tag('ultra')} is the in-game body atlas (${tex.atlas.base?.px ?? 0}² here = the density 2048² gives a whole Puddlepup). Head and paw: ${(t.total ?? 0).toLocaleString()} triangles, ${(st.build?.cards?.head ?? 0) + (st.build?.cards?.paw ?? 0)} soft fur cards, a tuft of ${st.build?.tuft_locks ?? 0} locks.</p>
<h2>1 · Head, three-quarter view (the hero's angle)</h2>
<div class="row">
${ref('1-hero.png', [0, 0, 1000, 1000], 'Reference: 1-hero.png (its face is the happy grin; the spike carries the neutral smile)', D)}
${img('shots/cine_head_34.png', `${tag('cinematic')} film, Ultra effects`, D)}
${img('shots/ultra_head_34.png', `${tag('ultra')} in-game body atlas`, D)}
${ok('webgpu_head_34') ? img('shots/webgpu_head_34.png', `${tag('cinematic')} the same on the WebGPU renderer`, D) : blank("WebGPU: not available in this PC's headless Chrome (the phone check tests it)")}
${img('shots/webp_head_34.png', `${tag('cinematic')} WebP textures (the others are KTX2: ETC1S colour, UASTC normals)`, D)}
${img('shots/etc1s_head_34.png', `${tag('cinematic')} KTX2 with ETC1S normals too (smallest)`, D)}
</div>
<h2>2 · Head, front and side</h2>
<div class="row">
${ref('2-turnaround.png', [36, 129, 452, 452], 'Reference: 2-turnaround.png, front', D)}
${img('shots/cine_head_front.png', `${tag('cinematic')} front`, D)}
${ref('3-faces.png', [0, 0, 362, 325], 'Reference: 3-faces.png, neutral', D)}
${ref('2-turnaround.png', [394, 129, 452, 452], 'Reference: 2-turnaround.png, side', D)}
${img('shots/cine_head_side.png', `${tag('cinematic')} side`, D)}
</div>
<h2>3 · Front paw</h2>
<div class="row">
${ref('1-hero.png', [455, 880, 320, 320], 'Reference: 1-hero.png, front paw', D)}
${ref('4-details.png', [1027, 0, 509, 427], 'Reference: 4-details.png, paw', D)}
${img('shots/ultra_paw_34.png', `${tag('ultra')} in-game body atlas`, D)}
</div>
<h2>4 · What the Performance check draws on the phone (the stand-in: this head, four paws, a grey-box torso)</h2>
<div class="row">
${img('shots/check_battle.png', 'Battle: two stand-ins, effects bursts', D)}
${img('shots/check_card.png', 'Monster Card close-up: cinematic set, depth of field', D)}
${benchTable(st)}
</div>
<h2>5 · At phone thumbnail sizes</h2>
<div class="cols"><div class="small">
${img('shots/ultra_head_34_s64.png', '64 px', 64)}${img('shots/ultra_head_front_s64.png', '64 px, front', 64)}
${img('shots/ultra_head_34_s100.png', '100 px', 100)}${img('shots/ultra_head_34_s200.png', '200 px', 200)}
<figure><div class="img" style="${crop(REF + '1-hero.png', IMG['1-hero.png']!, 0, 0, 1000, 1000, 64)}"></div><figcaption>reference, 64 px</figcaption></figure>
<figure><div class="img" style="${crop(REF + '1-hero.png', IMG['1-hero.png']!, 0, 0, 1000, 1000, 100)}"></div><figcaption>reference, 100 px</figcaption></figure>
</div>
<table><tr><th colspan="3">What ships (measured)</th></tr><tr><th></th><th>KTX2, ETC1S everywhere (the phone)</th><th>WebP</th></tr>
<tr><td>Body atlas ${tex.atlas.base?.px ?? 0}² (colour + normal + ORM)</td><td>${kb(etc1sBytes('atlas'))}</td><td>${kb(sum('atlas', 'webp'))}</td></tr>
<tr><td>Cinematic head set ${tex.cine.base?.px ?? 0}²</td><td>${kb(etc1sBytes('cine'))}</td><td>${kb(sum('cine', 'webp'))}</td></tr>
<tr><td>Mesh .glb (meshopt)</td><td colspan="2">${kb(st.glb.bytes)} · ${Object.entries(st.glb.triangles).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(' · ')}</td></tr>
</table>
</div>
<p style="margin-top:14px;color:#555">GPUs on this PC: WebGL ${st.gpu?.webgl ?? '?'} · WebGPU ${st.gpu?.webgpu ?? '?'}</p>
</body></html>`
}

// ---------------------------------------------------------------------------- main
async function main(): Promise<void> {
  mkdirSync(PUB, { recursive: true })
  mkdirSync(OUT, { recursive: true })
  const statsPath = join(OUT, 'stats.json')
  const prev = (existsSync(statsPath) ? JSON.parse(readFileSync(statsPath, 'utf8')) : {}) as Partial<Stats>
  const build = existsSync(join(SRC, 'stats_build.json')) ? (JSON.parse(readFileSync(join(SRC, 'stats_build.json'), 'utf8')) as Stats['build']) : undefined
  let glb = prev.glb
  let textures = prev.textures
  if (!has('--no-encode') || !glb || !textures?.cine) {
    glb = await optimiseGlb()
    textures = { atlas: encodeSet('atlas'), cine: encodeSet('cine') }
    if (existsSync(join(SRC, 'standin.glb')) && existsSync(join(SRC, 'standin_base.png'))) {
      textures.standin = encodeSet('standin')
      prev.standinGlb = await optimiseGlb('standin')
    }
    console.log('glb', glb, 'textures', JSON.stringify(textures))
  }
  const stats: Stats = { build, glb, textures, shots: prev.shots, gpu: prev.gpu, standinGlb: prev.standinGlb, bench: prev.bench }
  const server = await startServer()
  try {
    const b = await launch()
    try {
      const page = await openShotPage(b)
      stats.gpu = await gpuInfo(page)
      console.log('gpu', stats.gpu)
      if (!has('--no-shots')) stats.shots = await shots(page)
      if (!has('--no-bench')) {
        const rows: Record<string, unknown>[] = []
        for (const [label, o] of [
          ['Battle, two stand-ins, 2.0×, all effects', { kind: 'battle', dpr: 2 }],
          ['Battle, two stand-ins, 2.5×, all effects', { kind: 'battle', dpr: 2.5 }],
          ['Battle, 2.5×, WebP textures', { kind: 'battle', dpr: 2.5, format: 'webp' }],
          ['Monster Card close-up, cinematic + depth of field, 2.5×', { kind: 'card', dpr: 2.5 }],
          ['Meadow Dash, four stand-ins, 2.5×', { kind: 'dash', dpr: 2.5 }],
          ['Battle, 2.5×, WebGPU renderer', { kind: 'battle', dpr: 2.5, backend: 'webgpu' }],
        ] as const) {
          try {
            const r = await page.evaluate((x) => (window as unknown as { __perf: { bench(o: unknown): Promise<Record<string, unknown>> } }).__perf.bench(x), { width: 412, height: 560, ...o })
            rows.push({ label, ...r })
            console.log('bench', label, JSON.stringify(r))
          } catch (e) {
            const msg = (e as Error).message.split('\n')[0]
            rows.push({ label, error: msg })
            console.warn('bench failed', label, msg)
          }
        }
        stats.bench = rows
      }
      writeFileSync(statsPath, JSON.stringify(stats, null, 1) + '\n')
      writeFileSync(join(OUT, 'index.html'), sheetHtml(stats))
      const sheet = await b.newPage({ viewport: { width: 1944, height: 1200 }, deviceScaleFactor: 1 })
      await sheet.goto(`http://localhost:${PORT}/wildsong-ranch/art-review/detail-spike/index.html`)
      await sheet.waitForLoadState('networkidle')
      await sheet.screenshot({ path: join(OUT, 'sheet.png'), fullPage: true })
      console.log('sheet', join(OUT, 'sheet.png'))
    } finally {
      await b.close()
    }
  } finally {
    stopServer(server)
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
