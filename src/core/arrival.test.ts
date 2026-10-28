import { describe, expect, it } from 'vitest'
import { ARRIVAL } from '../data/tuning.ts'
import { applyAway, armAway, arrivalFor, awayStage, giveTreat, greetMood, noteGreeting, petMonster, setVacation } from './arrival.ts'
import { concludeLife } from './legacy.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { awardTitles } from './titles.ts'

const H = 3_600_000
const T0 = 1_800_000_000_000

function armed(o: Parameters<typeof makeMonster>[0] = {}): GameState {
  return armAway(createGameState({ monster: makeMonster({ spoil: 60, fear: 60, stress: 20, ...o }) }), T0)
}

describe('arriving at the ranch (GAME_DESIGN §6.10)', () => {
  it('turns time away into a stage at exactly 24 h, 48 h and 96 h', () => {
    expect(awayStage(24 * H - 1)).toBeNull()
    expect(awayStage(24 * H)).toBe('sad')
    expect(awayStage(48 * H - 1)).toBe('sad')
    expect(awayStage(48 * H)).toBe('abandoned')
    expect(awayStage(96 * H - 1)).toBe('abandoned')
    expect(awayStage(96 * H)).toBe('gone')
    const s = armed()
    expect(arrivalFor(s, T0, T0 + 24 * H - 1)).toBe('greet')
    expect(arrivalFor(s, T0, T0 + 24 * H)).toBe('sad')
    expect(arrivalFor(s, T0, T0 + 48 * H)).toBe('abandoned')
    expect(arrivalFor(s, T0, T0 + 96 * H)).toBe('gone')
  })

  it('never runs before the clock is armed, nor in Vacation mode, nor when the clock runs backwards, nor without a monster', () => {
    const unarmed = createGameState({ monster: makeMonster() })
    expect(arrivalFor(unarmed, T0 - 500 * H, T0)).toBe('none')
    const s = armed()
    // Armed later than the last save: measured from the arming, so an old save is never punished.
    expect(arrivalFor(s, T0 - 500 * H, T0 + H)).toBe('none')
    const vacation = setVacation(s, true, T0)
    expect(arrivalFor(vacation, T0, T0 + 200 * H)).toBe('greet')
    expect(arrivalFor(s, T0 + 5 * H, T0)).toBe('none')
    expect(arrivalFor({ ...s, monster: null }, T0, T0 + 200 * H)).toBe('none')
    expect(arrivalFor({ ...s, ended: 'passed' }, T0, T0 + 200 * H)).toBe('none')
    // Turning vacation off restarts the clock.
    const back = setVacation(vacation, false, T0 + 300 * H)
    expect(arrivalFor(back, T0, T0 + 301 * H)).toBe('none')
  })

  it('says hello after 2 h away, at most once every 12 h', () => {
    const s = armed()
    expect(arrivalFor(s, T0, T0 + 2 * H - 1)).toBe('none')
    expect(arrivalFor(s, T0, T0 + 2 * H)).toBe('greet')
    const greeted = noteGreeting(s, T0 + 2 * H)
    expect(arrivalFor(greeted, T0 + 3 * H, T0 + 8 * H)).toBe('none')
    expect(arrivalFor(greeted, T0 + 3 * H, T0 + 14 * H)).toBe('greet')
  })

  it('greets by loyalty: happy from 50, curious from 25, aloof below', () => {
    expect(greetMood(50)).toBe('happy')
    expect(greetMood(49)).toBe('curious')
    expect(greetMood(25)).toBe('curious')
    expect(greetMood(24)).toBe('aloof')
  })

  it('a pat is free; a treat costs 20G; both make the monster fonder and calmer', () => {
    const s = armed({ spoil: 40, stress: 20 })
    expect(petMonster(s).monster).toMatchObject({ spoil: 41, stress: 18 })
    const t = giveTreat(s)
    expect(t.refused).toBeNull()
    expect(t.state.money).toBe(s.money - ARRIVAL.treat.price)
    expect(t.state.monster).toMatchObject({ spoil: 43, stress: 17 })
    expect(giveTreat({ ...s, money: 19 }).refused).toBe('money')
  })

  it('a day away: stress up, affection and respect down, the bond boost gone', () => {
    const s = armed({ stress: 20, spoil: 60, fear: 60 })
    s.monster!.status.bondPct = 150
    const r = applyAway(s, 'sad', T0 + 30 * H)
    expect(r.state.monster).toMatchObject({ stress: 35, spoil: 50, fear: 55 })
    expect(r.state.monster!.status.bondPct).toBe(100)
    expect(r.changes).toMatchObject({ stress: 15, spoil: -10, fear: -5, lifespanWeeks: 0, sickWeeks: 0 })
    // The clock restarts, and no hello right after.
    expect(arrivalFor(r.state, T0 + 30 * H, T0 + 33 * H)).toBe('none')
  })

  it('two days away: worse, two weeks of life lost, and a week sick', () => {
    const s = armed({ stress: 20, spoil: 60, fear: 60 })
    const life = s.monster!.lifespanTotal
    const r = applyAway(s, 'abandoned', T0 + 50 * H)
    expect(r.state.monster).toMatchObject({ stress: 50, spoil: 40, fear: 50 })
    expect(r.state.monster!.lifespanTotal).toBe(life - 2)
    expect(r.state.monster!.status.sickWeeks).toBe(1)
    expect(r.changes.lifespanWeeks).toBe(-2)
  })

  it('four days away ends the life (left alone; on Gentle, back to the wild), and the Memorial never counts it for Gentle Heart', () => {
    const s = armed()
    const gone = applyAway(s, 'gone', T0 + 100 * H)
    expect(gone.state.ended).toBe('neglected')
    const gentle = applyAway({ ...s, difficulty: 'Gentle' }, 'gone', T0 + 100 * H)
    expect(gentle.state.ended).toBe('wandered')
    const concluded = concludeLife(gone.state, '')!
    expect(concluded.cause).toBe('neglected')
    expect(concluded.state.memorial[0]!.cause).toBe('neglected')
    expect(concluded.state.monster).toBeNull()
    // Even a monster that lived a full life doesn't earn Gentle Heart this way.
    const old = structuredClone(gone.state)
    old.monster!.ageWeeks = old.monster!.lifespanTotal
    expect(awardTitles(concludeLife(old, '')!.state).titles).not.toContain('Gentle Heart')
    const wild = concludeLife(gentle.state, '')!
    expect(wild.cause).toBe('wandered')
    expect(wild.state.elderGrove).toHaveLength(0)
  })
})
