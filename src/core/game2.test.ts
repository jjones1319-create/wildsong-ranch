import { describe, expect, it } from 'vitest'
import { signatureOf } from '../data/techniques.ts'
import { WEEKS_PER_YEAR, weekIndexOf } from './calendar.ts'
import { actionMenu, beginWeek, chooseAction, concludeTournament, enterTournament, finishWeek, makeTrialOpponent, readMail, resolvePendingTechnique, resolveTrial } from './game.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { simulatePending } from './tournament.ts'
import { firstWeekOfStage } from './presets.ts'

/** M5 additions to the turn controller: cups, the Trial, mail, sale months and the Signature at Prime. */
describe('the controller and the Guild (M5)', () => {
  it('rolls the sale months in January, mails the sale in week 1 of a sale month, and marks mail read', () => {
    const rng = createRng(3)
    const state = createGameState({ monster: makeMonster() })
    const r = beginWeek(state, rng, 'turnips')
    expect(r.state.saleMonths).toHaveLength(2)
    const saleMonth = r.state.saleMonths[0]!
    if (saleMonth === 1) {
      expect(r.state.mail.some((m) => m.kind === 'sale')).toBe(true)
    }
    // Jump to the first sale month and begin its first week.
    const later = structuredClone(r.state)
    later.week = weekIndexOf({ year: 1, month: saleMonth, week: 1 })
    later.weekPhase = 'start'
    const r2 = beginWeek(later, createRng(4))
    const mail = r2.state.mail.find((m) => m.kind === 'sale' && m.ref === String(saleMonth))
    expect(mail).toBeTruthy()
    expect(r2.events.some((e) => e.kind === 'sale')).toBe(true)
    const read = readMail(r2.state, mail!.id)
    expect(read.mail.find((m) => m.id === mail!.id)!.read).toBe(true)
    expect(readMail(read, mail!.id)).toBe(read)
  })

  it('enters a cup as the week’s action, blocks the menu, and concludes it', () => {
    const state = createGameState({ monster: makeMonster({ agePct: 20 }) })
    state.week = weekIndexOf({ year: 1, month: 1, week: 2 }) // Snowdrift Cup, E
    const begun = beginWeek(state, createRng(1)).state
    const entered = enterTournament(begun, 'snowdrift', 'auto')
    expect(entered.tournament?.eventId).toBe('snowdrift')
    expect(actionMenu(entered)).toMatchObject({ train: false, rest: false, reason: 'tournament' })
    expect(enterTournament(entered, 'snowdrift', 'auto')).toBe(entered) // already in one
    entered.tournament = simulatePending(entered.tournament!, true)
    const done = concludeTournament(entered, createRng(2))!
    expect(done.state.tournament).toBeNull()
    expect(done.outcome.playerMatches).toBeGreaterThanOrEqual(1)
    const ended = finishWeek(done.state, createRng(3))
    expect(ended.state.week).toBe(state.week + 1)
    expect(concludeTournament(ended.state, createRng(1))).toBeNull()
  })

  it('a finished Journey sets up the Trial; winning it pays, a KO can injure, and a pending technique can be learned', () => {
    const m = makeMonster({ agePct: 50, fear: 30, stats: { POW: 400, LIF: 300 } })
    let state = createGameState({ monster: m })
    state.money = 5000
    const rng = createRng(9)
    state = beginWeek(state, rng, 'turnips').state
    state = chooseAction(state, { kind: 'journey', site: 'iron-quarry' }, rng).state
    expect(state.journeysBySite['iron-quarry']).toBe(1)
    for (let i = 0; i < 3; i++) {
      state = finishWeek(state, rng).state
      state = beginWeek(state, rng).state
      state = chooseAction(state, { kind: 'none' }, rng).state
    }
    expect(state.journey).toBeNull()
    expect(state.trial?.site).toBe('iron-quarry')
    expect(actionMenu(state).reason).toBe('trial')
    const wild = makeTrialOpponent(state, rng)!
    expect(wild.mainBreed).toBe('cobblemaw')
    const won = resolveTrial(state, { winner: 0, how: 'time' }, rng)
    expect(won.outcome.won).toBe(true)
    expect(won.outcome.reward).toBe(600)
    expect(won.state.money).toBe(state.money + 600)
    expect(won.state.trial).toBeNull()
    let injuries = 0
    for (let seed = 0; seed < 40; seed++) {
      const lost = resolveTrial({ ...state, monster: { ...state.monster!, fatigue: 90 } }, { winner: 1, how: 'ko' }, createRng(seed))
      expect(lost.outcome.won).toBe(false)
      if (lost.outcome.injuredWeeks > 0) injuries++
    }
    expect(injuries).toBeGreaterThan(5)
    // A pending technique with a full list.
    const full = structuredClone(state)
    full.trial = { site: 'iron-quarry', pendingTechnique: 'universal.beat-bump' }
    full.monster!.techniques = Array.from({ length: 12 }, (_, i) => ({ id: `universal.${['shuffle-step-kick', 'hum-pulse', 'whistle-shot', 'staccato-jab', 'downbeat-strike', 'chime-bolt', 'piccolo-dart', 'crescendo-slam', 'timpani-crash', 'grand-finale', 'fortissimo-blast', 'drumroll-stomp'][i]}`, uses: 0, level: 1 as const }))
    const learned = resolvePendingTechnique(full, 'universal.shuffle-step-kick')
    expect(learned.monster!.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(true)
    expect(learned.monster!.techniques.some((t) => t.id === 'universal.shuffle-step-kick')).toBe(false)
    expect(learned.trial?.pendingTechnique).toBeNull()
    const letGo = resolvePendingTechnique(full, null)
    expect(letGo.monster!.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(false)
  })

  it('a monster entering Prime with loyalty ≥ 60 learns its Signature at the end of that week', () => {
    const m = makeMonster({ spoil: 60, fear: 60 })
    m.ageWeeks = firstWeekOfStage(m, 5) - 1
    let state = createGameState({ monster: m })
    state.week = 5
    const rng = createRng(1)
    state = beginWeek(state, rng).state
    state = chooseAction(state, { kind: 'rest' }, rng).state
    const r = finishWeek(state, rng)
    expect(r.events.some((e) => e.kind === 'signature')).toBe(true)
    expect(r.state.monster!.techniques.some((t) => t.id === signatureOf('puddlepup').id)).toBe(true)
    expect(WEEKS_PER_YEAR).toBe(48)
  })
})
