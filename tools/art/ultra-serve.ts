/**
 * Art 2.1: the review viewer's dev server and headless Chrome, shared by tools/art/ultra-review.ts and
 * tools/art/lineup.ts. The viewer (tools/art/ultra-viewer/) draws Ultra monsters with the game's film renderer.
 */
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from 'node:net'
import { chromium, type Browser, type Page } from '@playwright/test'

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
/**
 * The viewer server's port and base URL: each run takes a free port (startServer sets these; live bindings, so the
 * review, the lineup and viewerPage read the current values), so two builders' reviews never kill each other's server.
 */
export let PORT = 5181
export let BASE = `http://localhost:${PORT}/wildsong-ranch/`

/** A port nothing listens on right now (the OS picks it). */
function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer()
    srv.unref()
    srv.on('error', reject)
    srv.listen(0, '127.0.0.1', () => {
      const addr = srv.address()
      const port = typeof addr === 'object' && addr ? addr.port : 0
      srv.close(() => (port ? resolve(port) : reject(new Error('no free port'))))
    })
  })
}
const IS_WIN = process.platform === 'win32'

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

export async function startServer(): Promise<ChildProcess> {
  // a free port per run (another review may hold one); strictPort fails fast if a race took it, and we try again
  for (let attempt = 0; attempt < 4; attempt++) {
    PORT = await freePort()
    BASE = `http://localhost:${PORT}/wildsong-ranch/`
    const proc = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', '--config', 'tools/art/ultra-viewer/vite.config.ts', '--port', String(PORT), '--strictPort'],
      { cwd: ROOT, stdio: 'ignore', shell: IS_WIN })
    if (await waitFor(`${BASE}tools/art/ultra-viewer/index.html`, 90_000)) return proc
    stopServer(proc)
  }
  throw new Error('the viewer dev server did not start on a free port')
}

export function stopServer(p: ChildProcess): void {
  if (IS_WIN && p.pid) {
    try {
      execFileSync('taskkill', ['/PID', String(p.pid), '/F', '/T'], { stdio: 'ignore' })
    } catch {
      /* gone */
    }
  } else p.kill()
}

export function launch(): Promise<Browser> {
  return chromium.launch({
    channel: 'chrome',
    headless: true,
    args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'],
  })
}

/** A page on the viewer, ready for window.__ultra calls. */
export async function viewerPage(b: Browser, size = 1300): Promise<Page> {
  const page = await b.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 })
  page.on('pageerror', (e) => console.error('page error:', e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') console.error('console:', m.text())
  })
  await page.goto(`${BASE}tools/art/ultra-viewer/index.html`)
  await page.waitForFunction(() => (window as unknown as { __ultra?: { ready: boolean } }).__ultra?.ready === true, null, { timeout: 120_000 })
  return page
}

export function savePng(dataUrl: string): Buffer {
  return Buffer.from(dataUrl.slice(dataUrl.indexOf(',') + 1), 'base64')
}

/** The shipped sidecar of a look (public/models/monsters-ultra/<breed>.json). */
export interface UltraSide {
  look: string
  heightUnits: number
  restHeight: number
  bounds: { min: number[]; max: number[] }
  review?: { centre: number[]; size: number; head: { target: number[]; size: number } } | null
  variants: Record<string, { colorAttribute?: string }>
  clips: Record<string, { seconds: number; rootSpeed: number; rootDir?: number[]; markers: { name: string; t: number }[] }>
  [k: string]: unknown
}

export function readSide(breed: string): UltraSide {
  const p = join(ROOT, 'public', 'models', 'monsters-ultra', `${breed}.json`)
  if (!existsSync(p)) throw new Error(`no ${p}: ship it first (npm run art:ultra -- ${breed})`)
  return JSON.parse(readFileSync(p, 'utf8')) as UltraSide
}

/** A grown form's look ends with -grown (`hearthwing-grown`, recipe breeds/hearthwing_grown_ultra.py; RECIPE.md). */
export const GROWN_SUFFIX = '-grown'
export const isGrown = (look: string): boolean => look.endsWith(GROWN_SUFFIX)
/** The breed a look belongs to: `hearthwing-grown` → `hearthwing`; any other look is its own breed. */
export const baseBreed = (look: string): string => (isGrown(look) ? look.slice(0, -GROWN_SUFFIX.length) : look)
/** The reference pictures' name prefix: a grown form's are `grown-1-hero.png`, `grown-2-turnaround.png`, … in its breed's folder. */
export const refPrefix = (look: string): string => (isGrown(look) ? 'grown-' : '')

/**
 * The breed's reference folder, chatgpt/monsters/<nn>-<breed>/ (reference only: never shipped), or null. A grown form
 * (`<breed>-grown`) uses its breed's folder (its pictures carry the `grown-` prefix, refPrefix).
 */
export function refDir(breed: string): string | null {
  const root = join(ROOT, 'chatgpt', 'monsters')
  if (!existsSync(root)) return null
  const dirs = readdirSync(root)
  const hit = dirs.find((d) => d.replace(/^\d+-/, '') === breed) ?? (isGrown(breed) ? dirs.find((d) => d.replace(/^\d+-/, '') === baseBreed(breed)) : undefined)
  return hit ? join(root, hit) : null
}

const r2 = (v: number) => Math.round(v * 100) / 100

/**
 * The viewer's framing from the sidecar (Blender coordinates: −Y forward, Z up): the whole body, the head, a lying
 * pose, and the studio. Proportional to the rest height and the body's centre; a 1 m Puddlepup gets exactly the
 * framing the P1 sheets used (target [0, 0.02, 0.5], 1.75; head [0, −0.42, 0.76], 0.98; ko [0, −0.1, 0.35], 2.1).
 */
export function framing(side: UltraSide) {
  const h = side.restHeight
  const [, y0] = side.bounds.min as [number, number, number]
  const [, y1] = side.bounds.max as [number, number, number]
  const cy = (y0 + y1) / 2
  const length = y1 - y0
  const body = { target: [0, r2(cy - 0.08 * h), r2(0.507 * h)] as [number, number, number], frame: r2(Math.max(1.775 * h, 1.2 * length)) }
  const head = side.review?.head
    ? { target: side.review.head.target as [number, number, number], frame: side.review.head.size }
    : { target: [0, r2(y0 + 0.14 * length), r2(0.77 * h)] as [number, number, number], frame: r2(h) }
  const low = { target: [0, r2(cy - 0.2 * h), r2(0.355 * h)] as [number, number, number], frame: r2(Math.max(2.13 * h, 1.45 * length)) }
  const studio = { focus: [0, r2(0.507 * h), 0], reach: r2(1.62 * h) }
  return { body, head, low, studio }
}
