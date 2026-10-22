import { describe, expect, it } from 'vitest'
import { HEAVY_DRILLS, LIGHT_DRILLS } from '../../data/drills.ts'
import { makeSave, validateSave } from '../../save/schema.ts'
import { WEEKS_PER_YEAR } from '../calendar.ts'
import { buyItem, maxAffordable } from '../economy.ts'
import { actionMenu, answerRequest, beginWeek, chooseAction, finishWeek, learnFromSongbook, needsFoodChoice, react, replaceActiveMonster, useItems } from '../game.ts'
import { buySheet } from '../guild.ts'
import { marketMonster } from '../market.ts'
import { totalStats } from '../monster.ts'
import { createRng } from '../rng.ts'
import { createGameState, type GameState, type WeekAction } from '../state.ts'
import type { WeekEvent } from '../week.ts'

/**
 * BUILD_PLAN M3: "a scripted player raises a monster for 3 in-game years without errors", through the same
 * controller the phone uses (core/game.ts), with shopping, items, a Songsheet, an edit, and a save round trip
 * at the end of every year.
 */

const YEARS = 3

function playYears(seed: number, breed: 'puddlepup' | 'pluckrex' = 'puddlepup') {
  const rng = createRng(seed)
  let state: GameState = createGameState({ monster: marketMonster(breed, `gift-${seed}`), breederName: 'Tester', ranchName: 'Test Ranch', difficulty: 'Standard' })
  const log = { weeks: 0, drills: 0, rests: 0, waits: 0, requests: 0, items: 0, roundTrips: 0, summaryLines: 0 }
  let light = 0
  let heavy = 0
  let learned = false
  let edited = false
  let ateBatch = false

  while (state.week < YEARS * WEEKS_PER_YEAR && !state.ended) {
    const events: WeekEvent[] = []
    // 1. The week begins (food in week 1 of a month: the liked food when affordable, else turnips).
    if (needsFoodChoice(state)) {
      const liked = state.monster!.likes.food
      const begun = beginWeek(state, rng, state.money > 1000 ? liked : 'turnips')
      state = begun.state
      events.push(...begun.events)
    } else {
      const begun = beginWeek(state, rng)
      state = begun.state
      events.push(...begun.events)
    }
    expect(state.weekPhase).toBe('action')

    // 2. Free actions: shop and use items, learn a sheet, edit once.
    if (!learned && state.money >= 500) {
      const bought = buySheet(state, 'universal.beat-bump')
      expect(bought.refused).toBeNull()
      const l = learnFromSongbook(bought.state, 'universal.beat-bump')
      expect(l.status).toBe('learned')
      state = l.state
      learned = true
    }
    // Until tournaments (M5) pay out, chore pay is the only income, so a batch of sweets is whatever the purse allows.
    if (!ateBatch && state.week >= 4) {
      const n = Math.min(10, maxAffordable(state, 'mighty-muffin'))
      if (n >= 2) {
        const bought = buyItem(state, 'mighty-muffin', n)
        expect(bought.refused).toBeNull()
        const ate = useItems(bought.state, 'mighty-muffin', n)
        expect(ate.used).toBe(n)
        state = ate.state
        log.items += n
        ateBatch = true
      }
    }
    if (state.monster!.fatigue >= 45 && state.money >= 200) {
      const bought = buyItem(state, 'sun-plum', 2)
      if (!bought.refused) {
        const used = useItems(bought.state, 'sun-plum', 2)
        state = used.state
        log.items += used.used
      }
    }
    if (state.monster!.stress >= 40 && state.money >= 300) {
      const bought = buyItem(state, 'lavender-sachet', 2)
      if (!bought.refused) {
        const used = useItems(bought.state, 'lavender-sachet', 2)
        state = used.state
        log.items += used.used
      }
    }
    if (!edited && state.week === 100) {
      const m = structuredClone(state.monster!)
      m.stats.SKI += 25
      m.name = 'Edited'
      state = replaceActiveMonster(state, m, 1_700_000_000_000 + state.week)
      expect(state.monster!.flags.edited).toBe(true)
      expect(state.monsterHistory).toHaveLength(1)
      edited = true
    }

    // 3. Requests are always accepted.
    let forced: WeekAction | null = null
    if (state.pendingRequest) {
      log.requests += 1
      const a = answerRequest(state, true)
      state = a.state
      forced = a.forcedAction
      events.push(...a.events)
    }

    // 4. The action.
    const menu = actionMenu(state)
    let action: WeekAction
    if (forced) action = forced
    else if (menu.wait) action = { kind: 'none' }
    else if (!menu.train || state.monster!.fatigue >= 55) action = { kind: 'rest' }
    else if (state.monster!.fatigue <= 30) {
      const d = HEAVY_DRILLS.filter((x) => !x.needsTrainingYard)[heavy++ % 4]!
      action = { kind: 'drill', drill: d.id }
    } else action = { kind: 'drill', drill: LIGHT_DRILLS[light++ % LIGHT_DRILLS.length]!.id }
    const acted = chooseAction(state, action, rng)
    state = acted.state
    events.push(...acted.events)
    if (acted.drill) {
      log.drills += 1
      state = react(state, acted.drill.outcome, acted.drill.outcome === 'Cheat' || acted.drill.outcome === 'Slacked' ? 'scold' : 'praise')
    } else if (action.kind === 'rest') log.rests += 1
    else log.waits += 1

    // 5. The week ends.
    const finished = finishWeek(state, rng)
    state = finished.state
    events.push(...finished.events)
    log.weeks += 1
    expect(state.weekPhase).toBe('start')
    expect(Number.isFinite(state.money)).toBe(true)

    // 6. A save round trip at the end of every year: what we write is what we read.
    if (state.week % WEEKS_PER_YEAR === 0) {
      const save = makeSave(state, rng.getState(), { savedAt: 1, appVersion: 'test' })
      const back = validateSave(JSON.parse(JSON.stringify(save)))
      expect(back.ok).toBe(true)
      if (back.ok) {
        expect(back.save.game).toEqual(state)
        expect(back.save.rng).toBe(rng.getState())
        state = back.save.game
        rng.setState(back.save.rng)
      }
      log.roundTrips += 1
    }
  }
  return { state, log, learned, edited, ateBatch }
}

describe('a scripted player raises a monster for 3 in-game years (M3)', () => {
  it('plays through the controller without errors, shopping, eating sweets and learning a sheet', () => {
    const { state, log, learned, edited, ateBatch } = playYears(2026)
    expect(state.ended).toBeNull()
    expect(state.week).toBe(YEARS * WEEKS_PER_YEAR)
    expect(log.weeks).toBe(YEARS * WEEKS_PER_YEAR)
    expect(log.roundTrips).toBe(YEARS)
    expect(log.drills).toBeGreaterThan(60)
    expect(log.rests).toBeGreaterThan(3) // sun plums keep fatigue down, so rests are rare under this script
    expect(learned && edited && ateBatch).toBe(true)
    expect(state.counters.sheetsLearned).toBe(1)
    expect(state.counters.sweetsEaten).toBeGreaterThanOrEqual(2)
    expect(log.items).toBeGreaterThanOrEqual(state.counters.sweetsEaten)
    expect(state.counters.drillsDone).toBe(log.drills)
    expect(state.monster!.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(true)
    expect(state.monster!.records.fromSweets.POW).toBe(state.counters.sweetsEaten * 5)
    expect(totalStats(state.monster!.stats)).toBeGreaterThan(900)
    expect(state.monster!.ageWeeks).toBe(YEARS * WEEKS_PER_YEAR)
    expect(state.monster!.name).toBe('Edited')
  })

  it('is deterministic for a seed and works for a two-form breed too', () => {
    const a = playYears(7, 'pluckrex')
    const b = playYears(7, 'pluckrex')
    expect(a.state).toEqual(b.state)
    expect(a.state.monster!.status.announcedPrime).toBe(true)
  })
})
