import { describe, expect, it } from 'vitest'
import { EXPRESSION, REPORT } from '../data/tuning.ts'
import { emoteFor, emoteForReaction } from './emotes.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('emotes (§22)', () => {
  it('shows nothing for a calm, ordinary monster and nothing without one', () => {
    expect(emoteFor(createGameState({ monster: makeMonster({ fatigue: 10, stress: 5 }) }))).toBeNull()
    expect(emoteFor(createGameState())).toBeNull()
  })

  it('a request or a pending event is a surprise, and wins over everything else', () => {
    const g = createGameState({ monster: makeMonster({ fatigue: 90, stress: 90 }) })
    g.pendingRequest = { kind: 'rest', toy: null }
    expect(emoteFor(g)).toBe('surprise')
    g.pendingRequest = null
    g.pendingEvent = { kind: 'stormChase' }
    expect(emoteFor(g)).toBe('surprise')
  })

  it('tired is sleep, stressed is anger, and tired wins', () => {
    expect(emoteFor(createGameState({ monster: makeMonster({ fatigue: REPORT.tiredFatigue, stress: 0 }) }))).toBe('sleep')
    expect(emoteFor(createGameState({ monster: makeMonster({ fatigue: 0, stress: EXPRESSION.sweatStress }) }))).toBe('anger')
    expect(emoteFor(createGameState({ monster: makeMonster({ fatigue: 99, stress: 99 }) }))).toBe('sleep')
    const sick = createGameState({ monster: makeMonster() })
    sick.monster!.status.sickWeeks = 1
    expect(emoteFor(sick)).toBe('sleep')
  })

  it('a devoted, fresh monster shows a heart', () => {
    const m = makeMonster({ fatigue: 0, stress: 0, spoil: 100, fear: 100 })
    expect(emoteFor(createGameState({ monster: m }))).toBe('heart')
  })

  it('praise is a heart, scold is anger, silence is nothing', () => {
    expect(emoteForReaction('praise')).toBe('heart')
    expect(emoteForReaction('scold')).toBe('anger')
    expect(emoteForReaction('skip')).toBeNull()
  })
})
