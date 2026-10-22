import { signal } from '@preact/signals'
import { UI_TEXT } from '../../data/text/ui.ts'
import { UI } from '../../data/tuning.ts'
import { idbStore, loadLibrary, memoryTextStore, persistLibrary, readSettings, writeSettings, type KeyValueStore, type LoadSource, type TextStore } from '../../save/db.ts'
import { defaultSettings, emptyLibrary, type AppSettings, type Library, type LibraryEntry } from '../../save/schema.ts'

/**
 * App-wide state: settings, the global Library (§19, §20) and the toast. The UI reads these signals
 * and calls the functions below; nothing else writes to storage.
 */

export const ready = signal(false)
export const settings = signal<AppSettings>(defaultSettings())
export const library = signal<Library>(emptyLibrary())
export const librarySource = signal<LoadSource>('none')
/** `navigator.storage.persisted()`: true, false, or null when the browser can't say. */
export const persisted = signal<boolean | null>(null)
export const toast = signal<{ id: number; text: string } | null>(null)

let store: KeyValueStore | null = null
let text: TextStore | null = null

function kv(): KeyValueStore {
  return (store ??= idbStore())
}

function ls(): TextStore {
  if (text) return text
  try {
    text = window.localStorage
  } catch {
    text = memoryTextStore()
  }
  return text
}

/** For tests: swap the stores for in-memory ones. */
export function useStores(k: KeyValueStore, t: TextStore): void {
  store = k
  text = t
}

export async function refreshPersisted(): Promise<void> {
  try {
    persisted.value = typeof navigator !== 'undefined' && navigator.storage?.persisted ? await navigator.storage.persisted() : null
  } catch {
    persisted.value = null
  }
}

export async function bootApp(): Promise<void> {
  settings.value = await readSettings(kv())
  const loaded = await loadLibrary(kv(), ls())
  library.value = loaded.library
  librarySource.value = loaded.source
  await refreshPersisted()
  ready.value = true
}

let askedForPersistence = false

/** §20: ask the browser to protect our storage after the first save. */
async function askPersistence(): Promise<void> {
  if (askedForPersistence) return
  askedForPersistence = true
  try {
    if (typeof navigator !== 'undefined' && navigator.storage?.persist) await navigator.storage.persist()
  } catch {
    /* some browsers refuse; the status line in Settings says so */
  }
  await refreshPersisted()
}

export async function commitLibrary(next: Library): Promise<boolean> {
  library.value = next
  const ok = await persistLibrary(kv(), ls(), next)
  if (!ok) showToast(UI_TEXT.errors.saveFailed)
  void askPersistence()
  return ok
}

export async function updateSettings(patch: Partial<AppSettings>): Promise<void> {
  settings.value = { ...settings.value, ...patch }
  await writeSettings(kv(), settings.value)
}

let toastTimer: ReturnType<typeof setTimeout> | null = null

export function showToast(message: string): void {
  toast.value = { id: Date.now(), text: message }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = null
  }, UI.toastMs)
}

/* ---------- Library helpers ---------- */

export function findEntry(id: string): LibraryEntry | undefined {
  return library.value.entries.find((e) => e.monster.id === id)
}

/** Adds a new entry at the front, or replaces the one with the same id in place. */
export function upsertEntry(entry: LibraryEntry): Promise<boolean> {
  const entries = library.value.entries
  const i = entries.findIndex((e) => e.monster.id === entry.monster.id)
  const next = i >= 0 ? entries.map((e, j) => (j === i ? entry : e)) : [entry, ...entries]
  return commitLibrary({ ...library.value, entries: next })
}

export function removeEntry(id: string): Promise<boolean> {
  return commitLibrary({ ...library.value, entries: library.value.entries.filter((e) => e.monster.id !== id) })
}

export function addEntries(entries: LibraryEntry[]): Promise<boolean> {
  return commitLibrary({ ...library.value, entries: [...entries, ...library.value.entries] })
}
