import { describe, expect, it } from 'vitest'
import { LIGHT_DRILLS } from '../../data/drills.ts'
import { makeSave, validateSave } from '../../save/schema.ts'
import { WEEKS_PER_YEAR } from '../calendar.ts'
import { actionMenu, answerRequest, beginWeek, chooseAction, concludeTournament, enterTournament, finishWeek, makeTrialOpponent, needsFoodChoice, react, resolvePendingTechnique, resolveTrial } from '../game.ts'
import { isSiteOpen } from '../journey.ts'
import { marketMonster } from '../market.ts'
import { runBattle, timerTicksFor } from '../battle/engine.ts'
import { createRng } from '../rng.ts'
import { createGameState, type GameState, type WeekAction } from '../state.ts'
import { eventsForWeek, simulatePending } from '../tournament.ts'
import { dateOf } from '../calendar.ts'

/**
 * BUILD_PLAN M5: a scripted player raises a monster for three in-game years, enters every eligible cup on Auto,
 * takes two Journeys with their Trials, and keeps a valid save at the end of every year. The whole loop runs
 * through the same controller the phone uses.
 */

const YEARS = 3

function play(seed: number) {
  const rng = createRng(seed)
  let state: GameState = createGameState({ monster: marketMonster('puddlepup', `gift-${seed}`), breederName: 'Tester', difficulty: 'Standard' })
  const log = { cups: 0, wins: 0, podiums: 0, journeys: 0, trials: 0, promotions: 0, weeks: 0 }
  let light = 0
  let gradeBefore = state.monster!.grade

  while (state.week < YEARS * WEEKS_PER_YEAR && !state.ended) {
    const begun = needsFoodChoice(state) ? beginWeek(state, rng, state.money > 600 ? state.monster!.likes.food : 'turnips') : beginWeek(state, rng)
    state = begun.state
    if (state.pendingRequest) {
      const a = answerRequest(state, true)
      state = a.state
      if (a.forcedAction) state = chooseAction(state, a.forcedAction, rng).state
    }
    // A pending Journey technique with a full list: let it go.
    if (state.journey?.pendingTechnique || state.trial?.pendingTechnique) state = resolvePendingTechnique(state, null)
    // The Trial first, if one is waiting.
    if (state.trial) {
      const wild = makeTrialOpponent(state, rng)!
      const r = runBattle({ monster: state.monster!, control: 'ai', personality: 'Steady' }, { monster: wild, control: 'ai', personality: 'Steady' }, { seed: rng.nextU32(), timerTicks: timerTicksFor(60) })
      state = resolveTrial(state, { winner: r.outcome.winner, how: r.outcome.how }, rng).state
      log.trials += 1
    }
    const menu = actionMenu(state)
    const m = state.monster!
    if (menu.train) {
      const cup = eventsForWeek(state).find((v) => v.eligible && !v.tooEasy)
      const month = dateOf(state.week).month
      if (cup && m.fatigue < 60) {
        state = enterTournament(state, cup.event.id, 'auto')
        state = { ...state, tournament: simulatePending(state.tournament!, true) }
        const done = concludeTournament(state, rng)!
        state = done.state
        log.cups += 1
        if (done.outcome.placing === 1) log.wins += 1
        if (done.outcome.placing <= 3) log.podiums += 1
        if (done.outcome.promoted) log.promotions += 1
      } else if (log.journeys < 2 && state.week >= 10 && state.money >= 2000 && m.fatigue < 40 && isSiteOpen('iron-quarry', month)) {
        state = chooseAction(state, { kind: 'journey', site: 'iron-quarry' }, rng).state
        log.journeys += 1
      } else {
        const action: WeekAction = m.fatigue >= 50 ? { kind: 'rest' } : { kind: 'drill', drill: LIGHT_DRILLS[light++ % LIGHT_DRILLS.length]!.id }
        const acted = chooseAction(state, action, rng)
        state = acted.state
        if (acted.drill) state = react(state, acted.drill.outcome, 'praise')
      }
    } else if (menu.rest) {
      state = chooseAction(state, { kind: 'rest' }, rng).state
    } else {
      state = chooseAction(state, { kind: 'none' }, rng).state
    }
    state = finishWeek(state, rng).state
    log.weeks += 1
    if (state.monster!.grade !== gradeBefore) gradeBefore = state.monster!.grade
    if (state.week % WEEKS_PER_YEAR === 0) {
      const back = validateSave(JSON.parse(JSON.stringify(makeSave(state, rng.getState(), { savedAt: 1, appVersion: 'test' }))))
      expect(back.ok).toBe(true)
      if (back.ok) {
        expect(back.save.game).toEqual(state)
        state = back.save.game
        rng.setState(back.save.rng)
      }
    }
  }
  return { state, log }
}

describe('three years of cups and Journeys through the controller (M5)', () => {
  it('enters cups on Auto, wins some, takes two Journeys with Trials, gets promoted, and keeps a valid save', () => {
    const { state, log } = play(5)
    expect(state.ended).toBeNull()
    expect(log.weeks).toBe(YEARS * WEEKS_PER_YEAR)
    expect(log.cups).toBeGreaterThan(10)
    expect(log.podiums).toBeGreaterThan(3)
    expect(log.journeys).toBe(2)
    expect(log.trials).toBe(2)
    expect(state.journeysBySite['iron-quarry']).toBe(2)
    expect(log.promotions).toBeGreaterThanOrEqual(1)
    expect(state.monster!.grade).not.toBe('E')
    expect(state.breeder.rank).toBeGreaterThanOrEqual(2)
    expect(state.titles).toContain('First Ribbon')
    expect(state.mail.length).toBeGreaterThan(0)
    expect(state.saleMonths).toHaveLength(2)
    expect(state.monster!.records.wins + state.monster!.records.losses + state.monster!.records.draws).toBeGreaterThan(20)
  })

  it('is deterministic for a seed', () => {
    const a = play(11)
    const b = play(11)
    expect(a.state).toEqual(b.state)
  })
})
