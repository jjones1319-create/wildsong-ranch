import { describe, expect, it } from 'vitest'
import { newRanchmate } from './creation.ts'
import { findRelative } from './fusion.ts'
import { forgetFromCard, learnFromSongbook, useItems } from './game.ts'
import { freeMonster, freezerToPen, makeStar, penToFreezer, replaceRanchmate, setOrder } from './herd.ts'
import { addItems } from './items.ts'
import { updateRecordsMut } from './journal.ts'
import { findOwned, giveHeartstone, heartstoneFrom, ownedIds, releaseStored } from './legacy.ts'
import { totalStats } from './monster.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { knownMonsters } from './titles.ts'
import { reachedGrade } from './unlocks.ts'

/** A star 'star' and one ranch-mate 'mate', the week in play. */
function ranch(): GameState {
  const s = createGameState({ monster: makeMonster({ id: 'star' }) })
  s.weekPhase = 'action'
  s.ranchmates = [{ ...newRanchmate(makeMonster({ id: 'mate', main: 'tumblefox' })), order: { kind: 'drill', drill: 'puzzle-stones' } }]
  return s
}

describe('⭐ Make star (§6.11)', () => {
  it('swaps the star and the ranch-mate with their edit histories, and clears the old star’s week', () => {
    const s = ranch()
    s.monsterHistory = [{ monster: makeMonster({ id: 'star' }), savedAt: 1 }]
    s.ranchmates[0]!.history = [{ monster: makeMonster({ id: 'mate' }), savedAt: 2 }]
    s.pendingRequest = { kind: 'rest', toy: null }
    s.pendingEvent = { kind: 'stormChase' }
    s.lastAction = { kind: 'drill', drill: 'log-toss' }
    const r = makeStar(s, 'mate')
    expect(r.refused).toBeNull()
    expect(r.state.monster!.id).toBe('mate')
    expect(r.state.monsterHistory[0]!.savedAt).toBe(2)
    expect(r.state.ranchmates).toHaveLength(1)
    // The old star takes the pen, carrying on last week's drill.
    expect(r.state.ranchmates[0]).toMatchObject({ monster: { id: 'star' }, order: { kind: 'drill', drill: 'log-toss' }, last: null })
    expect(r.state.ranchmates[0]!.history[0]!.savedAt).toBe(1)
    expect(r.state.pendingRequest).toBeNull()
    expect(r.state.pendingEvent).toBeNull()
    expect(r.state.lastAction).toBeNull()
    expect(r.state.weekPhase).toBe('action')
    expect(s.monster!.id).toBe('star') // pure
  })

  it('with no star the ranch-mate simply steps onto the ranch', () => {
    const s = ranch()
    s.monster = null
    s.weekPhase = 'start'
    const r = makeStar(s, 'mate')
    expect(r.state.monster!.id).toBe('mate')
    expect(r.state.ranchmates).toEqual([])
  })

  it('is refused for a stranger, an ended life, a busy ranch or a cocoon', () => {
    const s = ranch()
    expect(makeStar(s, 'nobody').refused).toBe('notFound')
    expect(makeStar(s, 'star').refused).toBe('notFound')
    expect(makeStar({ ...s, ended: 'passed' }, 'mate').refused).toBe('ended')
    expect(makeStar({ ...s, journey: { site: 'iron-quarry', weekNo: 2, successes: 0, learned: null, pendingTechnique: null, gains: {}, elderMentor: false } as GameState['journey'] }, 'mate').refused).toBe('busy')
    expect(makeStar({ ...s, trial: { site: 'iron-quarry', pendingTechnique: null } }, 'mate').refused).toBe('busy')
    expect(makeStar({ ...s, unlocks: { ...s.unlocks, cocoonInto: 'velvesper' } }, 'mate').refused).toBe('cocoon')
  })
})

describe('orders, moves and setting free', () => {
  it('sets an order (a Yard drill is allowed; an unknown drill is not)', () => {
    const s = ranch()
    expect(setOrder(s, 'mate', { kind: 'rest' }).state.ranchmates[0]!.order).toEqual({ kind: 'rest' })
    expect(setOrder(s, 'mate', { kind: 'drill', drill: 'quarry-haul' }).refused).toBeNull()
    expect(setOrder(s, 'mate', { kind: 'drill', drill: 'nope' as never }).refused).toBe('unknownDrill')
    expect(setOrder(s, 'star', { kind: 'play' }).refused).toBe('notFound')
  })

  it('moves between a pen and the Freezer, within the room there is', () => {
    const s = ranch()
    const frozen = penToFreezer(s, 'mate')
    expect(frozen.state.ranchmates).toEqual([])
    expect(frozen.state.freezer.map((m) => m.id)).toEqual(['mate'])
    const back = freezerToPen(frozen.state, 'mate')
    expect(back.state.ranchmates[0]).toMatchObject({ monster: { id: 'mate' }, order: { kind: 'play' }, last: null })
    expect(freezerToPen(s, 'mate').refused).toBe('notFound')
    const crowded = structuredClone(frozen.state)
    crowded.ranchmates = [newRanchmate(makeMonster({ id: 'other' }))]
    expect(freezerToPen(crowded, 'mate').refused).toBe('full')
    const full = ranch()
    full.freezer = Array.from({ length: 20 }, (_, i) => makeMonster({ id: `f${i}` }))
    expect(penToFreezer(full, 'mate').refused).toBe('full')
    // Elders stay in the Grove.
    const grove = ranch()
    grove.ranchmates = []
    grove.elderGrove = [makeMonster({ id: 'elder' })]
    expect(freezerToPen(grove, 'elder').refused).toBe('notFound')
  })

  it('🕊️ sets a ranch-mate or a frozen monster free: Memorial "freed", no Heartstone, friendships end', () => {
    const s = ranch()
    s.freezer = [makeMonster({ id: 'ice' })]
    s.friendships = [
      { a: 'mate', b: 'star', points: 30 },
      { a: 'ice', b: 'star', points: 5 },
    ]
    expect(freeMonster(s, 'star').refused).toBe('star')
    expect(freeMonster(s, 'ghost').refused).toBe('notFound')
    const r = freeMonster(s, 'mate')
    expect(r.state.ranchmates).toEqual([])
    expect(r.state.memorial[0]).toMatchObject({ cause: 'freed', monster: { id: 'mate' } })
    expect(r.state.memorial[0]!.epitaph.length).toBeGreaterThan(0)
    expect(r.state.heartstones).toEqual([])
    expect(r.state.friendships).toEqual([{ a: 'ice', b: 'star', points: 5 }])
    const iced = freeMonster(r.state, 'ice')
    expect(iced.state.freezer).toEqual([])
    expect(iced.state.friendships).toEqual([])
    // Releasing a stored monster to the Library prunes its friendships too.
    expect(releaseStored(s, 'ice').friendships).toEqual([{ a: 'mate', b: 'star', points: 30 }])
  })

  it('✏️ Edit saves a ranch-mate with its own history, like the star', () => {
    const s = ranch()
    const edited = structuredClone(s.ranchmates[0]!.monster)
    edited.stats.POW = 777
    edited.id = 'tampered'
    expect(replaceRanchmate(s, edited, 5)).toBe(s) // unknown id: nothing changes
    edited.id = 'mate'
    const r = replaceRanchmate(s, edited, 5)
    expect(r.ranchmates[0]!.monster.stats.POW).toBe(777)
    expect(r.ranchmates[0]!.monster.flags.edited).toBe(true)
    expect(r.ranchmates[0]!.history).toHaveLength(1)
    expect(r.ranchmates[0]!.history[0]!.savedAt).toBe(5)
    expect(r.monsterHistory).toEqual([])
  })
})

describe('the Bag, the Songbook and Heartstones reach the ranch-mates', () => {
  it('items and Songsheets take a target; the one-per-week rule counts for the whole ranch', () => {
    const s = ranch()
    s.inventory = addItems(s.inventory, 'mighty-muffin', 3)
    const ate = useItems(s, 'mighty-muffin', 2, undefined, 'mate')
    expect(ate.used).toBe(2)
    expect(ate.state.ranchmates[0]!.monster.stats.POW).toBe(s.ranchmates[0]!.monster.stats.POW + 10)
    expect(ate.state.monster).toEqual(s.monster)
    expect(ate.state.counters.sweetsEaten).toBe(2)
    expect(useItems(s, 'mighty-muffin', 1, undefined, 'nobody').used).toBe(0)
    const classic = { ...s, settings: { ...s.settings, onePerWeek: true } }
    const once = useItems(classic, 'mighty-muffin', 1, undefined, 'mate')
    expect(once.used).toBe(1)
    expect(useItems(once.state, 'mighty-muffin', 1).result?.refused).toBe('onePerWeek')

    s.songbook = ['universal.beat-bump']
    const learned = learnFromSongbook(s, 'universal.beat-bump', undefined, 'mate')
    expect(learned.status).toBe('learned')
    expect(learned.state.ranchmates[0]!.monster.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(true)
    expect(learned.state.monster!.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(false)
    expect(learnFromSongbook(s, 'universal.beat-bump', undefined, 'nobody').status).toBe('unknownTechnique')
    const forgot = forgetFromCard(learned.state, 'universal.beat-bump', 'mate')
    expect(forgot.ranchmates[0]!.monster.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(false)
  })

  it('a young ranch-mate can take a Heartstone', () => {
    const s = ranch()
    s.heartstones = [heartstoneFrom(makeMonster({ id: 'donor', stats: { POW: 600 } }), 1)]
    const r = giveHeartstone(s, 'hs-donor', 'mate')
    expect(r.refused).toBeNull()
    expect(r.state.ranchmates[0]!.monster.status.heartstoneReceived).toBe(true)
  })

  it('Heartstone ids stay unique when the same monster leaves a second one', () => {
    const m = makeMonster({ id: 'twice' })
    const first = heartstoneFrom(m, 1)
    expect(first.id).toBe('hs-twice')
    expect(heartstoneFrom(m, 9, [first]).id).toBe('hs-twice-2')
    expect(heartstoneFrom(m, 9, [first, { id: 'hs-twice-2' }]).id).toBe('hs-twice-3')
  })
})

describe('the ranch remembers its ranch-mates', () => {
  it('owned ids, known monsters, grades reached, the best total and family trees include them', () => {
    const s = ranch()
    const m = s.ranchmates[0]!.monster
    m.grade = 'A'
    m.stats.POW = 900
    expect(findOwned(s, 'mate')?.where).toBe('pen')
    expect(findOwned(s, 'star')?.where).toBe('star')
    expect([...ownedIds(s)].sort()).toEqual(['mate', 'star'])
    expect(knownMonsters(s).map((k) => k.id)).toContain('mate')
    expect(reachedGrade(s, 'A')).toBe(true)
    updateRecordsMut(s)
    expect(s.records.bestTotal).toBe(totalStats(m.stats))
    expect(s.records.bestTotalName).toBe(m.name)
    // A living parent is found before an old Memorial copy.
    s.memorial = [{ monster: { ...structuredClone(m), name: 'Old copy' }, cause: 'neglected', epitaph: '', week: 0 }]
    expect(findRelative(s, 'mate')?.name).toBe(m.name)
  })
})
