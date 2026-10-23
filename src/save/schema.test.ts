import { describe, expect, it } from 'vitest'
import { createGameState } from '../core/state.ts'
import { makeMonster } from '../core/test-helpers.ts'
import { migrate, SAVE_VERSION } from './migrate.ts'
import { makeSave, validateMonster, validateSave } from './schema.ts'

describe('save validation (§20)', () => {
  it('round-trips a real game state through JSON', () => {
    const game = createGameState({ monster: makeMonster(), breederName: 'Jo', ranchName: 'Hillside' })
    game.inventory = { 'sun-plum': 3 }
    game.songbook = ['universal.beat-bump']
    const raw = JSON.parse(JSON.stringify(makeSave(game, 123456)))
    const r = validateSave(raw)
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.save.game).toEqual(game)
      expect(r.save.rng).toBe(123456)
      expect(r.save.schemaVersion).toBe(SAVE_VERSION)
    }
  })

  it('rejects garbage with a friendly message instead of throwing', () => {
    for (const bad of [null, undefined, 42, 'hello', [], {}, { kind: 'save' }, { schemaVersion: 1, kind: 'save', game: 'nope', rng: 1 }]) {
      const r = validateSave(bad)
      expect(r.ok).toBe(false)
      if (!r.ok) expect(r.error).toMatch(/save/i)
    }
    const unknownBreed = JSON.parse(JSON.stringify(makeSave(createGameState({ monster: makeMonster() }), 1)))
    unknownBreed.game.monster.mainBreed = 'dragonite'
    expect(validateSave(unknownBreed).ok).toBe(false)
  })

  it('clamps out-of-range values, fills missing fields and drops unknown ones', () => {
    const raw = JSON.parse(JSON.stringify(makeSave(createGameState({ monster: makeMonster() }), 1)))
    const m = raw.game.monster
    m.stats.POW = 5000
    m.stats.LIF = -3
    m.fatigue = 140
    m.stress = -20
    m.gutsRate = 99
    m.nature = 'wicked'
    m.techniques.push({ id: 'not.a.technique', uses: 1, level: 1 }, 'garbage', { id: 'universal.beat-bump', uses: -5, level: 9 })
    delete m.status
    delete m.records
    m.extraField = 'dropped'
    raw.game.money = 1e12
    raw.game.difficulty = 'Nightmare'
    raw.game.inventory = { 'sun-plum': 2, 'old-coin': 0, bogus: -4 }
    raw.game.songbook = ['universal.hum-pulse', 'nope', 'universal.hum-pulse']
    raw.game.somethingElse = true
    const r = validateSave(raw)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    const g = r.save.game
    expect(g.monster!.stats.POW).toBe(999)
    expect(g.monster!.stats.LIF).toBe(1)
    expect(g.monster!.fatigue).toBe(100)
    expect(g.monster!.stress).toBe(0)
    expect(g.monster!.gutsRate).toBe(20)
    expect(g.monster!.nature).toBe(0)
    expect(g.monster!.techniques.map((t) => t.id)).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop', 'universal.beat-bump'])
    expect(g.monster!.techniques[2]).toEqual({ id: 'universal.beat-bump', uses: 0, level: 1 })
    expect(g.monster!.status.sickWeeks).toBe(0)
    expect(g.monster!.records.fromSweets.POW).toBe(0)
    expect((g.monster as unknown as Record<string, unknown>).extraField).toBeUndefined()
    expect(g.money).toBe(1_000_000_000)
    expect(g.difficulty).toBe('Standard')
    expect(g.inventory).toEqual({ 'sun-plum': 2 })
    expect(g.songbook).toEqual(['universal.hum-pulse'])
    expect((g as unknown as Record<string, unknown>).somethingElse).toBeUndefined()
  })

  it('migrates a versionless save to the current version', () => {
    const raw = JSON.parse(JSON.stringify(makeSave(createGameState({ monster: null }), 7)))
    delete raw.schemaVersion
    expect(migrate(raw)).toMatchObject({ schemaVersion: SAVE_VERSION })
    expect(validateSave(raw).ok).toBe(true)
    expect(migrate('text')).toBe('text')
    expect(migrate({ schemaVersion: 99 })).toEqual({ schemaVersion: 99 })
  })

  it('validates a single monster for import', () => {
    const good = validateMonster(JSON.parse(JSON.stringify(makeMonster())))
    expect(good.ok).toBe(true)
    expect(validateMonster({ id: 'x' }).ok).toBe(false)
    expect(validateMonster({ id: '', mainBreed: 'puddlepup', subBreed: 'puddlepup' }).ok).toBe(false)
    const sparse = validateMonster({ id: 'x', mainBreed: 'coilfang', subBreed: 'wishlume', name: 'A very very long name indeed' })
    expect(sparse.ok).toBe(true)
    if (sparse.ok) {
      expect(sparse.monster.name).toBe('A very very long')
      expect(sparse.monster.stats.LIF).toBe(1)
      expect(sparse.monster.techniques).toEqual([])
    }
  })
})

describe('schema version 5 (M6)', () => {
  it('migrates a version-4 save by adding the legacy lists, and keeps the starters unlocked', () => {
    const game = createGameState({ monster: makeMonster() }) as unknown as Record<string, unknown>
    for (const k of ['freezer', 'elderGrove', 'memorial', 'heartstones', 'encyclopedia', 'sleepingStones', 'unlocked', 'elderMentorMonth']) delete game[k]
    delete (game.monster as Record<string, unknown>).heirloom
    const v4 = { schemaVersion: 4, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '0.7.0' } }
    const up = migrate(JSON.parse(JSON.stringify(v4))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game).toMatchObject({ freezer: [], elderGrove: [], memorial: [], heartstones: [], sleepingStones: [], elderMentorMonth: null })
    const r = validateSave(JSON.parse(JSON.stringify(v4)))
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game.unlocked.length).toBe(22)
    expect(r.save.game.monster!.heirloom).toBeNull()
    expect(r.save.game.encyclopedia).toEqual({ breeds: [], variants: [], phrases: [] })
  })

  it('tidies the legacy lists: duplicates and broken entries go, caps hold, bad variants are dropped', () => {
    const game = createGameState({ monster: makeMonster({ id: 'a' }) })
    game.freezer = Array.from({ length: 25 }, (_, i) => makeMonster({ id: `f${i % 23}` }))
    game.unlocked = ['puddlepup']
    game.encyclopedia.variants = ['songheart-puddlepup', 'not-a-variant']
    const raw = JSON.parse(JSON.stringify(makeSave(game, 1)))
    raw.game.memorial = [null, { monster: raw.game.monster, cause: 'exploded', epitaph: 'x'.repeat(200), week: 3 }, 'junk']
    raw.game.heartstones = [{ id: 'h1', donorId: 'a', donorName: 'A', donorBreed: 'puddlepup', gains: { POW: 50 }, family: 'Hit', week: 1 }, { id: 'h1' }, null]
    raw.game.monster.heirloom = 'Nonsense'
    const r = validateSave(raw)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game.freezer).toHaveLength(20)
    expect(new Set(r.save.game.freezer.map((m) => m.id)).size).toBe(20)
    expect(r.save.game.memorial).toHaveLength(1)
    expect(r.save.game.memorial[0]!.cause).toBe('passed')
    expect(r.save.game.memorial[0]!.epitaph).toHaveLength(80)
    expect(r.save.game.heartstones).toHaveLength(1)
    expect(r.save.game.heartstones[0]!.gains).toEqual({ LIF: 0, POW: 50, INT: 0, SKI: 0, SPD: 0, DEF: 0 })
    expect(r.save.game.unlocked).toHaveLength(22)
    expect(r.save.game.encyclopedia.variants).toEqual(['songheart-puddlepup'])
    expect(r.save.game.monster!.heirloom).toBeNull()
  })
})
