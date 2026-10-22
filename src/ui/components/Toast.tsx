import { toast } from '../store/appStore.ts'

/** The app's own short message (saved, copied, deleted…), separate from the update toast. */
export function AppToast() {
  const t = toast.value
  if (!t) return null
  return (
    <div class="toast toast--app" role="status" key={t.id}>
      <span class="toast__text">{t.text}</span>
    </div>
  )
}
