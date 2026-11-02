/**
 * docs/BATTLE_3D.md §8: the Guild arena crowd's review. Serves the built game (`vite preview`), opens Battle 3D in the
 * installed Chrome at a phone viewport (412 × 892 at 2.625×), and takes stills of the crowd at Fame 10, 40, 70 and 100
 * (the battle paused, the side-on camera), a close-up from behind, the fly-in and the win's standing ovation; framed
 * stills from the crowd viewer (tools/art/crowd-viewer.html: Fame, cheers, close-ups, Lite, Reduce motion); then
 * art-review/arena-guild/crowd-sheet.png with the crowd's counts, triangles, draws and CPU time.
 *
 *   node tools/art/crowd-review.ts [--no-build] [--viewer-only] [--only <shot>]
 */
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, type Browser, type Page } from '@playwright/test'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const OUT = join(ROOT, 'art-review', 'arena-guild')
const PORT = 4173
const URL = `http://localhost:${PORT}/wildsong-ranch/#lab/battle3d`
const IS_WIN = process.platform === 'win32'
const VIEW = { width: 412, height: 892 }
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

function stopPort(): void {
  if (!IS_WIN) return
  try {
    const out = execFileSync('netstat', ['-ano'], { encoding: 'utf8' })
    for (const line of out.split('\n')) if (line.includes(`:${PORT} `) && /LISTENING/.test(line)) execFileSync('taskkill', ['/PID', line.trim().split(/\s+/).pop()!, '/F', '/T'], { stdio: 'ignore' })
  } catch {
    /* nothing listening */
  }
}

async function serve(): Promise<ChildProcess> {
  stopPort()
  const p = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], { cwd: ROOT, stdio: 'ignore', shell: IS_WIN })
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(`http://localhost:${PORT}/wildsong-ranch/`)).ok) return p
    } catch {
      /* not yet */
    }
    await wait(1000)
  }
  throw new Error('vite preview did not start')
}

async function open(b: Browser): Promise<Page> {
  const ctx = await b.newContext({ viewport: VIEW, deviceScaleFactor: 2.625, hasTouch: true, isMobile: true })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.error('page error:', e.message))
  page.on('console', (m) => m.type() === 'error' && console.error('console:', m.text()))
  await page.goto(URL, { timeout: 240_000, waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => ['intro', 'error'].includes((window as unknown as { __battle3d?: { phase: string } }).__battle3d?.phase ?? ''), null, { timeout: 240_000 })
  return page
}

const H = `(window).__battle3d`
const run = (page: Page, js: string) => page.evaluate(js)

async function gameShots(rows: Record<string, unknown>): Promise<void> {
  if (!process.argv.includes('--no-build')) execFileSync(IS_WIN ? 'npx.cmd' : 'npx', ['vite', 'build'], { cwd: ROOT, stdio: 'inherit', shell: IS_WIN })
  const server = await serve()
  try {
    const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox', '--enable-unsafe-webgpu'] })
    try {
      // the fly-in, seen from above
      let page = await open(b)
      await wait(3600)
      await page.screenshot({ path: join(OUT, 'crowd-flyin.png') })
      await page.context().close()
      // Fame 10 → 100, paused, side-on
      page = await open(b)
      await run(page, `${H}.skipIntro()`)
      await page.waitForFunction(`${H}.phase === 'fight'`, null, { timeout: 60_000 })
      await page.locator('.b3d__top .btn').last().waitFor()
      await page.getByRole('button', { name: /pause/i }).click().catch(() => undefined)
      for (const fame of [10, 40, 70, 100]) {
        await run(page, `${H}.crowdFame(${fame})`)
        await wait(2500)
        await page.screenshot({ path: join(OUT, `crowd-fame${fame}.png`) })
        rows[`fame${fame}`] = await run(page, `${H}.stats()`)
        console.log('fame', fame, JSON.stringify((rows[`fame${fame}`] as { crowd: unknown }).crowd))
      }
      await run(page, `${H}.setCamera('behind')`)
      await wait(2000)
      await page.screenshot({ path: join(OUT, 'crowd-behind.png') })
      // the win: Auto at ×4 to the end, then the standing ovation
      await run(page, `${H}.setCamera('side')`)
      await page.getByRole('button', { name: /resume/i }).click().catch(() => undefined)
      await run(page, `${H}.auto(true)`)
      await run(page, `${H}.speed(4)`)
      await page.waitForFunction(() => document.querySelector('.b3d__result') !== null, null, { timeout: 180_000 }).catch(() => undefined)
      await wait(1800)
      await page.screenshot({ path: join(OUT, 'crowd-ovation.png') })
      rows.ovation = await run(page, `${H}.stats()`)
      await page.context().close()
    } finally {
      await b.close()
    }
  } finally {
    stopPort()
    server.kill()
  }
}

/** The crowd viewer (tools/art/crowd-viewer.html) through Vite's dev server: framed stills of the stands. */
const SHOTS: { file: string; q: string; label: string }[] = [
  { file: 'v-fame10', q: 'view=stands&fame=10', label: 'Fame 10' },
  { file: 'v-fame40', q: 'view=stands&fame=40', label: 'Fame 40' },
  { file: 'v-fame70', q: 'view=stands&fame=70', label: 'Fame 70' },
  { file: 'v-fame100', q: 'view=stands&fame=100', label: 'Fame 100' },
  { file: 'v-cheer', q: 'view=stands&fame=100&cheer=huge&t=6.9&cheerAt=5.8', label: 'Fame 100, a KO cheer (1.1 s after it starts on the far side)' },
  { file: 'v-front', q: 'view=front&fame=100&cheer=big&t=6.9&cheerAt=5.9', label: 'Close-up: the front rows in a big cheer' },
  { file: 'v-near', q: 'view=near&fame=100', label: 'By the fence (the behind camera distance)' },
  { file: 'v-gate', q: 'view=gateA&fame=100', label: 'Toward gate A: standing folk and cut-outs' },
  { file: 'v-nearB', q: 'view=nearB&fame=70', label: 'The near stand by gate B, Fame 70' },
  { file: 'v-open', q: 'view=open&fame=100&cheer=ovation&t=8&cheerAt=5', label: 'The open front, the win ovation' },
  { file: 'v-top', q: 'view=top&fame=70', label: 'The fly-in third stop, Fame 70' },
  { file: 'v-lite', q: 'view=stands&fame=100&lite=1', label: 'Lite, Fame 100 (half the spots)' },
  { file: 'v-reduce', q: 'view=stands&fame=100&reduce=1&cheer=huge&t=6.9&cheerAt=5.8', label: 'Reduce motion, the same KO cheer (gentle, no hops)' },
]
const VPORT = 5176

async function viewerShots(rows: Record<string, unknown>): Promise<void> {
  const server = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', '--config', 'vite.perf.config.ts', '--port', String(VPORT), '--strictPort'], { cwd: ROOT, stdio: 'ignore', shell: IS_WIN })
  const base = `http://localhost:${VPORT}/wildsong-ranch/tools/art/crowd-viewer.html`
  try {
    for (let i = 0; i < 120; i++) {
      try {
        if ((await fetch(base)).ok) break
      } catch {
        /* not yet */
      }
      await wait(1000)
    }
    const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'] })
    try {
      for (const s of SHOTS) {
        if (ONLY && !s.file.includes(ONLY)) continue
        const page = await b.newPage({ viewport: { width: 600, height: 800 }, deviceScaleFactor: 1 })
        page.on('pageerror', (e) => console.error('page error:', e.message))
        page.on('console', (m) => m.type() === 'error' && console.error('console:', m.text()))
        await page.goto(`${base}?w=600&h=800&${s.q}`)
        await page.waitForFunction(() => (window as unknown as { __crowd?: { ready: boolean } }).__crowd?.ready === true, null, { timeout: 240_000 })
        const r = (await page.evaluate(() => (window as unknown as { __crowd: { shot(): unknown } }).__crowd.shot())) as { png: string; calls: number; triangles: number; cpuMs: number; crowd: unknown }
        writeFileSync(join(OUT, `${s.file}.png`), Buffer.from(r.png.slice(r.png.indexOf(',') + 1), 'base64'))
        rows[s.file] = { calls: r.calls, triangles: r.triangles, cpuMs: r.cpuMs, crowd: r.crowd }
        console.log('shot', s.file, JSON.stringify(rows[s.file]))
        await page.close()
      }
    } finally {
      await b.close()
    }
  } finally {
    if (IS_WIN && server.pid) execFileSync('taskkill', ['/PID', String(server.pid), '/F', '/T'], { stdio: 'ignore' })
    else server.kill()
  }
}

const ONLY = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : undefined

async function main(): Promise<void> {
  mkdirSync(OUT, { recursive: true })
  const rows: Record<string, unknown> = {}
  await viewerShots(rows)
  if (ONLY) return
  if (!process.argv.includes('--viewer-only')) await gameShots(rows)
  else if (existsSync(join(OUT, 'crowd-stats.json'))) {
    // keep the last run's game stills' numbers
    const last = JSON.parse(readFileSync(join(OUT, 'crowd-stats.json'), 'utf8')) as Record<string, unknown>
    for (const [k, v] of Object.entries(last)) if (!(k in rows)) rows[k] = v
  }
  writeFileSync(join(OUT, 'crowd-stats.json'), JSON.stringify(rows, null, 1))
  writeFileSync(join(OUT, 'crowd-sheet.html'), sheet(rows))
  const b = await chromium.launch({ channel: 'chrome', headless: true })
  const p = await b.newPage({ viewport: { width: 1700, height: 900 } })
  await p.goto('file://' + join(OUT, 'crowd-sheet.html').replace(/\\/g, '/'))
  await p.waitForLoadState('load')
  await p.screenshot({ path: join(OUT, 'crowd-sheet.png'), fullPage: true })
  await b.close()
  console.log('sheet', join(OUT, 'crowd-sheet.png'))
}

function sheet(rows: Record<string, unknown>): string {
  const c = (k: string) => ((rows[k] as { crowd?: Record<string, number> | null } | undefined)?.crowd ?? {}) as Record<string, number>
  const cap = (k: string, label: string) => {
    const s = c(k)
    return `${label}<br>${s.people ?? '?'} people + ${s.cutouts ?? '?'} cut-outs of ${s.spots ?? '?'} spots · ${s.draws ?? '?'} draws · ${(s.triangles ?? 0).toLocaleString()} tris · ${(s.cpuMs ?? 0).toFixed(2)} ms CPU`
  }
  const fig = (src: string, caption: string) => `<figure><img src="${src}" width="262"><figcaption>${caption}</figcaption></figure>`
  return `<!doctype html><meta charset="utf-8"><style>body{margin:0;padding:14px;background:#e4e6ea;font:13px/1.35 system-ui,Segoe UI,sans-serif;color:#1d2126;width:1660px}
h1{font-size:19px;margin:0 0 8px}.row{display:flex;gap:8px}figure{margin:0;background:#fff;border-radius:8px;padding:5px;box-shadow:0 1px 2px #0002}img{display:block;border-radius:4px}figcaption{font-size:11.5px;margin-top:4px;max-width:262px}</style>
<h1>The Guild arena's crowd (BATTLE_3D §8): the crowd viewer (the game's arena and crowd code, WebGL, 600 × 800), then the game itself (412 × 892 at 2.625×)</h1>
<div class="row">${['v-fame10', 'v-fame40', 'v-fame70', 'v-fame100', 'v-cheer', 'v-reduce'].map((k) => fig(k + '.png', cap(k, SHOTS.find((s) => s.file === k)!.label))).join('')}</div>
<div class="row" style="margin-top:8px">${['v-front', 'v-near', 'v-gate', 'v-nearB', 'v-open', 'v-top'].map((k) => fig(k + '.png', SHOTS.find((s) => s.file === k)!.label)).join('')}</div>
<div class="row" style="margin-top:8px">${fig('v-lite.png', cap('v-lite', 'Lite, Fame 100'))}${fig('crowd-fame10.png', cap('fame10', 'In the game: Fame 10'))}${fig('crowd-fame100.png', cap('fame100', 'In the game: Fame 100'))}${fig('crowd-behind.png', 'In the game: behind camera')}${fig('crowd-ovation.png', cap('ovation', 'In the game: the win ovation'))}${fig('crowd-flyin.png', 'In the game: the fly-in at 3.6 s (Fame 60)')}</div></html>`
}

void main()
