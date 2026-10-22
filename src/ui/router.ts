import { signal } from '@preact/signals'
import { importCodeFromHash } from '../save/exportImport.ts'

/**
 * Hash-based screen state. The screen is app state (a signal) mirrored to `location.hash`,
 * so the browser back button works and GitHub Pages never has to rewrite a URL.
 * Lab sub-screens live under `#lab/...` and Back returns to `#lab`; an `#import=CODE` link
 * opens the Lab's Import screen with the code and then clears the code from the hash.
 */
export const SCREENS = ['title', 'credits', 'newGame', 'continue', 'lab', 'labCreate', 'labView', 'labEdit', 'labImport', 'labExport', 'settings'] as const
export type Screen = (typeof SCREENS)[number]

const SLUGS: Record<Screen, string> = {
  title: 'title',
  credits: 'credits',
  newGame: 'new-game',
  continue: 'continue',
  lab: 'lab',
  labCreate: 'lab/create',
  labView: 'lab/view',
  labEdit: 'lab/edit',
  labImport: 'lab/import',
  labExport: 'lab/export',
  settings: 'settings',
}

/** Where Back goes. */
const PARENT: Record<Screen, Screen | null> = {
  title: null,
  credits: 'title',
  newGame: 'title',
  continue: 'title',
  lab: 'title',
  labCreate: 'lab',
  labView: 'lab',
  labEdit: 'lab',
  labImport: 'lab',
  labExport: 'lab',
  settings: 'title',
}

/** The current screen. UI reads this; `navigate()` changes it. */
export const screen = signal<Screen>('title')

/** A share code that arrived in an `#import=` link and is waiting for the Import screen. */
export const pendingImport = signal<string | null>(null)

export interface Route {
  screen: Screen
  importCode: string | null
}

/** `#credits`, `#/credits`, `credits` and `#CREDITS` all mean the credits screen. Anything unknown is the title. */
export function parseRoute(hash: string): Route {
  const importCode = importCodeFromHash(hash)
  if (importCode) return { screen: 'labImport', importCode }
  const slug = hash.replace(/^#\/?/, '').trim().toLowerCase()
  for (const s of SCREENS) {
    if (SLUGS[s] === slug) return { screen: s, importCode: null }
  }
  return { screen: 'title', importCode: null }
}

export function parseHash(hash: string): Screen {
  return parseRoute(hash).screen
}

export function hashFor(target: Screen): string {
  return `#${SLUGS[target]}`
}

export function parentOf(target: Screen): Screen | null {
  return PARENT[target]
}

/** A minimal window-like host, so the router can be installed on a fake in tests. */
export interface RouterHost {
  location: { hash: string }
  addEventListener(type: 'hashchange', listener: () => void): void
  /** Optional: lets the router drop an import code from the URL without adding a history entry. */
  history?: { replaceState(data: unknown, unused: string, url?: string): void }
}

let host: RouterHost | null = null

function applyHash(target: RouterHost): void {
  const route = parseRoute(target.location.hash)
  if (route.importCode) {
    pendingImport.value = route.importCode
    screen.value = 'labImport'
    try {
      target.history?.replaceState(null, '', hashFor('labImport'))
    } catch {
      /* a host without history keeps the code in the URL; that's fine */
    }
    return
  }
  screen.value = route.screen
}

/** Reads the current hash and keeps the signal in sync with later hash changes. Call once at startup. */
export function installRouter(target: RouterHost): void {
  host = target
  applyHash(target)
  target.addEventListener('hashchange', () => applyHash(target))
}

/** Goes to a screen. With a host, it sets the hash (which then updates the signal); without one it sets the signal directly. */
export function navigate(target: Screen): void {
  if (host) {
    if (parseRoute(host.location.hash).screen === target && !parseRoute(host.location.hash).importCode) return
    host.location.hash = hashFor(target)
  } else {
    screen.value = target
  }
}

/** Back goes to the screen's parent: Lab sub-screens return to the Lab, everything else to the title. */
export function goBack(): void {
  navigate(PARENT[screen.value] ?? 'title')
}
