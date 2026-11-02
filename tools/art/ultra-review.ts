/**
 * Art 2.1 review sheet for one Ultra look (docs/ART_2_DETAIL.md §8, §9 P1.1; ART_2_PLAN §6).
 *
 *   node tools/art/ultra-review.ts [breed] [--no-shots]
 *
 * Renders public/models/monsters-ultra/<breed>.glb in the film look (the Performance check's renderer, src/art3d/perf/,
 * through tools/art/ultra-viewer/) in headless Chrome on this PC's GPU: the turnaround angles, the head, the clips' key
 * frames, Songheart, and 64 / 100 / 200 px; lays them beside the reference pictures (chatgpt/monsters/01-<breed>/) and
 * the Blender sheets (tools/blender/out/<breed>-ultra/review/), with the measured budget, and saves
 * art-review/<breed>-ultra/sheet.png.
 */
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, type Browser, type Page } from '@playwright/test'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const PORT = 5181
const IS_WIN = process.platform === 'win32'
const args = process.argv.slice(2)
const breed = args.find((a) => !a.startsWith('--')) ?? 'puddlepup'
const OUT = join(ROOT, 'art-review', `${breed}-ultra`)
const SHOTS = join(OUT, 'shots')
const BASE = `http://localhost:${PORT}/wildsong-ranch/`

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
  const proc = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', '--config', 'tools/art/ultra-viewer/vite.config.ts'], { cwd: ROOT, stdio: 'ignore', shell: IS_WIN })
  if (!(await waitFor(`${BASE}tools/art/ultra-viewer/index.html`, 90_000))) throw new Error('the viewer dev server did not start')
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

interface ShotOpts { az?: number; el?: number; target?: [number, number, number]; frame?: number; size?: number; clip?: string; t?: number; variant?: string; format?: string; dpr?: number; raw?: boolean }
const HEAD: Partial<ShotOpts> = { target: [0, -0.42, 0.76], frame: 0.98 }
const SHOT_LIST: [string, ShotOpts][] = [
  ['turn_front', { az: 0, el: 6 }],
  ['turn_34', { az: 35, el: 14 }],
  ['turn_side', { az: 90, el: 4 }],
  ['turn_back', { az: 180, el: 10 }],
  ['turn_34_other', { az: -35, el: 14 }],
  ['head_34', { ...HEAD, az: 26, el: 12 }],
  ['head_front', { ...HEAD, az: 0, el: 4 }],
  ['head_side', { ...HEAD, az: 90, el: 4 }],
  ['webp_34', { az: 35, el: 14, format: 'webp' }],
  ['raw_34', { az: 35, el: 14, raw: true }],
  ['variant_34', { az: 35, el: 14, variant: 'songheart-puddlepup' }],
  ['variant_back', { az: 160, el: 14, variant: 'songheart-puddlepup' }],
  ['s64', { az: 35, el: 14, size: 64 }],
  ['s64_front', { az: 0, el: 6, size: 64 }],
  ['s100', { az: 35, el: 14, size: 100 }],
  ['s200', { az: 35, el: 14, size: 200 }],
  ['clip_battle_idle', { az: 35, el: 14, clip: 'battle_idle', t: 0.25, size: 500 }],
  ['clip_strafe_l', { az: 20, el: 14, clip: 'strafe_l', t: 0.25, size: 500 }],
  ['clip_strafe_r', { az: 20, el: 14, clip: 'strafe_r', t: 0.75, size: 500 }],
  ['clip_sidestep_l', { az: 0, el: 10, clip: 'sidestep_l', t: 0.5, size: 500 }],
  ['clip_sidestep_r', { az: 0, el: 10, clip: 'sidestep_r', t: 0.5, size: 500 }],
  ['clip_strike', { az: 70, el: 10, clip: 'strike', t: 0.54, size: 500, frame: 2.1 }],
  ['clip_hit', { az: 35, el: 14, clip: 'hit', t: 0.3, size: 500 }],
  ['clip_hit_heavy', { az: 35, el: 14, clip: 'hit_heavy', t: 0.3, size: 500 }],
  ['clip_ko', { az: 35, el: 20, clip: 'ko', t: 0.99, size: 500, frame: 2.1, target: [0, -0.1, 0.35] }],
  ['clip_win', { az: 35, el: 14, clip: 'win', t: 0.2, size: 500 }],
  ['clip_walk', { az: 90, el: 6, clip: 'walk', t: 0.3, size: 500 }],
  ['clip_blink', { ...HEAD, az: 20, el: 8, clip: 'blink', t: 0.45, size: 500 }],
]

type ShotInfo = { ok: boolean; triangles?: number; cards?: number; error?: string; clips?: string[] }

async function shots(page: Page): Promise<Record<string, ShotInfo>> {
  mkdirSync(SHOTS, { recursive: true })
  const info: Record<string, ShotInfo> = {}
  for (const [file, o] of SHOT_LIST) {
    try {
      const r = await page.evaluate((x) => (window as unknown as { __ultra: { shot(o: unknown): Promise<{ png: string; triangles: number; cards: number; clips: string[] }> } }).__ultra.shot(x), { look: breed, ...o })
      writeFileSync(join(SHOTS, `${file}.png`), Buffer.from(r.png.slice(r.png.indexOf(',') + 1), 'base64'))
      info[file] = { ok: true, triangles: r.triangles, cards: r.cards, clips: file === 'turn_front' ? r.clips : undefined }
      console.log('shot', file, r.triangles, 'tris', r.cards, 'cards')
    } catch (e) {
      info[file] = { ok: false, error: (e as Error).message.split('\n')[0] }
      console.warn('shot failed', file, info[file]!.error)
    }
  }
  return info
}

// ---------------------------------------------------------------------------- the sheet
const REF_DIR = join(ROOT, 'chatgpt', 'monsters', '01-puddlepup')
const REF = '../../chatgpt/monsters/01-puddlepup/'
function pngSize(file: string): [number, number] {
  const b = readFileSync(join(REF_DIR, file))
  return [b.readUInt32BE(16), b.readUInt32BE(20)]
}
function crop(file: string, x: number, y: number, w: number, h: number, D: number): string {
  const [nw, nh] = pngSize(file)
  const s = D / Math.max(w, h)
  return `background:#8a8b8f url('${REF}${file}') no-repeat; background-size:${(nw * s).toFixed(1)}px ${(nh * s).toFixed(1)}px; background-position:${(-x * s + (D - w * s) / 2).toFixed(1)}px ${(-y * s + (D - h * s) / 2).toFixed(1)}px; width:${D}px; height:${D}px;`
}
const ref = (f: string, r: [number, number, number, number], cap: string, D: number) =>
  existsSync(join(REF_DIR, f)) ? `<figure class="ref"><div class="img" style="${crop(f, ...r, D)}"></div><figcaption>${cap}</figcaption></figure>` : ''
const img = (src: string, cap: string, D: number) => `<figure><img src="${src}" width="${D}" height="${D}"><figcaption>${cap}</figcaption></figure>`
const wide = (src: string, cap: string, W: number) => `<figure><img src="${src}" width="${W}"><figcaption>${cap}</figcaption></figure>`
const mb = (n: number) => `${(n / 1048576).toFixed(2)} MB`

interface Budget {
  triangles: number; trianglesByMesh: Record<string, number>; cards: number; cardLayers: number; joints: number; animations: number; animationBytes: number
  download: { glb: number; ktx2: { body: number; variants: number }; webp: { body: number; variants: number }; totalKtx2: number; totalWebp: number }
  problems: string[]
}

function sheetHtml(side: { budget: Budget; clips: Record<string, { seconds: number; rootSpeed: number; rootDir?: number[]; markers: { name: string; t: number }[] }> }, info: Record<string, ShotInfo>, verdicts: string): string {
  const D = 280
  const b = side.budget
  const ok = (f: string) => info[f]?.ok === true
  const shotOr = (f: string, cap: string, d = D) => (ok(f) ? img(`shots/${f}.png`, cap, d) : `<figure><div class="img" style="width:${d}px;height:${d}px"></div><figcaption>${cap}: ${info[f]?.error ?? 'missing'}</figcaption></figure>`)
  const blender = join(ROOT, 'tools', 'blender', 'out', `${breed}-ultra`, 'review')
  const bl = (f: string, cap: string) => (existsSync(join(blender, f)) ? wide(`../../tools/blender/out/${breed}-ultra/review/${f}`, cap, 760) : '')
  const clipRows = Object.entries(side.clips)
    .filter(([n]) => ['walk', 'battle_idle', 'step_fwd', 'step_back', 'strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r', 'strike', 'hit', 'hit_heavy', 'ko', 'win', 'blink'].includes(n))
    .map(([n, c]) => `<tr><td>${n}</td><td>${c.seconds.toFixed(3)} s</td><td>${c.rootSpeed ? `${c.rootSpeed} m/s ${c.rootDir ? `[${c.rootDir.join(', ')}]` : ''}` : ''}</td><td>${c.markers.map((m) => `${m.name} ${m.t}`).join(', ')}</td></tr>`)
    .join('')
  return `<!doctype html><html><head><meta charset="utf-8"><title>${breed} Ultra review</title><style>
body{margin:0;padding:18px 22px;background:#e4e6ea;font:14px/1.4 system-ui,Segoe UI,sans-serif;color:#1d2126;width:2440px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:18px 0 6px} p{margin:2px 0 8px;max-width:2300px}
.row{display:flex;gap:10px;flex-wrap:wrap} figure{margin:0;background:#fff;border-radius:8px;padding:6px;box-shadow:0 1px 2px #0002}
figure.ref{background:#f3ead8} figure img,.img{display:block;border-radius:4px;background:#8a8b8f} figcaption{font-size:12.5px;margin-top:5px;max-width:${D}px}
.small{display:flex;gap:14px;align-items:flex-end;background:#fff;border-radius:8px;padding:10px;box-shadow:0 1px 2px #0002}
table{border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 2px #0002} td,th{padding:4px 10px;border-bottom:1px solid #e4e6ea;text-align:left;font-size:13px} th{background:#f2f3f5}
.cols{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap} pre{white-space:pre-wrap;font-size:12.5px;background:#fff;padding:10px;border-radius:8px;max-width:1150px}
</style></head><body>
<h1>${breed}, Art 2.1 Ultra (P1.1): the whole monster, rigged and animated</h1>
<p>three.js r186 on this PC's GPU, the Performance check's film renderer (Ultra effects: soft key-light shadow, GTAO, bloom, grading, 4× MSAA; no outlines), KTX2 ETC1S textures. Beige frames are the reference pictures. ${b.triangles.toLocaleString()} triangles · ${b.cards.toLocaleString()} fur cards in ${b.cardLayers} layers · ${b.joints} joints · ${b.animations} clips.</p>
<h2>1 · Turnaround</h2>
<div class="row">
${ref('2-turnaround.png', [10, 175, 540, 560], 'Reference: front', D)}${shotOr('turn_front', 'front')}
${ref('2-turnaround.png', [515, 175, 740, 560], 'Reference: side', D)}${shotOr('turn_side', 'side')}
${ref('2-turnaround.png', [1180, 175, 500, 560], 'Reference: back', D)}${shotOr('turn_back', 'back')}
${shotOr('turn_34', 'three-quarter')}${ref('1-hero.png', [0, 0, 1254, 1254], 'Reference: hero', D)}
</div>
<h2>2 · Head (round 6 fixes)</h2>
<div class="row">
${ref('3-faces.png', [0, 0, 362, 325], 'Reference: neutral', D)}${shotOr('head_front', 'front')}${shotOr('head_34', 'three-quarter')}${shotOr('head_side', 'side')}
${ref('4-details.png', [0, 0, 510, 427], 'Reference: head detail', D)}${ref('4-details.png', [513, 0, 510, 427], 'Reference: eye', D)}
</div>
<h2>3 · Clips (key frames)</h2>
<div class="row">
${shotOr('clip_battle_idle', 'battle_idle', 230)}${shotOr('clip_walk', 'walk', 230)}${shotOr('clip_strafe_l', 'strafe_l', 230)}${shotOr('clip_strafe_r', 'strafe_r', 230)}${shotOr('clip_sidestep_l', 'sidestep_l (mid-hop)', 230)}${shotOr('clip_sidestep_r', 'sidestep_r (mid-hop)', 230)}
${shotOr('clip_strike', 'strike (impact)', 230)}${shotOr('clip_hit', 'hit', 230)}${shotOr('clip_hit_heavy', 'hit_heavy', 230)}${shotOr('clip_ko', 'ko (end)', 230)}${shotOr('clip_win', 'win (airborne)', 230)}${shotOr('clip_blink', 'blink (closed)', 230)}
</div>
<h2>4 · Songheart Puddlepup</h2>
<div class="row">${ref('variant-songheart-puddlepup.png', [0, 0, 1536, 1024], 'Reference: variant', D)}${shotOr('variant_34', 'three-quarter')}${shotOr('variant_back', 'back')}${shotOr('turn_34_other', 'base, other side')}${shotOr('webp_34', 'WebP textures (the rest are KTX2)')}${shotOr('raw_34', 'the .glb materials as loaded (no card edge fade)')}</div>
<h2>5 · Phone sizes</h2>
<div class="cols"><div class="small">
${shotOr('s64', '64 px', 64)}${shotOr('s64_front', '64 px, front', 64)}${shotOr('s100', '100 px', 100)}${shotOr('s200', '200 px', 200)}
${ref('1-hero.png', [0, 0, 1254, 1254], 'ref 64', 64)}${ref('1-hero.png', [0, 0, 1254, 1254], 'ref 100', 100)}
</div>
<table><tr><th colspan="2">What ships (measured)</th></tr>
<tr><td>Triangles</td><td>${b.triangles.toLocaleString()} (${Object.entries(b.trianglesByMesh).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(' · ')})</td></tr>
<tr><td>Fur cards</td><td>${b.cards.toLocaleString()} in ${b.cardLayers} layers</td></tr>
<tr><td>Joints</td><td>${b.joints}</td></tr>
<tr><td>Mesh + clips .glb (meshopt)</td><td>${mb(b.download.glb)} (animations ${mb(b.animationBytes)})</td></tr>
<tr><td>Body atlas 2048² (colour + normal + ORM)</td><td>KTX2 ${mb(b.download.ktx2.body)} · WebP ${mb(b.download.webp.body)}</td></tr>
<tr><td>Songheart colour map</td><td>KTX2 ${mb(b.download.ktx2.variants)} · WebP ${mb(b.download.webp.variants)}</td></tr>
<tr><td><b>Download, everything</b></td><td><b>KTX2 ${mb(b.download.totalKtx2)} · WebP ${mb(b.download.totalWebp)}</b> (cap 8 MB)</td></tr>
<tr><td>Budget problems</td><td>${b.problems.length ? b.problems.join('; ') : 'none'}</td></tr>
</table>
<table><tr><th>clip</th><th>length</th><th>root speed (model m/s, glTF dir)</th><th>markers</th></tr>${clipRows}</table>
</div>
${verdicts ? `<h2>6 · Fresh-eyes verdicts</h2><pre>${verdicts}</pre>` : ''}
<h2>7 · Blender review sheets (EEVEE, the same baked maps)</h2>
<div class="row">${bl('turnaround.png', 'turnaround')}${bl('poses.png', 'key poses')}${bl('variant.png', 'Songheart')}${bl('head.png', 'head')}</div>
</body></html>`
}

async function main(): Promise<void> {
  mkdirSync(OUT, { recursive: true })
  const sidePath = join(ROOT, 'public', 'models', 'monsters-ultra', `${breed}.json`)
  const side = JSON.parse(readFileSync(sidePath, 'utf8'))
  const infoPath = join(OUT, 'shots.json')
  let info: Record<string, ShotInfo> = existsSync(infoPath) ? JSON.parse(readFileSync(infoPath, 'utf8')) : {}
  const verdictPath = join(OUT, 'verdicts.txt')
  const verdicts = existsSync(verdictPath) ? readFileSync(verdictPath, 'utf8').replace(/</g, '&lt;') : ''
  const server = await startServer()
  try {
    const b: Browser = await chromium.launch({
      channel: 'chrome',
      headless: true,
      args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'],
    })
    try {
      if (!args.includes('--no-shots')) {
        const page = await b.newPage({ viewport: { width: 1300, height: 1300 }, deviceScaleFactor: 1 })
        page.on('pageerror', (e) => console.error('page error:', e.message))
        page.on('console', (m) => {
          if (m.type() === 'error') console.error('console:', m.text())
        })
        await page.goto(`${BASE}tools/art/ultra-viewer/index.html`)
        await page.waitForFunction(() => (window as unknown as { __ultra?: { ready: boolean } }).__ultra?.ready === true, null, { timeout: 120_000 })
        info = await shots(page)
        writeFileSync(infoPath, JSON.stringify(info, null, 1) + '\n')
      }
      writeFileSync(join(OUT, 'index.html'), sheetHtml(side, info, verdicts))
      const sheet = await b.newPage({ viewport: { width: 2484, height: 1400 }, deviceScaleFactor: 1 })
      await sheet.goto(`${BASE}art-review/${breed}-ultra/index.html`)
      await sheet.waitForLoadState('networkidle')
      await sheet.screenshot({ path: join(OUT, 'sheet.png'), fullPage: true })
      console.log('sheet', join(OUT, 'sheet.png'), readdirSync(SHOTS).length, 'shots')
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
