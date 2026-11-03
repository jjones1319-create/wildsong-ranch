import { expect, test, type Page } from '@playwright/test'
import { makePreset } from '../src/core/presets.ts'
import { FARM } from '../src/data/tuning.ts'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * v1.21 growing the farm (GAME_DESIGN §9.1, §6.11) at 360 × 780: a farm at level 2 with 5,000G shows "+ pen" on the
 * herd strip; the farm card builds the pen; a second ranch-mate moves in from the Freezer; the herd sheet and the
 * Monster Card show the friendship with the star. Screenshots go to art-review/farm/ (gitignored) for the review.
 */
const BASE = '/wildsong-ranch/'
const W = 360
const SHOTS = 'art-review/farm'

async function openWith(page: Page): Promise<void> {
  await page.setViewportSize({ width: W, height: 780 })
  const json = saveJsonAt({
    year: 1,
    month: 6,
    week: 2,
    grade: 'C',
    edit: (g) => {
      const fern = makePreset('puddlepup', 'C')
      fern.id = 'fern'
      fern.name = 'Fern'
      g.ranchmates = [{ monster: fern, order: { kind: 'play' }, last: { kind: 'play' }, history: [] }]
      const moss = makePreset('cobblemaw', 'E')
      moss.id = 'moss'
      moss.name = 'Moss'
      g.freezer = [moss]
      g.farm.xp = FARM.levelXp[1]! + 20
      g.friendships = [{ a: g.monster!.id < 'fern' ? g.monster!.id : 'fern', b: g.monster!.id < 'fern' ? 'fern' : g.monster!.id, points: 40 }]
      g.homecoming = { status: 'done', welcome: [] }
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

test('a level-2 farm builds a pen, a second ranch-mate fits, and friendships show', async ({ page }) => {
  await openWith(page)
  const strip = page.locator('.herd')
  await expect(strip).toBeVisible({ timeout: 20_000 })
  await expect(strip.getByText('Pens 1/1 · Farm Lv 2')).toBeVisible()
  const plus = strip.getByRole('button', { name: 'Build another pen at Ranch Upgrades.' })
  await expect(plus).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 360 px').toBeLessThanOrEqual(W)
  await page.screenshot({ path: `${SHOTS}/1-strip.png` })

  // "+ pen" opens Ranch Upgrades with the farm card on top
  await plus.click()
  const card = page.locator('.farmcard')
  await expect(card).toBeVisible()
  await expect(card.getByText('Farm Lv 2')).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/2-farm-card.png` })
  await card.getByRole('button', { name: 'Build a pen (3,000G)' }).click()
  await page.getByRole('button', { name: 'Build a pen (3,000G)' }).last().click()
  await expect(page.getByText('The new pen is built!')).toBeVisible()
  await expect(card.getByText('Pens built: 2 of 6')).toBeVisible()
  await expect(card.getByText('The farm needs to reach Lv 4 first.')).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/3-built.png`, fullPage: true })

  // back on the ranch: an empty pen and the next one locked
  await page.goBack()
  await expect(strip.getByText('Pens 1/2 · Farm Lv 2')).toBeVisible()
  await expect(strip.getByText('🔒 Lv 4')).toBeVisible()
  await strip.getByRole('button', { name: 'An empty pen. Move a monster in.' }).click()
  await page.getByText('Moss').first().click()
  await expect(strip.locator('.herd__tile', { hasText: 'Moss' })).toBeVisible()
  await expect(strip.getByText('Pens 2/2 · Farm Lv 2')).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/4-two-mates.png` })

  // Fern's sheet: her friendship with the star; then her Monster Card's Friends section
  await strip.locator('.herd__tile', { hasText: 'Fern' }).click()
  await expect(page.getByText('Close friends').first()).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/5-sheet-friend.png` })
  await page.getByRole('button', { name: 'Monster Card', exact: true }).click()
  const friends = page.getByRole('region', { name: 'Friends' })
  await expect(friends).toBeVisible()
  await expect(friends.getByText('Pip')).toBeVisible()
  await friends.scrollIntoViewIfNeeded()
  await page.screenshot({ path: `${SHOTS}/6-card-friends.png` })
})

test('a new farm level is celebrated in the week summary, with Ines’s letter', async ({ page }) => {
  await page.setViewportSize({ width: W, height: 780 })
  const json = saveJsonAt({
    year: 1,
    month: 6,
    week: 2,
    edit: (g) => {
      const fern = makePreset('puddlepup', 'C')
      fern.id = 'fern'
      fern.name = 'Fern'
      g.ranchmates = [{ monster: fern, order: { kind: 'rest' }, last: null, history: [] }]
      g.farm.xp = FARM.levelXp[2]! - 1
      g.homecoming = { status: 'done', welcome: [] }
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
  await expect(page.locator('.herd')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: 'Rest', exact: true }).click()
  const party = page.locator('.farmup')
  await expect(party).toBeVisible({ timeout: 15_000 })
  await expect(party.getByText('Farm Lv 3!')).toBeVisible()
  await expect(party.getByText('New: Feed Shed')).toBeVisible()
  await expect(page.getByText('The farm reached level 3! Ines sent a letter from the Guild.')).toBeVisible()
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${SHOTS}/7-level-up.png` })
})
