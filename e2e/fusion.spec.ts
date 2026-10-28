import { expect, test, type Page } from '@playwright/test'
import { makePreset } from '../src/core/presets.ts'
import type { GameState } from '../src/core/state.ts'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * GAME_DESIGN §15 Fusion 2 at 360 × 780: a frozen Coilfang and Galeheron at Dr. Pell's. The board shows both
 * parents' breeds at 35 % and two hidden surprises at 20 % and 10 %; a found recipe shows its breed by name.
 */
const BASE = '/wildsong-ranch/'
const W = 360

function freezeTwo(g: GameState): void {
  const snake = makePreset('coilfang', 'C')
  snake.id = 'snake'
  snake.name = 'Coily'
  const bird = makePreset('galeheron', 'C')
  bird.id = 'bird'
  bird.name = 'Gale'
  g.freezer = [snake, bird]
}

async function openFusion(page: Page, edit: (g: GameState) => void): Promise<void> {
  await page.setViewportSize({ width: W, height: 780 })
  const json = saveJsonAt({ year: 1, month: 3, week: 2, grade: 'C', edit })
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
  await page.evaluate(() => {
    location.hash = '#town/pell'
  })
  await page.getByRole('button', { name: 'Fusion', exact: true }).click()
  await page.getByRole('button', { name: /First parent/ }).click()
  await page.locator('.sheet').getByText('Coily').first().click()
  await page.getByRole('button', { name: /Second parent/ }).click()
  await page.locator('.sheet').getByText('Gale').first().click()
  await expect(page.locator('.odds__row')).toHaveCount(4)
}

async function noSidewaysScroll(page: Page): Promise<void> {
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 360 px').toBeLessThanOrEqual(W)
}

test('the board shows both parents at 35 % and two hidden surprises; fusing makes one whole-breed baby', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openFusion(page, freezeTwo)
  const rows = page.locator('.odds__row')
  await expect(rows.locator('.odds__pct')).toHaveText(['35%', '35%', '20%', '10%'])
  await expect(rows.nth(0)).toContainText('Coilfang')
  await expect(rows.nth(1)).toContainText('Galeheron')
  await expect(rows.nth(2)).toContainText('???')
  await expect(rows.nth(3)).toContainText('???')
  await expect(rows.locator('.odds__mystery')).toHaveCount(2)
  await expect(page.getByText('most likely')).toHaveCount(0) // a 35/35 tie has no single favorite
  await expect(page.getByText('These two might make something new')).toBeVisible()
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('1-board.png'), fullPage: true })

  await page.getByRole('button', { name: /^Fuse/ }).click()
  await page.locator('.sheet__actions .btn--primary').click()
  await expect(page.getByRole('heading', { name: /^Meet / })).toBeVisible()
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('2-born.png'), fullPage: true })
  expect(errors).toEqual([])
})

test('a found recipe shows its breed by name', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  await openFusion(page, (g) => {
    freezeTwo(g)
    g.fusionFinds = ['coilfang+galeheron>hearthwing']
  })
  const rows = page.locator('.odds__row')
  await expect(rows.nth(2)).toContainText('Hearthwing')
  await expect(rows.nth(2)).toContainText('A surprise!')
  await expect(rows.nth(2).locator('.odds__pct')).toHaveText('20%')
  await expect(rows.nth(3)).toContainText('???')
  await page.screenshot({ path: info.outputPath('3-found.png'), fullPage: true })
})
