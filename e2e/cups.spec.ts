import { expect, test, type Page } from '@playwright/test'
import { STAT_KEYS } from '../src/data/types.ts'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * "Playable events + round-by-round cups" at 412 × 915: an Official (RR6) played a round at a time. Round 1 is
 * fought by hand, round 2 starts on Auto and is taken over and handed back, the rest are skipped; after each round
 * the results and the standings appear; the Rounds tab shows the schedule; the cup finishes. Also an Elim4 cup's
 * bracket and the Summit's legs. Screenshots land in test-results for the layout review.
 */
const BASE = '/wildsong-ranch/'
const W = 412
const H = 915

async function openWithSave(page: Page, json: string): Promise<void> {
  await page.setViewportSize({ width: W, height: H })
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

async function enterCup(page: Page, name: RegExp, mode: 'Fight' | 'Auto'): Promise<void> {
  await page.goto(`${BASE}#ranch/cups`)
  await page.getByRole('button', { name }).first().click()
  await page.getByRole('tab', { name: mode, exact: true }).click()
  await page.getByRole('button', { name: /^Enter: / }).click()
  await expect(page.locator('.cupflow')).toBeVisible()
}

async function noSidewaysScroll(page: Page): Promise<void> {
  const width = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(width, 'no horizontal scroll at 412 px').toBeLessThanOrEqual(W)
}

/** Speeds the battle up (unless it already ended), waits for the result card and taps Continue. */
async function finishBattle(page: Page): Promise<void> {
  const done = page.getByRole('button', { name: 'Continue' })
  if (!(await done.isVisible().catch(() => false))) await page.getByRole('button', { name: '×4' }).click({ timeout: 3000 }).catch(() => undefined)
  await expect(done).toBeVisible({ timeout: 60_000 })
  await done.click()
}

test('an Ascension, round by round: fight by hand, take over Auto, skip, finish', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  test.setTimeout(300_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  // A grade-E monster far above the E band, so the hand-fought first round isn't a coin flip.
  await openWithSave(page, saveJsonAt({ year: 1, month: 3, week: 4, grade: 'E', edit: (g) => STAT_KEYS.forEach((k) => (g.monster!.stats[k] = 330)) }))
  await enterCup(page, /Spring Ascension/, 'Fight')

  // Round 1 preview: every pairing, the player's highlighted, Fight / Auto / Skip.
  await expect(page.getByText('Round 1 of 5')).toBeVisible()
  await expect(page.locator('.cupflow .cuprow')).toHaveCount(3)
  await expect(page.locator('.cupflow .cuprow--me')).toHaveCount(1)
  await expect(page.locator('.cupchoice .btn')).toHaveText(['Fight', 'Auto', 'Skip'])
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('1-round1-preview.png'), fullPage: true })

  // Round 1 by hand: walk in on the pads and fire whatever glows.
  await page.locator('.cupchoice .btn', { hasText: 'Fight' }).click()
  await expect(page.locator('.pads')).toBeVisible()
  const forward = page.getByRole('button', { name: /Walk in/ })
  await forward.dispatchEvent('pointerdown', { pointerId: 1 })
  await page.waitForTimeout(1200)
  await forward.dispatchEvent('pointerup', { pointerId: 1 })
  for (let i = 0; i < 12; i++) {
    const card = page.locator('.tcard--fire').first()
    if (await card.isVisible().catch(() => false)) await card.click().catch(() => undefined)
    await page.waitForTimeout(300)
  }
  await finishBattle(page)

  // The round's results and the standings after it.
  await expect(page.getByText('Round 1 results')).toBeVisible()
  await expect(page.getByText('After round 1 of 5')).toBeVisible()
  await expect(page.locator('.cupflow .cuprow')).toHaveCount(3)
  await expect(page.locator('.cupflow .ctable tbody tr')).toHaveCount(6)
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('2-round1-recap.png'), fullPage: true })

  // The breakdown: Rounds lists all five, later ones upcoming; a finished match opens its details.
  await page.getByRole('tab', { name: 'Rounds' }).click()
  await expect(page.locator('.cuptab .cupround')).toHaveCount(5)
  // Rounds 2–5: three matches each, all still to come (a monster KO'd in round 1 already has walkovers there).
  for (let r = 1; r <= 4; r++) {
    const rows = page.locator('.cuptab .cupround').nth(r).locator('.cuprow__meta')
    await expect(rows).toHaveCount(3)
    for (const text of await rows.allTextContents()) expect(text === 'upcoming' || text.includes('walkover')).toBe(true)
  }
  await page.locator('.cuptab .cuprow:not([disabled])').nth(1).click()
  await expect(page.locator('.sheet')).toContainText('How it ended')
  await expect(page.locator('.sheet')).toContainText('Time')
  await page.screenshot({ path: info.outputPath('3-details.png') })
  await page.locator('.sheet').getByRole('button', { name: 'Close' }).click()
  await noSidewaysScroll(page)

  // The next real match on Auto: the Auto button is there, one tap takes over (pads), another hands it back.
  // Later rounds are skipped; a round the player wins or loses by walkover just plays out.
  let autoDone = false
  for (let r = 2; r <= 5; r++) {
    await page.getByRole('button', { name: `Next: round ${r}` }).click()
    await expect(page.getByText(`Round ${r} of 5`)).toBeVisible()
    const choice = page.locator('.cupchoice .btn', { hasText: 'Auto' })
    if (!(await choice.isVisible().catch(() => false))) {
      await expect(page.getByRole('button', { name: 'Skip to final standings' })).toHaveCount(0)
      await page.screenshot({ path: info.outputPath(`4-round${r}-walkover.png`), fullPage: true })
      await page.getByRole('button', { name: `Play round ${r}` }).click()
    } else if (!autoDone) {
      await choice.click()
      const autoButton = page.locator('.bctrl .btn', { hasText: 'Auto' })
      await expect(autoButton).toBeVisible()
      await expect(page.locator('.pads')).toBeHidden()
      await autoButton.click()
      await expect(page.locator('.pads')).toBeVisible()
      await autoButton.click()
      await expect(page.locator('.pads')).toBeHidden()
      await page.screenshot({ path: info.outputPath('4-auto-battle.png') })
      await finishBattle(page)
      autoDone = true
    } else await page.locator('.cupchoice .btn', { hasText: 'Skip' }).click()
    await expect(page.getByText(`Round ${r} results`)).toBeVisible()
    if (r < 5) await expect(page.getByText(`After round ${r} of 5`)).toBeVisible()
  }
  expect(autoDone, 'one match was played on Auto and taken over').toBe(true)
  await expect(page.getByText('Final standings')).toBeVisible()
  await page.screenshot({ path: info.outputPath('5-final.png'), fullPage: true })
  await page.getByRole('button', { name: 'See the results' }).click()
  await expect(page.getByRole('heading').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Continue' })).toBeVisible()
  expect(errors).toEqual([])
})

test('an Elim4 cup shows its bracket with future slots', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openWithSave(page, saveJsonAt({ year: 1, month: 1, week: 2, grade: 'E' }))
  await enterCup(page, /Snowdrift Cup/, 'Auto')
  await expect(page.getByText(/Semi-finals · Round 1 of 2/)).toBeVisible()
  await expect(page.locator('.cupchoice .btn--primary')).toHaveText('Auto')
  await page.getByRole('tab', { name: 'Bracket' }).click()
  await expect(page.locator('.bracket__col')).toHaveCount(2)
  await expect(page.locator('.bslot')).toHaveCount(3)
  await expect(page.locator('.bracket')).toContainText('Winner of')
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('6-bracket.png'), fullPage: true })
  await page.locator('.cupchoice .btn', { hasText: 'Skip' }).click()
  await expect(page.getByText('Semi-finals', { exact: false }).first()).toBeVisible()
  await page.screenshot({ path: info.outputPath('7-bracket-after-r1.png'), fullPage: true })
  expect(errors).toEqual([])
})

test('the Summit shows the five legs; the player’s leg is a real match', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openWithSave(page, saveJsonAt({ year: 4, month: 8, week: 4, grade: 'C' }))
  await enterCup(page, /Vale–Coast Summit/, 'Fight')
  await expect(page.getByText('Your leg: grade C')).toBeVisible()
  await page.getByRole('tab', { name: 'Legs' }).click()
  await expect(page.locator('.cuptab .cuprow')).toHaveCount(5)
  await expect(page.locator('.cuptab .cuprow--me')).toHaveCount(1)
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('8-summit-legs.png'), fullPage: true })
  await page.locator('.cupchoice .btn', { hasText: 'Skip' }).click()
  await expect(page.locator('.cupscore').first()).toBeVisible()
  await page.screenshot({ path: info.outputPath('9-summit-after.png'), fullPage: true })
  expect(errors).toEqual([])
})
