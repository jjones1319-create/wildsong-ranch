import { describe, expect, it } from 'vitest'
import { FOOD_BY_ID } from '../data/foods.ts'
import { ECONOMY } from '../data/tuning.ts'
import { actionMenu, answerRequest, beginWeek, canSwitchDifficulty, chooseAction, finishWeek, forgetFromCard, learnFromSongbook, needsFoodChoice, react, replaceActiveMonster, switchDifficulty, useItems } from './game.ts'
import { addItems } from './items.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('the turn controller (M3)', () => {
  it('begins a week once, charges the food in week 1 and records the phase', () => {
    const state = createGameState({ monster: makeMonster() })
    expect(needsFoodChoice(state)).toBe(true)
    const rng = createRng(1)
    const begun = beginWeek(state, rng, 'honey-bread')
    expect(begun.state.weekPhase).toBe('action')
    expect(begun.state.foodChoice).toBe('honey-bread')
    expect(begun.state.money).toBe(ECONOMY.startMoney - FOOD_BY_ID['honey-bread'].price)
    expect(needsFoodChoice(begun.state)).toBe(false)
    // A second call does nothing: no double feeding.
    const again = beginWeek(begun.state, rng, 'turnips')
    expect(again.state).toBe(begun.state)
    expect(again.events).toEqual([])
  })

  it('a pending request blocks the menu until answered; accepting rest becomes the action', () => {
    const tired = makeMonster({ fatigue: 100, stress: 100 })
    let state = createGameState({ monster: tired })
    let request = null
    for (let seed = 0; seed < 50 && !request; seed++) {
      const r = beginWeek(state, createRng(seed), 'honey-bread')
      if (r.state.pendingRequest) {
        state = r.state
        request = r.state.pendingRequest
      }
    }
    expect(request).not.toBeNull()
    expect(actionMenu(state)).toMatchObject({ train: false, rest: false, reason: 'request' })
    const answered = answerRequest(state, true)
    expect(answered.state.pendingRequest).toBeNull()
    expect(answered.forcedAction).toEqual({ kind: request!.kind === 'play' ? 'play' : 'rest' })
    const acted = chooseAction(answered.state, answered.forcedAction!, createRng(3))
    expect(acted.state.counters.restsTaken).toBe(1)
    expect(acted.state.lastAction).toEqual({ kind: 'rest' })
    expect(acted.state.monster!.fatigue).toBeLessThan(100)
  })

  it('choosing an action with a request still pending denies it first', () => {
    const state = createGameState({ monster: makeMonster({ fatigue: 60, stress: 10, spoil: 50 }) })
    const begun = beginWeek(state, createRng(1), 'honey-bread').state
    begun.pendingRequest = { kind: 'rest', toy: null }
    const r = chooseAction(begun, { kind: 'drill', drill: 'log-toss' }, createRng(2))
    expect(r.events.some((e) => e.kind === 'requestDenied')).toBe(true)
    expect(r.state.pendingRequest).toBeNull()
    expect(r.state.monster!.spoil).toBeLessThan(50 + 10) // denied: spoil −2 (the drill reaction has not happened yet)
    expect(r.drill).not.toBeNull()
  })

  it('runs a full week: begin → drill → react → finish, and remembers last week for Repeat', () => {
    const rng = createRng(5)
    let state = beginWeek(createGameState({ monster: makeMonster() }), rng, 'honey-bread').state
    expect(actionMenu(state)).toMatchObject({ train: true, rest: true, wait: false, repeat: null })
    const acted = chooseAction(state, { kind: 'drill', drill: 'log-toss' }, rng)
    expect(acted.drill?.drill).toBe('log-toss')
    state = react(acted.state, acted.drill!.outcome, 'praise')
    const finished = finishWeek(state, rng)
    state = finished.state
    expect(state.week).toBe(1)
    expect(state.weekPhase).toBe('start')
    expect(state.counters.drillsDone).toBe(1)
    expect(needsFoodChoice(state)).toBe(false)
    state = beginWeek(state, rng).state
    expect(actionMenu(state).repeat).toEqual({ kind: 'drill', drill: 'log-toss' })
    // finishWeek is a no-op when the week has not begun.
    const idle = finishWeek({ ...state, weekPhase: 'start' }, rng)
    expect(idle.events).toEqual([])
  })

  it('a missing monster can only wait; a sick one can only rest', () => {
    const missing = makeMonster()
    missing.status.missingWeeks = 2
    const away = beginWeek(createGameState({ monster: missing }), createRng(1), 'turnips').state
    expect(actionMenu(away)).toMatchObject({ train: false, rest: false, wait: true, reason: 'missing' })
    const sick = makeMonster()
    sick.status.sickWeeks = 1
    const ill = beginWeek(createGameState({ monster: sick }), createRng(1), 'turnips').state
    expect(actionMenu(ill)).toMatchObject({ train: false, rest: true, wait: false, reason: 'sick' })
    const ended = createGameState({ monster: makeMonster() })
    ended.ended = 'passed'
    expect(actionMenu(ended).reason).toBe('ended')
  })

  it('free actions: items count sweets, sheets learn and forget, edits keep history', () => {
    let state = beginWeek(createGameState({ monster: makeMonster() }), createRng(1), 'turnips').state
    state.inventory = addItems(state.inventory, 'mighty-muffin', 10)
    const ate = useItems(state, 'mighty-muffin', 10)
    expect(ate.used).toBe(10)
    expect(ate.state.counters.sweetsEaten).toBe(10)
    expect(ate.state.monster!.stats.POW).toBe(state.monster!.stats.POW + 50)
    expect(ate.state.monster!.records.fromSweets.POW).toBe(50)
    state = ate.state

    expect(learnFromSongbook(state, 'universal.beat-bump').status).toBe('notOwned')
    state.songbook = ['universal.beat-bump']
    const learned = learnFromSongbook(state, 'universal.beat-bump')
    expect(learned.status).toBe('learned')
    expect(learned.state.counters.sheetsLearned).toBe(1)
    expect(learned.state.monster!.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(true)
    const forgot = forgetFromCard(learned.state, 'universal.beat-bump')
    expect(forgot.monster!.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(false)
    expect(learnFromSongbook(forgot, 'universal.beat-bump').status).toBe('learned')

    const edited = structuredClone(state.monster!)
    edited.stats.LIF = 500
    edited.id = 'something-else'
    const replaced = replaceActiveMonster(state, edited, 123)
    expect(replaced.monster!.stats.LIF).toBe(500)
    expect(replaced.monster!.id).toBe(state.monster!.id)
    expect(replaced.monster!.flags.edited).toBe(true)
    expect(replaced.monsterHistory).toHaveLength(1)
    expect(replaced.monsterHistory[0]!.savedAt).toBe(123)
    expect(replaced.monsterHistory[0]!.monster.stats.LIF).toBe(state.monster!.stats.LIF)
  })

  it('items are refused before the week begins (nothing to act on yet)', () => {
    const state = createGameState({ monster: makeMonster() })
    state.inventory = addItems(state.inventory, 'sun-plum', 1)
    expect(useItems(state, 'sun-plum', 1).used).toBe(0)
  })

  it('Gentle and Standard can swap; Classic is locked in', () => {
    const standard = createGameState({ monster: makeMonster(), difficulty: 'Standard' })
    expect(canSwitchDifficulty(standard, 'Gentle')).toBe(true)
    expect(switchDifficulty(standard, 'Gentle').difficulty).toBe('Gentle')
    expect(canSwitchDifficulty(standard, 'Classic')).toBe(false)
    const classic = createGameState({ monster: makeMonster(), difficulty: 'Classic' })
    expect(canSwitchDifficulty(classic, 'Standard')).toBe(false)
    expect(switchDifficulty(classic, 'Standard').difficulty).toBe('Classic')
  })
})
