import { describe, expect, it } from 'vitest'
import { BREED_BY_ID } from '../data/breeds.ts'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { UNLOCKS } from '../data/tuning.ts'
import { STAT_KEYS } from '../data/types.ts'
import { weekIndexOf } from './calendar.ts'
import { buyFromMarket } from './creation.ts'
import { actionMenu, answerEvent, beginWeek, chooseAction, finishWeek } from './game.ts'
import { concludeLife, trainedGains } from './legacy.ts'
import { marketStock } from './market.ts'
import { loyaltyOf, mixBreeds, type Monster } from './monster.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster, type MonsterOverrides } from './test-helpers.ts'
import { createTournament, eventsForWeek, finishTournament, simulatePending } from './tournament.ts'
import { attendVigil, chainStage, cocoonReady, emerge, giveBlueprint, metamorphose, offerAtShrine, offeringsInBag, reefclawArrival, stormChaseReady } from './unlocks.ts'

const at = (year: number, month: number, week: number) => weekIndexOf({ year, month, week })

function gameAt(week: number, m: Monster, phase: 'start' | 'action' = 'start'): GameState {
  const g = createGameState({ monster: m })
  g.week = week
  g.weekPhase = phase
  g.money = 50_000
  return g
}

function strong(main: MonsterOverrides['main'] = 'puddlepup'): Monster {
  const m = makeMonster({ main, stats: { LIF: 999, POW: 999, INT: 999, SKI: 999, SPD: 999, DEF: 999 } })
  m.lifespanTotal = 400
  m.ageWeeks = 100
  return m
}

/** Plays whole weeks through the controller with no action of its own. */
function passWeeks(input: GameState, n: number, rng = createRng(1)): { state: GameState; events: string[] } {
  let s = input
  const events: string[] = []
  for (let i = 0; i < n; i++) {
    const b = beginWeek(s, rng)
    s = b.state
    events.push(...b.events.map((e) => e.kind))
    const a = chooseAction(s, { kind: 'none' }, rng)
    s = a.state
    events.push(...a.events.map((e) => e.kind))
    const f = finishWeek(s, rng)
    s = f.state
    events.push(...f.events.map((e) => e.kind))
  }
  return { state: s, events }
}

describe('1. Velvesper: the cocoon (CONTENT §11)', () => {
  function readyGrub(): Monster {
    const m = makeMonster({ main: 'nibblegrub', spoil: 80, fear: 80 })
    m.lifespanTotal = 400
    m.ageWeeks = 150
    m.diet.puddingCount = 12
    return m
  }

  it('spins in June week 4 only when every condition holds, and emerges four weeks later as a Velvesper', () => {
    const grub = readyGrub()
    expect(loyaltyOf(grub)).toBeGreaterThanOrEqual(UNLOCKS.cocoon.loyaltyMin)
    const s0 = gameAt(at(1, 6, 4), grub)
    expect(cocoonReady(s0)).toBe(true)
    const rng = createRng(5)
    const begun = beginWeek(s0, rng)
    expect(begun.events.some((e) => e.kind === 'cocoonSpun')).toBe(true)
    let s = begun.state
    expect(s.monster!.status.cocoonWeeks).toBe(UNLOCKS.cocoon.weeks)
    expect(s.unlocks.cocoonInto).toBe('velvesper')
    expect(actionMenu(s)).toMatchObject({ wait: true, reason: 'cocoon' })
    const gains = trainedGains(s.monster!)
    const life = s.monster!.lifespanTotal

    // Week 1 (the cocoon week) and three more pass; the fourth end-of-week opens the cocoon.
    s = chooseAction(s, { kind: 'none' }, rng).state
    s = finishWeek(s, rng).state
    const rest = passWeeks(s, 3, rng)
    s = rest.state
    expect(rest.events).toContain('emerged')
    expect(s.monster!.mainBreed).toBe('velvesper')
    expect(s.monster!.subBreed).toBe('nibblegrub')
    expect(s.unlocked).toContain('velvesper')
    expect(s.titles).toContain('Silk & Moonlight')
    expect(s.unlocks.cocoonInto).toBeNull()
    expect(s.monster!.status.cocoonWeeks).toBe(0)
    expect(s.monster!.lifespanTotal).toBe(life + UNLOCKS.cocoon.lifespanBonus)
    const base = mixBreeds('velvesper', 'nibblegrub').base
    for (const k of STAT_KEYS) expect(s.monster!.stats[k]).toBe(Math.min(999, base[k] + Math.round((gains[k] * UNLOCKS.cocoon.keepGainsPct) / 100)))
    expect(s.monster!.growthType).toBe(BREED_BY_ID.velvesper.growth)
  })

  it('keeps techniques by family and gives the new starters', () => {
    const grub = readyGrub()
    grub.techniques = [
      { id: 'nibblegrub.nibble', uses: 0, level: 1 },
      { id: 'universal.beat-bump', uses: 30, level: 2 },
      ...grub.techniques.filter((t) => TECHNIQUE_BY_ID[t.id]?.family === 'Hit'),
    ]
    const hit = TECHNIQUE_BY_ID[grub.techniques.find((t) => TECHNIQUE_BY_ID[t.id]?.family === 'Hit')?.id ?? '']
    const moth = metamorphose(grub, 'velvesper')
    expect(moth.techniques.some((t) => t.id === 'universal.beat-bump' && t.uses === 30)).toBe(true)
    for (const id of mixBreeds('velvesper', 'nibblegrub').techniques) expect(moth.techniques.some((t) => t.id === id)).toBe(true)
    if (hit) expect(moth.techniques.some((t) => TECHNIQUE_BY_ID[t.id]?.family === 'Hit' && TECHNIQUE_BY_ID[t.id]?.breed === 'velvesper')).toBe(true)
    expect(moth.techniques.every((t) => TECHNIQUE_BY_ID[t.id]?.breed !== 'nibblegrub' || TECHNIQUE_BY_ID[t.id]?.family === 'Basic')).toBe(true)
    expect(moth.id).toBe(grub.id)
    expect(moth.name).toBe(grub.name)
  })

  it('does not spin when a condition is missed, and tries again next June', () => {
    const grub = readyGrub()
    grub.diet.puddingCount = 11
    const s0 = gameAt(at(1, 6, 4), grub)
    expect(cocoonReady(s0)).toBe(false)
    expect(beginWeek(s0, createRng(1)).state.unlocks.cocoonInto).toBeNull()
    const wrongWeek = gameAt(at(1, 6, 3), readyGrub())
    expect(cocoonReady(wrongWeek)).toBe(false)
    const nextYear = gameAt(at(2, 6, 4), readyGrub())
    expect(cocoonReady(nextYear)).toBe(true)
    expect(emerge(nextYear)).toBeNull()
  })
})

describe('2. Ashwraith: the Lantern Vigil', () => {
  it('a farewell brings the letter with the next week 1; the Vigil waits as long as it takes; the lantern wakes Ashwraith', () => {
    let s = gameAt(at(1, 1, 3), makeMonster())
    s.ended = 'passed'
    s = concludeLife(s, 'Loved the rain.')!.state
    expect(s.unlocks.vigilPending).toBe(true)
    s = buyFromMarket(s, 'quillion', 'q').state
    expect(s.monster).not.toBeNull()
    s.week = at(1, 2, 1)
    s.weekPhase = 'start'
    const begun = beginWeek(s, createRng(1))
    s = begun.state
    expect(begun.events.some((e) => e.kind === 'vigilMail')).toBe(true)
    expect(s.mail.some((m) => m.kind === 'vigil')).toBe(true)
    expect(s.unlocks.vigilOpen).toBe(true)
    expect(s.unlocks.vigilPending).toBe(false)
    expect(chainStage(s, 'vigil')).toBe(2)
    // Ignored for a month: still open.
    s = finishWeek(s, createRng(1)).state
    s = passWeeks(s, 5).state
    expect(s.unlocks.vigilOpen).toBe(true)
    const attended = attendVigil(s)
    expect(attended.refused).toBeNull()
    s = attended.state
    expect(s.inventory['vigil-lantern']).toBe(1)
    expect(s.unlocks.vigilOpen).toBe(false)
    expect(attendVigil(s).refused).toBe('closed')
    expect(offeringsInBag(s)).toEqual([{ itemId: 'vigil-lantern', breed: 'ashwraith', awake: false }])
    const offered = offerAtShrine(s, 'vigil-lantern')
    expect(offered.refused).toBeNull()
    expect(offered.breed).toBe('ashwraith')
    s = offered.state
    expect(s.unlocked).toContain('ashwraith')
    expect(s.inventory['vigil-lantern']).toBeUndefined()
    expect(chainStage(s, 'vigil')).toBe(3)
    expect(offerAtShrine(s, 'vigil-lantern').refused).toBe('notOwned')
    // A second farewell once Ashwraith is awake sends no letter.
    s.ended = 'passed'
    s = concludeLife(s, '')!.state
    s = buyFromMarket(s, 'puddlepup', 'p').state
    s.week = at(2, 1, 1)
    s.weekPhase = 'start'
    expect(beginWeek(s, createRng(1)).state.unlocks.vigilOpen).toBe(false)
  })
})

describe('3. Zipwisp: the storm chase', () => {
  function stormy(spd = 300): GameState {
    const m = makeMonster({ stats: { SPD: spd } })
    m.lifespanTotal = 400
    m.ageWeeks = 100
    const s = gameAt(at(1, 7, 2), m)
    s.weather = 'Storm'
    return s
  }

  it('offers the spark on a storm week to a fast, calm, rested monster; yes uses the week and brings Stormglass', () => {
    const s0 = stormy()
    expect(stormChaseReady(s0)).toBe(true)
    expect(stormChaseReady(stormy(299))).toBe(false)
    const tired = stormy()
    tired.monster!.fatigue = 31
    expect(stormChaseReady(tired)).toBe(false)
    const calm = stormy()
    calm.weather = 'Rain'
    expect(stormChaseReady(calm)).toBe(false)

    const rng = createRng(2)
    const begun = beginWeek(s0, rng)
    expect(begun.events.some((e) => e.kind === 'stormSpark')).toBe(true)
    let s = begun.state
    expect(s.pendingEvent).toEqual({ kind: 'stormChase' })
    expect(actionMenu(s).reason).toBe('event')
    const chased = answerEvent(s, true, rng)
    expect(chased.events.some((e) => e.kind === 'stormChase')).toBe(true)
    s = chased.state
    expect(s.inventory.stormglass).toBe(1)
    expect(s.monster!.fatigue).toBe(UNLOCKS.storm.fatigueCost)
    expect(s.pendingEvent).toBeNull()
    expect(chainStage(s, 'storm-chase')).toBe(2)
    s = offerAtShrine(s, 'stormglass').state
    expect(s.unlocked).toContain('zipwisp')
    s = finishWeek(s, rng).state
    expect(s.titles).toContain('Storm Chaser')
    expect(stormChaseReady({ ...stormy(), unlocked: s.unlocked })).toBe(false)
  })

  it('no to the spark costs nothing, and the next storm offers it again', () => {
    const rng = createRng(3)
    let s = beginWeek(stormy(), rng).state
    s = answerEvent(s, false, rng).state
    expect(s.pendingEvent).toBeNull()
    expect(actionMenu(s).train).toBe(true)
    expect(s.inventory.stormglass).toBeUndefined()
    s = chooseAction(s, { kind: 'rest' }, rng).state
    s = finishWeek(s, rng).state
    s.weather = 'Storm'
    s.monster!.fatigue = 0
    s.monster!.stress = 0
    expect(beginWeek(s, rng).state.pendingEvent).toEqual({ kind: 'stormChase' })
  })
})

describe('4. Mirrorkin: the Masquerade Cup', () => {
  it('Basil whispers in September once a monster reached B; October brings the Masked Breeder; a win gives the Shard Mask', () => {
    const rng = createRng(4)
    const champ = strong()
    champ.grade = 'B'
    let s = gameAt(at(1, 9, 1), champ)
    const begun = beginWeek(s, rng)
    s = begun.state
    expect(begun.events.some((e) => e.kind === 'masqueradeMail')).toBe(true)
    expect(s.unlocks.masqueradeInvited).toBe(true)
    expect(s.unlocks.rumorsHeard).toContain('masquerade')
    s.week = at(1, 10, 1)
    s.weekPhase = 'action'
    const view = eventsForWeek(s).find((v) => v.event.id === 'masquerade')!
    expect(view.eligible).toBe(true)
    const t = createTournament(s, 'masquerade', 'auto')
    expect(t.participants).toHaveLength(2)
    expect(t.participants[1]!.rivalId).toBe('masked-breeder')
    expect(t.participants[1]!.monster.mainBreed).toBe('mirrorkin')
    expect(t.participants[1]!.habit).toBe('stealsGuts')
    s.tournament = simulatePending(t, true)
    const done = finishTournament(s, rng)
    expect(done.outcome.placing).toBe(1)
    expect(done.outcome.items).toContainEqual({ id: 'shard-mask', qty: 1 })
    s = done.state
    expect(s.inventory['shard-mask']).toBe(1)
    expect(s.records.cupsWon).toBe(1)
    s = offerAtShrine(s, 'shard-mask').state
    expect(s.unlocked).toContain('mirrorkin')
    s = finishWeek(s, rng).state
    expect(s.titles).toContain('Unmasked')
  })

  it('a loss changes nothing: the cup is back every October', () => {
    const rng = createRng(5)
    const weak = makeMonster({ stats: { LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 } })
    weak.lifespanTotal = 400
    weak.ageWeeks = 100
    weak.grade = 'B'
    let s = gameAt(at(1, 10, 1), weak, 'action')
    s.unlocks.masqueradeInvited = true
    const t = createTournament(s, 'masquerade', 'auto')
    s.tournament = simulatePending(t, true)
    const done = finishTournament(s, rng)
    expect(done.outcome.placing).toBe(2)
    s = done.state
    expect(s.inventory['shard-mask']).toBeUndefined()
    s.week = at(2, 10, 1)
    s.monster!.status.injuredWeeks = 0
    s.monster!.fatigue = 0
    expect(eventsForWeek(s).find((v) => v.event.id === 'masquerade')!.eligible).toBe(true)
    const before = gameAt(at(1, 10, 1), strong(), 'action')
    expect(eventsForWeek(before).find((v) => v.event.id === 'masquerade')!.reason).toBe('invitation')
  })
})

describe('5. Gearhoot: the Brass Blueprint', () => {
  it('handing the Blueprint to Dr. Pell wakes Gearhoot and puts it on the Market stall', () => {
    let s = gameAt(at(1, 7, 1), makeMonster())
    expect(giveBlueprint(s).refused).toBe('notOwned')
    s.inventory['brass-blueprint'] = 1
    expect(chainStage(s, 'blueprint')).toBe(2)
    const given = giveBlueprint(s)
    expect(given.refused).toBeNull()
    s = given.state
    expect(s.unlocked).toContain('gearhoot')
    expect(s.inventory['brass-blueprint']).toBeUndefined()
    expect(marketStock(7, s.unlocked).some((o) => o.breed === 'gearhoot' && o.price === 2500 && o.unlocked)).toBe(true)
    expect(marketStock(7, []).some((o) => o.breed === 'gearhoot')).toBe(false)
    expect(buyFromMarket({ ...s, monster: null }, 'gearhoot', 'g').monster?.mainBreed).toBe('gearhoot')
    expect(giveBlueprint({ ...s, inventory: { 'brass-blueprint': 1 } }).refused).toBe('awake')
    s = finishWeek({ ...s, weekPhase: 'action' }, createRng(1)).state
    expect(s.titles).toContain('Tinkerer')
  })
})

describe('6. Reefclaw: the Tide Pool', () => {
  it('moves in on June week 1 after the Tide Pool (to the Freezer when the ranch is taken) and joins the summer Market', () => {
    const s0 = gameAt(at(1, 6, 1), makeMonster())
    s0.upgrades.tidePool = true
    const begun = beginWeek(s0, createRng(1))
    expect(begun.events).toContainEqual({ kind: 'reefclaw', placed: 'freezer' })
    const s = begun.state
    expect(s.freezer.map((m) => m.mainBreed)).toEqual(['reefclaw'])
    expect(s.unlocked).toContain('reefclaw')
    expect(s.unlocks.reefclawArrived).toBe(true)
    expect(s.mail.some((m) => m.kind === 'reefclaw')).toBe(true)
    expect(marketStock(7, s.unlocked).some((o) => o.breed === 'reefclaw' && o.seasonal)).toBe(true)
    expect(marketStock(1, s.unlocked).some((o) => o.breed === 'reefclaw')).toBe(false)
    expect(reefclawArrival(s).placed).toBe('freezer')
    expect(beginWeek({ ...s, week: at(2, 6, 1), weekPhase: 'start' }, createRng(1)).state.freezer).toHaveLength(1)
  })

  it('with no room anywhere it waits for next June', () => {
    const s0 = gameAt(at(1, 6, 1), makeMonster())
    s0.upgrades.tidePool = true
    s0.freezer = Array.from({ length: 20 }, (_, i) => makeMonster({ id: `f${i}` }))
    const begun = beginWeek(s0, createRng(1))
    expect(begun.events).toContainEqual({ kind: 'reefclaw', placed: null })
    const s = begun.state
    expect(s.unlocks.reefclawArrived).toBe(false)
    expect(s.unlocked).not.toContain('reefclaw')
    s.freezer = []
    s.week = at(2, 6, 1)
    s.weekPhase = 'start'
    const again = beginWeek(s, createRng(1))
    expect(again.events).toContainEqual({ kind: 'reefclaw', placed: 'freezer' })
    expect(again.state.unlocks.reefclawArrived).toBe(true)
  })
})

describe('8. Aurelwyrm: four Crowns', () => {
  it('the fourth Crown brings the Wyrm Scale once; offered, it wakes Aurelwyrm', () => {
    const rng = createRng(8)
    const champ = strong()
    champ.grade = 'S'
    let s = gameAt(at(1, 11, 2), champ, 'action')
    s.guild.crownsWon = ['dawn', 'tides', 'embers']
    s.guild.crownInvite = true
    expect(eventsForWeek(s).find((v) => v.event.id === 'crown-of-frost')!.eligible).toBe(true)
    s.tournament = simulatePending(createTournament(s, 'crown-of-frost', 'auto'), true)
    const done = finishTournament(s, rng)
    expect(done.outcome.placing).toBe(1)
    s = done.state
    expect(s.guild.crownsWon).toHaveLength(4)
    expect(s.inventory['wyrm-scale']).toBe(1)
    expect(s.unlocks.wyrmScaleGiven).toBe(true)
    expect(s.mail.some((m) => m.kind === 'wyrm')).toBe(true)
    expect(s.titles).toContain('Four Crowns')
    expect(chainStage(s, 'four-crowns')).toBe(2)
    s = offerAtShrine(s, 'wyrm-scale').state
    expect(s.unlocked).toContain('aurelwyrm')
    expect(chainStage(s, 'four-crowns')).toBe(3)
    // A fifth Crown does not hand out a second scale.
    s.week = at(2, 2, 2)
    s.monster!.fatigue = 0
    s.monster!.stress = 0
    s.monster!.status.injuredWeeks = 0
    s.tournament = simulatePending(createTournament(s, 'crown-of-dawn', 'auto'), true)
    const again = finishTournament(s, rng)
    expect(again.outcome.items.some((i) => i.id === 'wyrm-scale')).toBe(false)
  })
})

describe('the Journal stages', () => {
  it('reads 0 → 1 → 2 → 3 for every chain', () => {
    const s = gameAt(at(1, 1, 1), makeMonster())
    for (const chain of ['cocoon', 'vigil', 'storm-chase', 'masquerade', 'blueprint', 'tide-pool', 'strange-chest', 'four-crowns'] as const) expect(chainStage(s, chain)).toBe(0)
    s.unlocks.rumorsHeard = ['strange-chest']
    expect(chainStage(s, 'strange-chest')).toBe(1)
    s.unlocks.expeditionsBySite['thornwood-ruins'] = 1
    expect(chainStage(s, 'strange-chest')).toBe(2)
    s.unlocked.push('lootlid')
    expect(chainStage(s, 'strange-chest')).toBe(3)
    s.upgrades.tidePool = true
    expect(chainStage(s, 'tide-pool')).toBe(2)
  })
})
