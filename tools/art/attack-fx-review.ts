/**
 * docs/BATTLE_3D.md §7: the attack effects' review. Builds the game (unless --no-build), serves dist/, opens Lab →
 * Battle 3D in the installed Chrome, pauses the fight and fires chosen techniques with the picture-only preview,
 * capturing frames from each fire; then tiles them into contact sheets (rows: techniques, columns: frames in order).
 *
 *   node tools/art/attack-fx-review.ts [--no-build] [--arena crown] [--upright] [--slow 0.1] [--set fixed [--tag before]]
 *
 * Output: art-review/attack-fx/ (-crown, -upright; gitignored): sheet.png, sheet-2.png, rows.txt (what each row is), frames/.
 */
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { copyFileSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, type Page } from '@playwright/test'
import { FFMPEG } from '../audio/opus.ts'

/** What the Battle 3D screen exposes for reviews (src/ui/screens/battle3d/Battle3DScreen.tsx), read through a cast so the tools' own declarations don't clash. */
type W = { __battle3d?: { phase: string; skipIntro(): void; stats(): unknown; preview(tech: string, side: 0 | 1, outcome: 'hit' | 'miss'): number; pause(on: boolean): void; slowMo(k: number): void; clock(): number } }

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const IS_WIN = process.platform === 'win32'
const args = process.argv.slice(2)
const opt = (f: string, d: string) => (args.includes(f) ? args[args.indexOf(f) + 1]! : d)
const ARENA = opt('--arena', 'guild')
const UPRIGHT = args.includes('--upright')
const FRAMES = 8
/** The picture runs this much slower while capturing (the battle itself is paused). */
const SLOW = Number(opt('--slow', '0.1'))
const OUT = join(ROOT, 'art-review', `attack-fx${ARENA === 'crown' ? '-crown' : ''}${UPRIGHT ? '-upright' : ''}`)
const PORT = 4173
const URL = `http://localhost:${PORT}/wildsong-ranch/${ARENA === 'crown' ? '?arena=crown' : ''}#lab/battle3d`
const VIEW = UPRIGHT ? { width: 412, height: 892 } : { width: 892, height: 412 }
/** The part of the screen the fight is in (CSS px): sideways, left of the cards; upright, between the bars and the panel. */
const CLIP = UPRIGHT ? { x: 0, y: 150, width: 412, height: 420 } : { x: 0, y: 125, width: 600, height: 285 }

/** [technique, side, outcome]: several elements, melee and ranged, a sweep, a multi-hit, a drain, a Signature, a miss. */
const SHEETS: [string, 0 | 1, 'hit' | 'miss'][][] = [
  [
    ['cinderlynx.ember-swipe', 0, 'hit'],
    ['puddlepup.bubble-pop', 0, 'hit'],
    ['zipwisp.zigzag-bolt', 0, 'hit'],
    ['frostlance.glacier-pierce', 0, 'hit'],
    ['cobblemaw.landslide-maul', 0, 'hit'],
    ['ashwraith.soulsiphon', 0, 'hit'],
    ['galeheron.squall-line', 0, 'hit'],
    ['wishlume.festival-of-lights', 0, 'hit'],
  ],
  [
    ['petalphant.sleepy-blossom', 0, 'hit'],
    ['universal.timpani-crash', 0, 'hit'],
    ['plumdrake.cloud-gust-blast', 0, 'hit'],
    ['puddlepup.bubble-pop', 0, 'miss'],
    ['tumblefox.ninefold-feint', 1, 'hit'],
    ['puddlepup.puddle-party', 0, 'hit'],
  ],
]

/**
 * `--set fixed`: the weak spots of the v1.21 review, one sheet (sheet-fixed.png, or sheet-fixed-<tag>.png with
 * `--tag before`): a Basic fire melee, a melee and a ranged miss, Wind (ranged, melee and the Special's cut), a long
 * line telegraph, a sweep telegraph, and the opponent's Signature cut.
 */
const FIXED: [string, 0 | 1, 'hit' | 'miss'][] = [
  ['cinderlynx.ember-swipe', 0, 'hit'],
  ['cinderlynx.ember-swipe', 0, 'miss'],
  ['puddlepup.bubble-pop', 0, 'miss'],
  ['galeheron.gust-feather', 0, 'hit'],
  ['galeheron.lightning-stride', 0, 'hit'],
  ['puddlepup.belly-flop', 0, 'hit'],
  ['cobblemaw.landslide-maul', 0, 'hit'],
  ['galeheron.squall-line', 0, 'hit'],
  ['tumblefox.ninefold-feint', 1, 'hit'],
]
const SET = opt('--set', 'all')
const TAG = opt('--tag', '')

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

/** Stage times of the columns, from the fire: two in the wind-up (as a share of it), then after the landing (s). */
const WINDUP_AT = [0.35, 0.85]
const AFTER_LAND = [0.01, 0.06, 0.12, 0.2, 0.32, 0.5]

/** Fires one technique in slow motion, captures frames with their stage times, and keeps the ones nearest each column. */
async function row(page: Page, dir: string, n: number, [tech, side, outcome]: [string, 0 | 1, 'hit' | 'miss']): Promise<unknown> {
  const raw = join(dir, `raw-${n}`)
  mkdirSync(raw, { recursive: true })
  await page.evaluate((k) => (window as unknown as W).__battle3d!.slowMo(k), SLOW)
  const t0 = await page.evaluate(() => (window as unknown as W).__battle3d!.clock())
  const landIn = await page.evaluate(([t, s, o]) => (window as unknown as W).__battle3d!.preview(t, s, o), [tech, side, outcome] as const)
  const shots: { file: string; t: number }[] = []
  let maxFx = { quads: 0, draws: 0, ms: 0 }
  for (let i = 0; ; i++) {
    const file = join(raw, `${i}.png`)
    const t = (await page.evaluate(() => (window as unknown as W).__battle3d!.clock())) - t0
    await page.screenshot({ path: file, clip: CLIP })
    shots.push({ file, t })
    const st = (await page.evaluate(() => (window as unknown as W).__battle3d!.stats())) as { fx?: { quads: number; draws: number; ms: number } } | null
    if (st?.fx && st.fx.quads > maxFx.quads) maxFx = st.fx
    if (t > landIn + AFTER_LAND.at(-1)! + 0.05 || i > 400) break
  }
  const want = [...WINDUP_AT.map((k) => k * landIn), ...AFTER_LAND.map((d) => landIn + d)]
  want.forEach((w, c) => {
    const best = shots.reduce((p, q) => (Math.abs(q.t - w) < Math.abs(p.t - w) ? q : p))
    copyFileSync(best.file, join(dir, `f_${String(n * FRAMES + c).padStart(3, '0')}.png`))
  })
  await page.evaluate(() => (window as unknown as W).__battle3d!.slowMo(1))
  await wait(1500)
  return { landIn: +landIn.toFixed(3), frames: shots.length, peakFx: maxFx }
}

async function main(): Promise<void> {
  const fixed = SET === 'fixed'
  const sheets = fixed ? [FIXED] : SHEETS
  const suffix = fixed ? `-fixed${TAG ? `-${TAG}` : ''}` : ''
  // the fixed set keeps the full review's files (and its own before sheet) beside it
  rmSync(fixed ? join(OUT, `frames${suffix}`) : OUT, { recursive: true, force: true })
  mkdirSync(OUT, { recursive: true })
  if (!args.includes('--no-build')) execFileSync(IS_WIN ? 'npx.cmd' : 'npx', ['vite', 'build'], { cwd: ROOT, stdio: 'inherit', shell: IS_WIN })
  const server = await serve()
  const notes: string[] = []
  try {
    const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox', '--enable-unsafe-webgpu'] })
    try {
      const ctx = await b.newContext({ viewport: VIEW, deviceScaleFactor: 1.5, hasTouch: true, isMobile: true })
      const page = await ctx.newPage()
      page.on('pageerror', (e) => console.error('page error:', e.message))
      await page.goto(URL, { timeout: 240_000, waitUntil: 'domcontentloaded' })
      await page.waitForFunction(() => (window as unknown as W).__battle3d?.phase === 'intro', null, { timeout: 240_000 })
      await page.evaluate(() => (window as unknown as W).__battle3d!.skipIntro())
      await page.waitForFunction(() => (window as unknown as W).__battle3d!.phase === 'fight', null, { timeout: 60_000 })
      await page.evaluate(() => (window as unknown as W).__battle3d!.pause(true))
      await wait(2500)
      await page.screenshot({ path: join(OUT, `screen${suffix}.png`) })
      for (const [s, list] of sheets.entries()) {
        const dir = join(OUT, `frames${suffix}`, String(s + 1))
        mkdirSync(dir, { recursive: true })
        for (const [i, r] of list.entries()) {
          const st = await row(page, dir, i, r)
          notes.push(`sheet ${s + 1} row ${i + 1}: ${r.join(' ')} · stats ${JSON.stringify(st)}`)
          console.log(notes.at(-1))
        }
        const name = fixed ? `sheet${suffix}.png` : s === 0 ? 'sheet.png' : `sheet-${s + 1}.png`
        const w = Math.round((CLIP.width * 1.5) / 2)
        execFileSync(FFMPEG, ['-y', '-loglevel', 'error', '-framerate', '1', '-i', join(dir, 'f_%03d.png'), '-vf', `scale=${w}:-1,tile=${FRAMES}x${list.length}:padding=4:color=white`, '-frames:v', '1', join(OUT, name)])
      }
      await ctx.close()
    } finally {
      await b.close()
    }
  } finally {
    kill(server)
  }
  writeFileSync(join(OUT, `rows${suffix}.txt`), notes.join('\n') + '\n')
  console.log('done', OUT)
}

void main()
