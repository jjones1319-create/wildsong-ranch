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
    expect(r.save.game.encyclopedia).toEqual({ breeds: [], variants: [], phrases: [], combos: [] })
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

describe('schema version 6 (M7)', () => {
  it('migrates a version-5 save by adding the expedition, unlock progress, records and the Journal fields', () => {
    const game = createGameState({ monster: makeMonster() }) as unknown as Record<string, unknown>
    for (const k of ['expedition', 'pendingEvent', 'unlocks', 'records', 'oddJobWeek', 'memorialVisitMonth']) delete game[k]
    delete (game.encyclopedia as Record<string, unknown>).combos
    const v5 = { schemaVersion: 5, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '0.8.0' } }
    const up = migrate(JSON.parse(JSON.stringify(v5))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game).toMatchObject({ expedition: null, pendingEvent: null, oddJobWeek: null, memorialVisitMonth: null })
    const r = validateSave(JSON.parse(JSON.stringify(v5)))
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game.unlocks).toEqual({
      rumorsHeard: [],
      masqueradeInvited: false,
      vigilPending: false,
      vigilOpen: false,
      cocoonInto: null,
      expeditionsBySite: { 'thornwood-ruins': 0, 'sunken-library': 0, 'hollowmoon-caverns': 0, 'skyreef-isles': 0 },
      reefclawArrived: false,
      wyrmScaleGiven: false,
    })
    expect(r.save.game.records.highestGeneration).toBe(1)
    expect(r.save.game.encyclopedia.combos).toEqual([])
    // A fresh game now lists its first monster's look; a migrated v5 save catches that up at its next week's end.
    const expected = createGameState({ monster: r.save.game.monster })
    expected.encyclopedia.combos = []
    expect(r.save.game).toEqual(expected)
  })

  it('keeps a good expedition, drops a broken one, and never keeps a trip without a monster', () => {
    const game = createGameState({ monster: makeMonster() })
    game.expedition = {
      site: 'thornwood-ruins',
      seed: 12345,
      startWeek: 8,
      weekNo: 1,
      stamina: 40,
      staminaMax: 50,
      at: 0,
      visited: [0, 0, 99, -1],
      searched: [],
      passed: [],
      blockedAt: 99,
      visit: 1,
      loot: [{ id: 'old-coin', qty: 2 }],
      sheets: [],
      keyFound: null,
      lootlidPlaced: null,
      ended: null,
      log: Array.from({ length: 60 }, (_, i) => `step${i}`),
    }
    const raw = JSON.parse(JSON.stringify(makeSave(game, 1)))
    raw.game.expedition.loot.push(null, 'junk')
    raw.game.unlocks.rumorsHeard = ['cocoon', 'cocoon', 'bogus']
    const r = validateSave(raw)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    const e = r.save.game.expedition!
    expect(e.visited).toEqual([0])
    expect(e.blockedAt).toBeNull()
    expect(e.loot).toEqual([{ id: 'old-coin', qty: 2 }])
    expect(e.log).toHaveLength(30)
    expect(r.save.game.unlocks.rumorsHeard).toEqual(['cocoon'])

    const broken = JSON.parse(JSON.stringify(makeSave(game, 1)))
    broken.game.expedition.at = 500
    const r2 = validateSave(broken)
    expect(r2.ok && r2.save.game.expedition).toBeNull()

    const nobody = JSON.parse(JSON.stringify(makeSave(game, 1)))
    nobody.game.monster = null
    const r3 = validateSave(nobody)
    expect(r3.ok && r3.save.game.expedition).toBeNull()
    expect(r3.ok && r3.save.game.pendingEvent).toBeNull()
  })
})

describe('schema version 7 (M8)', () => {
  it('migrates a version-7 save by adding the Echo Stones week and best round', () => {
    const game = structuredClone(createGameState({ monster: makeMonster() })) as unknown as Record<string, unknown>
    delete game.echoStonesWeek
    delete game.echoStonesBest
    const v7 = { schemaVersion: 7, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '1.1.0' } }
    const up = migrate(JSON.parse(JSON.stringify(v7))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game.echoStonesWeek).toBeNull()
    expect(up.game.echoStonesBest).toBe(0)
    const r = validateSave(up)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game.echoStonesBest).toBe(0)
    // Garbage is clamped, never fatal (a nonsense week becomes week 0, like oddJobWeek).
    const bad = JSON.parse(JSON.stringify(up)) as { game: Record<string, unknown> }
    bad.game.echoStonesBest = -4
    bad.game.echoStonesWeek = 'tuesday'
    const r2 = validateSave(bad)
    expect(r2.ok).toBe(true)
    if (r2.ok) {
      expect(r2.save.game.echoStonesBest).toBe(0)
      expect(r2.save.game.echoStonesWeek).toBe(0)
    }
  })

  it('migrates a version-6 save by adding an empty planner, and caps a long queue', () => {
    const game = createGameState({ monster: makeMonster() }) as unknown as Record<string, unknown>
    delete game.planner
    const v6 = { schemaVersion: 6, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '0.9.0' } }
    const up = migrate(JSON.parse(JSON.stringify(v6))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game.planner).toEqual({ queue: [], log: [], lastStop: null })
    const r = validateSave(JSON.parse(JSON.stringify(v6)))
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game).toEqual(createGameState({ monster: r.save.game.monster }))

    const full = createGameState({ monster: makeMonster() })
    full.planner.queue = Array.from({ length: 12 }, () => ({ kind: 'rest' as const }))
    const raw = JSON.parse(JSON.stringify(makeSave(full, 1)))
    raw.game.planner.queue.push(null, { kind: 'drill', drill: 'not-a-drill' })
    raw.game.planner.lastStop = 'bogus'
    const r2 = validateSave(raw)
    expect(r2.ok).toBe(true)
    if (!r2.ok) return
    expect(r2.save.game.planner.queue).toHaveLength(8)
    expect(r2.save.game.planner.lastStop).toBeNull()
  })
})

describe('schema version 11 (Odd Jobs 2)', () => {
  it('migrates a version-10 save by adding the Turnip Sort best and the Meadow Dash week and best', () => {
    const game = structuredClone(createGameState({ monster: makeMonster() })) as unknown as Record<string, unknown>
    delete game.turnipBest
    delete game.dashWeek
    delete game.dashBest
    const v10 = { schemaVersion: 10, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '1.7.0' } }
    const up = migrate(JSON.parse(JSON.stringify(v10))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game).toMatchObject({ turnipBest: 0, dashWeek: null, dashBest: 0 })
    const r = validateSave(up)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game).toEqual(createGameState({ monster: r.save.game.monster }))
    // Garbage is clamped, never fatal.
    const bad = JSON.parse(JSON.stringify(up)) as { game: Record<string, unknown> }
    bad.game.turnipBest = -4
    bad.game.dashWeek = 'monday'
    bad.game.dashBest = 1e9
    const r2 = validateSave(bad)
    expect(r2.ok).toBe(true)
    if (r2.ok) {
      expect(r2.save.game.turnipBest).toBe(0)
      expect(r2.save.game.dashWeek).toBe(0)
      expect(r2.save.game.dashBest).toBe(10_000)
    }
  })
})

describe('schema version 12 (Bonds)', () => {
  it('migrates a version-11 save: Vacation off, an unarmed away clock, no keepsakes, every monster at no bond boost', () => {
    const game = structuredClone(createGameState({ monster: makeMonster() })) as unknown as Record<string, unknown>
    delete game.keepsakes
    delete game.away
    game.settings = { onePerWeek: false }
    delete ((game.monster as Record<string, unknown>).status as Record<string, unknown>).bondPct
    const v11 = { schemaVersion: 11, kind: 'save', game, rng: 5, meta: { savedAt: 1, appVersion: '1.8.0' } }
    const up = migrate(JSON.parse(JSON.stringify(v11))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game).toMatchObject({ keepsakes: [], away: { armedAt: null, lastGreetAt: null }, settings: { onePerWeek: false, vacation: false } })
    const r = validateSave(up)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    expect(r.save.game.monster!.status.bondPct).toBe(100)
    expect(r.save.game).toEqual(createGameState({ monster: r.save.game.monster }))
    // Garbage is clamped or dropped, never fatal; the new endings and levels are accepted.
    const bad = JSON.parse(JSON.stringify(up)) as { game: Record<string, unknown> & { monster: { status: Record<string, unknown> } } }
    bad.game.keepsakes = ['pinwheel', 'pinwheel', 'not-a-thing', 7]
    bad.game.away = { armedAt: -5, lastGreetAt: 'soon' }
    bad.game.monster.status.bondPct = 900
    bad.game.ended = 'neglected'
    const r2 = validateSave(bad)
    expect(r2.ok).toBe(true)
    if (!r2.ok) return
    expect(r2.save.game.keepsakes).toEqual(['pinwheel', 'kick-ball'])
    expect(r2.save.game.away).toEqual({ armedAt: null, lastGreetAt: null })
    expect(r2.save.game.monster!.status.bondPct).toBe(175)
    expect(r2.save.game.ended).toBe('neglected')
  })
})
