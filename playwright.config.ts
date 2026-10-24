import { defineConfig, devices } from '@playwright/test'

/**
 * M9 smoke test: the built app, served by `vite preview`, driven in the installed Google Chrome with phone
 * emulation (a Pixel and an iPhone profile; both run in Chromium, so no browser download is needed).
 * `npm run e2e` builds first. Not part of `npm run verify` or the deploy.
 */
const BASE = 'http://localhost:4173/wildsong-ranch/'

export default defineConfig({
  testDir: 'e2e',
  timeout: 150_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: 'list',
  // A missing control fails in seconds rather than waiting out the whole test.
  use: { baseURL: BASE, actionTimeout: 10_000, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'pixel-7', use: { ...devices['Pixel 7'], channel: 'chrome' } },
    { name: 'iphone-14', use: { ...devices['iPhone 14'], browserName: 'chromium', channel: 'chrome' } },
  ],
  webServer: {
    command: 'npm run build && npx vite preview --port 4173 --strictPort',
    url: BASE,
    reuseExistingServer: true,
    timeout: 240_000,
  },
})
