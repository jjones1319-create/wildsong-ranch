/**
 * docs/BATTLE_3D.md §5: sideways battles (the owner, Nov 2: "sideways, upright still works"). The installed app stays
 * upright everywhere else (the manifest), so a battle asks to turn: where the browser can (Android: the installed
 * app, or a tab in full screen) it turns the screen itself; elsewhere (iPhone) the player turns the phone.
 */

type Lockable = ScreenOrientation & { lock?: (o: 'landscape' | 'portrait') => Promise<void>; unlock?: () => void }

let enteredFullscreen = false

/** Turn the screen sideways; false when this browser can't (the player is asked to turn the phone instead). */
export async function goSideways(): Promise<boolean> {
  const o = (typeof screen !== 'undefined' ? screen.orientation : undefined) as Lockable | undefined
  if (!o?.lock) return false
  try {
    const installed = matchMedia('(display-mode: standalone)').matches || matchMedia('(display-mode: fullscreen)').matches
    if (!installed && !document.fullscreenElement && document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' })
      enteredFullscreen = true
    }
    await o.lock('landscape')
    return true
  } catch {
    return false
  }
}

/** Back to how the rest of the game is held. */
export function leaveSideways(): void {
  try {
    ;(screen.orientation as Lockable | undefined)?.unlock?.()
  } catch {
    /* nothing to undo */
  }
  if (enteredFullscreen && document.fullscreenElement) void document.exitFullscreen().catch(() => undefined)
  enteredFullscreen = false
}

export function isPortrait(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(orientation: portrait)').matches
}
