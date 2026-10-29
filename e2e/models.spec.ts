import { expect, test, type Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * Art 2.0 P1 (ART_2_PLAN §3.2 fallbacks, §6 step 4): the 3D monsters appear where they should, never more than
 * one 3D canvas is live, and every failure path lands on the Classic drawing without an error.
 * Headless Chrome needs software WebGL: the config launches it with the ANGLE/SwiftShader flags.
 */
const BASE = '/wildsong-ranch/'
const W = 412

declare global {
  interface Window {
    __art3d?: { ready: boolean; set: (s: Record<string, unknown>) => void; step: (ms: number) => void; loseContext: () => void; restoreContext: () => void; stats: () => { drawCalls: number } | null }
  }
}

async function seed(page: Page, json: string): Promise<void> {
  await page.setViewportSize({ width: W, height: 915 })
  await page.addInitScript(
    ([key, value]) => {
      if (!sessionStorage.getItem('e2e-seeded')) {
        localStorage.setItem(key!, value!)
        sessionStorage.setItem('e2e-seeded', '1')
      }
    },
    [MIRROR_KEY, json],
  )
}

function collectErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => {
    if (m.type() === 'error' && !/favicon|404/.test(m.text())) errors.push(m.text())
  })
  return errors
}

test.describe('3D monsters (Art P1)', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'pixel-7', 'one profile is enough')
  })

  test('Puddlepup is live in 3D on the ranch, the card and the Lab, one canvas at a time', async ({ page }) => {
    const errors = collectErrors(page)
    await seed(page, saveJsonAt({ year: 1, month: 3, week: 2, breed: 'puddlepup' }))
    await page.goto(`${BASE}#ranch`)
    await expect(page.locator('.stage .portrait--3d-ready')).toBeVisible({ timeout: 60_000 })
    expect(await page.locator('canvas.art3d-canvas').count()).toBe(1)
    await page.goto(`${BASE}#ranch/card`)
    await expect(page.locator('.portrait--3d-ready')).toBeVisible({ timeout: 60_000 })
    expect(await page.locator('canvas.art3d-canvas').count()).toBe(1)
    await page.goto(`${BASE}?artmanual=1#lab/models`)
    await page.waitForFunction(() => window.__art3d?.ready === true, undefined, { timeout: 60_000 })
    await page.evaluate(() => window.__art3d?.step(50))
    const stats = await page.evaluate(() => window.__art3d?.stats() ?? null)
    expect(stats?.drawCalls ?? 0).toBeGreaterThan(0)
    expect(await page.locator('canvas.art3d-canvas').count()).toBe(1)
    // a breed without a model shows Classic and says so
    await page.evaluate(() => window.__art3d?.set({ breed: 'tumblefox' }))
    await expect(page.locator('.modelslab__stage .ws-mon')).toBeVisible({ timeout: 10_000 })
    expect(errors).toEqual([])
  })

  test('without WebGL everything is Classic and nothing breaks', async ({ page }) => {
    const errors = collectErrors(page)
    await seed(page, saveJsonAt({ year: 1, month: 3, week: 2, breed: 'puddlepup' }))
    await page.addInitScript(() => {
      const orig = HTMLCanvasElement.prototype.getContext
      HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string, ...rest: unknown[]) {
        if (kind === 'webgl' || kind === 'webgl2') return null
        return (orig as (this: HTMLCanvasElement, k: string, ...r: unknown[]) => unknown).call(this, kind, ...rest)
      } as typeof orig
    })
    await page.goto(`${BASE}#ranch`)
    await expect(page.locator('.stage .ws-mon')).toBeVisible({ timeout: 30_000 })
    await page.waitForTimeout(1500)
    expect(await page.locator('canvas.art3d-canvas').count()).toBe(0)
    await page.goto(`${BASE}#settings`)
    await expect(page.getByText('can’t draw 3D')).toBeVisible()
    // three reports the refused context once; that is the expected path, not a bug
    expect(errors.filter((e) => !/WebGL/i.test(e))).toEqual([])
  })

  test('a missing model falls back to Classic without an error', async ({ page }) => {
    const errors = collectErrors(page)
    await seed(page, saveJsonAt({ year: 1, month: 3, week: 2, breed: 'puddlepup' }))
    await page.route('**/models/**', (r) => r.abort())
    await page.goto(`${BASE}#ranch`)
    await expect(page.locator('.stage .ws-mon')).toBeVisible({ timeout: 30_000 })
    await page.waitForTimeout(2500)
    expect(await page.locator('.stage .portrait--3d-ready').count()).toBe(0)
    // the aborted model requests log "Failed to load resource"; nothing else may
    expect(errors.filter((e) => !/models\/|Failed to load resource|ERR_FAILED/.test(e))).toEqual([])
  })

  test('Settings → Monsters: Classic turns the canvas off, and 3D turns it back on', async ({ page }) => {
    const errors = collectErrors(page)
    await seed(page, saveJsonAt({ year: 1, month: 3, week: 2, breed: 'puddlepup' }))
    await page.goto(`${BASE}#settings`)
    await page.getByRole('tablist', { name: 'Monsters' }).getByRole('tab', { name: 'Classic' }).click()
    await page.goto(`${BASE}#ranch`)
    await expect(page.locator('.stage .ws-mon')).toBeVisible({ timeout: 30_000 })
    await page.waitForTimeout(800)
    expect(await page.locator('canvas.art3d-canvas').count()).toBe(0)
    await page.goto(`${BASE}#settings`)
    await page.getByRole('tablist', { name: 'Monsters' }).getByRole('tab', { name: '3D' }).click()
    await page.goto(`${BASE}#ranch`)
    await expect(page.locator('.stage .portrait--3d-ready')).toBeVisible({ timeout: 60_000 })
    expect(errors).toEqual([])
  })

  test('a lost WebGL context shows Classic and a restored one brings the model back', async ({ page }) => {
    const errors = collectErrors(page)
    await page.setViewportSize({ width: W, height: 915 })
    await page.goto(`${BASE}?artmanual=1#lab/models`)
    await page.waitForFunction(() => window.__art3d?.ready === true, undefined, { timeout: 60_000 })
    await expect(page.locator('.portrait--3d-ready')).toBeVisible({ timeout: 30_000 })
    await page.evaluate(() => window.__art3d?.loseContext())
    await expect(page.locator('.portrait--3d-ready')).toHaveCount(0, { timeout: 10_000 })
    await page.evaluate(() => window.__art3d?.restoreContext())
    await expect(page.locator('.portrait--3d-ready')).toBeVisible({ timeout: 30_000 })
    expect(errors.filter((e) => !/WebGL|context/i.test(e))).toEqual([])
  })
})
