import { expect, test } from '@playwright/test'

/**
 * VISUAL_V1_EFFECTS §9 (optional e2e): the Effects Lab opens, a combo fires, the fps counter reads a number,
 * there are no page errors, and one screenshot per element lands in test-results/.
 */
const BASE = '/wildsong-ranch/'
const ELEMENTS = ['Fire', 'Water', 'Ice', 'Lightning', 'Wind', 'Earth', 'Nature', 'Light', 'Dark', 'Sound', 'Physical']

declare global {
  interface Window {
    __fx?: { fire: (name: string, element: string, strength?: number) => void; combo: () => void; stress: () => void; clear: () => void; stats: () => { fps: number; particles: number } | null; ready: boolean }
  }
}

test('the Effects Lab fires a combo with no errors and a live fps counter', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`${BASE}#lab/effects`)
  await page.waitForFunction(() => window.__fx?.ready === true, undefined, { timeout: 30_000 })
  await page.getByRole('button', { name: 'Combo' }).click()
  await page.waitForTimeout(500)
  const stats = await page.evaluate(() => window.__fx!.stats())
  expect(stats).not.toBeNull()
  expect(stats!.fps).toBeGreaterThan(0)
  await expect(page.locator('.fxlab__stats')).toContainText('fps')
  for (const el of ELEMENTS) {
    await page.evaluate((e) => window.__fx!.fire('impact', e, 1), el)
    await page.waitForTimeout(90)
    await page.locator('.arena').screenshot({ path: testInfo.outputPath(`fx-${el.toLowerCase()}.png`) })
  }
  await page.getByRole('button', { name: 'Stress test' }).click()
  await page.waitForTimeout(800)
  const busy = await page.evaluate(() => window.__fx!.stats())
  expect(busy!.fps).toBeGreaterThan(0)
  expect(errors, errors.join('\n')).toEqual([])
})
