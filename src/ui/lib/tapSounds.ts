import { playSfx } from '../../audio/player.ts'

/**
 * SOUND_UPGRADE §10.2 the UI sounds: one delegated listener for every control, mapping what was tapped to a
 * soft wooden tick (buttons), a kalimba tick (chips and segmented controls), a lower tick (back and close),
 * two notes up or down (switches) and a paper flick (tabs). A control can opt out with `data-silent`, or
 * name its own sound with `data-sound`. The Button sounds setting silences the whole UI bus.
 */
export function uiSoundFor(button: HTMLElement): 'tap' | 'select' | 'back' | 'toggleOn' | 'toggleOff' | 'tab' | 'deny' | 'sheetOpen' | 'sheetClose' | null {
  const named = button.dataset.sound
  if (named === 'tap' || named === 'select' || named === 'back' || named === 'toggleOn' || named === 'toggleOff' || named === 'tab' || named === 'deny' || named === 'sheetOpen' || named === 'sheetClose') return named
  if (button.getAttribute('aria-disabled') === 'true') return 'deny'
  const role = button.getAttribute('role')
  if (role === 'switch') return button.getAttribute('aria-checked') === 'true' ? 'toggleOff' : 'toggleOn'
  if (role === 'tab') return 'tab'
  if (button.classList.contains('chip') || button.classList.contains('seg__btn')) return 'select'
  const label = `${button.getAttribute('aria-label') ?? ''} ${button.textContent ?? ''}`.trim()
  if (/^(‹|←|×|✕)/.test(label) || /^(back|close|cancel|done|got it)\b/i.test(label) || button.classList.contains('topbar__back') || button.classList.contains('btn--ghost')) return 'back'
  return 'tap'
}

export function installTapSounds(doc: Document): void {
  doc.addEventListener(
    'click',
    (e) => {
      const target = e.target as HTMLElement | null
      const button = target?.closest?.('button, [role="tab"], [role="switch"], .tcard, .expnode') as HTMLElement | null
      if (!button || (button as HTMLButtonElement).disabled || button.dataset.silent !== undefined) return
      const id = uiSoundFor(button)
      if (id) playSfx(id)
    },
    { passive: true },
  )
}
