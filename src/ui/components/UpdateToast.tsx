import { UI_TEXT } from '../../data/text/ui.ts'
import { applyUpdate, dismissUpdate, needRefresh, offlineReady } from '../store/updateStore.ts'

/**
 * "Update ready: Restart" when a new build is waiting (§20). It never reloads on its own: the player taps
 * Restart. `visible` keeps it off every screen but the title and the quiet ranch, so never mid-battle.
 */
export function UpdateToast({ visible }: { visible: boolean }) {
  if (!visible) return null

  if (needRefresh.value) {
    return (
      <div class="toast" role="status">
        <span class="toast__text">{UI_TEXT.toast.updateReady}</span>
        <button type="button" class="btn btn--small btn--primary" onClick={() => void applyUpdate()}>
          {UI_TEXT.toast.restart}
        </button>
        <button type="button" class="btn btn--small" onClick={dismissUpdate}>
          {UI_TEXT.toast.later}
        </button>
      </div>
    )
  }

  if (offlineReady.value) {
    return (
      <div class="toast" role="status">
        <span class="toast__text">{UI_TEXT.toast.offlineReady}</span>
      </div>
    )
  }

  return null
}
