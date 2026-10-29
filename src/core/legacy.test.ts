import { describe, expect, it } from 'vitest'
import { FREEZER, HEARTSTONE } from '../data/tuning.ts'
import {
  canReceiveHeartstone,
  concludeLife,
  editMemorial,
  elderMentorFor,
  elderSite,
  freezeActive,
  giveHeartstone,
  heartstoneCap,
  heartstoneFrom,
  heartstoneGrant,
  makeActive,
  monthIndexOf,
  mostUsedFamily,
  releaseStored,
  replaceStored,
  sendToFreezer,
  trainedGains,
} from './legacy.ts'
import { breedBirth } from './monster.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const fill = (n: number) => Array.from({ length: n }, (_, i) => makeMonster({ id: `f${i}` }))

describe('the Freezer (§16)', () => {
  it('freezes the active monster for free and empties the ranch', () => {
    const state = createGameState({ monster: makeMonster({ id: 'a' }) })
    state.weekPhase = 'action'
    state.lastAction = { kind: 'rest' }
    const r = freezeActive(state)
    expect(r.refused).toBeNull()
    expect(r.state.monster).toBeNull()
    expect(r.state.freezer.map((m) => m.id)).toEqual(['a'])
    expect(r.state.weekPhase).toBe('start')
    expect(r.state.lastAction).toBeNull()
    expect(state.monster?.id).toBe('a') // the input is untouched
  })

  it('refuses when the ranch is busy, empty, or the Freezer is full', () => {
    const empty = createGameState({ monster: null })
    expect(freezeActive(empty).refused).toBe('noMonster')
    const busy = createGameState({ monster: makeMonster() })
    busy.trial = { site: 'iron-quarry', pendingTechnique: null }
    expect(freezeActive(busy).refused).toBe('busy')
    const full = createGameState({ monster: makeMonster({ id: 'x' }) })
    full.freezer = fill(FREEZER.slots)
    expect(freezeActive(full).refused).toBe('full')
    expect(sendToFreezer(full, makeMonster({ id: 'y' })).refused).toBe('full')
  })

  it('Make Active swaps with the current monster, and an Elder needs a free slot for the swap', () => {
    const state = createGameState({ monster: makeMonster({ id: 'a' }) })
    state.freezer = [makeMonster({ id: 'b' })]
    const r = makeActive(state, 'b')
    expect(r.refused).toBeNull()
    expect(r.state.monster?.id).toBe('b')
    expect(r.state.freezer.map((m) => m.id)).toEqual(['a'])
    expect(r.state.encyclopedia.breeds).toContain('puddlepup')
    expect(makeActive(state, 'nope').refused).toBe('notFound')
    const elder = createGameState({ monster: makeMonster({ id: 'a' }) })
    elder.elderGrove = [makeMonster({ id: 'e' })]
    elder.freezer = fill(FREEZER.slots)
    expect(makeActive(elder, 'e').refused).toBe('full')
    const emptyRanch = createGameState({ monster: null })
    emptyRanch.elderGrove = [makeMonster({ id: 'e' })]
    const r2 = makeActive(emptyRanch, 'e')
    expect(r2.state.monster?.id).toBe('e')
    expect(r2.state.elderGrove).toEqual([])
  })

  it('sends, releases and replaces stored monsters by id', () => {
    const state = createGameState({ monster: makeMonster({ id: 'a' }) })
    expect(sendToFreezer(state, makeMonster({ id: 'a' })).refused).toBe('duplicate')
    const sent = sendToFreezer(state, makeMonster({ id: 'b' })).state
    expect(sent.freezer).toHaveLength(1)
    const edited = structuredClone(sent.freezer[0]!)
    edited.name = 'Renamed'
    const replaced = replaceStored(sent, edited)
    expect(replaced.freezer[0]!.name).toBe('Renamed')
    expect(replaced.freezer[0]!.flags.edited).toBe(false) // a name change alone is not an edit
    edited.stats.POW = 500
    expect(replaceStored(sent, edited).freezer[0]!.flags.edited).toBe(true)
    expect(releaseStored(replaced, 'b').freezer).toEqual([])
    expect(releaseStored(replaced, 'zzz')).toBe(replaced)
  })
})

describe('Heartstones and the Heirloom (§16)', () => {
  it('records the trained gains, the most-used family, and grants 15 % capped at +60', () => {
    const base = breedBirth('puddlepup').base
    const m = makeMonster({ stats: { POW: base.POW + 500, INT: base.INT + 100, LIF: base.LIF - 20 } })
    m.techniques = [
      { id: 'puddlepup.splash-nip', uses: 3, level: 1 },
      { id: 'universal.beat-bump', uses: 10, level: 1 },
    ]
    expect(trainedGains(m)).toMatchObject({ POW: 500, INT: 100, LIF: 0 })
    expect(mostUsedFamily(m)).toBe('Basic')
    const stone = heartstoneFrom(m, 12)
    expect(stone.donorName).toBe(m.name)
    expect(heartstoneGrant(stone)).toMatchObject({ POW: HEARTSTONE.capPerStat, INT: 15, LIF: 0 })
  })

  it('only a monster under 48 weeks that has none can take one; the gift sets the Heirloom', () => {
    const young = makeMonster()
    expect(canReceiveHeartstone(young)).toEqual({ ok: true })
    const old = makeMonster()
    old.ageWeeks = HEARTSTONE.maxAgeWeeks
    expect(canReceiveHeartstone(old)).toEqual({ ok: false, reason: 'age' })
    const has = makeMonster()
    has.status.heartstoneReceived = true
    expect(canReceiveHeartstone(has)).toEqual({ ok: false, reason: 'has' })

    const state = createGameState({ monster: young })
    const stone = heartstoneFrom(makeMonster({ stats: { SKI: 900 } }), 1)
    stone.family = 'Hit'
    state.heartstones = [stone]
    const before = young.stats.SKI
    const r = giveHeartstone(state, stone.id)
    expect(r.refused).toBeNull()
    expect(r.grant?.SKI).toBe(HEARTSTONE.capPerStat)
    expect(r.state.monster!.stats.SKI).toBe(before + HEARTSTONE.capPerStat)
    expect(r.state.monster!.status.heartstoneReceived).toBe(true)
    expect(r.state.monster!.heirloom).toBe('Hit')
    expect(r.state.heartstones).toEqual([])
    expect(giveHeartstone(r.state, stone.id).refused).toBe('noStone')
    state.heartstones = [stone]
    expect(giveHeartstone(r.state, stone.id).refused).toBe('noStone')
    expect(giveHeartstone({ ...state, monster: null }, stone.id).refused).toBe('noTarget')
  })

  it('caps the shelf at 10, or 15 with the Lantern Garden', () => {
    const state = createGameState()
    expect(heartstoneCap(state)).toBe(HEARTSTONE.max)
    state.upgrades.lanternGarden = true
    expect(heartstoneCap(state)).toBe(HEARTSTONE.maxWithLanternGarden)
  })
})

describe('the farewell (§7)', () => {
  it('on Standard the monster joins the Memorial with its epitaph and leaves a Heartstone', () => {
    const state = createGameState({ monster: makeMonster({ id: 'old' }) })
    state.ended = 'passed'
    state.week = 40
    const r = concludeLife(state, '  Loved every puddle.  ')!
    expect(r.cause).toBe('passed')
    expect(r.heartstone?.donorId).toBe('old')
    expect(r.heartstoneLost).toBe(false)
    expect(r.state.memorial[0]).toMatchObject({ cause: 'passed', epitaph: 'Loved every puddle.', week: 40 })
    expect(r.state.memorial[0]!.monster.id).toBe('old')
    expect(r.state.elderGrove).toEqual([])
    expect(r.state.monster).toBeNull()
    expect(r.state.ended).toBeNull()
    expect(r.state.heartstones[0]!.id).toBe('hs-old')
    expect(concludeLife(r.state, 'again')).toBeNull()
  })

  it('on Gentle the monster retires to the Elder Grove too, and a full shelf loses the stone', () => {
    const state = createGameState({ monster: makeMonster({ id: 'elder' }), difficulty: 'Gentle' })
    state.ended = 'retired'
    state.heartstones = Array.from({ length: HEARTSTONE.max }, (_, i) => ({ ...heartstoneFrom(makeMonster({ id: `d${i}` }), 0) }))
    const r = concludeLife(state, '')!
    expect(r.cause).toBe('retired')
    expect(r.heartstone).toBeNull()
    expect(r.heartstoneLost).toBe(true)
    expect(r.state.elderGrove.map((m) => m.id)).toEqual(['elder'])
    expect(r.state.memorial[0]!.cause).toBe('retired')
    expect(r.state.heartstones).toHaveLength(HEARTSTONE.max)
  })

  it('edits a Memorial name and epitaph in place', () => {
    const state = createGameState({ monster: makeMonster({ id: 'old' }) })
    state.ended = 'passed'
    const done = concludeLife(state, 'first')!.state
    const edited = editMemorial(done, 'old', ' Pip ', 'A good one.')
    expect(edited.memorial[0]!.monster.name).toBe('Pip')
    expect(edited.memorial[0]!.epitaph).toBe('A good one.')
    expect(editMemorial(done, 'nope', 'x', 'y')).toBe(done)
  })
})

describe('the Elder Grove mentors (§7)', () => {
  it('an Elder mentors the site of its best stat, once a month', () => {
    const elder = makeMonster({ id: 'e', stats: { POW: 400, INT: 100, SKI: 100, SPD: 100, DEF: 100, LIF: 900 } })
    expect(elderSite(elder)).toBe('iron-quarry')
    const state = createGameState({ monster: makeMonster() })
    state.elderGrove = [elder]
    state.week = 9
    expect(elderMentorFor(state, 'iron-quarry')?.id).toBe('e')
    expect(elderMentorFor(state, 'windrun-steppe')).toBeNull()
    state.elderMentorMonth = monthIndexOf(9)
    expect(elderMentorFor(state, 'iron-quarry')).toBeNull()
    state.week = 12 // next month
    expect(elderMentorFor(state, 'iron-quarry')?.id).toBe('e')
  })
})
