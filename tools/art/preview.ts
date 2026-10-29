/**
 * Shared by the art scripts: build the app, serve dist/ with `vite preview` on port 4173, and launch the
 * installed Chrome headless with software WebGL so the 3D monsters render on the build machine.
 */
import { execFileSync, spawn, spawnSync, type ChildProcess } from 'node:child_process'
import { chromium, devices, type Browser, type BrowserContext } from '@playwright/test'

export const PORT = 4173
export const BASE = `http://localhost:${PORT}/wildsong-ranch/`
const IS_WIN = process.platform === 'win32'

/** What the Models viewer exposes for these scripts (src/ui/screens/lab/LabModels.tsx). */
declare global {
  interface Window {
    __art3d?: {
      ready: boolean
      set: (s: Record<string, unknown>) => void
      snapshot: (req: Record<string, unknown>) => Promise<string | null>
      step: (ms: number) => void
      loseContext: () => void
      restoreContext: () => void
      stats: () => unknown
      state: () => { variant: string | null; clip: string | null; stage: number; face: string } | null
    }
  }
}

export function killStalePreview(): void {
  if (!IS_WIN) return
  try {
    const out = execFileSync('netstat', ['-ano'], { encoding: 'utf8' })
    for (const line of out.split('\n')) {
      if (line.includes(`:${PORT}`) && line.includes('LISTENING')) {
        const pid = line.trim().split(/\s+/).pop()
        if (pid && /^\d+$/.test(pid)) spawnSync('taskkill', ['/PID', pid, '/F', '/T'], { stdio: 'ignore' })
      }
    }
  } catch {
    /* nothing listening */
  }
}

export function buildApp(): void {
  execFileSync(IS_WIN ? 'npm.cmd' : 'npm', ['run', 'build'], { stdio: 'inherit', shell: IS_WIN })
}

async function waitFor(url: string, ms: number): Promise<boolean> {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) {
    try {
      const r = await fetch(url)
      if (r.ok) return true
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 300))
  }
  return false
}

export async function startPreview(): Promise<ChildProcess> {
  killStalePreview()
  const proc = spawn(IS_WIN ? 'npx.cmd' : 'npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], { stdio: 'ignore', shell: IS_WIN })
  if (!(await waitFor(BASE, 60_000))) {
    proc.kill()
    throw new Error('vite preview did not come up on 4173')
  }
  return proc
}

export function stopPreview(proc: ChildProcess | null): void {
  try {
    proc?.kill()
  } catch {
    /* already gone */
  }
  killStalePreview()
}

/** Chrome with WebGL forced on through ANGLE's software path (headless Chrome blocks it otherwise). */
export async function launchChrome(): Promise<Browser> {
  return chromium.launch({
    channel: 'chrome',
    headless: true,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'],
  })
}

/** A phone-shaped context at 412 CSS px wide (the Pixel 7 profile), at 2× so outlines read on the sheets. */
export async function phoneContext(browser: Browser, dpr = 2): Promise<BrowserContext> {
  const d = devices['Pixel 7']!
  return browser.newContext({ ...d, deviceScaleFactor: dpr, viewport: { width: 412, height: 915 } })
}

export function dataUrlToPng(dataUrl: string): Buffer {
  const i = dataUrl.indexOf(',')
  return Buffer.from(dataUrl.slice(i + 1), 'base64')
}
