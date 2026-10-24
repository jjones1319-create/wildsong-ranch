import { describe, expect, it } from 'vitest'
import { createGameState } from '../core/state.ts'
import { makeMonster } from '../core/test-helpers.ts'
import { LAB } from '../data/tuning.ts'
import { SAVE_VERSION, migrate } from './migrate.ts'
import { defaultSettings, emptyLibrary, makeMonsterFile, makeSave, validateAny, validateLibrary, validateMonsterFile, validateSettings, type Library } from './schema.ts'

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

  it('migrates a version-2 save by adding the M3 week fields (schema version 3)', () => {
    const game = createGameState({ monster: makeMonster() }) as unknown as Record<string, unknown>
    for (const k of ['weekPhase', 'pendingRequest', 'lastAction', 'monsterHistory', 'tipsSeen', 'counters', 'sandbox']) delete game[k]
    const v2 = { schemaVersion: 2, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '0.4.0' } }
    const up = migrate(clone(v2)) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game).toMatchObject({ weekPhase: 'start', pendingRequest: null, lastAction: null, monsterHistory: [], tipsSeen: [], sandbox: false })
    const r = validateAny(clone(v2))
    expect(r.ok && r.kind === 'save').toBe(true)
    if (r.ok && r.kind === 'save') {
      expect(r.save.game.weekPhase).toBe('start')
      expect(r.save.game.counters).toEqual({ sweetsEaten: 0, sheetsLearned: 0, drillsDone: 0, restsTaken: 0 })
      expect(r.save.game.monster?.name).toBe(game.monster && (game.monster as { name: string }).name)
    }
    // A v2 monster file only gets its version bumped.
    const v2Monster = { schemaVersion: 2, kind: 'monster', monster: makeMonster(), history: [] }
    expect((migrate(clone(v2Monster)) as Record<string, unknown>).game).toBeUndefined()
    expect(validateAny(clone(v2Monster)).ok).toBe(true)
  })

  it('migrates a version-3 save by adding the M5 Guild, tournament and mail fields (and on to the current version)', () => {
    const game = createGameState({ monster: makeMonster() }) as unknown as Record<string, unknown>
    for (const k of ['tournament', 'trial', 'guild', 'hallOfFame', 'mail', 'saleMonths', 'journeysBySite', 'titles']) delete game[k]
    const v3 = { schemaVersion: 3, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '0.6.0' } }
    const up = migrate(clone(v3)) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game).toMatchObject({ tournament: null, trial: null, hallOfFame: [], mail: [], saleMonths: [], titles: [], freezer: [], memorial: [], heartstones: [] })
    const r = validateAny(clone(v3))
    expect(r.ok && r.kind === 'save').toBe(true)
    if (r.ok && r.kind === 'save') {
      expect(r.save.game.guild).toEqual({ officialsWon: [], crownsWon: [], legendWon: false, crownInvite: false, legendInvite: false, creditsRolled: false })
      expect(r.save.game.journeysBySite['iron-quarry']).toBe(0)
    }
    // Broken M5 fields fall back; a tournament for an unknown event is dropped.
    const broken = clone(makeSave(createGameState({ monster: makeMonster() }), 1)) as unknown as { game: Record<string, unknown> }
    broken.game.guild = { officialsWon: ['Z', 'E'], crownsWon: 'x' }
    broken.game.mail = [null, { id: 'm1', week: 3, kind: 'sale', ref: '4', read: false }, 'junk']
    broken.game.tournament = { eventId: 'not-a-cup', week: 1, seed: 1, mode: 'auto', participants: [], matches: [] }
    broken.game.saleMonths = [3, 3, 14]
    const r2 = validateAny(broken)
    expect(r2.ok && r2.kind === 'save').toBe(true)
    if (r2.ok && r2.kind === 'save') {
      expect(r2.save.game.guild.officialsWon).toEqual([])
      expect(r2.save.game.mail).toHaveLength(1)
      expect(r2.save.game.tournament).toBeNull()
      expect(r2.save.game.saleMonths).toEqual([3, 12])
    }
  })

  it('keeps and validates the M3 week fields on a round trip', () => {
    const game = createGameState({ monster: makeMonster() })
    game.weekPhase = 'action'
    game.pendingRequest = { kind: 'treat', toy: 'rubber-ball' }
    game.lastAction = { kind: 'drill', drill: 'log-toss' }
    game.tipsSeen = ['firstDrill', 'firstDrill']
    game.monsterHistory = [{ monster: makeMonster(), savedAt: 10 }]
    const r = validateAny(clone(makeSave(game, 1)))
    expect(r.ok && r.kind === 'save').toBe(true)
    if (r.ok && r.kind === 'save') {
      expect(r.save.game.pendingRequest).toEqual({ kind: 'treat', toy: 'rubber-ball' })
      expect(r.save.game.lastAction).toEqual({ kind: 'drill', drill: 'log-toss' })
      expect(r.save.game.tipsSeen).toEqual(['firstDrill'])
      expect(r.save.game.monsterHistory).toHaveLength(1)
    }
    const broken = clone(makeSave(game, 1)) as unknown as { game: Record<string, unknown> }
    broken.game.pendingRequest = { kind: 'nap' }
    broken.game.lastAction = { kind: 'drill', drill: 'not-a-drill' }
    broken.game.weekPhase = 'middle'
    broken.game.monsterHistory = [null, 'x', { monster: makeMonster(), savedAt: 2 }]
    const r2 = validateAny(broken)
    expect(r2.ok && r2.kind === 'save').toBe(true)
    if (r2.ok && r2.kind === 'save') {
      expect(r2.save.game.pendingRequest).toBeNull()
      expect(r2.save.game.lastAction).toBeNull()
      expect(r2.save.game.weekPhase).toBe('start')
      expect(r2.save.game.monsterHistory).toHaveLength(1)
    }
    // Without a monster a pending request makes no sense and is dropped.
    const empty = createGameState({ monster: null })
    empty.pendingRequest = { kind: 'rest', toy: null }
    empty.weekPhase = 'action'
    const r3 = validateAny(clone(makeSave(empty, 1)))
    expect(r3.ok && r3.kind === 'save' && r3.save.game.pendingRequest === null && r3.save.game.weekPhase === 'start').toBe(true)
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
    expect(validateSettings(undefined)).toEqual(defaultSettings())
    expect(validateSettings({ showEditedBadge: 'yes', reduceMotion: true, textSize: 999, transparency: 'x-ray' })).toEqual({ ...defaultSettings(), reduceMotion: true })
    expect(validateSettings({ ...defaultSettings(), transparency: 'lens', textSize: 130, speed: 'instant' })).toMatchObject({ transparency: 'lens', textSize: 130, speed: 'instant' })
    expect(validateSettings('???')).toEqual(defaultSettings())
  })

  it('M10 battle settings: Auto style and thinking icons fall back and default to balanced / follow the mode', () => {
    expect(defaultSettings()).toMatchObject({ autoStyle: 'balanced', showThinking: null })
    expect(validateSettings({ autoStyle: 'berserk', showThinking: 'yes' })).toEqual(defaultSettings())
    expect(validateSettings({ autoStyle: 7, showThinking: 1 })).toEqual(defaultSettings())
    expect(validateSettings({ ...defaultSettings(), autoStyle: 'aggressive', showThinking: true })).toMatchObject({ autoStyle: 'aggressive', showThinking: true })
    expect(validateSettings({ ...defaultSettings(), autoStyle: 'defensive', showThinking: false })).toMatchObject({ autoStyle: 'defensive', showThinking: false })
    // An older settings file without the fields loads with the defaults.
    const { autoStyle: _a, showThinking: _s, ...old } = defaultSettings()
    expect(validateSettings(old)).toEqual(defaultSettings())
  })
})
