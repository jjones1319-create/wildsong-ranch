/**
 * GAME_DESIGN §21 install help: which phone this is and whether the game already runs from its icon.
 * The pure parts take the user agent as an argument so they can be tested.
 */
export type Platform = 'ios' | 'android' | 'other'

export function platformOf(userAgent: string, maxTouchPoints = 0): Platform {
  const ua = userAgent.toLowerCase()
  if (/iphone|ipad|ipod/.test(ua)) return 'ios'
  // iPadOS reports itself as a Mac; the touch points give it away.
  if (/macintosh/.test(ua) && maxTouchPoints > 1) return 'ios'
  if (/android/.test(ua)) return 'android'
  return 'other'
}

export function currentPlatform(): Platform {
  if (typeof navigator === 'undefined') return 'other'
  return platformOf(navigator.userAgent, navigator.maxTouchPoints ?? 0)
}

/** True when opened from the Home Screen icon (standalone), so the install card can stay away. */
export function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const nav = navigator as Navigator & { standalone?: boolean }
    if (nav.standalone === true) return true
    return window.matchMedia?.('(display-mode: standalone)').matches ?? false
  } catch {
    return false
  }
}

/** Chromium's install prompt, when the browser offered one. */
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

let deferredPrompt: BeforeInstallPromptEvent | null = null
const listeners = new Set<() => void>()

export function installPromptCapture(target: Window): void {
  target.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredPrompt = e as BeforeInstallPromptEvent
    listeners.forEach((fn) => fn())
  })
  target.addEventListener('appinstalled', () => {
    deferredPrompt = null
    listeners.forEach((fn) => fn())
  })
}

export function canPromptInstall(): boolean {
  return deferredPrompt !== null
}

export function onInstallPromptChange(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export async function promptInstall(): Promise<'accepted' | 'dismissed' | 'unavailable'> {
  const p = deferredPrompt
  if (!p) return 'unavailable'
  try {
    await p.prompt()
    const choice = await p.userChoice
    if (choice.outcome === 'accepted') deferredPrompt = null
    listeners.forEach((fn) => fn())
    return choice.outcome
  } catch {
    return 'unavailable'
  }
}
