import { signal } from '@preact/signals'
import { importCodeFromHash } from '../save/exportImport.ts'

/**
 * Hash-based screen state. The screen is app state (a signal) mirrored to `location.hash`,
 * so the browser back button works and GitHub Pages never has to rewrite a URL.
 * Lab sub-screens live under `#lab/...` and Back returns to `#lab`; ranch sub-screens live under
 * `#ranch/...`; an `#import=CODE` link opens the Lab's Import screen with the code and then clears it.
 */
export const SCREENS = [
  'title',
  'credits',
  'newGame',
  'ranch',
  'ranchCard',
  'bag',
  'songbook',
  'town',
  'shop',
  'library',
  'pell',
  'shrine',
  'market',
  'farewell',
  'lab',
  'labCreate',
  'labView',
  'labEdit',
  'labImport',
  'labExport',
  'labVersus',
  'labBattleLab',
  'labEffects',
  'labSound',
  'labModels',
  'battle',
  'tournament',
  'tournamentPlay',
  'tournamentResults',
  'guild',
  'mail',
  'journey',
  'creditsRoll',
  'settings',
  'expedition',
  'journal',
  'oddJobs',
  'upgrades',
  'calendar',
] as const
export type Screen = (typeof SCREENS)[number]

const SLUGS: Record<Screen, string> = {
  title: 'title',
  credits: 'credits',
  newGame: 'new-game',
  ranch: 'ranch',
  ranchCard: 'ranch/card',
  bag: 'ranch/bag',
  songbook: 'ranch/songbook',
  town: 'town',
  shop: 'town/shop',
  library: 'town/library',
  pell: 'town/pell',
  shrine: 'town/shrine',
  market: 'town/market',
  farewell: 'farewell',
  lab: 'lab',
  labCreate: 'lab/create',
  labView: 'lab/view',
  labEdit: 'lab/edit',
  labImport: 'lab/import',
  labExport: 'lab/export',
  labVersus: 'lab/versus',
  labBattleLab: 'lab/battle-lab',
  labEffects: 'lab/effects',
  labSound: 'lab/sound',
  labModels: 'lab/models',
  battle: 'battle',
  tournament: 'ranch/cups',
  tournamentPlay: 'ranch/cup',
  tournamentResults: 'ranch/cup/results',
  guild: 'town/guild',
  mail: 'town/mail',
  journey: 'ranch/journey',
  creditsRoll: 'credits-roll',
  settings: 'settings',
  expedition: 'ranch/expedition',
  journal: 'town/journal',
  oddJobs: 'town/jobs',
  upgrades: 'town/upgrades',
  calendar: 'calendar',
}

/** Where Back goes. */
const PARENT: Record<Screen, Screen | null> = {
  title: null,
  credits: 'title',
  newGame: 'title',
  ranch: 'title',
  ranchCard: 'ranch',
  bag: 'ranch',
  songbook: 'ranch',
  town: 'ranch',
  shop: 'town',
  library: 'town',
  pell: 'town',
  shrine: 'town',
  market: 'town',
  farewell: 'title',
  lab: 'title',
  labCreate: 'lab',
  labView: 'lab',
  labEdit: 'lab',
  labImport: 'lab',
  labExport: 'lab',
  labVersus: 'lab',
  labBattleLab: 'lab',
  labEffects: 'lab',
  labSound: 'lab',
  labModels: 'lab',
  battle: 'labVersus',
  tournament: 'ranch',
  tournamentPlay: 'ranch',
  tournamentResults: 'ranch',
  guild: 'town',
  mail: 'town',
  journey: 'ranch',
  creditsRoll: 'ranch',
  settings: 'title',
  expedition: 'ranch',
  journal: 'town',
  oddJobs: 'town',
  upgrades: 'town',
  calendar: 'ranch',
}

/** The current screen. UI reads this; `navigate()` changes it. */
export const screen = signal<Screen>('title')

/** A share code that arrived in an `#import=` link and is waiting for the Import screen. */
export const pendingImport = signal<string | null>(null)

/** Where a screen opened with `navigateFrom` should return to (the ranch card for the editor, Town for the Lab…). */
export const returnTo = signal<{ screen: Screen; back: Screen } | null>(null)

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

export function isRanchScreen(s: Screen): boolean {
  return (
    s === 'ranch' ||
    s === 'ranchCard' ||
    s === 'bag' ||
    s === 'songbook' ||
    s === 'town' ||
    s === 'shop' ||
    s === 'library' ||
    s === 'pell' ||
    s === 'shrine' ||
    s === 'market' ||
    s === 'farewell' ||
    s === 'expedition' ||
    s === 'journal' ||
    s === 'oddJobs' ||
    s === 'upgrades' ||
    s === 'calendar'
  )
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

/** Back goes to the screen's parent, or to where a screen was opened from (the ranch, for Settings and the editor). */
export function goBack(): void {
  const r = returnTo.value
  if (r && r.screen === screen.value) {
    returnTo.value = null
    navigate(r.back)
    return
  }
  navigate(PARENT[screen.value] ?? 'title')
}

/** Opens a screen and remembers where its Back should go. Sub-screens of the target still climb to their own parent. */
export function navigateFrom(from: Screen, target: Screen): void {
  returnTo.value = { screen: target, back: from }
  navigate(target)
}

/** The screen Back would go to from `target` right now. */
export function backTargetOf(target: Screen): Screen {
  const r = returnTo.value
  return r && r.screen === target ? r.back : (PARENT[target] ?? 'title')
}
