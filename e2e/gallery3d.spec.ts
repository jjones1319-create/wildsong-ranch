import { expect, test, type Page } from '@playwright/test'

/**
 * Lab → 3D Gallery (docs/ART_2_DETAIL.md §9.3): it opens, shows a finished Ultra breed in the film renderer (the canvas
 * draws a monster, not a blank frame), a breed can be picked, and a move button plays its clip.
 * The Ultra models need a real GPU: this spec runs Chrome on this PC's GPU (ANGLE on D3D11), not SwiftShader.
 */
const BASE = '/wildsong-ranch/'

test.use({ launchOptions: { args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'] } })

declare global {
  interface Window {
    __gallery3d?: {
      ready: boolean
      phase: string
      stats(): { look: string; clip: string | null; triangles: number; kind: string | null; flies?: boolean; liftM?: number } | null
      show(look: string): void
      snapshot(): string | null
    }
  }
}

function collectErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => {
    if (m.type() === 'error' && !/favicon|404/.test(m.text())) errors.push(m.text())
  })
  return errors
}

/** The share of the frame's pixels that differ clearly from its top-left corner (the studio backdrop). */
async function drawnShare(page: Page): Promise<number> {
  const src = await page.evaluate(() => window.__gallery3d?.snapshot() ?? null)
  expect(src).toBeTruthy()
  return page.evaluate(async (url) => {
    const img = new Image()
    img.src = url
    await img.decode()
    const c = document.createElement('canvas')
    c.width = img.width
    c.height = img.height
    const g = c.getContext('2d')!
    g.drawImage(img, 0, 0)
    const d = g.getImageData(0, 0, c.width, c.height).data
    const [r0, g0, b0] = [d[0]!, d[1]!, d[2]!]
    let n = 0
    for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i]! - r0) + Math.abs(d[i + 1]! - g0) + Math.abs(d[i + 2]! - b0) > 60) n++
    return n / (d.length / 4)
  }, src!)
}

test.describe('3D Gallery (Art 2.1)', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'pixel-7', 'one profile is enough')
  })

  test('shows a finished breed, a picked one, and plays a move', async ({ page }) => {
    test.setTimeout(240_000)
    const errors = collectErrors(page)
    await page.setViewportSize({ width: 412, height: 915 })
    await page.goto(`${BASE}?backend=webgl#lab/gallery3d`)
    await expect(page.getByRole('heading', { name: '3D Gallery' })).toBeVisible()
    await page.waitForFunction(() => window.__gallery3d?.phase === 'ready', undefined, { timeout: 180_000 })

    // a look from the chips: the last one listed (Puddlepup when it is the only one)
    const chips = page.getByRole('group', { name: 'Monster' }).getByRole('button')
    const pick = chips.last()
    await pick.click()
    await expect(pick).toHaveAttribute('aria-pressed', 'true')
    await page.waitForFunction(() => window.__gallery3d?.phase === 'ready', undefined, { timeout: 180_000 })
    const stats = await page.evaluate(() => window.__gallery3d!.stats())
    // the stage shows the picked look (its id on the stage, its name on the chip)
    expect(stats?.look).toBe(await page.locator('.gallery3d__stage').getAttribute('data-look'))
    expect(stats?.look).not.toBe('puddlepup')
    expect(stats?.triangles ?? 0).toBeGreaterThan(5_000)

    // the canvas draws the monster, not a blank frame
    expect(await drawnShare(page)).toBeGreaterThan(0.02)

    // a move button plays its clip
    const strike = page.locator('.gallery3d__moves [data-clip="strike"]')
    await strike.click()
    await expect(strike).toHaveAttribute('aria-pressed', 'true')
    await expect.poll(async () => (await page.evaluate(() => window.__gallery3d!.stats()))?.clip, { timeout: 5_000 }).toMatch(/^(strike|shove)$/)
    // and it settles back into idle on its own
    await expect.poll(async () => (await page.evaluate(() => window.__gallery3d!.stats()))?.clip, { timeout: 15_000 }).toMatch(/idle/)
    expect(errors).toEqual([])
  })

  test('a look that flies takes off from its 🪽 button and draws in the air', async ({ page }) => {
    test.setTimeout(240_000)
    const errors = collectErrors(page)
    await page.setViewportSize({ width: 412, height: 915 })
    await page.goto(`${BASE}?backend=webgl#lab/gallery3d`)
    await page.waitForFunction(() => window.__gallery3d?.phase === 'ready', undefined, { timeout: 180_000 })
    // Hearthwing (its file has the flying clips)
    await page.evaluate(() => window.__gallery3d!.show('hearthwing'))
    await page.waitForFunction(() => window.__gallery3d?.phase === 'ready' && window.__gallery3d.stats()?.look === 'hearthwing', undefined, { timeout: 180_000 })
    expect((await page.evaluate(() => window.__gallery3d!.stats()))?.flies).toBe(true)
    const takeoff = page.locator('.gallery3d__moves [data-clip="fly_takeoff"]')
    await takeoff.click()
    // its flying clips play and it rises off the floor
    await expect.poll(async () => (await page.evaluate(() => window.__gallery3d!.stats()))?.clip, { timeout: 5_000 }).toMatch(/^fly/)
    await expect.poll(async () => (await page.evaluate(() => window.__gallery3d!.stats()))?.liftM ?? 0, { timeout: 5_000 }).toBeGreaterThan(0.3)
    expect(await drawnShare(page)).toBeGreaterThan(0.02)
    expect(errors).toEqual([])
  })
})
