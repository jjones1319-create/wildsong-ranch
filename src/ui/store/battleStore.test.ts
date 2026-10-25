import { describe, expect, it } from 'vitest'
import { createTournament, nextPlayerMatch, playerMatchSetup, skipPlayerMatch } from '../../core/tournament.ts'
import { createGameState } from '../../core/state.ts'
import { makeMonster } from '../../core/test-helpers.ts'
import { EVENT_BY_ID } from '../../data/calendar.ts'
import { TOURNAMENT } from '../../data/tuning.ts'
import { finishedResult, leaveBattle, skipToEnd, startBattle } from './battleStore.ts'

/**
 * §12.11 through the battle screen's own store: a cup match started on Auto (the engine flag as a recorded input
 * at tick 1) and run untouched ends exactly like Skip on the same seed.
 */
describe('the battle store: Auto start equals Skip', () => {
  for (const id of ['spring-ascension', 'snowdrift', 'rival-showdown']) {
    it(id, () => {
      const e = EVENT_BY_ID[id]!
      const m = makeMonster({ agePct: 30, stats: { LIF: 400, POW: 350, INT: 300, SKI: 300, SPD: 300, DEF: 300 } })
      m.grade = 'C'
      const g = createGameState({ monster: m })
      g.week = e.week
      const t = createTournament(g, id, 'auto')
      const pm = nextPlayerMatch(t)!
      const s = playerMatchSetup(t, pm.index, 'balanced')
      startBattle({ a: s.player.monster, b: s.opponent.monster, aControl: 'player', personalityA: 'Steady', personalityB: 'Steady', tierA: 'expert', tierB: s.opponent.tier, timerSec: TOURNAMENT.matchSeconds, origin: 'tournamentPlay', setups: { a: s.player, b: s.opponent }, seed: s.options.seed, autoStart: true })
      skipToEnd()
      const r = finishedResult()!
      leaveBattle()
      const skipped = skipPlayerMatch(t, pm.index, 'balanced').matches[pm.index]!.result!
      const fromScreen = s.playerIsA ? r.hpPct : ([r.hpPct[1], r.hpPct[0]] as [number, number])
      expect({ how: r.how, hpPct: fromScreen, ticks: r.ticks }).toEqual({ how: skipped.how, hpPct: skipped.hpPct, ticks: skipped.ticks })
    })
  }
})
