import { describe, expect, it } from 'vitest'
import { markTipSeen, nextTip, tipText, TIP_IDS } from './onboarding.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('onboarding tips (§21)', () => {
  it('walks a new player through the first month in order, each tip once', () => {
    let state: GameState = createGameState({ monster: makeMonster(), breederName: 'Jo', ranchName: 'Hillside' })
    state.weekPhase = 'action'
    expect(nextTip(state, { screen: 'food' })).toBe('firstFood')
    state = markTipSeen(state, 'firstFood')
    expect(nextTip(state, { screen: 'food' })).toBeNull()
    expect(nextTip(state, { screen: 'ranch' })).toBe('welcome')
    expect(tipText(state, 'welcome')).toContain('Hillside')
    expect(tipText(state, 'welcome')).toContain('Jo')
    state = markTipSeen(state, 'welcome')
    // §6.10 the away rule comes next, at once (before it could ever bite), and mentions Vacation mode.
    expect(nextTip({ ...state, weekPhase: 'start' }, { screen: 'ranch' })).toBe('awayRule')
    expect(tipText(state, 'awayRule')).toContain('Vacation mode')
    state = markTipSeen(state, 'awayRule')
    // Before the week begins (the food prompt is still to come) no other ranch tip shows.
    expect(nextTip({ ...state, weekPhase: 'start' }, { screen: 'ranch' })).toBeNull()
    expect(nextTip(state, { screen: 'ranch' })).toBe('firstDrill')
    state = markTipSeen(state, 'firstDrill')
    expect(nextTip(state, { screen: 'result' })).toBeNull() // no drill done yet
    state.counters.drillsDone = 1
    expect(nextTip(state, { screen: 'result' })).toBe('praiseScold')
    state = markTipSeen(state, 'praiseScold')
    expect(nextTip(state, { screen: 'ranch' })).toBe('openCard') // not tired yet
    state.monster!.fatigue = 40
    expect(nextTip(state, { screen: 'ranch' })).toBe('firstRest')
    state = markTipSeen(state, 'firstRest')
    state = markTipSeen(state, 'openCard')
    expect(nextTip(state, { screen: 'ranch' })).toBeNull()
    expect(markTipSeen(state, 'openCard')).toBe(state) // already seen: same object
  })

  it('event tips come from the week summary, and nothing shows during a request or after the end', () => {
    const state = createGameState({ monster: makeMonster() })
    state.weekPhase = 'action'
    expect(nextTip(state, { screen: 'summary', events: [{ kind: 'prime' }] })).toBe('prime')
    expect(nextTip(state, { screen: 'summary', events: [{ kind: 'breakdown', type: 'collapse', fee: 200 }] })).toBe('breakdown')
    expect(nextTip(state, { screen: 'summary', events: [] })).toBeNull()
    expect(nextTip(state, { screen: 'request' })).toBe('firstRequest')
    state.pendingRequest = { kind: 'rest', toy: null }
    expect(nextTip(state, { screen: 'ranch' })).toBeNull()
    state.ended = 'passed'
    expect(nextTip(state, { screen: 'request' })).toBeNull()
  })

  it('every tip has text without leftover placeholders', () => {
    const state = createGameState({ monster: makeMonster() })
    for (const id of TIP_IDS) expect(tipText(state, id)).not.toMatch(/\{\w+\}/)
  })
})
