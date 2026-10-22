import { describe, expect, it } from 'vitest'
import { createGameState } from '../core/state.ts'
import { makeMonster } from '../core/test-helpers.ts'
import { SAVES } from '../data/tuning.ts'
import {
  clearSlot,
  KEYS,
  listSlots,
  loadLatestSave,
  loadLibrary,
  memoryStore,
  memoryTextStore,
  persistAutosave,
  persistLibrary,
  persistSlot,
  readLatestAutosave,
  readSettings,
  readSlot,
  writeAutosave,
  writeSettings,
  writeSlot,
  type KeyValueStore,
} from './db.ts'
import { defaultSettings, emptyLibrary, makeSave, type Library } from './schema.ts'

const saveNamed = (name: string, savedAt = 0) => makeSave(createGameState({ monster: makeMonster(), breederName: name }), 1, { savedAt })

function brokenStore(): KeyValueStore {
  return {
    get: async () => {
      throw new Error('IndexedDB is unavailable')
    },
    set: async () => {
      throw new Error('IndexedDB is unavailable')
    },
    del: async () => {
      throw new Error('IndexedDB is unavailable')
    },
    keys: async () => {
      throw new Error('IndexedDB is unavailable')
    },
  }
}

describe('save slots (§20)', () => {
  it('writes, reads, lists and clears the three slots', async () => {
    const store = memoryStore()
    expect(await writeSlot(store, 2, saveNamed('Two'))).toBe(true)
    expect((await readSlot(store, 2))?.game.breeder.name).toBe('Two')
    expect(await readSlot(store, 1)).toBeNull()
    const slots = await listSlots(store)
    expect(slots.map((s) => s.slot)).toEqual([1, 2, 3])
    expect(slots.map((s) => s.save?.game.breeder.name ?? null)).toEqual([null, 'Two', null])
    expect(await clearSlot(store, 2)).toBe(true)
    expect(await readSlot(store, 2)).toBeNull()
    expect(await writeSlot(store, 0, saveNamed('Zero'))).toBe(false)
    expect(await writeSlot(store, SAVES.slots + 1, saveNamed('Four'))).toBe(false)
  })

  it('reads a corrupt slot as empty instead of throwing', async () => {
    const store = memoryStore()
    await store.set(KEYS.slot(1), { kind: 'save', schemaVersion: 2, game: 'nonsense' })
    await store.set(KEYS.slot(2), 'not even an object')
    expect(await readSlot(store, 1)).toBeNull()
    expect(await readSlot(store, 2)).toBeNull()
  })
})

describe('autosave ring (§20)', () => {
  it('keeps the latest plus three backups and reads the newest', async () => {
    const store = memoryStore()
    expect(await readLatestAutosave(store)).toBeNull()
    for (let i = 1; i <= 6; i++) expect(await writeAutosave(store, saveNamed(`Week ${i}`))).toBe(true)
    expect((await readLatestAutosave(store))?.game.breeder.name).toBe('Week 6')
    const kept = (await store.keys()).filter((k) => k.startsWith(KEYS.autosave(0).slice(0, -1)) && k !== KEYS.autosaveHead)
    expect(kept).toHaveLength(SAVES.autosaveBackups + 1)
  })

  it('falls back to an older backup when the newest is corrupt', async () => {
    const store = memoryStore()
    await writeAutosave(store, saveNamed('Good'))
    await writeAutosave(store, saveNamed('Also good'))
    const head = (await store.get(KEYS.autosaveHead)) as number
    await store.set(KEYS.autosave(head), { garbage: true })
    expect((await readLatestAutosave(store))?.game.breeder.name).toBe('Good')
    await store.set(KEYS.autosaveHead, 'weird')
    expect(await readLatestAutosave(store)).toBeNull()
  })
})

describe('library, settings and the mirror (§20)', () => {
  it('stores the library in the database and the mirror, and loads from either', async () => {
    const store = memoryStore()
    const text = memoryTextStore()
    const lib: Library = { ...emptyLibrary(), entries: [{ monster: makeMonster({ id: 'a' }), history: [], createdAt: 1, updatedAt: 2 }] }
    expect(await persistLibrary(store, text, lib)).toBe(true)
    expect((await loadLibrary(store, text)).source).toBe('db')
    await store.set(KEYS.library, { kind: 'library', schemaVersion: 2, entries: 'broken' })
    const fromMirror = await loadLibrary(store, text)
    expect(fromMirror.source).toBe('mirror')
    expect(fromMirror.library.entries[0]!.monster.id).toBe('a')
    expect((await loadLibrary(memoryStore(), memoryTextStore())).source).toBe('none')
  })

  it('survives a broken database and a full localStorage', async () => {
    const text = memoryTextStore()
    const lib = emptyLibrary()
    expect(await persistLibrary(brokenStore(), text, lib)).toBe(true)
    expect((await loadLibrary(brokenStore(), text)).source).toBe('mirror')
    const fullText = { ...memoryTextStore(), setItem: () => {
      throw new Error('QuotaExceededError')
    } }
    expect(await persistLibrary(brokenStore(), fullText, lib)).toBe(false)
    expect(await persistAutosave(brokenStore(), fullText, saveNamed('x'))).toBe(false)
    expect((await loadLatestSave(brokenStore(), fullText)).save).toBeNull()
  })

  it('loads the most recent game: autosave first, then the newest slot, then the mirror', async () => {
    const store = memoryStore()
    const text = memoryTextStore()
    expect((await loadLatestSave(store, text)).source).toBe('none')
    await persistSlot(store, text, 1, saveNamed('Old slot', 100))
    await persistSlot(store, text, 3, saveNamed('New slot', 200))
    expect((await loadLatestSave(store, text)).save?.game.breeder.name).toBe('New slot')
    await persistAutosave(store, text, saveNamed('Auto', 300))
    expect((await loadLatestSave(store, text)).save?.game.breeder.name).toBe('Auto')
    const mirrorOnly = await loadLatestSave(memoryStore(), text)
    expect(mirrorOnly.source).toBe('mirror')
    expect(mirrorOnly.save?.game.breeder.name).toBe('Auto')
  })

  it('settings default when missing or broken', async () => {
    const store = memoryStore()
    expect(await readSettings(store)).toEqual(defaultSettings())
    await writeSettings(store, { ...defaultSettings(), showEditedBadge: true })
    expect((await readSettings(store)).showEditedBadge).toBe(true)
    await store.set(KEYS.settings, 42)
    expect(await readSettings(store)).toEqual(defaultSettings())
  })
})
