import { describe, expect, it } from 'vitest'
import { EVENTS, EVENT_BY_ID, eventsAt, formatSize, isSummitYear } from '../data/calendar.ts'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { DIFFICULTY, TOURNAMENT } from '../data/tuning.ts'
import { TOURNAMENT_GRADES, type TournamentGrade } from '../data/types.ts'
import { WEEKS_PER_YEAR, weekIndexOf } from './calendar.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState, type TournamentState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { applyTooEasy, createTournament, eventsForWeek, finishTournament, isComplete, nextPlayerMatch, playerPlacing, recordMatch, simulatePending, standings } from './tournament.ts'
import { loyaltyOf, totalStats } from './monster.ts'

const at = (year: number, month: number, week: number) => weekIndexOf({ year, month, week })

function gameAt(week: number, grade: TournamentGrade = 'E', over: Partial<Parameters<typeof makeMonster>[0]> = {}): GameState {
  const m = makeMonster({ agePct: 20, ...over })
  m.grade = grade
  const g = createGameState({ monster: m })
  g.week = week
  g.weekPhase = 'action'
  return g
}

describe('the cup calendar (CONTENT §9)', () => {
  it('has at least one event every week for ten years, Officials each season, and the year-parity cups', () => {
    for (let year = 1; year <= 10; year++) {
      for (let w = 0; w < WEEKS_PER_YEAR; w++) {
        const list = eventsAt(w, year)
        expect(list.length, `year ${year} week ${w}`).toBeGreaterThanOrEqual(1)
      }
      for (const w of [11, 23, 35, 47]) expect(eventsAt(w, year).some((e) => e.kind === 'official')).toBe(true)
      const june2 = eventsAt(21, year).map((e) => e.id)
      expect(june2).toEqual(year % 2 === 0 ? ['sprout'] : ['elders'])
      expect(eventsAt(27, year).map((e) => e.id)).toEqual(isSummitYear(year) ? ['summit-qualifier'] : ['heatwave'])
      expect(eventsAt(31, year).map((e) => e.id)).toEqual(isSummitYear(year) ? ['vale-coast-summit'] : ['stargazer'])
    }
    expect(EVENTS.filter((e) => e.kind === 'crown')).toHaveLength(4)
    expect(new Set(EVENTS.map((e) => e.id)).size).toBe(EVENTS.length)
    expect(formatSize('RR6')).toEqual({ participants: 6, playerMatches: 5 })
    expect(formatSize('Elim8')).toEqual({ participants: 8, playerMatches: 3 })
  })
})

describe('entry rules (§13)', () => {
  it('a fresh E monster may enter E and D cups but not C, invitationals or the Rival Showdown', () => {
    const snow = eventsForWeek(gameAt(at(1, 1, 2)))
    expect(snow[0]!.event.id).toBe('snowdrift')
    expect(snow[0]!.eligible).toBe(true)
    const frost = eventsForWeek(gameAt(at(1, 1, 1)))[0]!
    expect(frost.event.id).toBe('frost-fair')
    expect(frost).toMatchObject({ eligible: false, reason: 'gradeTooHigh' })
    const ice = eventsForWeek(gameAt(at(1, 2, 1)))[0]!
    expect(ice).toMatchObject({ eligible: true, tooEasy: false })
    const feb2 = eventsForWeek(gameAt(at(1, 2, 2)))
    expect(feb2.find((v) => v.event.id === 'crown-of-dawn')).toMatchObject({ eligible: false, reason: 'invitation' })
    expect(eventsForWeek(gameAt(at(1, 4, 4))).find((v) => v.event.id === 'wildsong-legend')?.reason).toBe('invitation')
    expect(eventsForWeek(gameAt(at(1, 12, 3)))[0]).toMatchObject({ eligible: false, reason: 'minGrade' })
    expect(eventsForWeek(gameAt(at(1, 10, 1)))[0]!.reason).toBe('invitation') // Masquerade waits for its rumor
  })

  it('"too easy" below your grade, gates by state, rules and technique types', () => {
    const c = eventsForWeek(gameAt(at(1, 1, 2), 'C'))[0]!
    expect(c).toMatchObject({ eligible: true, tooEasy: true })
    const away = gameAt(at(1, 1, 2))
    away.monster!.status.sickWeeks = 1
    expect(eventsForWeek(away)[0]!.reason).toBe('sick')
    const inj = gameAt(at(1, 1, 2))
    inj.monster!.status.injuredWeeks = 2
    expect(eventsForWeek(inj)[0]!.reason).toBe('injured')
    const trav = gameAt(at(1, 1, 2))
    trav.journey = { site: 'iron-quarry', weekNo: 2, successes: 1, learned: null, pendingTechnique: null, gains: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 } }
    expect(eventsForWeek(trav)[0]!.reason).toBe('journey')
    const old = gameAt(at(2, 6, 2))
    old.monster!.ageWeeks = 100
    old.monster!.lifespanTotal = 400
    expect(eventsForWeek(old)[0]).toMatchObject({ eligible: false, reason: 'rule' }) // Sprout Cup, even year, too old
    const hero = gameAt(at(1, 10, 4), 'E', { nature: 30 })
    const rally = eventsForWeek(hero)
    expect(rally.find((v) => v.event.id === 'heros-rally')?.eligible).toBe(true)
    expect(rally.find((v) => v.event.id === 'rogues-rally')?.reason).toBe('rule')
    const iron = gameAt(at(1, 5, 1), 'B')
    iron.monster!.techniques = iron.monster!.techniques.filter((t) => TECHNIQUE_BY_ID[t.id]!.type === 'INT')
    expect(eventsForWeek(iron)[0]).toMatchObject({ eligible: false, reason: 'noTechniques' })
  })
})

describe('building a cup', () => {
  it('fills every format, puts the player first, and is the same for the same week and cup', () => {
    for (const id of ['snowdrift', 'thaw', 'spring-ascension', 'new-year-open', 'rival-showdown']) {
      const e = EVENT_BY_ID[id]!
      const g = gameAt(e.week, id === 'rival-showdown' ? 'C' : 'E')
      const t = createTournament(g, id, 'auto')
      expect(t.participants).toHaveLength(formatSize(e.format).participants)
      expect(t.participants[0]!.player).toBe(true)
      expect(t.participants.slice(1).every((p) => !p.player && p.monster.techniques.length > 0)).toBe(true)
      const again = createTournament(g, id, 'auto')
      expect(again.participants.map((p) => p.monster.id)).toEqual(t.participants.map((p) => p.monster.id))
      expect(again.seed).toBe(t.seed)
    }
    const other = createTournament(gameAt(at(2, 1, 2)), 'snowdrift', 'auto')
    expect(other.seed).not.toBe(createTournament(gameAt(at(1, 1, 2)), 'snowdrift', 'auto').seed)
  })

  it('Corin Hale joins the Officials at your total × 1.05, turns Aggressive from grade A, and brings an Aurelwyrm to the Crowns', () => {
    const g = gameAt(at(1, 3, 4), 'E', { stats: { LIF: 150, POW: 150, INT: 100, SKI: 100, SPD: 100, DEF: 100 } })
    const t = createTournament(g, 'spring-ascension', 'auto')
    const corin = t.participants.find((p) => p.rivalId === 'corin-hale')!
    expect(corin).toBeTruthy()
    expect(corin.habit).toBe('opensFar')
    expect(corin.personality).toBe('Steady')
    expect(totalStats(corin.monster.stats)).toBe(Math.round(700 * 1.05))
    expect(corin.monster.mainBreed).toBe('tumblefox')
    const a = gameAt(at(1, 3, 4), 'A', { stats: { LIF: 400, POW: 400, INT: 400, SKI: 400, SPD: 400, DEF: 400 } })
    expect(createTournament(a, 'spring-ascension', 'auto').participants.find((p) => p.rivalId === 'corin-hale')!.personality).toBe('Aggressive')
    const s = gameAt(at(1, 2, 2), 'S', { stats: { LIF: 500, POW: 500, INT: 500, SKI: 500, SPD: 500, DEF: 500 } })
    s.guild.crownInvite = true
    const crown = createTournament(s, 'crown-of-dawn', 'auto')
    expect(crown.participants.find((p) => p.rivalId === 'corin-hale')!.monster.mainBreed).toBe('aurelwyrm')
    expect(crown.participants.slice(1).every((p) => totalStats(p.monster.stats) >= 2900)).toBe(true)
  })

  it('round robin matches, elimination rounds, KO withdrawal and the tiebreaks', () => {
    const g = gameAt(at(1, 2, 3)) // Thaw Cup, RR4
    let t = createTournament(g, 'thaw', 'manual')
    expect(t.matches).toHaveLength(6)
    expect(nextPlayerMatch(t)!.index).toBe(0)
    // Player wins by KO, then all other results by hand: a three-way tie decided by head-to-head.
    const res = (w: 0 | 1 | null, how: 'ko' | 'time' = 'time', hp: [number, number] = [500, 400]) => ({ winner: w, how, hpPct: hp })
    t = recordMatch(t, 0, res(0, 'ko', [800, 0])) // 0 beats 1 by KO → 1 withdraws
    expect(t.koOut).toEqual([1])
    expect(t.matches.filter((m) => (m.a === 1 || m.b === 1) && m.result?.how === 'walkover')).toHaveLength(2)
    const pm = nextPlayerMatch(t)!
    expect(pm.match.a === 0 || pm.match.b === 0).toBe(true)
    t = recordMatch(t, pm.index, res(1)) // player loses to 2
    const pm2 = nextPlayerMatch(t)!
    t = recordMatch(t, pm2.index, res(0)) // player beats 3
    const rest = t.matches.findIndex((m) => m.result === null)
    expect(rest).toBeGreaterThanOrEqual(0)
    t = recordMatch(t, rest, res(1)) // 2 vs 3: 3 wins
    expect(isComplete(t)).toBe(true)
    const table = standings(t)
    expect(table[0]!.index).toBe(0) // 4 (KO win) + 0 + 3 = 7; 2 and 3 have a walkover (3) + a win (3) = 6 each
    expect(table[0]!.points).toBe(7)
    expect(table.find((s) => s.index === 2)!.points).toBe(6)
    expect(table.find((s) => s.index === 3)!.points).toBe(6)
    expect(table.find((s) => s.index === 3)!.place).toBe(2) // head-to-head: 3 beat 2
    expect(table.find((s) => s.index === 1)!.place).toBe(4)
    expect(nextPlayerMatch(t)).toBeNull()

    let e = createTournament(gameAt(at(1, 1, 2)), 'snowdrift', 'manual') // Elim4
    expect(e.matches).toHaveLength(2)
    expect(e.matches.every((m) => m.round === 1)).toBe(true)
    e = recordMatch(e, 0, res(e.matches[0]!.a === 0 ? 0 : 1))
    e = recordMatch(e, 1, res(0))
    expect(e.matches).toHaveLength(3)
    expect(e.matches[2]!.round).toBe(2)
    expect(e.matches[2]!.a === 0 || e.matches[2]!.b === 0).toBe(true)
    e = recordMatch(e, 2, res(e.matches[2]!.a === 0 ? 0 : 1, 'ko', [700, 0]))
    expect(isComplete(e)).toBe(true)
    expect(playerPlacing(e)).toBe(1)
    const places = standings(e).map((s) => s.place).sort()
    expect(places).toEqual([1, 2, 3, 3])
  })

  it('simulates the matches without the player and completes an Elim8 bracket', () => {
    const g = gameAt(at(1, 1, 4))
    let t = createTournament(g, 'new-year-open', 'auto')
    t = simulatePending(t, true)
    expect(isComplete(t)).toBe(true)
    expect(t.matches).toHaveLength(7)
    const places = standings(t).map((s) => s.place).sort((a, b) => a - b)
    expect(places).toEqual([1, 2, 3, 3, 5, 5, 5, 5])
  })
})

describe('finishing a cup (§13 prizes, fame, growth, after-effects, promotion, rank)', () => {
  function winAll(t: TournamentState, how: 'ko' | 'time' = 'time'): TournamentState {
    let cur = t
    for (let guard = 0; guard < 20; guard++) {
      const pm = nextPlayerMatch(cur)
      if (!pm) break
      cur = recordMatch(cur, pm.index, { winner: pm.match.a === 0 ? 0 : 1, how, hpPct: pm.match.a === 0 ? [900, 100] : [100, 900] }, { 'puddlepup.splash-nip': 2 })
    }
    return simulatePending(cur)
  }

  it('first place: the purse, match bonuses, three sweets, fame, three stat gains, after-effects, records and First Ribbon', () => {
    const g = gameAt(at(1, 2, 3)) // Thaw Cup E RR4 1,000
    g.tournament = winAll(createTournament(g, 'thaw', 'auto'))
    const before = structuredClone(g.monster!)
    const { state, outcome } = finishTournament(g, createRng(1))
    expect(outcome.placing).toBe(1)
    expect(outcome.purse).toBe(1000)
    expect(outcome.perWinGold).toBe(TOURNAMENT.perWinGoldPerGrade * 1 * 3)
    expect(state.money).toBe(g.money + 1000 + 150)
    expect(outcome.items.reduce((s, i) => s + i.qty, 0)).toBe(3)
    expect(outcome.fame).toBe(TOURNAMENT.fame.cupWin.E)
    expect(Object.keys(outcome.growth)).toHaveLength(3)
    for (const v of Object.values(outcome.growth)) expect(v).toBeGreaterThanOrEqual(1)
    expect(outcome.fatigue).toBe(25)
    expect(outcome.stress).toBe(-35)
    expect(outcome.lifespan).toBe(-1)
    expect(state.monster!.fatigue).toBe(Math.min(100, before.fatigue + 25))
    expect(state.monster!.lifespanTotal).toBe(before.lifespanTotal - 1)
    expect(state.monster!.records).toMatchObject({ wins: 3, losses: 0, cupsWon: 1, earnings: 1150 })
    expect(state.monster!.techniques.find((t) => t.id === 'puddlepup.splash-nip')!.uses).toBe(6)
    expect(outcome.titles).toEqual(['First Ribbon'])
    expect(state.titles).toEqual(['First Ribbon'])
    expect(state.tournament).toBeNull()
    expect(outcome.promoted).toBeNull()
  })

  it('a KO loss and last place: no purse, −1 fame, extra fatigue and lifespan, an injury roll; Gentle never injures', () => {
    const g = gameAt(at(1, 2, 3))
    g.monster!.fame = 10
    let t = createTournament(g, 'thaw', 'auto')
    const pm = nextPlayerMatch(t)!
    t = recordMatch(t, pm.index, { winner: pm.match.a === 0 ? 1 : 0, how: 'ko', hpPct: pm.match.a === 0 ? [0, 800] : [800, 0] })
    g.tournament = simulatePending(t)
    let injuries = 0
    for (let seed = 0; seed < 40; seed++) {
      const { state, outcome } = finishTournament(g, createRng(seed))
      expect(outcome.koed).toBe(true)
      expect(outcome.purse).toBe(0)
      expect(outcome.fame).toBe(-1)
      expect(outcome.fatigue).toBe(38 + 10)
      expect(outcome.lifespan).toBeLessThanOrEqual(-3)
      if (outcome.injuredWeeks > 0) {
        injuries++
        expect(state.monster!.status.injuredWeeks).toBe(outcome.injuredWeeks)
        expect(outcome.lifespan).toBe(-5)
      }
    }
    expect(injuries).toBeGreaterThan(0)
    const gentle = { ...structuredClone(g), difficulty: 'Gentle' as const }
    for (let seed = 0; seed < 20; seed++) expect(finishTournament(gentle, createRng(seed)).outcome.injuredWeeks).toBe(0)
  })

  it('winning your Official promotes, raises rank, pays a Wondercake and Ascended; the S Official invites to the Crowns', () => {
    const g = gameAt(at(1, 3, 4))
    g.tournament = winAll(createTournament(g, 'spring-ascension', 'auto'))
    const { state, outcome } = finishTournament(g, createRng(2))
    expect(outcome.placing).toBe(1)
    expect(outcome.purse).toBe(TOURNAMENT.officialPursePerGrade)
    expect(outcome.promoted).toBe('D')
    expect(state.monster!.grade).toBe('D')
    expect(state.monster!.records.highestGrade).toBe('D')
    expect(state.guild.officialsWon).toEqual(['E'])
    expect(outcome.rankAfter).toBe(2)
    expect(outcome.items).toEqual([{ id: 'wondercake', qty: 1 }])
    expect(outcome.titles).toEqual(['Ascended'])
    expect(outcome.fame).toBe(TOURNAMENT.fame.officialWin.E)
    expect(state.mail.some((m) => m.kind === 'promotion' && m.ref === 'D')).toBe(true)
    expect(state.mail.some((m) => m.kind === 'rank' && m.ref === '2')).toBe(true)

    // Climb the ladder: every Official E–A → rank 6; the S Official → Crown invitation and S-Class Breeder.
    let s = state
    for (const grade of ['D', 'C', 'B', 'A', 'S'] as const) {
      s.monster!.grade = grade
      s.week = at(2, 3, 4)
      s.tournament = winAll(createTournament(s, 'spring-ascension', 'auto'))
      s = finishTournament(s, createRng(3)).state
    }
    expect(s.guild.officialsWon).toEqual(['E', 'D', 'C', 'B', 'A', 'S'])
    expect(s.breeder.rank).toBe(6)
    expect(s.guild.crownInvite).toBe(true)
    expect(s.titles).toContain('S-Class Breeder')
    expect(s.monster!.grade).toBe('S')

    // Four Crowns → rank 10, Grand Breeder, the Legend invitation; the Legend win → Hall of Fame.
    for (const id of ['crown-of-dawn', 'crown-of-tides', 'crown-of-embers', 'crown-of-frost']) {
      s.week = EVENT_BY_ID[id]!.week + WEEKS_PER_YEAR * 2
      s.tournament = winAll(createTournament(s, id, 'auto'))
      s = finishTournament(s, createRng(4)).state
    }
    expect(s.guild.crownsWon).toEqual(['dawn', 'tides', 'embers', 'frost'])
    expect(s.breeder.rank).toBe(10)
    expect(s.titles).toContain('Four Crowns')
    expect(s.titles).toContain('Grand Breeder')
    expect(s.guild.legendInvite).toBe(true)
    expect(s.monster!.records.crownsWon).toBe(4)
    expect(s.songbook.some((id) => TECHNIQUE_BY_ID[id]!.family === 'Signature')).toBe(true)
    s.week = at(4, 4, 4)
    expect(eventsForWeek(s).find((v) => v.event.id === 'wildsong-legend')?.eligible).toBe(true)
    s.tournament = winAll(createTournament(s, 'wildsong-legend', 'auto'))
    const legend = finishTournament(s, createRng(5))
    expect(legend.outcome.hallOfFame).toBe(true)
    expect(legend.state.hallOfFame).toHaveLength(1)
    expect(legend.state.titles).toContain('Legend of the Vale')
    expect(legend.outcome.items).toEqual([{ id: 'tempo-bell', qty: 1 }, { id: 'wondercake', qty: 3 }])
  })

  it('Gentle pays ×1.25 and the "too easy" entry costs fame and loyalty', () => {
    const g = gameAt(at(1, 2, 3), 'C')
    g.difficulty = 'Gentle'
    g.tournament = winAll(createTournament(g, 'thaw', 'auto'))
    const { outcome } = finishTournament(g, createRng(1))
    expect(outcome.purse).toBe(Math.round((1000 * DIFFICULTY.Gentle.prizeMulPct) / 100))
    expect(TOURNAMENT_GRADES.indexOf('C')).toBe(2)
    const m = makeMonster({ spoil: 40, fear: 40 })
    m.fame = 10
    const entered = createGameState({ monster: m })
    const after = applyTooEasy(entered)
    expect(after.monster!.fame).toBe(8)
    expect(loyaltyOf(after.monster!)).toBe(38)
  })
})
