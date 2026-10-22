import { signal } from '@preact/signals'

/**
 * Hash-based screen state. The screen is app state (a signal) mirrored to `location.hash`,
 * so the browser back button works and GitHub Pages never has to rewrite a URL.
 */
export const SCREENS = ['title', 'credits', 'newGame', 'continue', 'lab', 'settings'] as const
export type Screen = (typeof SCREENS)[number]

const SLUGS: Record<Screen, string> = {
  title: 'title',
  credits: 'credits',
  newGame: 'new-game',
  continue: 'continue',
  lab: 'lab',
  settings: 'settings',
}

/** The current screen. UI reads this; `navigate()` changes it. */
export const screen = signal<Screen>('title')

/** `#credits`, `#/credits`, `credits` and `#CREDITS` all mean the credits screen. Anything unknown is the title. */
export function parseHash(hash: string): Screen {
  const slug = hash.replace(/^#\/?/, '').trim().toLowerCase()
  for (const s of SCREENS) {
    if (SLUGS[s] === slug) return s
  }
  return 'title'
}

export function hashFor(target: Screen): string {
  return `#${SLUGS[target]}`
}

/** A minimal window-like host, so the router can be installed on a fake in tests. */
export interface RouterHost {
  location: { hash: string }
  addEventListener(type: 'hashchange', listener: () => void): void
}

let host: RouterHost | null = null

/** Reads the current hash and keeps the signal in sync with later hash changes. Call once at startup. */
export function installRouter(target: RouterHost): void {
  host = target
  screen.value = parseHash(target.location.hash)
  target.addEventListener('hashchange', () => {
    screen.value = parseHash(target.location.hash)
  })
}

/** Goes to a screen. With a host, it sets the hash (which then updates the signal); without one it sets the signal directly. */
export function navigate(target: Screen): void {
  if (host) {
    if (parseHash(host.location.hash) === target) return
    host.location.hash = hashFor(target)
  } else {
    screen.value = target
  }
}

/** Every M0 screen is one step from the title, so Back simply returns there. */
export function goBack(): void {
  navigate('title')
}
