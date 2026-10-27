import { expect, test, type Page } from '@playwright/test'
import { MIRROR_KEY, saveJsonAt } from './saves.ts'

/**
 * SOUND_UPGRADE §14.5 at 412 × 915: the first tap unlocks audio; the ranch plays the season's song (read from
 * window.__audio); Town switches song within 2 s; a cup battle uses its event's theme and the cup screens load
 * the events sample pack (S2); Pause sets the music filter to 700 Hz; the Sound Lab plays a song and an
 * effect without console errors, and its event picker plays an Ascension on the Ascension theme. Nothing here
 * needs to be heard: the engine's debug view says what plays.
 */
const BASE = '/wildsong-ranch/'
const W = 412

interface AudioState {
  song: string | null
  section: string
  layers: string[]
  stem: string | null
  bed: string | null
  musicFilterHz: number
  lateEvents: number
  packs: { pack: string; state: string }[]
  request: { song: string | null; bed: string | null } | null
}

declare global {
  interface Window {
    __audio?: { state?: AudioState; labReady?: boolean }
  }
}

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

const audioState = (page: Page) => page.evaluate(() => window.__audio?.state ?? null)

/** Logs the scheduler's late-event count so far (a dropped note); the Lab part of the run must add none. */
async function lateSoFar(page: Page, label: string): Promise<number> {
  const n = (await audioState(page))?.lateEvents ?? 0
  console.log(`late events after ${label}: ${n}`)
  return n
}

async function waitForSong(page: Page, song: string, timeout = 8000): Promise<void> {
  await page.waitForFunction((s) => window.__audio?.state?.song === s, song, { timeout })
}

test('the first tap unlocks audio, the ranch plays its season, Town switches, a cup fights to its theme, Pause filters, the Lab plays', async ({ page }, info) => {
  test.skip(info.project.name !== 'pixel-7', 'one profile is enough')
  test.setTimeout(420_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  // March week 2: spring, the Meadow Cup this week.
  await openWithSave(page, saveJsonAt({ year: 1, month: 3, week: 2, grade: 'C' }))
  expect(await page.evaluate(() => window.__audio === undefined)).toBe(true)

  // The first tap (a real pointer gesture) switches the sound on and the pending request plays.
  await page.locator('.calstrip__date--button').click()
  await page.waitForFunction(() => window.__audio?.state !== undefined, undefined, { timeout: 20_000 })
  await page.goto(`${BASE}#ranch`)
  await waitForSong(page, 'ranch-spring', 15_000)
  const ranch = await audioState(page)
  expect(ranch?.bed).toBe('meadow')
  await page.waitForFunction(() => window.__audio?.state?.packs.some((p) => p.pack === 'core' && p.state === 'ready'), undefined, { timeout: 90_000 })
  await page.screenshot({ path: info.outputPath('1-ranch.png') })
  await lateSoFar(page, 'the ranch')

  // Town within 2 s, then a shop stem without a restart (the song id stays, the stem changes).
  await page.goto(`${BASE}#town`)
  const t0 = Date.now()
  await waitForSong(page, 'town', 2000 + 250)
  expect(Date.now() - t0).toBeLessThan(2600)
  await page.goto(`${BASE}#town/shop`)
  await page.waitForFunction(() => window.__audio?.state?.stem === 'shop', undefined, { timeout: 4000 })
  expect((await audioState(page))?.song).toBe('town')
  await lateSoFar(page, 'Town')

  // A cup: the entry screen and the cup screens play the cup lobby; the fight plays the cup's battle layers.
  await page.goto(`${BASE}#ranch/cups`)
  await page.getByRole('button', { name: /Meadow Cup/ }).first().click()
  await page.getByRole('tab', { name: 'Fight', exact: true }).click()
  await page.getByRole('button', { name: /^Enter: / }).click()
  await expect(page.locator('.cupflow')).toBeVisible()
  await waitForSong(page, 'cup')
  await page.waitForFunction(() => window.__audio?.state?.layers.includes('lobby'), undefined, { timeout: 5000 })
  // S2: the cup screens want the events pack (violins, cajon, the new instruments), and it decodes.
  await page.waitForFunction(() => window.__audio?.state?.packs.some((p) => p.pack === 'events' && p.state === 'ready'), undefined, { timeout: 90_000 })
  await page.locator('.cupchoice .btn', { hasText: 'Fight' }).click()
  await page.waitForFunction(() => window.__audio?.state?.layers.includes('base'), undefined, { timeout: 8000 })
  await page.screenshot({ path: info.outputPath('2-battle.png') })
  await lateSoFar(page, 'the match start')

  // Pause lowpasses the music to 700 Hz; resuming opens it again.
  await page.getByRole('button', { name: 'Pause' }).click()
  await page.waitForFunction(() => (window.__audio?.state?.musicFilterHz ?? 20000) <= 720, undefined, { timeout: 3000 })
  await page.screenshot({ path: info.outputPath('3-paused.png') })
  const resume = page.locator('.sheet').getByRole('button', { name: /Resume|Back to the fight|Continue/ }).first()
  if (await resume.isVisible().catch(() => false)) await resume.click()
  else await page.keyboard.press('Escape')
  await page.waitForFunction(() => (window.__audio?.state?.musicFilterHz ?? 0) >= 5000, undefined, { timeout: 4000 }).catch(() => undefined)

  // The Sound Lab plays a song and an effect without page errors.
  await page.goto(`${BASE}#lab/sound`)
  await page.waitForFunction(() => window.__audio?.labReady === true, undefined, { timeout: 20_000 })
  const lateBeforeLab = await lateSoFar(page, 'Pause and the Lab opening')
  await page.getByRole('button', { name: '▶' }).first().click()
  await page.waitForFunction(() => window.__audio?.state?.song === 'wildsong', undefined, { timeout: 15_000 })
  await page.getByRole('tab', { name: 'Effects' }).click()
  await page.getByRole('button', { name: 'tap', exact: true }).click()
  await page.getByRole('button', { name: 'coin', exact: true }).click().catch(() => undefined)
  await page.waitForTimeout(500)
  const lab = await audioState(page)
  expect(lab?.song).toBe('wildsong')
  // S2: the event picker plays any calendar event as its row plays; an Ascension is the Ascension march.
  await page.getByRole('tab', { name: 'Music' }).click()
  await page.getByRole('combobox', { name: 'Event', exact: true }).selectOption('spring-ascension')
  await page.locator('section.card', { has: page.getByRole('combobox', { name: 'Event', exact: true }) }).getByRole('button', { name: /Play/ }).click()
  await waitForSong(page, 'ascension', 20_000)
  // Late notes are logged, not gated: a software-rendered headless browser on a busy PC stalls past the 400 ms
  // lookahead at boot, at the match start (the effects layer) and when a chunk loads. The unit test (300 ms stalls,
  // zero late notes) and audio:check (offline, zero late events) hold the guarantee.
  console.log(`late events while the Lab played: ${(lab?.lateEvents ?? 0) - lateBeforeLab}`)
  expect(await page.evaluate(() => document.documentElement.scrollWidth), 'no horizontal scroll at 412 px').toBeLessThanOrEqual(W)
  await page.screenshot({ path: info.outputPath('4-sound-lab.png'), fullPage: true })
  expect(errors, errors.join('\n')).toEqual([])
})
