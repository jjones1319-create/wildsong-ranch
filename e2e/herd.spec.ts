import { expect, test, type Page } from '@playwright/test'
import { makePreset } from '../src/core/presets.ts'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * v1.20 ranch-mates and the one-time homecoming (GAME_DESIGN §6.10–§6.11, §21) at 360 × 780: a runaway in the
 * Memorial comes home, the herd strip shows the star and the ranch-mate, a ranch-mate's sheet opens, and it can be
 * made the star. Screenshots go to art-review/herd/ (gitignored) for the review.
 */
const BASE = '/wildsong-ranch/'
const W = 360
const SHOTS = 'art-review/herd'

async function openWith(page: Page): Promise<void> {
  await page.setViewportSize({ width: W, height: 780 })
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
      const moss = makePreset('cobblemaw', 'E')
      moss.id = 'moss'
      moss.name = 'Moss'
      g.freezer = [moss]
      const bramble = makePreset('quillion', 'E')
      bramble.id = 'bramble'
      bramble.name = 'Bramble'
      g.memorial = [{ monster: bramble, cause: 'neglected', epitaph: '', week: g.week - 10 }]
      g.homecoming = { status: 'due', welcome: [] }
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

test('a runaway comes home; the herd strip, a ranch-mate sheet, and making it the star', async ({ page }) => {
  await openWith(page)
  // the homecoming card: Bramble comes back (the one pen is Fern's, so to the Freezer)
  const card = page.getByRole('dialog', { name: 'Welcome home!' })
  await expect(card).toBeVisible({ timeout: 20_000 })
  await expect(card.getByText('Bramble came home!')).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/1-homecoming.png` })
  await card.getByRole('button', { name: 'Welcome home!' }).click()
  await expect(card).toBeHidden()

  // the herd strip: the star and Fern
  const strip = page.locator('.herd')
  await expect(strip).toBeVisible()
  await expect(strip.getByText('Fern')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 360 px').toBeLessThanOrEqual(W)
  await page.screenshot({ path: `${SHOTS}/2-ranch.png` })

  // Fern's sheet, then make her the star
  await strip.locator('.herd__tile', { hasText: 'Fern' }).click()
  await expect(page.getByRole('button', { name: '⭐ Make star' })).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/3-sheet.png` })
  await page.getByRole('button', { name: '⭐ Make star' }).click()
  await page.getByRole('button', { name: '⭐ Make star' }).last().click()
  await expect(strip.locator('.herd__tile', { hasText: 'Pip' })).toBeVisible({ timeout: 10_000 })
  await page.screenshot({ path: `${SHOTS}/4-swapped.png` })
})
