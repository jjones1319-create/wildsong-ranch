import { signal } from '@preact/signals'
import { registerSW } from 'virtual:pwa-register'
import { UI } from '../../data/tuning.ts'

/**
 * GAME_DESIGN §20 updates: the service worker is registered once here; the toast and Settings read these
 * signals. Nothing reloads on its own: the player taps Restart (and never mid-battle, because the toast only
 * shows on the title and the quiet ranch).
 */

export const needRefresh = signal(false)
export const offlineReady = signal(false)
/** The last manual check: null until one ran. */
export const lastCheck = signal<'checking' | 'upToDate' | 'updateFound' | 'failed' | null>(null)

let update: ((reload?: boolean) => Promise<void>) | null = null
let registration: ServiceWorkerRegistration | null = null
let installed = false

export function installUpdates(doc: Document): void {
  if (installed || typeof window === 'undefined') return
  installed = true
  try {
    update = registerSW({
      immediate: true,
      onNeedRefresh() {
        needRefresh.value = true
        if (lastCheck.value === 'checking') lastCheck.value = 'updateFound'
      },
      onOfflineReady() {
        offlineReady.value = true
        setTimeout(() => {
          offlineReady.value = false
        }, UI.offlineToastMs)
      },
      onRegisteredSW(_url, reg) {
        registration = reg ?? null
        if (!reg) return
        const check = () => {
          if (doc.visibilityState === 'visible') void reg.update()
        }
        doc.addEventListener('visibilitychange', check)
        setInterval(check, UI.updateCheckIntervalMs)
      },
      onRegisterError() {
        /* no service worker (dev, or an old browser): the game still plays */
      },
    })
  } catch {
    update = null
  }
}

/** Restart with the new build. */
export async function applyUpdate(): Promise<void> {
  if (update) await update(true)
}

export function dismissUpdate(): void {
  needRefresh.value = false
}

/** Settings → Check for updates. Resolves to what it found. */
export async function checkForUpdate(): Promise<void> {
  if (needRefresh.value) {
    lastCheck.value = 'updateFound'
    return
  }
  if (!registration) {
    lastCheck.value = 'failed'
    return
  }
  lastCheck.value = 'checking'
  try {
    await registration.update()
    // The worker reports a waiting build through onNeedRefresh within a moment; otherwise we are current.
    setTimeout(() => {
      if (lastCheck.value === 'checking') lastCheck.value = needRefresh.value ? 'updateFound' : 'upToDate'
    }, 2500)
  } catch {
    lastCheck.value = 'failed'
  }
}
