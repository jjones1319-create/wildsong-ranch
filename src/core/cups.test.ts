import { describe, expect, it } from 'vitest'
import { EVENTS, EVENT_BY_ID } from '../data/calendar.ts'
import { CORIN } from '../data/rivals.ts'
import type { AutoStyle, TournamentEvent, TournamentGrade } from '../data/types.ts'
import { migrate, SAVE_VERSION } from '../save/migrate.ts'
import { makeSave, validateSave } from '../save/schema.ts'
import { createBattle, step } from './battle/engine.ts'
import type { Battle } from './battle/engine.ts'
import type { BattleInput } from './battle/types.ts'
import { trialOpponent } from './journey.ts'
import { totalStats } from './monster.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState, type MatchRecord, type TournamentState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import {
  autoStartInput,
  bossIndex,
  bracket,
  createTournament,
  currentRound,
  finishTournament,
  isComplete,
  matchSetup,
  nextPlayerMatch,
  placeChanges,
  playerFighter,
  playerMatchResult,
  playerMatchSetup,
  recordMatch,
  relayLegs,
  roundCount,
  simulatePending,
  simulateRelay,
  simulateRound,
  skipPlayerMatch,
  standings,
  trialTier,
} from './tournament.ts'

/**
 * "Playable events + round-by-round cups": the circle-method schedule, standings after each round, the cup only
 * ever played up to the current round, the player's side always under the player's control (Auto is the engine's
 * flag), Skip equal to an untouched Auto run, exact replays, and cups saved by older versions.
 */

function gameFor(event: TournamentEvent, grade: TournamentGrade = 'E'): GameState {
  const m = makeMonster({ agePct: 30, stats: { LIF: 400, POW: 350, INT: 300, SKI: 300, SPD: 300, DEF: 300 } })
  m.grade = grade
  const g = createGameState({ monster: m })
  g.week = event.week
  g.weekPhase = 'action'
  return g
}

/** The grade a monster needs to be in an event at all (the tests don't check eligibility, only playability). */
function gradeFor(e: TournamentEvent): TournamentGrade {
  if (e.kind === 'crown' || e.kind === 'legend') return 'S'
  if (e.minGrade) return e.minGrade
  if (e.grade !== 'own' && e.grade !== 'any') return e.grade
  return 'C'
}

function cup(eventId: string, grade?: TournamentGrade): TournamentState {
  const e = EVENT_BY_ID[eventId]!
  return createTournament(gameFor(e, grade ?? gradeFor(e)), eventId, 'auto')
}

/** Runs a battle the way the battle screen does: inputs stamped on the next tick, until it ends. */
function playOut(battle: Battle, inputsByTick: Map<number, BattleInput[]> = new Map()): void {
  for (let guard = 0; guard < 4000 && !battle.state.outcome; guard++) step(battle, inputsByTick.get(battle.state.tick + 1) ?? [])
}

const pairKey = (m: MatchRecord) => `${Math.min(m.a, m.b)}-${Math.max(m.a, m.b)}`

describe('the round robin schedule (circle method)', () => {
  for (const [eventId, n] of [
    ['thaw', 4],
    ['spring-ascension', 6],
    ['heros-rally', 6],
    ['frost-fair', 4],
  ] as const) {
    it(`${eventId}: every pair once, everyone once per round, the player in every round, ${n - 1} rounds`, () => {
      const t = cup(eventId)
      expect(t.participants).toHaveLength(n)
      expect(t.matches).toHaveLength((n * (n - 1)) / 2)
      expect(new Set(t.matches.map(pairKey)).size).toBe(t.matches.length)
      expect(roundCount(t)).toBe(n - 1)
      for (let r = 1; r <= n - 1; r++) {
        const inRound = t.matches.filter((m) => m.round === r)
        expect(inRound).toHaveLength(n / 2)
        const who = inRound.flatMap((m) => [m.a, m.b]).sort((x, y) => x - y)
        expect(who).toEqual(Array.from({ length: n }, (_, i) => i))
        // The player's match is listed first, with the player as side a.
        expect(inRound[0]!.a).toBe(0)
      }
      // Rounds are stored in order, so the match index follows the round.
      expect(t.matches.map((m) => m.round)).toEqual([...t.matches.map((m) => m.round)].sort((x, y) => x - y))
    })
  }

  it('is the same for the same seed and differs between cups', () => {
    const a = cup('spring-ascension')
    const b = cup('spring-ascension')
    expect(b.matches).toEqual(a.matches)
    const other = createTournament(gameFor(EVENT_BY_ID['spring-ascension']!, 'C'), 'summer-ascension', 'auto')
    expect(other.seed).not.toBe(a.seed)
  })

  it('puts Corin in the player’s last round in the Officials, and otherwise the strongest opponent', () => {
    for (const id of ['spring-ascension', 'summer-ascension', 'autumn-ascension', 'winter-ascension']) {
      for (const grade of ['E', 'C', 'A'] as const) {
        const t = cup(id, grade)
        const corin = t.participants.findIndex((p) => p.rivalId === CORIN.id)
        expect(corin).toBeGreaterThan(0)
        expect(bossIndex(t.participants)).toBe(corin)
        const last = t.matches.filter((m) => m.round === roundCount(t))
        expect(last.some((m) => m.a === 0 && m.b === corin)).toBe(true)
      }
    }
    const t = cup('thaw')
    expect(t.participants.some((p) => p.rivalId === CORIN.id)).toBe(false)
    const totals = t.participants.map((p) => totalStats(p.monster.stats))
    const strongest = totals.slice(1).indexOf(Math.max(...totals.slice(1))) + 1
    expect(bossIndex(t.participants)).toBe(strongest)
    expect(t.matches.filter((m) => m.round === 3).some((m) => m.a === 0 && m.b === strongest)).toBe(true)
  })

  it('leaves elimination brackets and single matches as they were', () => {
    const e = cup('snowdrift')
    expect(e.matches.every((m) => m.round === 1)).toBe(true)
    expect(roundCount(e)).toBe(2)
    expect(roundCount(cup('new-year-open'))).toBe(3)
    expect(cup('masquerade', 'B').matches).toEqual([{ round: 1, a: 0, b: 1, result: null }])
  })
})

describe('round by round', () => {
  it('never simulates a match ahead of the current round', () => {
    let t = cup('spring-ascension')
    expect(currentRound(t)).toBe(1)
    // The player's round-1 match is pending: the others in round 1 may resolve, nothing in round 2+.
    t = simulatePending(t)
    expect(t.matches.filter((m) => m.round > 1).every((m) => m.result === null)).toBe(true)
    expect(t.matches.filter((m) => m.round === 1 && m.a !== 0).every((m) => m.result !== null)).toBe(true)
    // simulateRound touches only its own round, and never the player's match.
    const fresh = cup('spring-ascension')
    const r2 = simulateRound(fresh, 2)
    r2.matches.forEach((m, i) => {
      if (m.round === 2 && m.a !== 0) expect(m.result).not.toBeNull()
      else expect(m.result).toEqual(fresh.matches[i]!.result)
    })
    // Playing round by round: after each round, later rounds are still untouched.
    let c = cup('spring-ascension')
    for (let r = 1; r <= 5; r++) {
      expect(currentRound(c)).toBe(r)
      const pm = nextPlayerMatch(c)!
      expect(pm.match.round).toBe(r)
      c = simulateRound(skipPlayerMatch(c, pm.index, 'balanced'), r)
      expect(c.matches.filter((m) => m.round > r).every((m) => m.result === null || m.result.how === 'walkover')).toBe(true)
      expect(c.matches.filter((m) => m.round <= r).every((m) => m.result !== null)).toBe(true)
    }
    expect(isComplete(c)).toBe(true)
  })

  it('standings after round r count only rounds up to r, with place changes', () => {
    let t = cup('spring-ascension')
    for (let r = 1; r <= 5; r++) {
      const pm = nextPlayerMatch(t)
      if (pm) t = skipPlayerMatch(t, pm.index, 'balanced')
      t = simulateRound(t, r)
    }
    for (let r = 1; r <= 5; r++) {
      const rows = standings(t, r)
      const played = t.matches.filter((m) => m.round <= r && m.result)
      expect(rows.reduce((s, x) => s + x.wins + x.losses + x.draws, 0)).toBe(played.length * 2)
      // Each participant has played at most r matches by round r.
      for (const row of rows) expect(row.wins + row.losses + row.draws).toBeLessThanOrEqual(r)
      expect(rows.map((x) => x.place)).toEqual([1, 2, 3, 4, 5, 6])
    }
    expect(standings(t, 5)).toEqual(standings(t))
    expect(placeChanges(t, 1).size).toBe(0)
    const ch = placeChanges(t, 3)
    const before = standings(t, 2)
    for (const row of standings(t, 3)) expect(ch.get(row.index)).toBe(before.find((x) => x.index === row.index)!.place - row.place)
  })

  it('a KO’d player sits out the rest; the remaining rounds still play one at a time', () => {
    let t = cup('spring-ascension')
    const pm = nextPlayerMatch(t)!
    t = recordMatch(t, pm.index, { winner: 1, how: 'ko', hpPct: [0, 700], ticks: 400 })
    expect(nextPlayerMatch(t)).toBeNull()
    expect(t.matches.filter((m) => m.a === 0 && m.round > 1).every((m) => m.result?.how === 'walkover')).toBe(true)
    t = simulateRound(t, 1)
    expect(currentRound(t)).toBe(2)
    t = simulateRound(t, 2)
    expect(currentRound(t)).toBe(3)
    expect(t.matches.filter((m) => m.round > 2 && m.a !== 0).every((m) => m.result === null)).toBe(true)
    t = simulatePending(t)
    expect(isComplete(t)).toBe(true)
  })

  it('the elimination bracket shows future slots as the winners of their feeders', () => {
    let t = cup('new-year-open', 'C')
    let tree = bracket(t)
    expect(tree.map((r) => r.length)).toEqual([4, 2, 1])
    expect(tree[1]![0]!.a).toEqual({ kind: 'winnerOf', round: 1, slot: 0 })
    expect(tree[2]![0]!.b).toEqual({ kind: 'winnerOf', round: 2, slot: 1 })
    // One quarter-final decided: its winner moves into the semi-final slot before the semi exists.
    t = simulateRound(t, 1)
    tree = bracket(t)
    const qf = t.matches.filter((m) => m.round === 1)
    expect(qf.slice(1).every((m) => m.result !== null)).toBe(true)
    expect(tree[1]![1]!.a.kind).toBe('p')
    t = simulatePending(t, true)
    expect(isComplete(t)).toBe(true)
    expect(bracket(t).every((r) => r.every((s) => s.match !== null))).toBe(true)
  })

  it('the Summit shows its five legs, and the NPC legs agree with the count stored at entry', () => {
    const e = EVENT_BY_ID['vale-coast-summit']!
    for (const grade of ['D', 'B', 'S'] as const) {
      const t = createTournament(gameFor(e, grade), e.id, 'auto')
      const legs = relayLegs(t, grade)
      expect(legs.map((l) => l.grade)).toEqual(['D', 'C', 'B', 'A', 'S'])
      expect(legs.filter((l) => l.player).map((l) => l.grade)).toEqual([grade])
      expect(legs.filter((l) => !l.player).every((l) => l.result !== null && l.vale && l.coast)).toBe(true)
      expect(legs.filter((l) => !l.player && l.result!.winner === 0)).toHaveLength(simulateRelay(t, grade))
      expect(relayLegs(t, grade)).toEqual(legs)
    }
  })
})

describe('the player’s side: Fight, Auto (take over any time), Skip', () => {
  const kinds = [...new Set(EVENTS.map((e) => e.kind))]

  it('covers every event kind in the calendar', () => {
    expect(kinds.sort()).toEqual(['crown', 'cup', 'legend', 'masquerade', 'official', 'open', 'rival', 'summit', 'summitQualifier'])
  })

  for (const kind of kinds) {
    it(`${kind}: a match started on Auto can be taken over and handed back`, () => {
      const e = EVENTS.find((x) => x.kind === kind)!
      const t = cup(e.id)
      const pm = nextPlayerMatch(t)!
      const style: AutoStyle = 'aggressive'
      const s = playerMatchSetup(t, pm.index, style)
      expect(s.player).toMatchObject({ control: 'player', tier: 'expert', style })
      const battle = createBattle(s.player, s.opponent, s.options)
      step(battle, [autoStartInput(style)])
      const me = battle.state.fighters[0]
      expect(me.control).toBe('player')
      expect(me.auto).toBe(true)
      expect(me.style).toBe(style)
      for (let i = 0; i < 40; i++) step(battle)
      // Take over: Auto off, then the pads work.
      step(battle, [{ tick: battle.state.tick + 1, side: 0, action: { kind: 'auto', on: false } }])
      expect(me.auto).toBe(false)
      step(battle, [{ tick: battle.state.tick + 1, side: 0, action: { kind: 'move', dir: -1 } }])
      expect(me.moveDir).toBe(-1)
      // Hand back: Auto on again, and the brain plans for side 0 again.
      step(battle, [{ tick: battle.state.tick + 1, side: 0, action: { kind: 'auto', on: true, style } }])
      expect(me.auto).toBe(true)
      expect(battle.state.log.some((x) => x.kind === 'plan' && x.side === 0)).toBe(true)
      // While Auto is on, the pads are ignored: the same battle with and without a stray tap ends identically.
      const run = (stray: boolean) => {
        const b2 = createBattle(s.player, s.opponent, s.options)
        const inputs = new Map<number, BattleInput[]>([[1, [autoStartInput(style)]]])
        if (stray) inputs.set(30, [{ tick: 30, side: 0, action: { kind: 'move', dir: 1 } }, { tick: 30, side: 0, action: { kind: 'dash' } }])
        playOut(b2, inputs)
        return b2.state.outcome
      }
      expect(run(true)).toEqual(run(false))
    })
  }

  it('the Journey Trial: Auto is the same takeover-able flag', () => {
    const m = makeMonster({ agePct: 50, stats: { POW: 400, LIF: 300 } })
    m.grade = 'C'
    const wild = trialOpponent(m, 'iron-quarry', createRng(3))
    const battle = createBattle(playerFighter(m, 'balanced'), { monster: wild, control: 'ai', personality: 'Steady', tier: trialTier(wild.grade) }, { seed: 77, timerTicks: 1800 })
    step(battle, [autoStartInput('balanced')])
    expect(battle.state.fighters[0].auto).toBe(true)
    step(battle, [{ tick: 2, side: 0, action: { kind: 'auto', on: false } }])
    expect(battle.state.fighters[0].auto).toBe(false)
    step(battle, [{ tick: 3, side: 0, action: { kind: 'auto', on: true } }])
    expect(battle.state.fighters[0].auto).toBe(true)
  })

  for (const id of ['thaw', 'spring-ascension', 'snowdrift', 'masquerade', 'vale-coast-summit', 'crown-of-dawn']) {
    it(`${id}: Skip gives exactly the result of an untouched Auto run on the same seed`, () => {
      const t = cup(id)
      const pm = nextPlayerMatch(t)!
      for (const style of ['balanced', 'defensive'] as const) {
        const skipped = skipPlayerMatch(t, pm.index, style)
        const s = playerMatchSetup(t, pm.index, style)
        const battle = createBattle(s.player, s.opponent, s.options)
        playOut(battle, new Map([[1, [autoStartInput(style)]]]))
        const watched = recordMatch(t, pm.index, playerMatchResult(battle.state.outcome!, s.playerIsA), battle.state.fighters[0].techUses)
        expect(skipped.matches[pm.index]!.result).toEqual(watched.matches[pm.index]!.result)
        expect(skipped.playerTechUses).toEqual(watched.playerTechUses)
        expect(skipped.matches[pm.index]!.result!.ticks).toBeGreaterThan(0)
      }
    })
  }

  it('a recorded NPC match replays exactly (the Watch button)', () => {
    let t = cup('spring-ascension')
    t = simulateRound(t, 1)
    const npc = t.matches.map((m, i) => ({ m, i })).filter((x) => x.m.round === 1 && x.m.a !== 0)
    expect(npc.length).toBe(2)
    for (const { m, i } of npc) {
      const s = matchSetup(t, i)
      const battle = createBattle(s.a, s.b, s.options)
      playOut(battle)
      const o = battle.state.outcome!
      expect({ winner: o.winner, how: o.how, hpPct: o.hpPct, ticks: o.ticks }).toEqual(m.result)
    }
  })
})

describe('cups saved by older versions', () => {
  /** The pre-v9 schedule: one round per pairing, the player's matches first. */
  function legacySchedule(n: number): MatchRecord[] {
    const out: MatchRecord[] = []
    let round = 1
    for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) out.push({ round: round++, a, b, result: null })
    return out
  }

  function v8SaveWith(t: TournamentState): unknown {
    const e = EVENT_BY_ID[t.eventId]!
    const g = gameFor(e, t.participants[0]!.monster.grade)
    g.tournament = t
    const raw = JSON.parse(JSON.stringify(makeSave(g, 5))) as { schemaVersion: number; game: { tournament: { matches: { result: { ticks?: number } | null }[] } } }
    raw.schemaVersion = 8
    // v8 results had no length.
    for (const m of raw.game.tournament.matches) if (m.result) delete m.result.ticks
    return raw
  }

  it('an RR6 Official in progress with the old schedule and mode auto loads and still finishes', () => {
    let t = cup('spring-ascension')
    t = { ...t, mode: 'auto', matches: legacySchedule(6) }
    t = recordMatch(t, 0, { winner: 0, how: 'time', hpPct: [600, 300] })
    const up = migrate(v8SaveWith(t))
    expect((up as { schemaVersion: number }).schemaVersion).toBe(SAVE_VERSION)
    const r = validateSave(up)
    expect(r.ok).toBe(true)
    if (!r.ok) return
    let loaded = r.save.game.tournament!
    expect(loaded.mode).toBe('auto')
    expect(loaded.matches.map((m) => m.round)).toEqual(Array.from({ length: 15 }, (_, i) => i + 1))
    expect(loaded.matches[0]!.result).toEqual({ winner: 0, how: 'time', hpPct: [600, 300] })
    expect(roundCount(loaded)).toBe(15)
    // The round-by-round flow drives it to the end: the player's four remaining matches, then the others.
    for (let guard = 0; guard < 40 && !isComplete(loaded); guard++) {
      const round = currentRound(loaded)!
      const pm = nextPlayerMatch(loaded)
      if (pm && pm.match.round === round) loaded = skipPlayerMatch(loaded, pm.index, 'balanced')
      loaded = simulateRound(loaded, round)
    }
    expect(isComplete(loaded)).toBe(true)
    expect(loaded.matches.filter((m) => m.a === 0).every((m) => m.result !== null)).toBe(true)
    const g = r.save.game
    g.tournament = loaded
    const { outcome } = finishTournament(g, createRng(1))
    expect(outcome.playerMatches).toBe(5)
    expect(outcome.participants).toBe(6)
  })

  it('an RR4 cup saved after the player’s last match finishes with Skip to final standings', () => {
    let t = cup('thaw')
    t = { ...t, matches: legacySchedule(4) }
    for (const i of [0, 1, 2]) t = recordMatch(t, i, { winner: 1, how: 'time', hpPct: [200, 500] })
    const r = validateSave(migrate(v8SaveWith(t)))
    expect(r.ok).toBe(true)
    if (!r.ok) return
    const loaded = r.save.game.tournament!
    expect(nextPlayerMatch(loaded)).toBeNull()
    const done = simulatePending(loaded)
    expect(isComplete(done)).toBe(true)
    expect(standings(done).find((s) => s.index === 0)!.losses).toBe(3)
  })

  it('a v8 save with a finished cup match keeps its results; old results simply have no time', () => {
    let t = cup('snowdrift')
    t = recordMatch(t, 0, { winner: 0, how: 'ko', hpPct: [500, 0] })
    const r = validateSave(migrate(v8SaveWith(t)))
    expect(r.ok && r.save.game.tournament!.matches[0]!.result).toEqual({ winner: 0, how: 'ko', hpPct: [500, 0] })
  })

  it('a v9 result keeps its time through a save and a load', () => {
    let t = cup('thaw')
    t = skipPlayerMatch(t, 0, 'balanced')
    const g = gameFor(EVENT_BY_ID.thaw!, 'E')
    g.tournament = t
    const r = validateSave(JSON.parse(JSON.stringify(makeSave(g, 1))))
    expect(r.ok && r.save.game.tournament!.matches[0]!.result!.ticks).toBe(t.matches[0]!.result!.ticks)
  })
})
