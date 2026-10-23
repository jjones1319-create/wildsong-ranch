import { playSfx } from '../../audio/player.ts'

/** §23 the UI tap: one delegated listener for every button, instead of a call in each component. */
export function installTapSounds(doc: Document): void {
  doc.addEventListener(
    'click',
    (e) => {
      const target = e.target as HTMLElement | null
      const button = target?.closest?.('button, [role="tab"], .tcard, .expnode') as HTMLButtonElement | null
      if (!button || button.disabled || button.dataset.silent !== undefined) return
      playSfx(button.classList.contains('chip') || button.classList.contains('seg__btn') ? 'select' : 'tap')
    },
    { passive: true },
  )
}
