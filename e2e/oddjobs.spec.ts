import { expect, test, type Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * CONTENT §13 Odd Jobs 2 at 360 × 780 (the narrowest phone): Turnip Sort past 150G into overtime (weeds, the
 * Compost bin) until an item slides off; Echo Stones to round 12 with the Moon stone; Meadow Dash winning heat 1
 * by tapping and losing heat 2 by not. Small in-page bots play each game (they read the screen like a player:
 * the item on the chute, the stones that light up, the Run pad).
 */
const BASE = '/wildsong-ranch/'
const W = 360

async function openJobs(page: Page): Promise<void> {
  await page.setViewportSize({ width: W, height: 780 })
  const json = saveJsonAt({ year: 1, month: 3, week: 2, grade: 'C' })
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
    location.hash = '#town/jobs'
  })
  await expect(page.locator('.jobcard')).toHaveCount(3)
}

async function noSidewaysScroll(page: Page): Promise<void> {
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 360 px').toBeLessThanOrEqual(W)
}

async function play(page: Page, job: string): Promise<void> {
  await page.locator('.jobcard', { hasText: job }).getByRole('button', { name: 'Play for pay' }).click()
}

test('Turnip Sort: 150G in the first phase, then overtime with weeds until one slides off', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openJobs(page)
  await expect(page.locator('.jobcard', { hasText: 'Turnip Sort' })).toContainText('5G an item, no limit')
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('1-board.png'), fullPage: true })
  await play(page, 'Turnip Sort')
  await page.getByRole('button', { name: 'Start sorting' }).click()

  // A bot sorts every item the moment it shows, until told to stop.
  await page.evaluate(() => {
    const w = window as unknown as { sortBot: number; sorted: number }
    w.sorted = 0
    w.sortBot = window.setInterval(() => {
      const item = document.querySelector('.chute__item')?.textContent ?? ''
      const buttons = [...document.querySelectorAll<HTMLButtonElement>('.chute__btn')]
      const pick = item.includes('🥕') ? buttons[0] : item.includes('🌿') ? buttons.find((b) => b.textContent!.includes('Compost')) : item.includes('🪨') ? buttons[buttons.length - 1] : undefined
      if (pick) {
        pick.click()
        w.sorted += 1
      }
    }, 40)
  })
  await expect(page.locator('.chute__intro')).toBeVisible({ timeout: 32_000 })
  await expect(page.locator('.chute__score')).toContainText('No clock now!')
  await page.screenshot({ path: info.outputPath('2-overtime-intro.png') })
  await page.getByRole('button', { name: 'Ready' }).click()
  await expect(page.getByRole('button', { name: '▼ Compost' })).toBeVisible()
  // Let the bot sort a dozen overtime items, then stop it so the next one slides off.
  await page.waitForFunction(() => (window as unknown as { sorted: number }).sorted >= 42, null, { timeout: 30_000 })
  await page.screenshot({ path: info.outputPath('3-overtime.png') })
  await noSidewaysScroll(page)
  await page.evaluate(() => clearInterval((window as unknown as { sortBot: number }).sortBot))
  await expect(page.getByText('One slid off the end of the chute.')).toBeVisible({ timeout: 5_000 })
  const pay = Number((await page.locator('.card p.heading').innerText()).replace(/[^0-9]/g, ''))
  expect(pay).toBeGreaterThan(150)
  await page.screenshot({ path: info.outputPath('4-done.png') })
  await page.getByRole('button', { name: 'Done' }).click()
  await expect(page.locator('.jobcard', { hasText: 'Turnip Sort' })).toContainText('Paid this week')
  await expect(page.locator('.jobcard', { hasText: 'Turnip Sort' })).toContainText(/Best: \d+ sorted/)
  expect(errors).toEqual([])
})

test('Echo Stones: the Moon stone wakes at round 11 and the game goes on', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  test.setTimeout(240_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openJobs(page)
  await play(page, 'Echo Stones')
  await page.getByRole('button', { name: 'Listen' }).click()

  // A bot listens (records each stone as it lights) and echoes the tune back, up to `stopAt` rounds.
  await page.evaluate(() => {
    const w = window as unknown as { echoBot: number; heard: number[]; stopAt: number; lastLit: number | null; echoing: boolean }
    w.heard = []
    w.stopAt = 12
    w.lastLit = null
    w.echoing = false
    const stoneOf = (el: Element): number => Number([...el.classList].find((c) => /^stone--\d$/.test(c))!.slice(7))
    w.echoBot = window.setInterval(() => {
      const open = document.querySelector('.echo__grid--open')
      const round = Number(document.querySelector('.chute__score span')?.textContent?.replace(/\D/g, '') ?? 0)
      if (!open) {
        if (w.echoing) return
        const lit = document.querySelector('.stone--lit')
        const now = lit ? stoneOf(lit) : null
        if (now !== null && w.lastLit === null) w.heard.push(now)
        w.lastLit = now
        return
      }
      if (w.echoing || round > w.stopAt) return
      w.echoing = true
      const tune = w.heard.slice(-round)
      let i = 0
      const next = (): void => {
        const stones = [...document.querySelectorAll<HTMLButtonElement>('.stone')]
        stones.find((s) => stoneOf(s) === tune[i])?.click()
        i += 1
        if (i < tune.length) window.setTimeout(next, 30)
        else
          window.setTimeout(() => {
            w.heard = []
            w.lastLit = null
            w.echoing = false
          }, 30)
      }
      next()
    }, 10)
  })
  await expect(page.locator('.chute__score')).toContainText('Round 11', { timeout: 120_000 })
  await expect(page.getByText('A fifth stone wakes: the Moon!')).toBeVisible()
  await expect(page.locator('.stone')).toHaveCount(5)
  await page.screenshot({ path: info.outputPath('5-moon.png') })
  await expect(page.locator('.chute__score')).toContainText('Round 13', { timeout: 60_000 })
  await expect(page.locator('.echo__grid--open')).toBeVisible({ timeout: 30_000 })
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('6-round13.png') })
  await page.evaluate(() => clearInterval((window as unknown as { echoBot: number }).echoBot))
  // Two wrong stones (anything but round 13's first note): the retry, then the slip that ends the game.
  const first = await page.evaluate(() => {
    const heard = (window as unknown as { heard: number[] }).heard
    return heard[heard.length - 13]
  })
  await page.locator(`.stone:not(.stone--${first})`).first().click()
  await page.getByRole('button', { name: 'Listen again' }).click()
  await expect(page.locator('.echo__grid--open')).toBeVisible({ timeout: 30_000 })
  await page.locator(`.stone:not(.stone--${first})`).first().click()
  await expect(page.getByText('Rounds cleared: 12')).toBeVisible({ timeout: 10_000 })
  await expect(page.locator('.card p.heading')).toContainText('180')
  await page.screenshot({ path: info.outputPath('7-echo-done.png') })
  expect(errors).toEqual([])
})

test('Meadow Dash: tapping wins heat 1, standing still loses heat 2, and the heats won are paid', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openJobs(page)
  await expect(page.locator('.jobcard', { hasText: 'Meadow Dash' })).toContainText('25G a heat, no limit')
  await play(page, 'Meadow Dash')
  await page.screenshot({ path: info.outputPath('8-dash-intro.png') })
  await page.getByRole('button', { name: 'To the start line' }).click()
  await expect(page.locator('.dash__lane')).toHaveCount(4)
  await expect(page.locator('.dash__count')).toHaveText('3')
  await page.screenshot({ path: info.outputPath('9-countdown.png') })

  // Tap the pad about 8 times a second, like a quick thumb.
  await page.evaluate(() => {
    const w = window as unknown as { tapBot: number }
    w.tapBot = window.setInterval(() => {
      document.querySelector('.dash__pad')?.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: 'touch', isPrimary: true }))
    }, 120)
  })
  await page.waitForTimeout(4_500)
  await noSidewaysScroll(page)
  await page.screenshot({ path: info.outputPath('10-running.png') })
  await expect(page.getByText('Heat 1 won!')).toBeVisible({ timeout: 15_000 })
  await page.evaluate(() => clearInterval((window as unknown as { tapBot: number }).tapBot))
  await page.screenshot({ path: info.outputPath('11-heat-won.png') })
  const next = page.getByRole('button', { name: 'Next heat' })
  await expect(next).toBeDisabled()
  await expect(next).toBeEnabled({ timeout: 3_000 })
  await next.click()
  await expect(page.locator('.chute__score')).toContainText('Heat 2')
  await expect(page.getByText('got there first in heat 2')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Heats won: 1')).toBeVisible()
  await expect(page.locator('.card p.heading')).toContainText('25')
  await page.screenshot({ path: info.outputPath('12-dash-done.png') })
  await expect(page.getByRole('button', { name: 'Done' })).toBeEnabled({ timeout: 3_000 })
  await page.getByRole('button', { name: 'Done' }).click()
  await expect(page.locator('.jobcard', { hasText: 'Meadow Dash' })).toContainText('Best: 1 heat won')
  expect(errors).toEqual([])
})
