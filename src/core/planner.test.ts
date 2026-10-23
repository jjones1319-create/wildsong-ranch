import { describe, expect, it } from 'vitest'
import { PLANNER } from '../data/tuning.ts'
import { weekIndexOf } from './calendar.ts'
import { beginWeek } from './game.ts'
import { clearQueue, PLANNER_MAX, plannerBlocker, queueStep, removeStep, runPlannedWeek, runPlanner, startRun } from './planner.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState, type PlannerStep } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const REST: PlannerStep = { kind: 'rest' }
const LOG: PlannerStep = { kind: 'drill', drill: 'log-toss' }

/** A calm, healthy monster in the middle of a month (no food prompt, no mail week), with a queue. */
function planned(steps: PlannerStep[], over: Parameters<typeof makeMonster>[0] = {}, week = weekIndexOf({ year: 1, month: 2, week: 2 })): GameState {
  const m = makeMonster({ fatigue: 0, stress: 0, ...over })
  m.lifespanTotal = 400
  m.ageWeeks = 30
  const g = createGameState({ monster: m })
  g.week = week
  // The first monster's letters and the January sale roll are already in the past for this ranch.
  g.mail = []
  for (const s of steps) Object.assign(g, queueStep(g, s))
  return g
}

describe('the planner queue (§3)', () => {
  it('holds at most eight steps and can remove or clear them', () => {
    let g = createGameState({ monster: makeMonster() })
    for (let i = 0; i < 12; i++) g = queueStep(g, i % 2 ? REST : LOG)
    expect(g.planner.queue).toHaveLength(PLANNER_MAX)
    expect(PLANNER_MAX).toBe(8)
    g = removeStep(g, 0)
    expect(g.planner.queue).toHaveLength(7)
    expect(g.planner.queue[0]).toEqual(REST)
    expect(removeStep(g, 99)).toBe(g)
    g = clearQueue(g)
    expect(g.planner).toEqual({ queue: [], log: [], lastStop: null })
    expect(clearQueue(g)).toBe(g)
  })

  it('plays a clean run of eight rests and logs every week, then stops because the queue is empty', () => {
    const g = planned(Array.from({ length: 8 }, () => REST))
    const rng = createRng(3)
    let r = runPlanner(g, rng)
    let weeks = r.weeks
    // A letter (an invitation) pauses the run; reading it and tapping Keep going resumes the same queue.
    while (r.stop === 'mail') {
      r.state.mail.forEach((m) => (m.read = true))
      r = runPlanner(r.state, rng)
      weeks += r.weeks
    }
    expect(r.stop).toBe('empty')
    expect(weeks).toBe(8)
    expect(r.state.week).toBe(g.week + 8)
    expect(r.state.planner.queue).toEqual([])
    expect(r.state.planner.log.length).toBeGreaterThan(0)
    expect(r.state.planner.log.at(-1)).toMatchObject({ week: g.week + 7, step: REST, outcome: null, pay: 0 })
    expect(r.state.planner.lastStop).toBe('empty')
    expect(r.state.counters.restsTaken).toBe(8)
  })

  it('is deterministic: the same seed gives the same run', () => {
    const g = planned([LOG, LOG, REST, LOG])
    const a = runPlanner(g, createRng(11))
    const b = runPlanner(g, createRng(11))
    expect(JSON.stringify(a.state)).toBe(JSON.stringify(b.state))
  })

  it('logs a drill with its outcome and gains and says nothing afterwards (no spoil or fear change)', () => {
    const g = planned([LOG])
    const spoil = g.monster!.spoil
    const fear = g.monster!.fear
    const r = runPlannedWeek(startRun(g), createRng(5))
    expect(r.acted).toBe(true)
    const entry = r.state.planner.log[0]!
    expect(entry.step).toEqual(LOG)
    expect(entry.outcome).not.toBeNull()
    expect(r.state.counters.drillsDone).toBe(1)
    expect(r.state.monster!.spoil).toBe(spoil)
    expect(r.state.monster!.fear).toBe(fear)
    expect(r.state.weekPhase).toBe('start')
  })

  it('keeps last month’s food at a month start instead of asking', () => {
    const g = planned([REST], {}, weekIndexOf({ year: 1, month: 2, week: 1 }))
    g.foodChoice = 'honey-bread'
    const money = g.money
    const r = runPlannedWeek(startRun(g), createRng(1))
    expect(r.acted).toBe(true)
    expect(r.state.foodChoice).toBe('honey-bread')
    expect(r.state.money).toBeLessThan(money)
  })

  it('stops before acting when the monster makes a request, and leaves the step queued', () => {
    // Very tired and stressed: the request roll fires on some seed within a few tries.
    const g = planned([LOG, LOG], { fatigue: 55, stress: 45 })
    let stopped = null
    for (let seed = 0; seed < 60 && !stopped; seed++) {
      const r = runPlannedWeek(startRun(g), createRng(seed))
      if (r.stop === 'request') stopped = r
    }
    expect(stopped).not.toBeNull()
    expect(stopped!.acted).toBe(false)
    expect(stopped!.state.pendingRequest).not.toBeNull()
    expect(stopped!.state.planner.queue).toHaveLength(2)
    expect(stopped!.state.weekPhase).toBe('action')
    expect(plannerBlocker(stopped!.state)).toBe('request')
  })

  it('stops after a week that leaves fatigue or stress too high', () => {
    const tired = planned([LOG, LOG, LOG], { fatigue: PLANNER.stopFatigue - 5, stress: 0 })
    const a = runPlanner(tired, createRng(2))
    expect(a.stop).toBe('fatigue')
    expect(a.weeks).toBe(1)
    expect(a.state.monster!.fatigue).toBeGreaterThanOrEqual(PLANNER.stopFatigue)
    const tense = planned([LOG, LOG, LOG], { fatigue: 0, stress: PLANNER.stopStress - 2 })
    const b = runPlanner(tense, createRng(2))
    expect(b.stop).toBe('stress')
    expect(b.weeks).toBe(1)
  })

  it('stops for new mail (an expedition invitation) before the week’s action', () => {
    // March week 1: Tomas's Thornwood letter arrives with the week.
    const g = planned([REST, REST], {}, weekIndexOf({ year: 1, month: 3, week: 1 }))
    const r = runPlannedWeek(startRun(g), createRng(1))
    expect(r.stop).toBe('mail')
    expect(r.acted).toBe(false)
    expect(r.state.mail.some((m) => !m.read)).toBe(true)
    expect(r.state.planner.queue).toHaveLength(2)
  })

  it('does not stop for an ordinary cup (almost every week holds one; the ranch lists them)', () => {
    // Y1 Jan w2: the Snowdrift Cup (grade E) is open to a fresh monster.
    const g = planned([REST, REST], {}, 1)
    const begun = beginWeek(g, createRng(1), g.foodChoice).state
    begun.mail.forEach((m) => (m.read = true))
    const r = runPlannedWeek(startRun(begun), createRng(1))
    expect(r.acted).toBe(true)
    expect(r.stop).toBeNull()
  })

  it('stops after an illness or a breakdown', () => {
    // Fatigue ≥ 90 risks illness (10 %/week); strain ≥ 200 risks a breakdown (25 %). Rest weeks recover, so queue drills.
    const g = planned(Array.from({ length: 8 }, () => LOG), { fatigue: 88, stress: 60 })
    const stops = new Set<string>()
    for (let seed = 0; seed < 40; seed++) stops.add(runPlanner(g, createRng(seed)).stop)
    expect([...stops].every((s) => ['illness', 'breakdown', 'fatigue', 'stress', 'request'].includes(s))).toBe(true)
    expect(stops.has('illness') || stops.has('breakdown')).toBe(true)
  })

  it('turns a drill into a rest for a sick monster and stops (forced rest)', () => {
    const g = planned([LOG, LOG])
    g.monster!.status.sickWeeks = 2
    const r = runPlannedWeek(startRun(g), createRng(1))
    expect(r.acted).toBe(true)
    expect(r.stop).toBe('forcedRest')
    expect(r.state.planner.log[0]!.outcome).toBeNull()
  })

  it('drops a drill that is not available and stops without using the week', () => {
    const g = planned([{ kind: 'drill', drill: 'quarry-haul' }, REST])
    const r = runPlannedWeek(startRun(g), createRng(1))
    expect(r.stop).toBe('invalid')
    expect(r.acted).toBe(false)
    expect(r.state.planner.queue).toEqual([REST])
    expect(r.state.weekPhase).toBe('action')
  })

  it('refuses to start while the monster is away, in a cup, on a Journey or on a trip', () => {
    const g = planned([REST])
    expect(plannerBlocker({ ...g, journey: { site: 'iron-quarry', weekNo: 1, successes: 0, learned: null, pendingTechnique: null, gains: {}, elderMentor: false } as unknown as GameState['journey'] })).toBe('journey')
    const missing = structuredClone(g)
    missing.monster!.status.missingWeeks = 2
    expect(plannerBlocker(missing)).toBe('locked')
    expect(plannerBlocker({ ...g, planner: { queue: [], log: [], lastStop: null } })).toBe('empty')
    expect(plannerBlocker({ ...g, monster: null })).toBe('noMonster')
    const r = runPlannedWeek(missing, createRng(1))
    expect(r.acted).toBe(false)
    expect(r.state.planner.lastStop).toBe('locked')
  })

  it('stops at a lifespan warning and at prime', () => {
    // A monster a week away from its quarter-life warning.
    const g = planned(Array.from({ length: 8 }, () => REST))
    g.monster!.lifespanTotal = 100
    g.monster!.ageWeeks = 74
    const r = runPlanner(g, createRng(1))
    expect(['warning', 'prime']).toContain(r.stop)
    expect(r.weeks).toBeGreaterThanOrEqual(1)
    expect(r.weeks).toBeLessThan(8)
  })
})
