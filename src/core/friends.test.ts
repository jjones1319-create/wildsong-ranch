import { describe, expect, it } from 'vitest'
import { HERD_TEXT } from '../data/text/herd.ts'
import { FARM, FRIENDS } from '../data/tuning.ts'
import { newRanchmate } from './creation.ts'
import { atHome, friendPoints, friendsOf, friendsWeekMut, tierOf, trainingPartner } from './friends.ts'
import { freeMonster } from './herd.ts'
import { herdLines } from './report.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState, type MateOrder } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { isGoodOutcome, resolveDrill } from './training.ts'
import { endWeek, resolveAction } from './week.ts'

/** The star and ranch-mates (each `[id, order]`), every one named after its id. */
function ranch(mates: [string, MateOrder][] = []): GameState {
  const star = makeMonster({ id: 'star' })
  star.name = 'Star'
  const s = createGameState({ monster: star })
  s.week = 1
  s.weekPhase = 'action'
  s.farm.pensBought = 5
  s.ranchmates = mates.map(([id, order]) => {
    const m = makeMonster({ id })
    m.name = id
    return { ...newRanchmate(m), order }
  })
  return s
}

const REST: MateOrder = { kind: 'rest' }
const PLAY: MateOrder = { kind: 'play' }
const LOG: MateOrder = { kind: 'drill', drill: 'log-toss' }
const befriend = (s: GameState, x: string, y: string, points: number) => s.friendships.push({ a: x < y ? x : y, b: x < y ? y : x, points })

describe('friendships grow at home (§6.11)', () => {
  it('every pair at home gains a point a week, +1 when either is on Play', () => {
    const s = ranch([['fern', REST], ['moss', PLAY]])
    expect(friendsWeekMut(s)).toEqual([])
    expect(friendPoints(s, 'star', 'fern')).toBe(FRIENDS.perWeek)
    expect(friendPoints(s, 'star', 'moss')).toBe(FRIENDS.perWeek + FRIENDS.playBonus)
    expect(friendPoints(s, 'fern', 'moss')).toBe(FRIENDS.perWeek + FRIENDS.playBonus)
    // Pairs are saved sorted, once each.
    expect(s.friendships.every((f) => f.a < f.b)).toBe(true)
    expect(s.friendships).toHaveLength(3)
  })

  it('the Campfire Circle (farm Lv9) adds a point, and points stop at the cap', () => {
    const s = ranch([['fern', REST]])
    s.farm.xp = FARM.levelXp[8]!
    friendsWeekMut(s)
    expect(friendPoints(s, 'star', 'fern')).toBe(FRIENDS.perWeek + FRIENDS.campfireBonus)
    s.friendships[0]!.points = FRIENDS.maxPoints - 1
    friendsWeekMut(s)
    expect(friendPoints(s, 'star', 'fern')).toBe(FRIENDS.maxPoints)
  })

  it('only monsters at home: not missing, at the clinic or in a cocoon, and the star not away', () => {
    const s = ranch([['fern', REST], ['moss', REST]])
    s.ranchmates[1]!.monster.status.clinicWeeks = 2
    friendsWeekMut(s)
    expect(friendPoints(s, 'star', 'fern')).toBe(1)
    expect(friendPoints(s, 'star', 'moss')).toBe(0)
    s.journey = { site: 'emberCrag' } as unknown as GameState['journey']
    expect(atHome(s).map((h) => h.m.id)).toEqual(['fern'])
    expect(friendsWeekMut(s)).toEqual([])
    expect(friendPoints(s, 'star', 'fern')).toBe(1)
  })

  it('fewer than two at home: nothing happens (a one-monster game is unchanged)', () => {
    const s = ranch()
    s.monster!.stress = 30
    const before = structuredClone(s)
    expect(friendsWeekMut(s)).toEqual([])
    expect(s).toEqual(before)
  })

  it('frozen monsters and Elders keep their points', () => {
    const s = ranch([['fern', REST]])
    const ice = makeMonster({ id: 'ice' })
    s.freezer = [ice]
    befriend(s, 'star', 'ice', 40)
    friendsWeekMut(s)
    expect(friendPoints(s, 'star', 'ice')).toBe(40)
  })
})

describe('tiers and the summary line', () => {
  it('Friends 12, Close 36, Best 72', () => {
    expect(FRIENDS.tiers).toEqual([12, 36, 72])
    expect([0, 11, 12, 35, 36, 71, 72, 100].map(tierOf)).toEqual([0, 0, 1, 1, 2, 2, 3, 3])
  })

  it('reaching a tier is news once, and Wren says so', () => {
    const s = ranch([['fern', PLAY]])
    befriend(s, 'star', 'fern', 10)
    const news = friendsWeekMut(s)
    expect(news).toEqual([{ aId: 'star', bId: 'fern', a: 'Star', b: 'fern', tier: 1 }])
    expect(friendsWeekMut(s)).toEqual([])
    const lines = herdLines([{ kind: 'friends', news }])
    expect(lines).toHaveLength(1)
    expect(lines[0]!.text).toBe('Star and fern are friends now! They keep finding reasons to sit together.')
    expect(HERD_TEXT.friends.reached[3]).toContain('best friends now!')
  })

  it('endWeek reports the tier as a friends event', () => {
    const s = ranch([['fern', PLAY]])
    befriend(s, 'star', 'fern', 34)
    const r = endWeek(s, createRng(4))
    expect(r.events.find((e) => e.kind === 'friends')).toMatchObject({ news: [{ tier: 2 }] })
  })
})

describe('calm: stress by the best present friend', () => {
  it('−1 for Friends or Close, −2 for Best, only with the friend at home', () => {
    expect(FRIENDS.stressByTier).toEqual([1, 1, 2])
    const s = ranch([['fern', REST], ['moss', REST]])
    befriend(s, 'star', 'fern', 80)
    befriend(s, 'star', 'moss', 20)
    for (const m of [s.monster!, s.ranchmates[0]!.monster, s.ranchmates[1]!.monster]) m.stress = 30
    friendsWeekMut(s)
    expect(s.monster!.stress).toBe(28)
    expect(s.ranchmates[0]!.monster.stress).toBe(28)
    expect(s.ranchmates[1]!.monster.stress).toBe(29)
    // The best friend away: the next best present one counts.
    s.ranchmates[0]!.monster.status.missingWeeks = 3
    friendsWeekMut(s)
    expect(s.monster!.stress).toBe(27)
  })
})

describe('the training partner', () => {
  it('a Friends-or-better ranch-mate on the same drill, at home and not resting by itself', () => {
    const s = ranch([['fern', LOG], ['moss', { kind: 'drill', drill: 'plow-pull' }]])
    expect(trainingPartner(s, 'log-toss')).toBeNull()
    befriend(s, 'star', 'fern', 11)
    expect(trainingPartner(s, 'log-toss')).toBeNull()
    s.friendships[0]!.points = 12
    expect(trainingPartner(s, 'log-toss')?.monster.id).toBe('fern')
    befriend(s, 'star', 'moss', 90)
    expect(trainingPartner(s, 'log-toss')?.monster.id).toBe('fern')
    s.ranchmates[0]!.monster.fatigue = 70
    expect(trainingPartner(s, 'log-toss')).toBeNull()
    s.ranchmates[0]!.monster.fatigue = 0
    s.ranchmates[0]!.monster.status.missingWeeks = 1
    expect(trainingPartner(s, 'log-toss')).toBeNull()
  })

  it('good outcomes get +2 on the main gain, with the friend’s name; others are unchanged', () => {
    const m = makeMonster({ id: 'star' })
    let good = 0
    let bad = 0
    for (let seed = 1; seed < 80; seed++) {
      const solo = resolveDrill(m, 'log-toss', createRng(seed))
      const duo = resolveDrill(m, 'log-toss', createRng(seed), { trainingYard: false, buddy: 'Fern' })
      expect(duo.result.outcome).toBe(solo.result.outcome)
      if (isGoodOutcome(solo.result.outcome)) {
        good += 1
        expect(duo.result.buddy).toBe('Fern')
        expect(duo.result.gains.POW).toBe((solo.result.gains.POW ?? 0) + FRIENDS.buddyGain)
      } else {
        bad += 1
        expect(duo.result).toEqual(solo.result)
        expect(duo.result.buddy).toBeUndefined()
      }
    }
    expect(good).toBeGreaterThan(0)
    expect(bad).toBeGreaterThan(0)
  })

  it('the star’s drill week passes the partner through, with no extra randomness', () => {
    const s = ranch([['fern', LOG]])
    befriend(s, 'star', 'fern', 50)
    const a = createRng(9)
    const b = createRng(9)
    const r = resolveAction(s, { kind: 'drill', drill: 'log-toss' }, a)
    const solo = resolveDrill(s.monster!, 'log-toss', b, { trainingYard: false })
    expect(a.getState()).toBe(b.getState())
    expect(r.drill!.buddy).toBe(isGoodOutcome(solo.result.outcome) ? 'fern' : undefined)
  })
})

describe('pruning and the card list', () => {
  it('setting a monster free ends its friendships; the card lists the rest, closest first', () => {
    const s = ranch([['fern', REST], ['moss', REST]])
    befriend(s, 'star', 'fern', 40)
    befriend(s, 'star', 'moss', 80)
    befriend(s, 'fern', 'moss', 5)
    expect(friendsOf(s, 'star').map((f) => [f.name, f.tier])).toEqual([
      ['moss', 3],
      ['fern', 2],
    ])
    const freed = freeMonster(s, 'moss').state
    expect(freed.friendships.map((f) => `${f.a}|${f.b}`)).toEqual(['fern|star'])
    expect(friendsOf(freed, 'fern').map((f) => f.id)).toEqual(['star'])
  })
})
