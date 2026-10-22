import { describe, expect, it } from 'vitest'
import { createGameState } from '../core/state.ts'
import { makeMonster } from '../core/test-helpers.ts'
import { LAB } from '../data/tuning.ts'
import { migrate, SAVE_VERSION } from './migrate.ts'
import { emptyLibrary, makeMonsterFile, makeSave, validateAny, validateLibrary, validateMonsterFile, validateSettings, type Library } from './schema.ts'

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x)) as T

describe('schema version 2 (M2)', () => {
  it('migrates a version-1 save by adding meta, and leaves monster files alone', () => {
    const v1 = { schemaVersion: 1, kind: 'save', game: createGameState({ monster: null }), rng: 3 }
    const up = migrate(clone(v1)) as { schemaVersion: number; meta: unknown }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.meta).toEqual({ savedAt: 0, appVersion: '' })
    const v1Monster = { schemaVersion: 1, kind: 'monster', monster: makeMonster() }
    const upMonster = migrate(clone(v1Monster)) as Record<string, unknown>
    expect(upMonster.schemaVersion).toBe(SAVE_VERSION)
    expect(upMonster.meta).toBeUndefined()
    const r = validateAny(clone(v1))
    expect(r.ok && r.kind === 'save' && r.save.meta.savedAt === 0).toBe(true)
  })

  it('keeps meta on a round trip and clamps it', () => {
    const save = makeSave(createGameState({ monster: null }), 1, { savedAt: 1_700_000_000_000, appVersion: '0.3.0' })
    const r = validateAny(clone(save))
    expect(r.ok && r.kind === 'save' && r.save.meta).toEqual({ savedAt: 1_700_000_000_000, appVersion: '0.3.0' })
    const weird = clone(save) as unknown as { meta: unknown }
    weird.meta = { savedAt: -5, appVersion: 12 }
    const r2 = validateAny(weird)
    expect(r2.ok && r2.kind === 'save' && r2.save.meta).toEqual({ savedAt: 0, appVersion: '' })
  })

  it('refuses a file from a newer version with a clear message', () => {
    const r = validateAny({ schemaVersion: SAVE_VERSION + 1, kind: 'save' })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.error).toMatch(/newer version/i)
  })
})

describe('monster files', () => {
  it('validates a monster file, drops broken history entries and caps history', () => {
    const m = makeMonster({ id: 'm1' })
    const history = Array.from({ length: LAB.historyLimit + 4 }, (_, i) => {
      const h = makeMonster({ id: 'm1' })
      h.name = `v${i}`
      return { monster: h, savedAt: i }
    })
    const raw = clone(makeMonsterFile(m, history)) as unknown as { history: unknown[] }
    raw.history.splice(2, 0, 'garbage', { monster: { id: 'x' }, savedAt: 1 })
    const r = validateMonsterFile(raw)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.file.history).toHaveLength(LAB.historyLimit)
    expect(r.file.history.at(-1)!.monster.name).toBe(`v${LAB.historyLimit + 3}`)
  })

  it('accepts a bare monster and rejects nonsense', () => {
    const bare = validateMonsterFile(clone(makeMonster()))
    expect(bare.ok && bare.file.kind === 'monster').toBe(true)
    for (const bad of [null, 1, 'x', [], {}, { kind: 'monster' }, { kind: 'monster', schemaVersion: SAVE_VERSION, monster: 5 }]) {
      expect(validateMonsterFile(bad).ok).toBe(false)
    }
  })
})

describe('library files', () => {
  it('drops broken entries and duplicate ids, keeps the rest', () => {
    const lib: Library = {
      ...emptyLibrary(),
      entries: [
        { monster: makeMonster({ id: 'a' }), history: [], createdAt: 1, updatedAt: 1 },
        { monster: makeMonster({ id: 'a' }), history: [], createdAt: 2, updatedAt: 2 },
        { monster: makeMonster({ id: 'b' }), history: [], createdAt: 3, updatedAt: 3 },
      ],
    }
    const raw = clone(lib) as unknown as { entries: unknown[] }
    raw.entries.push(null, 'junk', { monster: { id: 'c', mainBreed: 'nope', subBreed: 'nope' }, history: [], createdAt: 0, updatedAt: 0 })
    const r = validateLibrary(raw)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.library.entries.map((e) => e.monster.id)).toEqual(['a', 'b'])
    expect(r.library.entries[0]!.createdAt).toBe(1)
  })

  it('rejects a library whose entry list is missing (so the mirror copy gets a turn)', () => {
    expect(validateLibrary({ kind: 'library', schemaVersion: SAVE_VERSION, entries: 'x' }).ok).toBe(false)
    expect(validateLibrary(undefined).ok).toBe(false)
    expect(validateLibrary({ kind: 'save', schemaVersion: SAVE_VERSION }).ok).toBe(false)
  })
})

describe('validateAny never throws', () => {
  it('sorts out saves, monsters and libraries by kind and rejects everything else', () => {
    const save = makeSave(createGameState({ monster: makeMonster() }), 1)
    const file = makeMonsterFile(makeMonster())
    expect(validateAny(clone(save)).ok && (validateAny(clone(save)) as { kind: string }).kind).toBe('save')
    expect((validateAny(clone(file)) as { kind: string }).kind).toBe('monster')
    expect((validateAny(clone(emptyLibrary())) as { kind: string }).kind).toBe('library')
    const garbage: unknown[] = [
      null,
      undefined,
      0,
      -1,
      NaN,
      'string',
      '',
      [],
      [1, 2],
      {},
      { kind: 'save' },
      { kind: 'monster' },
      { kind: 'library' },
      { kind: 'spaceship' },
      { kind: 42 },
      { schemaVersion: 'two', kind: 'save' },
      { schemaVersion: SAVE_VERSION, kind: 'save', game: null, rng: 'x' },
      { schemaVersion: SAVE_VERSION, kind: 'monster', monster: null },
      { schemaVersion: SAVE_VERSION, kind: 'library', entries: null },
      { mainBreed: 'puddlepup' },
      { mainBreed: 42, id: 'x' },
      { id: 'x', mainBreed: 'puddlepup', subBreed: 'puddlepup', stats: 'no' },
      new Date(),
      () => 1,
      Symbol('s'),
      Object.create(null),
      { toJSON: () => 'x' },
      { kind: 'save', schemaVersion: SAVE_VERSION, game: { monster: { id: 'x' } }, rng: 1 },
      { kind: 'monster', schemaVersion: SAVE_VERSION, monster: makeMonster(), history: 'nope' },
      { kind: 'monster', schemaVersion: SAVE_VERSION, monster: makeMonster(), history: [null, 1, 'x', {}] },
    ]
    for (const g of garbage) {
      const r = validateAny(g)
      expect(typeof r.ok).toBe('boolean')
      if (!r.ok) expect(r.error.length).toBeGreaterThan(0)
    }
    expect(validateAny({ id: 'x', mainBreed: 'puddlepup', subBreed: 'puddlepup', stats: 'no' }).ok).toBe(true)
  })

  it('settings never fail', () => {
    expect(validateSettings(undefined)).toEqual({ showEditedBadge: false, reduceMotion: false })
    expect(validateSettings({ showEditedBadge: 'yes', reduceMotion: true })).toEqual({ showEditedBadge: false, reduceMotion: true })
    expect(validateSettings('???')).toEqual({ showEditedBadge: false, reduceMotion: false })
  })
})
