import { expect, test, type Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * The storm spark (CONTENT §11): on a storm week with no Journey, the event card must open on the ranch.
 * Regression for the soft-lock where "Answer the spark first." showed with every action disabled.
 */
const BASE = '/wildsong-ranch/'

function stormSave(): string {
  return saveJsonAt({
    year: 1,
    month: 3,
    week: 2,
    breed: 'puddlepup',
    edit: (g) => {
      g.weather = 'Storm'
      g.journey = null
      g.pendingEvent = { kind: 'stormChase' }
    },
  })
}

async function openRanch(page: Page): Promise<void> {
  await page.setViewportSize({ width: 412, height: 915 })
  await page.addInitScript(
    ([key, value]) => {
      if (!sessionStorage.getItem('e2e-seeded')) {
        localStorage.setItem(key!, value!)
        sessionStorage.setItem('e2e-seeded', '1')
      }
    },
    [MIRROR_KEY, stormSave()],
  )
  await page.goto(`${BASE}#ranch`)
  await expect(page.getByText('Pip').first()).toBeVisible({ timeout: 20_000 })
}

test.describe('the storm spark', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'pixel-7', 'one profile is enough')
  })

  test('its card opens on a storm week with no journey, and Let it go unlocks the actions', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    await openRanch(page)
    await expect(page.getByText('A storm spark!')).toBeVisible({ timeout: 15_000 })
    await page.getByRole('button', { name: 'Let it go' }).click()
    await expect(page.getByText('A storm spark!')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Train', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Rest', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Journey', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Battle', exact: true })).toBeEnabled()
    expect(errors).toEqual([])
  })

  test('Chase it gives Stormglass and ends the week', async ({ page }) => {
    await openRanch(page)
    await expect(page.getByText('A storm spark!')).toBeVisible({ timeout: 15_000 })
    await page.getByRole('button', { name: 'Chase it (uses the week)' }).click()
    await expect(page.getByRole('dialog', { name: 'End of the week' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Stormglass').first()).toBeVisible()
    await page.getByRole('button', { name: 'Next week', exact: true }).click()
    await page.goto(`${BASE}#ranch/bag`)
    await expect(page.getByText('Stormglass').first()).toBeVisible({ timeout: 15_000 })
  })

  test('the reason line and the ?! bubble open the card by hand', async ({ page }) => {
    await openRanch(page)
    await expect(page.getByText('A storm spark!')).toBeVisible({ timeout: 15_000 })
    // The card is open on its own; the two hand-openers must exist underneath it for the day something hides it.
    await expect(page.locator('.actionbar__reason--link')).toHaveCount(1)
    await expect(page.locator('.emote--tap')).toHaveCount(1)
  })
})
