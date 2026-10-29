/**
 * Art 2.0 (ART_2_PLAN §3.3): the precached base portraits. For every look and its variants, the game's own
 * renderer (the Models viewer in headless Chrome) draws the prime-size, neutral-face picture at 256 px and it is
 * written as public/portraits/<look>[.<variant>].webp (encoded with ffmpeg from the PNG the page returns).
 *
 *   npm run art:portraits [-- --no-build]
 */
import { existsSync, mkdirSync, unlinkSync, writeFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'
import { MODEL_LOOKS, lookKey, type LookId } from '../../src/art/models.ts'
import { ART } from '../../src/data/tuning.ts'
import { BASE, buildApp, dataUrlToPng, launchChrome, phoneContext, startPreview, stopPreview } from './preview.ts'

const OUT = join('public', 'portraits')

function ffmpegBin(): string {
  const local = join('node_modules', 'ffmpeg-static', process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg')
  return existsSync(local) ? local : 'ffmpeg'
}

function toWebp(png: string, webp: string): void {
  const r = spawnSync(ffmpegBin(), ['-hide_banner', '-y', '-i', png, '-c:v', 'libwebp', '-quality', '88', '-compression_level', '6', '-preset', 'picture', webp], { stdio: 'ignore' })
  if (r.status !== 0) throw new Error(`ffmpeg failed for ${png}`)
}

async function main(): Promise<void> {
  const rest = process.argv.slice(2)
  if (!rest.includes('--no-build')) buildApp()
  mkdirSync(OUT, { recursive: true })
  const preview = await startPreview()
  const browser = await launchChrome()
  try {
    const ctx = await phoneContext(browser, 1)
    const page = await ctx.newPage()
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    await page.goto(`${BASE}?artmanual=1#lab/models`)
    await page.waitForFunction(() => window.__art3d?.ready === true, undefined, { timeout: 60_000 })
    const jobs: { look: LookId; variant: string | null }[] = []
    for (const [id, look] of Object.entries(MODEL_LOOKS) as [LookId, (typeof MODEL_LOOKS)[LookId]][]) {
      jobs.push({ look: id, variant: null })
      for (const v of look.variants) jobs.push({ look: id, variant: v })
    }
    for (const job of jobs) {
      const dataUrl = await page.evaluate((j) => window.__art3d!.snapshot({ look: j.look, variant: j.variant, stage: 5, face: 'neutral', clip: 'idle', size: j.size }), { ...job, size: ART.portrait.px })
      if (!dataUrl) {
        console.error(`no picture for ${lookKey(job)}`)
        process.exitCode = 1
        continue
      }
      const key = lookKey(job)
      const png = join(OUT, `${key}.png`)
      const webp = join(OUT, `${key}.webp`)
      writeFileSync(png, dataUrlToPng(dataUrl))
      toWebp(png, webp)
      unlinkSync(png)
      console.log(`wrote ${webp}`)
    }
    for (const e of errors) console.log(`  page error: ${e}`)
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
