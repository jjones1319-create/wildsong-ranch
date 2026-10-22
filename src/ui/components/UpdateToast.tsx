import { useEffect } from 'preact/hooks'
import { useRegisterSW } from 'virtual:pwa-register/preact'
import { UI_TEXT } from '../../data/text/ui.ts'
import { UI } from '../../data/tuning.ts'

/**
 * Registers the service worker and shows "Update ready: Restart" when a new build is waiting.
 * It never reloads on its own: the player taps Restart. `visible` keeps it off mid-battle later.
 */
export function UpdateToast({ visible }: { visible: boolean }) {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    offlineReady: [offlineReady, setOfflineReady],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      if (!registration) return
      const check = () => {
        if (document.visibilityState === 'visible') void registration.update()
      }
      document.addEventListener('visibilitychange', check)
      setInterval(check, UI.updateCheckIntervalMs)
    },
  })

  useEffect(() => {
    if (!offlineReady) return
    const timer = setTimeout(() => setOfflineReady(false), UI.offlineToastMs)
    return () => clearTimeout(timer)
  }, [offlineReady])

  if (!visible) return null

  if (needRefresh) {
    return (
      <div class="toast" role="status">
        <span class="toast__text">{UI_TEXT.toast.updateReady}</span>
        <button type="button" class="btn btn--small btn--primary" onClick={() => void updateServiceWorker()}>
          {UI_TEXT.toast.restart}
        </button>
        <button type="button" class="btn btn--small" onClick={() => setNeedRefresh(false)}>
          {UI_TEXT.toast.later}
        </button>
      </div>
    )
  }

  if (offlineReady) {
    return (
      <div class="toast" role="status">
        <span class="toast__text">{UI_TEXT.toast.offlineReady}</span>
      </div>
    )
  }

  return null
}
