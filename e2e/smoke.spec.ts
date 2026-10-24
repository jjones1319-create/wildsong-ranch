import { expect, test, type Locator, type Page } from '@playwright/test'

/**
 * BUILD_PLAN M9: new game → train for a week → a battle → the save survives a reload, on phone emulation.
 * Controls are found by their visible text, like a player would: buttons, tabs (the segmented controls) and
 * radios (the difficulty cards). A string matches part of the label ("Serve" finds "Serve Turnips (20G)");
 * a RegExp matches part of it.
 */

const BASE = '/wildsong-ranch/'
const TAPPABLE = 'button:visible, [role=button]:visible, [role=tab]:visible, [role=radio]:visible'

/** The first visible, enabled control whose text is `name` (or matches it). */
function tap(page: Page, name: string | RegExp): Locator {
  // A label's spans run together in the DOM ("♥ Praise", "？Side AChoose…", "ContinueJo · Hillside"), so a
  // string is a plain substring match (Playwright: case-insensitive, whitespace-normalised).
  const hasText = name
  return page.locator(TAPPABLE, { hasText }).and(page.locator(':not([disabled])')).first()
}

/** Clicks a control if it is on screen right now (tips, "Got it" cards). */
async function tapIfVisible(page: Page, name: string | RegExp): Promise<boolean> {
  const b = tap(page, name)
  if (await b.isVisible().catch(() => false)) {
    await b.click()
    return true
  }
  return false
}

test('new game, a week of training, a battle, and the save survives a reload', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))

  // Title → New Game.
  await page.goto(BASE)
  await expect(page.getByText('Wildsong Ranch').first()).toBeVisible()
  await tap(page, 'New Game').click()
  await tapIfVisible(page, 'Start anyway')
  await page.getByLabel('Your name').fill('Jo')
  await page.getByLabel('Ranch name').fill('Hillside')
  await tap(page, 'Next').click()
  await tap(page, /^\s*Gentle/).click()
  await tap(page, 'Next').click()
  await tap(page, /Tumblefox/).click()
  await tap(page, 'Next').click()
  await expect(page.getByText('Meet').first()).toBeVisible()
  await page.getByLabel('Name').first().fill('Pip')
  await tap(page, 'Begin').click()

  // The ranch: welcome, the month's food, then a drill.
  await expect(page.getByText('Hillside').first()).toBeVisible()
  await tapIfVisible(page, 'Got it')
  await expect(page.getByText("This month's food")).toBeVisible()
  await tapIfVisible(page, 'Got it')
  await tap(page, 'Serve').click()
  await expect(tap(page, 'Train')).toBeVisible()
  await tapIfVisible(page, 'Got it')
  await tap(page, 'Train').click()
  await tap(page, /Hill Sprints|Target Toss|Dodge the Gourds|Puzzle Stones/).click()
  await tapIfVisible(page, 'Skip')
  await tapIfVisible(page, 'Got it')
  await expect(tap(page, 'Praise')).toBeVisible()
  await tap(page, 'Praise').click()
  await tap(page, 'Continue').click()
  await expect(page.getByText('Pip').first()).toBeVisible()

  // A CPU vs CPU battle from the Lab's Versus tab, at ×4 speed.
  await page.goto(`${BASE}#lab`)
  await tap(page, 'Versus').click()
  await tap(page, 'Choose…').click()
  await tap(page, 'Presets').click()
  await page.locator('.sheet .mcard').nth(3).click()
  await tap(page, 'Choose…').click()
  await tap(page, 'Presets').click()
  await page.locator('.sheet .mcard').nth(13).click()
  await tap(page, 'CPU vs CPU').click()
  await tap(page, 'Fight!').click()
  await tap(page, '×4').click()
  await expect(tap(page, 'Rematch')).toBeVisible({ timeout: 90_000 })
  await tap(page, 'Done').click()

  // The save survives a reload: the ranch still knows Pip and Hillside, and Continue opens it.
  await page.goto(`${BASE}#ranch`)
  await page.reload()
  await expect(page.getByText('Pip').first()).toBeVisible()
  await page.goto(`${BASE}#title`)
  await expect(page.getByText('Hillside').first()).toBeVisible()
  await tap(page, 'Continue').click()
  await expect(page.getByText('Pip').first()).toBeVisible()

  expect(errors).toEqual([])
})
