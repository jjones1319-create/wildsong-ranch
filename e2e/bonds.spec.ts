import { expect, test, type Page } from '@playwright/test'
import type { GameState } from '../src/core/state.ts'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * The Bonds update (GAME_DESIGN §6.9–§6.10) at 360 × 780: the hello (pet, treat), a day away, two days away, four
 * days away (the note, then the Farewell), Vacation mode stopping it, a Fetch week (a bot that lets go in the green)
 * and a shopping trip that buys a keepsake for the ranch. The away clock is set by arming it hours ago in the save.
 */
const BASE = '/wildsong-ranch/'
const W = 360
const H = 3_600_000

async function open(page: Page, edit: (g: GameState) => void): Promise<void> {
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
}

/** The clip ends by itself, or a tap skips it. */
async function skipClip(page: Page): Promise<void> {
  await page.locator('.clip').click()
}

const awayFor = (hours: number, o: { loyal?: boolean; vacation?: boolean } = {}) => (g: GameState) => {
  g.away = { armedAt: Date.now() - hours * H, lastGreetAt: null }
  if (o.vacation) g.settings.vacation = true
  if (o.loyal && g.monster) {
    g.monster.spoil = 70
    g.monster.fear = 70
  }
}

test('the hello: your monster runs up, you pet it and give it a treat', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await open(page, awayFor(3, { loyal: true }))
  await expect(page.getByText('Pip spots you and comes running!')).toBeVisible({ timeout: 20_000 })
  await page.waitForTimeout(2600)
  await page.screenshot({ path: info.outputPath('1-hello.png') })
  await skipClip(page)
  await page.getByRole('button', { name: /Pet Pip/ }).first().click()
  await expect(page.getByText('leans into your hand')).toBeVisible()
  await page.getByRole('button', { name: /Give a treat/ }).click()
  await expect(page.getByText('crunches the biscuit')).toBeVisible()
  await page.screenshot({ path: info.outputPath('2-hello-done.png') })
  await page.getByRole('button', { name: 'Back to the ranch' }).click()
  await expect(page.locator('.stage')).toBeVisible()
  expect(errors).toEqual([])
})

test('a day away, then two days away: sad, then abandoned, with what it cost', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  await open(page, awayFor(30))
  await expect(page.getByRole('heading', { name: 'While you were away…' })).toBeVisible({ timeout: 20_000 })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: info.outputPath('3-sad-clip.png') })
  await skipClip(page)
  await expect(page.getByText('Stress +15')).toBeVisible()
  await expect(page.getByText(/Vacation mode/).first()).toBeVisible()
  await page.screenshot({ path: info.outputPath('4-sad-card.png') })
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.locator('.stage')).toBeVisible()
})

test('two days away: the ranch looks abandoned, and your monster is sick', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  await open(page, awayFor(50))
  await expect(page.getByRole('heading', { name: 'The ranch has gone quiet…' })).toBeVisible({ timeout: 20_000 })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: info.outputPath('5-abandoned-clip.png') })
  await skipClip(page)
  await expect(page.getByText('Lifespan -2 weeks')).toBeVisible()
  await expect(page.getByText('Sick for 1 week')).toBeVisible()
  await page.screenshot({ path: info.outputPath('6-abandoned-card.png') })
})

test('four days away: the note on the gate, then the Farewell', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await open(page, awayFor(100))
  await expect(page.getByRole('heading', { name: 'A note on the gate' })).toBeVisible({ timeout: 20_000 })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: info.outputPath('7-note-clip.png') })
  await skipClip(page)
  await page.getByRole('button', { name: 'Read the note' }).click()
  await expect(page.getByText('Why did you leave me?')).toBeVisible()
  await expect(page.getByText('Pip passed away while you were gone.')).toBeVisible()
  await page.screenshot({ path: info.outputPath('8-note.png') })
  await page.getByRole('button', { name: 'Say goodbye' }).click()
  await expect(page).toHaveURL(/#farewell$/)
  await expect(page.getByText('waited by the gate for you')).toBeVisible()
  await page.screenshot({ path: info.outputPath('9-farewell.png') })
  expect(errors).toEqual([])
})

test('Vacation mode: four days away is just a hello', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  await open(page, awayFor(100, { vacation: true, loyal: true }))
  await expect(page.getByText('Pip spots you and comes running!')).toBeVisible({ timeout: 20_000 })
  await skipClip(page)
  await page.getByRole('button', { name: 'Back to the ranch' }).click()
  await expect(page.getByText('🏖 Vacation mode is on')).toBeVisible()
})

test('a Bond week: fetch boosts training; a shopping trip buys a keepsake for the ranch', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await open(page, (g) => {
    g.away = { armedAt: Date.now(), lastGreetAt: Date.now() }
  })
  await expect(page.locator('.stage')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: 'Train' }).click()
  await page.getByRole('tab', { name: 'Bond 💞' }).click()
  await page.screenshot({ path: info.outputPath('10-bond-tab.png') })
  await page.getByRole('button', { name: /Play fetch/ }).click()

  // A bot holds the throw button and lets go when the bar is in the green.
  await page.evaluate(async () => {
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))
    for (let i = 0; i < 5; i++) {
      const btn = document.querySelector<HTMLButtonElement>('.fetch__throw')!
      while (btn.disabled) await wait(50)
      btn.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: 'touch', isPrimary: true, pointerId: 1 }))
      for (;;) {
        await wait(8)
        const m = /scaleX\(([\d.]+)\)/.exec(document.querySelector<HTMLElement>('.fetch__fill')!.style.transform)
        const p = m ? Number(m[1]) : 0
        if (p >= 0.68 && p <= 0.8) break
      }
      btn.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerType: 'touch', isPrimary: true, pointerId: 1 }))
      await wait(300)
    }
  })
  await expect(page.getByText(/Caught \d of 5/).last()).toBeVisible({ timeout: 20_000 })
  await page.screenshot({ path: info.outputPath('11-fetch.png') })
  await page.getByRole('button', { name: 'Finish the week' }).click()
  await expect(page.getByText(/brought every one back/)).toBeVisible({ timeout: 10_000 })
  await page.getByRole('button', { name: /Next week|Continue|Back/ }).first().click()
  await expect(page.getByText('💞 ×1.75')).toBeVisible()

  await page.getByRole('button', { name: 'Train' }).click()
  await page.getByRole('tab', { name: 'Bond 💞' }).click()
  await page.getByRole('button', { name: /Shopping trip/ }).click()
  await expect(page.getByText('Pip found something!')).toBeVisible({ timeout: 10_000 })
  await page.screenshot({ path: info.outputPath('12-shop.png') })
  await page.getByRole('button', { name: /Buy it/ }).click()
  await page.getByRole('button', { name: 'Finish the week' }).click()
  await expect(page.getByText(/sits on the ranch/)).toBeVisible({ timeout: 10_000 })
  await page.getByRole('button', { name: /Next week|Continue|Back/ }).first().click()
  await expect(page.locator('.keepsake')).toHaveCount(1)
  await page.screenshot({ path: info.outputPath('13-ranch-keepsake.png') })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(W)
  expect(errors).toEqual([])
})
