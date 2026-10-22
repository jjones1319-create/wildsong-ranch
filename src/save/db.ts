import { createStore, del, get, keys, set, type UseStore } from 'idb-keyval'
import { SAVES } from '../data/tuning.ts'
import {
  emptyLibrary,
  validateLibrary,
  validateSave,
  validateSettings,
  type AppSettings,
  type Library,
  type SaveFile,
} from './schema.ts'

/**
 * GAME_DESIGN §20 storage. IndexedDB through idb-keyval, every key prefixed `wildsong/` because all
 * GitHub Pages sites of one account share an origin. Everything here is written against a tiny
 * store interface so the rules can be tested on an in-memory store, and nothing here ever throws:
 * a broken database reads as "nothing there" and a failed write returns false.
 */

export interface KeyValueStore {
  get(key: string): Promise<unknown>
  set(key: string, value: unknown): Promise<void>
  del(key: string): Promise<void>
  keys(): Promise<string[]>
}

/** The localStorage shape, for the JSON mirror (§20 fallback). */
export interface TextStore {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export const KEY_PREFIX = 'wildsong/'

export const KEYS = {
  slot: (n: number) => `${KEY_PREFIX}slot/${n}`,
  autosaveHead: `${KEY_PREFIX}autosave/head`,
  autosave: (n: number) => `${KEY_PREFIX}autosave/${n}`,
  library: `${KEY_PREFIX}library`,
  settings: `${KEY_PREFIX}settings`,
  mirrorSave: `${KEY_PREFIX}mirror/latest`,
  mirrorLibrary: `${KEY_PREFIX}mirror/library`,
} as const

/** The real thing: one IndexedDB database of our own, so other sites on the origin can't collide with it. */
export function idbStore(): KeyValueStore {
  let store: UseStore | null = null
  const use = () => (store ??= createStore('wildsong-ranch', 'kv'))
  return {
    get: (key) => get(key, use()),
    set: (key, value) => set(key, value, use()),
    del: (key) => del(key, use()),
    keys: async () => (await keys(use())).filter((k): k is string => typeof k === 'string'),
  }
}

/** For tests and for pages where IndexedDB is unavailable. */
export function memoryStore(): KeyValueStore {
  const map = new Map<string, unknown>()
  return {
    get: async (key) => structuredClone(map.get(key)),
    set: async (key, value) => void map.set(key, structuredClone(value)),
    del: async (key) => void map.delete(key),
    keys: async () => [...map.keys()],
  }
}

export function memoryTextStore(): TextStore {
  const map = new Map<string, string>()
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => void map.set(key, value),
    removeItem: (key) => void map.delete(key),
  }
}

async function safeGet(store: KeyValueStore, key: string): Promise<unknown> {
  try {
    return await store.get(key)
  } catch {
    return undefined
  }
}

async function safeSet(store: KeyValueStore, key: string, value: unknown): Promise<boolean> {
  try {
    await store.set(key, value)
    return true
  } catch {
    return false
  }
}

async function safeDel(store: KeyValueStore, key: string): Promise<boolean> {
  try {
    await store.del(key)
    return true
  } catch {
    return false
  }
}

/* ---------- Slots (§20: 3 manual slots) ---------- */

export function isSlot(n: number): boolean {
  return Number.isInteger(n) && n >= 1 && n <= SAVES.slots
}

export async function readSlot(store: KeyValueStore, n: number): Promise<SaveFile | null> {
  if (!isSlot(n)) return null
  const r = validateSave(await safeGet(store, KEYS.slot(n)))
  return r.ok ? r.save : null
}

export function writeSlot(store: KeyValueStore, n: number, save: SaveFile): Promise<boolean> {
  if (!isSlot(n)) return Promise.resolve(false)
  return safeSet(store, KEYS.slot(n), save)
}

export function clearSlot(store: KeyValueStore, n: number): Promise<boolean> {
  if (!isSlot(n)) return Promise.resolve(false)
  return safeDel(store, KEYS.slot(n))
}

export interface SlotSummary {
  slot: number
  save: SaveFile | null
}

export async function listSlots(store: KeyValueStore): Promise<SlotSummary[]> {
  const out: SlotSummary[] = []
  for (let n = 1; n <= SAVES.slots; n++) out.push({ slot: n, save: await readSlot(store, n) })
  return out
}

/* ---------- Autosave ring (§20: the latest plus 3 backups) ---------- */

const RING = SAVES.autosaveBackups + 1

function ringIndex(raw: unknown): number {
  return typeof raw === 'number' && Number.isInteger(raw) && raw >= 0 && raw < RING ? raw : -1
}

export async function writeAutosave(store: KeyValueStore, save: SaveFile): Promise<boolean> {
  const head = ringIndex(await safeGet(store, KEYS.autosaveHead))
  const next = (head + 1) % RING
  if (!(await safeSet(store, KEYS.autosave(next), save))) return false
  return safeSet(store, KEYS.autosaveHead, next)
}

/** The newest autosave that still validates; older backups are tried in turn. */
export async function readLatestAutosave(store: KeyValueStore): Promise<SaveFile | null> {
  const head = ringIndex(await safeGet(store, KEYS.autosaveHead))
  if (head < 0) return null
  for (let back = 0; back < RING; back++) {
    const r = validateSave(await safeGet(store, KEYS.autosave((head - back + RING) % RING)))
    if (r.ok) return r.save
  }
  return null
}

export async function clearAutosaves(store: KeyValueStore): Promise<void> {
  for (let i = 0; i < RING; i++) await safeDel(store, KEYS.autosave(i))
  await safeDel(store, KEYS.autosaveHead)
}

/* ---------- Library and settings ---------- */

export async function readLibrary(store: KeyValueStore): Promise<Library | null> {
  const r = validateLibrary(await safeGet(store, KEYS.library))
  return r.ok ? r.library : null
}

export function writeLibrary(store: KeyValueStore, library: Library): Promise<boolean> {
  return safeSet(store, KEYS.library, library)
}

export async function readSettings(store: KeyValueStore): Promise<AppSettings> {
  return validateSettings(await safeGet(store, KEYS.settings))
}

export function writeSettings(store: KeyValueStore, settings: AppSettings): Promise<boolean> {
  return safeSet(store, KEYS.settings, settings)
}

/* ---------- localStorage mirror (§20 fallback) ---------- */

export function writeMirror(text: TextStore, key: string, value: unknown): boolean {
  try {
    text.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export function readMirror(text: TextStore, key: string): unknown {
  try {
    const raw = text.getItem(key)
    return raw ? (JSON.parse(raw) as unknown) : undefined
  } catch {
    return undefined
  }
}

export type LoadSource = 'db' | 'mirror' | 'none'

/** The Library from IndexedDB, or from the mirror if the database is empty or broken, or an empty one. */
export async function loadLibrary(store: KeyValueStore, text: TextStore): Promise<{ library: Library; source: LoadSource }> {
  const fromDb = await readLibrary(store)
  if (fromDb) return { library: fromDb, source: 'db' }
  const fromMirror = validateLibrary(readMirror(text, KEYS.mirrorLibrary))
  if (fromMirror.ok) return { library: fromMirror.library, source: 'mirror' }
  return { library: emptyLibrary(), source: 'none' }
}

/** Writes the Library to the database and the mirror; true when at least one of them took it. */
export async function persistLibrary(store: KeyValueStore, text: TextStore, library: Library): Promise<boolean> {
  const db = await writeLibrary(store, library)
  const mirror = writeMirror(text, KEYS.mirrorLibrary, library)
  return db || mirror
}

/** The most recent game: the newest valid autosave, else the most recently written slot, else the mirror. */
export async function loadLatestSave(store: KeyValueStore, text: TextStore): Promise<{ save: SaveFile | null; source: LoadSource }> {
  const auto = await readLatestAutosave(store)
  if (auto) return { save: auto, source: 'db' }
  const slots = (await listSlots(store)).map((s) => s.save).filter((s): s is SaveFile => s !== null)
  slots.sort((a, b) => b.meta.savedAt - a.meta.savedAt)
  if (slots[0]) return { save: slots[0], source: 'db' }
  const fromMirror = validateSave(readMirror(text, KEYS.mirrorSave))
  if (fromMirror.ok) return { save: fromMirror.save, source: 'mirror' }
  return { save: null, source: 'none' }
}

/** Autosave to the ring and the mirror; true when at least one of them took it. */
export async function persistAutosave(store: KeyValueStore, text: TextStore, save: SaveFile): Promise<boolean> {
  const db = await writeAutosave(store, save)
  const mirror = writeMirror(text, KEYS.mirrorSave, save)
  return db || mirror
}

/** Manual save to a slot and the mirror; true when at least one of them took it. */
export async function persistSlot(store: KeyValueStore, text: TextStore, n: number, save: SaveFile): Promise<boolean> {
  const db = await writeSlot(store, n, save)
  const mirror = writeMirror(text, KEYS.mirrorSave, save)
  return db || mirror
}
