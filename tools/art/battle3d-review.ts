/**
 * docs/BATTLE_3D.md §8: the Battle 3D test build's review. Builds the game, serves dist/ with `vite preview`, and in
 * the installed Chrome (this PC's GPU, a 412 × 892 phone viewport at 2.625×) records one video per camera:
 *   1-intro (the fly-in and walk-on), 2-side, 3-behind, 4-cinematic (Auto at ×2 to the end: the Special, Signature and KO cuts),
 * plus a contact sheet of stills and stats.json (fps, render resolution, effect level, GPU/CPU ms, download sizes).
 *
 *   node tools/art/battle3d-review.ts [--no-build] [--seconds 14]
 *
 * Output: art-review/battle3d/ (gitignored). Videos are trimmed and converted to MP4 (H.264) with ffmpeg.
 */
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'
import { readFileSync } from 'node:fs'
import { chromium, type Browser, type Page } from '@playwright/test'
import { FFMPEG } from '../audio/opus.ts'

/** What the Battle 3D screen exposes for this script (src/ui/screens/battle3d/Battle3DScreen.tsx). */
declare global {
  interface Window {
    __battle3d?: { phase: string; setCamera(c: 'side' | 'behind'): void; skipIntro(): void; stats(): unknown; auto(on: boolean): void; speed(x: 1 | 2 | 4): void }
  }
}

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const OUT = join(ROOT, 'art-review', 'battle3d')
const PORT = 4173
const URL = `http://localhost:${PORT}/wildsong-ranch/#lab/battle3d`
const IS_WIN = process.platform === 'win32'
const args = process.argv.slice(2)
const has = (f: string) => args.includes(f)
const SECONDS = Number(args[args.indexOf('--seconds') + 1] ?? 14) || 14
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

function kill(p: ChildProcess): void {
  if (IS_WIN && p.pid) {
    try {
      execFileSync('taskkill', ['/PID', String(p.pid), '/F', '/T'], { stdio: 'ignore' })
    } catch {
      /* gone */
    }
  } else p.kill()
}

/** One recorded session: open the screen, run `script`, return the video and the seconds to keep. */
async function record(b: Browser, name: string, script: (page: Page, t0: number) => Promise<[number, number]>): Promise<void> {
  const dir = join(OUT, `.raw-${name}`)
  rmSync(dir, { recursive: true, force: true })
  const ctx = await b.newContext({ viewport: VIEW, deviceScaleFactor: 2.625, hasTouch: true, isMobile: true, recordVideo: { dir, size: { width: VIEW.width * 2, height: VIEW.height * 2 } } })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.error(`[${name}] page error:`, e.message))
  const t0 = Date.now()
  await page.goto(URL, { timeout: 240_000, waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__battle3d?.phase === 'intro' || window.__battle3d?.phase === 'error', null, { timeout: 240_000 })
  const [from, to] = await script(page, t0)
  await page.screenshot({ path: join(OUT, `${name}.png`) })
  await ctx.close()
  const raw = readdirSync(dir).find((f) => f.endsWith('.webm'))
  if (!raw) return
  execFileSync(FFMPEG, ['-y', '-loglevel', 'error', '-ss', String(from), '-i', join(dir, raw), '-t', String(Math.max(1, to - from)), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', join(OUT, `${name}.mp4`)])
  rmSync(dir, { recursive: true, force: true })
  console.log('video', name, `${(to - from).toFixed(1)} s`)
}

const since = (t0: number) => (Date.now() - t0) / 1000

async function fight(page: Page): Promise<void> {
  await page.evaluate(() => window.__battle3d!.skipIntro())
  await page.waitForFunction(() => window.__battle3d!.phase === 'fight', null, { timeout: 60_000 })
  await page.evaluate(() => window.__battle3d!.auto(true))
}

/** Sizes of what the test downloads: the models and the screen's code (gzipped). */
function sizes(): Record<string, number> {
  const out: Record<string, number> = {}
  const add = (label: string, dir: string, match: RegExp) => {
    if (!existsSync(dir)) return
    for (const f of readdirSync(dir)) if (match.test(f)) out[`${label}/${f}`] = statSync(join(dir, f)).size
  }
  add('monster', join(ROOT, 'public', 'models', 'monsters-ultra'), /^puddlepup\.(glb|json)$/)
  add('lite-monster', join(ROOT, 'public', 'models', 'monsters'), /^puddlepup\.(glb|json)$/)
  add('arena', join(ROOT, 'public', 'models', 'arenas', 'guild'), /^guild(_lite)?\.(glb|json)$/)
  const assets = join(ROOT, 'dist', 'assets')
  if (existsSync(assets)) for (const f of readdirSync(assets)) if (/^(duel3d|viewGpu|Battle3DScreen)-.*\.js$/.test(f)) out[`code-gz/${f}`] = gzipSync(readFileSync(join(assets, f))).length
  return out
}

async function main(): Promise<void> {
  mkdirSync(OUT, { recursive: true })
  if (!has('--no-build')) execFileSync(IS_WIN ? 'npx.cmd' : 'npx', ['vite', 'build'], { cwd: ROOT, stdio: 'inherit', shell: IS_WIN })
  const server = await serve()
  const stats: Record<string, unknown> = { sizes: sizes() }
  try {
    const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox', '--enable-unsafe-webgpu'] })
    try {
      await record(b, '1-intro', async (page, t0) => {
        const from = since(t0)
        await page.waitForFunction(() => window.__battle3d!.phase === 'fight', null, { timeout: 60_000 })
        return [from, since(t0)]
      })
      for (const [name, cam] of [['2-side', 'side'], ['3-behind', 'behind']] as const) {
        await record(b, name, async (page, t0) => {
          await fight(page)
          await page.evaluate((c) => window.__battle3d!.setCamera(c), cam)
          await wait(1500)
          const from = since(t0)
          const samples: unknown[] = []
          for (let i = 0; i < SECONDS; i++) {
            await wait(1000)
            samples.push(await page.evaluate(() => window.__battle3d!.stats()))
          }
          stats[name] = samples
          return [from, since(t0)]
        })
      }
      await record(b, '4-cinematic', async (page, t0) => {
        await fight(page)
        await page.evaluate(() => window.__battle3d!.speed(2))
        const from = since(t0)
        await page.waitForFunction(() => document.querySelector('.b3d__result') !== null, null, { timeout: 120_000 }).catch(() => undefined)
        await wait(2500)
        return [from, since(t0)]
      })
    } finally {
      await b.close()
    }
  } finally {
    kill(server)
  }
  writeFileSync(join(OUT, 'stats.json'), JSON.stringify(stats, null, 1))
  console.log('done', OUT)
}

void main()
