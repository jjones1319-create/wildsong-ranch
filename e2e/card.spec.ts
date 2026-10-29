import { expect, test, type Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * v1.11 Monster Card at 360 × 780: six coloured stat rows that fill toward each grade's cap, Stat Sweets as a lighter
 * segment past the cap with the cap marked, an S grade, an inherited trait, and the stats guide (from the card and
 * as the Journal's Stats page).
 */
const BASE = '/wildsong-ranch/'
const W = 360

async function openWith(page: Page): Promise<void> {
  await page.setViewportSize({ width: W, height: 780 })
  const json = saveJsonAt({
    year: 1,
    month: 3,
    week: 2,
    grade: 'C',
    edit: (g) => {
      const m = g.monster!
      m.grades.POW = 'S'
      m.stats.POW = 1450
      // Tumblefox SPD is grade B (cap 1,300): 1,180 trained + 200 from sweets runs past the cap.
      m.stats.SPD = 1380
      m.records.fromSweets.SPD = 200
      m.inheritedTrait = 'fortified'
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
  await expect(page.getByText('Pip').first()).toBeVisible({ timeout: 20_000 })
}

async function noSidewaysScroll(page: Page): Promise<void> {
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 360 px').toBeLessThanOrEqual(W)
}

test('the card fills each stat toward its cap, shows sweets past it, and opens the stats guide', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openWith(page)
  await page.evaluate(() => {
    location.hash = '#ranch/card'
  })
  const rows = page.locator('.statrow')
  await expect(rows).toHaveCount(6)
  // Every bar has a visible, coloured fill.
  for (let i = 0; i < 6; i++) {
    const box = await rows.nth(i).locator('.stats__fill').boundingBox()
    expect(box!.width).toBeGreaterThan(2)
    expect(box!.height).toBeGreaterThan(4)
  }
  const pow = rows.nth(1)
  await expect(pow.locator('.pill--s')).toHaveText('S')
  await expect(pow).toContainText('cap 1,500')
  const spd = rows.nth(4)
  await expect(spd.locator('.stats__sweets')).toBeVisible()
  await expect(spd.locator('.stats__capmark')).toBeVisible()
  await expect(spd).toContainText('(+200)')
  await expect(page.getByText('Inherited trait')).toBeVisible()
  await expect(page.getByText('Fortified')).toBeVisible()
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('1-card.png'), fullPage: true })

  await spd.click()
  const sheet = page.locator('.sheet')
  await expect(sheet.getByRole('heading', { name: 'What do stats do?' })).toBeVisible()
  await expect(sheet.locator('.guide__stat--focus')).toContainText('Speed')
  await expect(sheet).toContainText('Dodge the Gourds')
  await expect(sheet).toContainText('S 1,500')
  await page.screenshot({ path: info.outputPath('2-guide.png'), fullPage: true })
  await sheet.getByRole('button', { name: 'Got it' }).click()
  await expect(sheet).toHaveCount(0)

  await page.evaluate(() => {
    location.hash = '#town/journal'
  })
  await page.getByRole('button', { name: 'Stats', exact: true }).click()
  await expect(page.locator('.guide__stat')).toHaveCount(7)
  await noSidewaysScroll(page)
  expect(errors).toEqual([])
})
