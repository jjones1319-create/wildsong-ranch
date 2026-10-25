import { expect, test, type Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * §3 the Calendar at 412 × 915: opened from the ranch's date bar, the three views, a month tile, a ★ reminder that
 * shows on the ranch's "Next:" line, and Enter from an event held this week. A grade-C monster in March week 2:
 * the Meadow Cup (B) this week, the Spring Ascension in two weeks.
 */
const BASE = '/wildsong-ranch/'
const W = 412

async function openWithSave(page: Page, json: string): Promise<void> {
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
  await page.goto(`${BASE}#ranch`)
  await expect(page.getByText('Pip').first()).toBeVisible({ timeout: 20_000 })
}

async function noSidewaysScroll(page: Page): Promise<void> {
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 412 px').toBeLessThanOrEqual(W)
}

test('the calendar: views, a month tile, a ★ on the ranch line, Enter from this week', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openWithSave(page, saveJsonAt({ year: 1, month: 3, week: 2, grade: 'C' }))

  // The date bar tells what's next and opens the calendar.
  const dateBar = page.locator('.calstrip__date--button')
  await expect(dateBar.locator('.calstrip__next')).toHaveText('Next: Spring Ascension · in 2 wks')
  await page.screenshot({ path: info.outputPath('1-ranch-next.png') })
  await dateBar.click()
  await expect(page).toHaveURL(/#calendar$/)
  await expect(page.locator('.calweek').first()).toContainText('This week')
  await expect(page.locator('.calweek')).toHaveCount(12)
  await expect(page.locator('.calweek').first().locator('.calcard', { hasText: 'Meadow Cup' })).toBeVisible()
  await expect(page.locator('.calweek').nth(2).locator('.calcard', { hasText: 'Spring Ascension' })).toContainText('Your grade (C) · promotion')
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('2-agenda.png'), fullPage: true })

  // Month, then Year, then a month tile back into Month.
  await page.getByRole('tab', { name: 'Month' }).click()
  await expect(page.locator('.calrow')).toHaveCount(4)
  await expect(page.locator('.calrow--past')).toHaveCount(1)
  await expect(page.locator('.calrow--now')).toHaveCount(1)
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('3-month.png'), fullPage: true })
  await page.getByRole('tab', { name: 'Year' }).click()
  await expect(page.locator('.caltile')).toHaveCount(12)
  await expect(page.locator('.caltile--now')).toHaveCount(1)
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('4-year.png'), fullPage: true })
  await page.getByRole('button', { name: 'June' }).click()
  await expect(page.locator('.calnav__label')).toContainText('June, Year 1')
  await expect(page.getByRole('tab', { name: 'Month' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('.calrow').nth(2)).toContainText('Firefly Cup')
  await expect(page.locator('.calrow').first()).not.toContainText('Sunny Cup')

  // Back to this month's agenda and star the Meadow Cup.
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Previous month' }).click()
  await page.getByRole('tab', { name: 'Agenda' }).click()
  await page.locator('.calweek').first().locator('.calcard', { hasText: 'Meadow Cup' }).click()
  await expect(page.locator('.sheet')).toContainText('Round robin of 4 · 3 rounds')
  await expect(page.locator('.sheet')).toContainText("Based on Pip's grade today (C).")
  await page.screenshot({ path: info.outputPath('5-sheet.png') })
  await page.locator('.sheet').getByRole('button', { name: '☆ Remind me' }).click()
  await expect(page.locator('.sheet').getByRole('button', { name: '★ Reminder set' })).toBeVisible()
  await page.locator('.sheet').getByRole('button', { name: 'Close' }).click()
  await expect(page.locator('.calweek').first().locator('.calcard', { hasText: 'Meadow Cup' })).toContainText('★')

  // The ranch line now leads with the starred cup, and the Battle button has its dot.
  await page.getByRole('button', { name: 'Back' }).click()
  await expect(page).toHaveURL(/#ranch$/)
  await expect(page.locator('.calstrip__next')).toHaveText('★ Next: Meadow Cup · this week')
  await expect(page.locator('.actions .btn--dot')).toHaveCount(1)
  await page.screenshot({ path: info.outputPath('6-ranch-star.png') })

  // Open the cup from the calendar and Enter: the entry screen opens with it picked.
  await page.locator('.calstrip__date--button').click()
  await page.locator('.calweek').first().locator('.calcard', { hasText: 'Meadow Cup' }).click()
  await page.locator('.sheet').getByRole('button', { name: 'Enter' }).click()
  await expect(page).toHaveURL(/#ranch\/cups$/)
  await expect(page.getByRole('button', { name: 'Enter: Meadow Cup' })).toBeEnabled()
  await expect(page.getByRole('button', { name: /See calendar/ })).toBeVisible()
  await noSidewaysScroll(page)
  expect(errors).toEqual([])
})
