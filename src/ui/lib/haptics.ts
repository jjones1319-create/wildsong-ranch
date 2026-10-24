import { settings } from '../store/appStore.ts'

/**
 * A short haptic tick on Android (§12.11, §24). iOS has no `navigator.vibrate`, and browsers only allow
 * vibration after a real tap, so the first pointer-down is remembered and nothing is tried before it.
 */
let userTapped = false
if (typeof document !== 'undefined') {
  document.addEventListener(
    'pointerdown',
    () => {
      userTapped = true
    },
    { once: true, passive: true },
  )
}

export function hapticTick(ms = 12): void {
  try {
    if (userTapped && settings.value.haptics && typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') navigator.vibrate(ms)
  } catch {
    /* no haptics */
  }
}
