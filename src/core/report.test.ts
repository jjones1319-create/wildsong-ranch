import { describe, expect, it } from 'vitest'
import { drillLine, eventLines, growsUpAtPrime, learnedLine, weeklyReport } from './report.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import type { WeekEvent } from './week.ts'

describe("Wren's report (CONTENT §15)", () => {
  it('picks the weekly line from the condition and adds the request', () => {
    const fresh = createGameState({ monster: makeMonster({ id: 'a' }) })
    fresh.monster!.name = 'Pip'
    expect(weeklyReport(fresh).map((l) => l.key)).toEqual(['weeklyFresh'])
    expect(weeklyReport(fresh)[0]!.text).toContain('Pip')
    const tired = createGameState({ monster: makeMonster({ fatigue: 60 }) })
    expect(weeklyReport(tired)[0]!.key).toBe('weeklyTired')
    const exhausted = createGameState({ monster: makeMonster({ fatigue: 80, stress: 50 }) })
    expect(weeklyReport(exhausted).map((l) => l.key)).toEqual(['weeklyExhausted', 'stressed'])
    const stressed = createGameState({ monster: makeMonster({ fatigue: 10, stress: 50 }) })
    expect(weeklyReport(stressed)[0]!.key).toBe('stressed')
    const fine = createGameState({ monster: makeMonster({ fatigue: 40, stress: 10 }) })
    expect(weeklyReport(fine)[0]!.key).toBe('weeklyFine')
    const asking = createGameState({ monster: makeMonster({ fatigue: 50 }) })
    asking.pendingRequest = { kind: 'play', toy: null }
    expect(weeklyReport(asking).map((l) => l.key)).toEqual(['weeklyFine', 'requestPlay'])
    const sick = createGameState({ monster: makeMonster() })
    sick.monster!.status.sickWeeks = 1
    expect(weeklyReport(sick)[0]!.key).toBe('sickWeek')
    const missing = createGameState({ monster: makeMonster({ fatigue: 90 }) })
    missing.monster!.status.missingWeeks = 1
    expect(weeklyReport(missing).map((l) => l.key)).toEqual(['missingWeek'])
    expect(weeklyReport(createGameState({ monster: null }))).toEqual([])
  })

  it('turns the week’s events into lines, once each, and knows who grows up', () => {
    const m = makeMonster()
    m.name = 'Nib'
    const events: WeekEvent[] = [
      { kind: 'food', food: 'turnips', relation: 'disliked', bored: true, effect: {}, price: 20 },
      { kind: 'rest', fatigue: -40, stress: -10 },
      { kind: 'aging', event: { kind: 'prime' } },
      { kind: 'aging', event: { kind: 'warning', which: 'w10' } },
      { kind: 'aging', event: { kind: 'breakdown', type: 'runAway', fee: 300 } },
      { kind: 'aging', event: { kind: 'breakdown', type: 'runAway', fee: 300 } },
      { kind: 'aging', event: { kind: 'returned', from: 'sick' } },
      { kind: 'aging', event: { kind: 'endOfLife', how: 'retired' } },
    ]
    const keys = eventLines(events, m).map((l) => l.key)
    expect(keys).toEqual(['bored', 'rested', 'prime', 'tenWeeksLeft', 'breakdownRunAway', 'breakdownAdvice', 'recovered', 'retire'])
    expect(eventLines(events, m)[0]!.text).toBe("Nib's getting tired of Turnips…")
    expect(growsUpAtPrime({ mainBreed: 'puddlepup' })).toBe(false)
    expect(growsUpAtPrime({ mainBreed: 'pluckrex' })).toBe(true)
    const rex = makeMonster({ main: 'pluckrex' })
    expect(eventLines([{ kind: 'aging', event: { kind: 'prime' } }], rex).map((l) => l.key)).toEqual(['grewUp', 'prime'])
  })

  it('has a line for every drill outcome and for learning', () => {
    const m = makeMonster()
    for (const outcome of ['Great', 'Success', 'Cheat', 'Fail', 'Slacked'] as const) {
      const line = drillLine(m, { drill: 'log-toss', outcome, stars: 1, gains: {}, fatigue: 0, stress: 0, form: 0, pay: 0 })
      expect(line.text.length).toBeGreaterThan(5)
      expect(line.text).not.toContain('{')
    }
    expect(learnedLine(m, 'universal.beat-bump').text).toContain('Beat Bump')
  })
})
