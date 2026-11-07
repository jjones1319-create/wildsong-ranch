import { expect, test, type Page } from '@playwright/test'
import { makePreset } from '../src/core/presets.ts'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * The owner (Nov 3): on short phones the ranch's action bar covered the bottom of the herd strip. With a ranch-mate,
 * at 360 × 640, 412 × 700, 360 × 780 and 412 × 892: as the ranch opens the whole strip sits above the bar, Wren's bubble can be
 * scrolled clear of it (and is, whenever the browser scrolls it into view), and at the bottom nothing is under it.
 * Screenshots go to art-review/herd-layout/ (gitignored).
 */
const BASE = '/wildsong-ranch/'
const SHOTS = 'art-review/herd-layout'
const SIZES = [[360, 640], [412, 700], [360, 780], [412, 892]] as const

async function openWith(page: Page, w: number, h: number): Promise<void> {
  await page.setViewportSize({ width: w, height: h })
  const json = saveJsonAt({
    year: 1,
    month: 4,
    week: 2,
    grade: 'C',
    edit: (g) => {
      const fern = makePreset('puddlepup', 'C')
      fern.id = 'fern'
      fern.name = 'Fern'
      g.ranchmates = [{ monster: fern, order: { kind: 'rest' }, last: null, history: [] }]
    },
  })
  await page.addInitScript(
    ([key, value]) => {
      if (!sessionStorage.getItem('e2e-seeded')) {
        localStorage.setItem(key!, value!)
        sessionStorage.setItem('e2e-seeded', '1')
      }
    },
    [MIRROR_KEY, json],
  )
  await page.goto(`${BASE}#ranch`)
}

/** The bottom of `sel` and the top of the action bar, in the viewport (CSS px). */
async function edges(page: Page, sel: string): Promise<{ bottom: number; bar: number }> {
  return page.evaluate((s) => {
    const el = document.querySelector(s)!.getBoundingClientRect()
    const bar = document.querySelector('.actionbar')!.getBoundingClientRect()
    return { bottom: el.bottom, bar: bar.top }
  }, sel)
}

for (const [w, h] of SIZES) {
  test(`ranch at ${w} × ${h}: the herd strip and Wren's bubble clear the action bar`, async ({ page }) => {
    await openWith(page, w, h)
    const strip = page.locator('.herd')
    await expect(strip.getByText('Fern')).toBeVisible({ timeout: 20_000 })
    await page.waitForTimeout(600)
    await page.screenshot({ path: `${SHOTS}/${w}x${h}-1-open.png` })
    const open = await edges(page, '.herd')
    expect(open.bottom, 'the whole herd strip shows above the bar as the ranch opens').toBeLessThanOrEqual(open.bar + 0.5)

    // the browser scrolling Wren's bubble into view keeps it clear of the bar (scroll-padding)
    await page.locator('.bubble').evaluate((el) => el.scrollIntoView({ block: 'end' }))
    await page.waitForTimeout(300)
    const bubble = await edges(page, '.bubble')
    expect(bubble.bottom, "Wren's bubble scrolls clear of the bar").toBeLessThanOrEqual(bubble.bar + 0.5)
    await page.screenshot({ path: `${SHOTS}/${w}x${h}-2-bubble.png` })

    // at the bottom, the bar sits under everything
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
    await page.waitForTimeout(300)
    const end = await edges(page, '.screen > .bars')
    expect(end.bottom).toBeLessThanOrEqual(end.bar + 0.5)
    await page.screenshot({ path: `${SHOTS}/${w}x${h}-3-bottom.png` })
    await page.screenshot({ path: `${SHOTS}/${w}x${h}-4-full.png`, fullPage: true })
  })
}
