/**
 * Art 2.0 (ART_2_PLAN §6 step 2): the in-game review sheets. Playwright drives the built app in the installed
 * Chrome at 412 CSS px wide and writes PNG sheets into art-review/<look>/ (gitignored):
 *   turnaround.png (8 angles) · faces.png (every face) · variant_<id>.png · clips/<clip>.png (6 key frames)
 *   ranch.png (the live ranch stage) · battle.png (the arena) · lineup.png (base + variants, and 64/100-px tiles)
 *   index.html
 *
 *   npm run art:review -- <look> [--no-build] [--clips a,b]
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from '../../e2e/saves.ts'
import { MODEL_LOOKS, MODELS, type LookId } from '../../src/art/models.ts'
import { FACES, STAR_CLIPS } from '../../src/art3d/types.ts'
import { BASE, buildApp, launchChrome, phoneContext, startPreview, stopPreview } from './preview.ts'

const MAIN_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop', 'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash', 'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win'] as const
const ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]
const YAW_BASE = 28

interface Tile {
  png: string
  label: string
}

async function openViewer(page: Page): Promise<void> {
  await page.goto(`${BASE}?artmanual=1#lab/models`)
  await page.waitForFunction(() => window.__art3d?.ready === true, undefined, { timeout: 60_000 })
  await page.waitForSelector('.portrait--3d-ready', { timeout: 60_000 })
  await step(page, 40)
}

async function step(page: Page, ms: number): Promise<void> {
  await page.evaluate((m) => window.__art3d?.step(m), ms)
}

async function set(page: Page, s: Record<string, unknown>): Promise<void> {
  await page.evaluate((v) => window.__art3d?.set(v), s)
  // the viewer applies the change after its next paint; wait until the live actor really shows it
  const want = s as { variant?: string | null; clip?: string; face?: string; stage?: number }
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(25)
    await step(page, 33)
    const st = await page.evaluate(() => window.__art3d?.state() ?? null)
    if (!st) continue
    const ok = (want.variant === undefined || st.variant === want.variant) && (want.clip === undefined || st.clip === want.clip) && (want.face === undefined || st.face === want.face) && (want.stage === undefined || st.stage === want.stage)
    if (ok) break
    if (i === 59) console.log(`  warning: viewer state did not settle for ${JSON.stringify(s)} (got ${JSON.stringify(st)})`)
  }
  await step(page, 33)
}

async function shot(page: Page): Promise<string> {
  return (await page.locator('.modelslab__stage').screenshot({ animations: 'disabled', caret: 'hide' })).toString('base64')
}

async function compose(page: Page, tiles: Tile[], cols: number, tilePx: number, title: string, out: string): Promise<void> {
  const html = `<!doctype html><meta charset="utf-8"><style>
    body{margin:0;background:#d9dde3;font:13px system-ui;color:#223}
    h1{font-size:16px;margin:10px 12px 4px}
    .g{display:grid;grid-template-columns:repeat(${cols},${tilePx}px);gap:8px;padding:8px 12px 14px}
    figure{margin:0;background:#eef0f3;border-radius:8px;overflow:hidden}
    img{display:block;width:${tilePx}px;height:auto;image-rendering:auto}
    figcaption{padding:3px 6px;font-size:12px}
  </style><h1>${title}</h1><div class="g">${tiles.map((t) => `<figure><img src="data:image/png;base64,${t.png}"><figcaption>${t.label}</figcaption></figure>`).join('')}</div>`
  await page.setContent(html)
  await page.waitForTimeout(100)
  const buf = await page.screenshot({ fullPage: true })
  writeFileSync(out, buf)
  console.log(`wrote ${out}`)
}

async function main(): Promise<void> {
  const [look, ...rest] = process.argv.slice(2)
  if (!look || !(look in MODEL_LOOKS)) {
    console.error(`usage: npm run art:review -- <look> [--no-build] [--clips a,b]; looks: ${Object.keys(MODEL_LOOKS).join(', ')}`)
    process.exit(1)
  }
  const lookId = look as LookId
  const onlyClips = rest.includes('--clips') ? rest[rest.indexOf('--clips') + 1]!.split(',') : null
  const breed = (Object.entries(MODELS).find(([, m]) => m.young === lookId || m.grown === lookId) ?? ['puddlepup'])[0]
  const out = join('art-review', look)
  mkdirSync(join(out, 'clips'), { recursive: true })
  if (!rest.includes('--no-build')) buildApp()
  const preview = await startPreview()
  const browser = await launchChrome()
  const sheets: string[] = []
  const errors: string[] = []
  try {
    const ctx = await phoneContext(browser, 2)
    const page = await ctx.newPage()
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push(m.text())
    })
    const composer = await browser.newPage({ viewport: { width: 1700, height: 900 }, deviceScaleFactor: 1 })
    await openViewer(page)
    await set(page, { breed, variant: null, stage: 5, face: 'neutral', clip: 'idle', yaw: 0 })

    // turnaround
    const turn: Tile[] = []
    for (const a of ANGLES) {
      await set(page, { yaw: a - YAW_BASE })
      turn.push({ png: await shot(page), label: `${a}°` })
    }
    await compose(composer, turn, 4, 400, `${look}: turnaround (in game)`, join(out, 'turnaround.png'))
    sheets.push('turnaround.png')

    // faces
    const faces: Tile[] = []
    await set(page, { yaw: -YAW_BASE + 8 })
    for (const f of FACES) {
      await set(page, { face: f })
      faces.push({ png: await shot(page), label: f })
    }
    await compose(composer, faces, 4, 400, `${look}: faces (in game)`, join(out, 'faces.png'))
    sheets.push('faces.png')
    await set(page, { face: 'neutral' })

    // stages
    const stages: Tile[] = []
    for (const st of [1, 3, 5, 8]) {
      await set(page, { stage: st, yaw: 0 })
      stages.push({ png: await shot(page), label: `stage ${st}` })
    }
    await compose(composer, stages, 4, 400, `${look}: life stages`, join(out, 'stages.png'))
    sheets.push('stages.png')
    await set(page, { stage: 5 })

    // variants
    for (const v of MODEL_LOOKS[lookId].variants) {
      const tiles: Tile[] = []
      await set(page, { variant: v })
      for (const a of [0, 45, 90, 180]) {
        await set(page, { yaw: a - YAW_BASE })
        tiles.push({ png: await shot(page), label: `${v} ${a}°` })
      }
      await set(page, { face: 'happy' })
      tiles.push({ png: await shot(page), label: `${v} happy` })
      await set(page, { face: 'neutral', variant: null, yaw: 0 })
      await compose(composer, tiles, 5, 320, `${look}: ${v}`, join(out, `variant_${v}.png`))
      sheets.push(`variant_${v}.png`)
    }

    // lineup: the base look and its variants at three sizes (let the last clip fade out and the springs settle first)
    const lineup: Tile[] = []
    await set(page, { variant: null, yaw: 0, face: 'neutral', clip: 'idle' })
    for (let k = 0; k < 24; k++) await step(page, 33)
    const front = await shot(page)
    lineup.push({ png: front, label: look })
    for (const v of MODEL_LOOKS[lookId].variants) {
      await set(page, { variant: v })
      lineup.push({ png: await shot(page), label: v })
    }
    await set(page, { variant: null })
    const sizes = `<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#d9dde3;font:13px system-ui}div{display:flex;align-items:flex-end;gap:16px;padding:14px}img{display:block}figcaption{font-size:11px;text-align:center}</style>
      <div>${[64, 100, 200, 300].map((s) => `<figure style="margin:0"><img src="data:image/png;base64,${front}" width="${s}" height="${s}"><figcaption>${s} px</figcaption></figure>`).join('')}</div>`
    await composer.setContent(sizes)
    const sizesPng = (await composer.screenshot({ fullPage: true })).toString('base64')
    lineup.push({ png: sizesPng, label: 'at 64 / 100 / 200 / 300 px' })
    await compose(composer, lineup, lineup.length, 420, `${look}: lineup`, join(out, 'lineup.png'))
    sheets.push('lineup.png')

    // clips: six key frames each
    const clips = (onlyClips ?? MAIN_CLIPS).filter((c) => (STAR_CLIPS as readonly string[]).includes(c))
    const sidecar = JSON.parse(readFileSync(join('public', MODEL_LOOKS[lookId].meta), 'utf8')) as { clips: Record<string, { seconds: number }> }
    for (const c of clips) {
      await set(page, { clip: c, yaw: 12 })
      const tiles: Tile[] = []
      const total = sidecar.clips[c]?.seconds ?? 2
      for (let k = 0; k < 6; k++) {
        if (k > 0) await step(page, (total * 1000) / 6)
        tiles.push({ png: await shot(page), label: `${c} ${((k * total) / 6).toFixed(2)}s` })
      }
      await compose(composer, tiles, 6, 280, `${look}: ${c}`, join(out, 'clips', `${c}.png`))
      sheets.push(`clips/${c}.png`)
    }
    await set(page, { clip: 'idle', yaw: 0 })

    // the ranch, with a seeded save
    const ranchCtx = await phoneContext(browser, 2)
    const json = saveJsonAt({ year: 1, month: 3, week: 2, breed: breed as never })
    await ranchCtx.addInitScript(([key, value]) => {
      if (!sessionStorage.getItem('art-seeded')) {
        localStorage.setItem(key!, value!)
        sessionStorage.setItem('art-seeded', '1')
      }
    }, [MIRROR_KEY, json])
    const ranch = await ranchCtx.newPage()
    ranch.on('pageerror', (e) => errors.push(e.message))
    await ranch.goto(`${BASE}#ranch`)
    await ranch.waitForSelector('.stage .portrait--3d-ready', { timeout: 60_000 })
    await ranch.waitForTimeout(900)
    const ranchShots: Tile[] = []
    for (let k = 0; k < 3; k++) {
      ranchShots.push({ png: (await ranch.screenshot({ clip: { x: 0, y: 0, width: 412, height: 560 } })).toString('base64'), label: `ranch ${k}` })
      await ranch.waitForTimeout(1200)
    }
    await ranch.goto(`${BASE}#ranch/card`)
    await ranch.waitForSelector('.portrait--3d-ready', { timeout: 60_000 })
    await ranch.waitForTimeout(700)
    ranchShots.push({ png: (await ranch.screenshot({ clip: { x: 0, y: 0, width: 412, height: 560 } })).toString('base64'), label: 'monster card' })
    await compose(composer, ranchShots, 4, 412, `${look}: ranch and card (live)`, join(out, 'ranch.png'))
    sheets.push('ranch.png')
    await ranchCtx.close()

    // the arena (the Effects Lab's static battle; the real one plays the same clips)
    const battle = await ctx.newPage()
    battle.on('pageerror', (e) => errors.push(e.message))
    await battle.goto(`${BASE}?fxmanual=1#lab/effects`)
    await battle.waitForSelector('.fighter__art--3d', { timeout: 60_000 })
    await battle.waitForTimeout(900)
    const battleShots: Tile[] = []
    for (let k = 0; k < 3; k++) {
      battleShots.push({ png: (await battle.locator('.arena').screenshot()).toString('base64'), label: `arena ${k}` })
      await battle.waitForTimeout(700)
    }
    await compose(composer, battleShots, 3, 500, `${look}: the arena`, join(out, 'battle.png'))
    sheets.push('battle.png')
    await battle.close()

    const index = `<!doctype html><meta charset="utf-8"><title>${look} review</title><style>body{font:14px system-ui;background:#eee;margin:16px}img{max-width:100%;display:block;margin:0 0 20px;background:#ddd}h2{margin:18px 0 6px}</style>
      <h1>${look}: in-game review sheets</h1><p>${errors.length ? `<b>${errors.length} page errors</b>: ${errors.slice(0, 5).join(' · ')}` : 'No page errors.'}</p>
      ${sheets.map((s) => `<h2>${s}</h2><img src="${s}">`).join('')}`
    writeFileSync(join(out, 'index.html'), index)
    console.log(`wrote ${join(out, 'index.html')}${errors.length ? ` (${errors.length} page errors)` : ''}`)
    for (const e of errors.slice(0, 10)) console.log(`  error: ${e}`)
  } finally {
    await browser.close()
    stopPreview(preview)
  }
}

main().catch((e) => {
  console.error(e)
  stopPreview(null)
  process.exit(1)
})
