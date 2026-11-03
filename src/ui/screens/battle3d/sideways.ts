/**
 * docs/BATTLE_3D.md §5: sideways battles (the owner, Nov 2: "sideways, upright still works"). The installed app stays
 * upright everywhere else (the manifest), so a battle asks to turn. Browsers only let a page turn the screen while it
 * is full screen (the owner's phone, v1.17–v1.18: the installed app didn't rotate because it skipped full screen), and
 * full screen only straight after a tap: so "Play sideways" always enters full screen first, then turns. Where turning
 * isn't possible at all (iPhone), the player is asked to turn the phone.
 */

type Lockable = ScreenOrientation & { lock?: (o: 'landscape' | 'portrait') => Promise<void>; unlock?: () => void }

let enteredFullscreen = false

/** Call straight from a tap. Full screen, then sideways; false when this browser can't (turn the phone instead). */
export async function goSideways(): Promise<boolean> {
  const o = (typeof screen !== 'undefined' ? screen.orientation : undefined) as Lockable | undefined
  if (!o?.lock) return false
  try {
    if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' })
      enteredFullscreen = true
    }
    await o.lock('landscape')
    return true
  } catch {
    leaveSideways()
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
