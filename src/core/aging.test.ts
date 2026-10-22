import { describe, expect, it } from 'vitest'
import { availability, endOfWeekTick, expressionCues, extraLifespanLoss, fatigueLabel, loyaltyLabel, strainDebtStep, stressLabel } from './aging.ts'
import { createRng } from './rng.ts'
import { makeMonster } from './test-helpers.ts'

describe('strain → extra lifespan loss (§6.6)', () => {
  it('uses the 80 / 45 ladder capped at 3', () => {
    expect([0, 79, 80, 124, 125, 169, 170, 300].map((s) => extraLifespanLoss(s))).toEqual([0, 0, 1, 1, 2, 2, 3, 3])
  })

  it('caps at 1 in Gentle and adds a step (cap 4) in Classic', () => {
    expect([80, 125, 170].map((s) => extraLifespanLoss(s, 'Gentle'))).toEqual([1, 1, 1])
    expect([79, 80, 125, 170, 300].map((s) => extraLifespanLoss(s, 'Classic'))).toEqual([0, 2, 3, 4, 4])
  })

  it('the proposed debt rule piles up strain over 10, compounds above 150, and costs a week per 160 points', () => {
    expect(strainDebtStep(0, 10)).toEqual({ debt: 0, loss: 0 })
    expect(strainDebtStep(0, 120)).toEqual({ debt: 110, loss: 0 })
    expect(strainDebtStep(100, 120)).toEqual({ debt: 50, loss: 1 })
    expect(strainDebtStep(0, 1000)).toEqual({ debt: 8925, loss: 3 }) // capped at 3 per week
    expect(strainDebtStep(0, 220, 'Gentle')).toEqual({ debt: 18, loss: 1 }) // 357 × 50% = 178 ≥ 160
    expect(strainDebtStep(900, 1000, 'Gentle')).toEqual({ debt: 5442, loss: 1 }) // Gentle cap 1
    expect(strainDebtStep(0, 180, 'Classic')).toEqual({ debt: 116, loss: 1 })
  })
})

describe('end-of-week tick (§7)', () => {
  it('ages one week and subtracts the strain loss from the lifespan total', () => {
    const calm = makeMonster({ fatigue: 10, stress: 10 })
    const r = endOfWeekTick(calm, 'Standard', createRng(1))
    expect(r.monster.ageWeeks).toBe(1)
    expect(r.monster.lifespanTotal).toBe(418)
    expect(r.lifespanLost).toBe(0)
    const strained = makeMonster({ fatigue: 60, stress: 60 }) // strain 180 → 3
    const s = endOfWeekTick(strained, 'Standard', createRng(1))
    expect(s.monster.lifespanTotal).toBe(415)
    expect(s.lifespanLost).toBe(3)
    expect(strained.ageWeeks).toBe(0) // input untouched
  })

  it('rolls illness only at fatigue ≥ 90, about 10% of the time, for 2 weeks and −2 lifespan', () => {
    const tired = makeMonster({ fatigue: 90, stress: 0 })
    let sick = 0
    for (let seed = 0; seed < 1000; seed++) {
      const r = endOfWeekTick(tired, 'Standard', createRng(seed))
      if (r.events.some((e) => e.kind === 'illness')) {
        sick++
        expect(r.monster.status.sickWeeks).toBe(2)
        expect(r.monster.lifespanTotal).toBe(418 - 1 - 2)
        expect(availability(r.monster)).toMatchObject({ restOnly: true, reason: 'sick' })
      }
    }
    expect(sick).toBeGreaterThan(60)
    expect(sick).toBeLessThan(140)
    const fine = makeMonster({ fatigue: 89 })
    for (let seed = 0; seed < 200; seed++) expect(endOfWeekTick(fine, 'Standard', createRng(seed)).events.some((e) => e.kind === 'illness')).toBe(false)
  })

  it('breaks down about 25% of weeks at strain ≥ 200 (10% in Gentle), resetting fatigue and stress to 30', () => {
    const wrecked = makeMonster({ fatigue: 100, stress: 60, spoil: 40, fear: 40 })
    let runAway = 0
    let collapse = 0
    let gentle = 0
    for (let seed = 0; seed < 1000; seed++) {
      const r = endOfWeekTick(wrecked, 'Standard', createRng(seed))
      const b = r.events.find((e) => e.kind === 'breakdown')
      if (b && b.kind === 'breakdown') {
        if (b.type === 'runAway') {
          runAway++
          expect(r.monster.status.missingWeeks).toBe(2)
          expect(r.monster).toMatchObject({ fatigue: 30, stress: 30, spoil: 35, fear: 35 })
          expect(r.fees).toBe(300)
          expect(availability(r.monster)).toMatchObject({ locked: true, reason: 'missing' })
        } else {
          collapse++
          expect(r.monster.status.clinicWeeks).toBe(2)
          expect(r.fees).toBe(200)
          expect(r.monster.lifespanTotal).toBeLessThanOrEqual(418 - 3 - 2)
        }
      }
      if (endOfWeekTick(wrecked, 'Gentle', createRng(seed)).events.some((e) => e.kind === 'breakdown')) gentle++
    }
    expect(runAway + collapse).toBeGreaterThan(200)
    expect(runAway + collapse).toBeLessThan(300)
    expect(runAway).toBeGreaterThan(80)
    expect(collapse).toBeGreaterThan(80)
    expect(gentle).toBeGreaterThan(60)
    expect(gentle).toBeLessThan(140)
  })

  it('counts down timers, decrements tonics and reports returns', () => {
    const m = makeMonster({ fatigue: 0, stress: 0 })
    m.status.sickWeeks = 1
    m.status.tonics.POW = 2
    m.status.tonics.INT = 1
    const r = endOfWeekTick(m, 'Standard', createRng(1))
    expect(r.monster.status.sickWeeks).toBe(0)
    expect(r.events).toContainEqual({ kind: 'returned', from: 'sick' })
    expect(r.monster.status.tonics).toEqual({ POW: 1 })
  })

  it('warns at 25% life left, 48 weeks and 10 weeks, each once, and announces prime and past prime', () => {
    const m = makeMonster({ fatigue: 0, stress: 0 })
    m.lifespanTotal = 400
    m.ageWeeks = 298 // after the tick: 299 → 101 left → 25.25% (no warning yet)
    const a = endOfWeekTick(m, 'Standard', createRng(1))
    expect(a.events.filter((e) => e.kind === 'warning')).toEqual([])
    expect(a.events).toContainEqual({ kind: 'pastPrime' })
    expect(a.events.some((e) => e.kind === 'prime')).toBe(false) // already past it; prime is only announced in stages 5–6
    const b = endOfWeekTick(a.monster, 'Standard', createRng(1)) // 300 → 100 left = 25%
    expect(b.events).toContainEqual({ kind: 'warning', which: 'quarterLife' })
    expect(b.events.some((e) => e.kind === 'prime')).toBe(false)
    const c = endOfWeekTick(b.monster, 'Standard', createRng(1))
    expect(c.events.filter((e) => e.kind === 'warning')).toEqual([])
    c.monster.ageWeeks = 351
    const d = endOfWeekTick(c.monster, 'Standard', createRng(1)) // 352 → 48 left
    expect(d.events).toContainEqual({ kind: 'warning', which: 'w48' })
    d.monster.ageWeeks = 389
    const e = endOfWeekTick(d.monster, 'Standard', createRng(1)) // 390 → 10 left
    expect(e.events).toContainEqual({ kind: 'warning', which: 'w10' })
  })

  it('announces prime once on entering stage 5', () => {
    const m = makeMonster({ fatigue: 0, stress: 0 })
    m.ageWeeks = 200 // lifespan 418, Steady: stage 5 starts at week 201
    const r = endOfWeekTick(m, 'Standard', createRng(1))
    expect(r.events).toContainEqual({ kind: 'prime' })
    expect(endOfWeekTick(r.monster, 'Standard', createRng(1)).events.some((e) => e.kind === 'prime')).toBe(false)
  })

  it('ends the life when age reaches the total: passing in Standard, retiring in Gentle', () => {
    const m = makeMonster({ fatigue: 0, stress: 0 })
    m.lifespanTotal = 100
    m.ageWeeks = 99
    expect(endOfWeekTick(m, 'Standard', createRng(1)).events).toContainEqual({ kind: 'endOfLife', how: 'passed' })
    expect(endOfWeekTick(m, 'Gentle', createRng(1)).events).toContainEqual({ kind: 'endOfLife', how: 'retired' })
    expect(endOfWeekTick(m, 'Classic', createRng(1)).events).toContainEqual({ kind: 'endOfLife', how: 'passed' })
  })
})

describe('labels and expressions (§6.6)', () => {
  it('maps fatigue, stress and loyalty to the assistant words', () => {
    expect([0, 14, 15, 34, 35, 54, 55, 74, 75, 89, 90, 100].map(fatigueLabel)).toEqual([
      'Bright-eyed', 'Bright-eyed', 'Fine', 'Fine', 'A bit tired', 'A bit tired', 'Tired', 'Tired', 'Exhausted', 'Exhausted', 'About to collapse', 'About to collapse',
    ])
    expect([0, 9, 10, 24, 25, 44, 45, 64, 65, 84, 85].map(stressLabel)).toEqual([
      'Carefree', 'Carefree', 'Calm', 'Calm', 'A little tense', 'A little tense', 'Stressed', 'Stressed', 'Very stressed', 'Very stressed', 'At breaking point',
    ])
    expect([0, 19, 20, 39, 40, 59, 60, 79, 80, 100].map(loyaltyLabel)).toEqual(['Distant', 'Distant', 'Wary', 'Wary', 'Friendly', 'Friendly', 'Devoted', 'Devoted', 'Inseparable', 'Inseparable'])
  })

  it('derives expression cues from the thresholds', () => {
    expect(expressionCues(makeMonster({ fatigue: 55, stress: 45, spoil: 80, fear: 80, nature: -60 }))).toEqual(['droopy', 'sweat', 'sparkle', 'grin'])
    expect(expressionCues(makeMonster({ fatigue: 54, stress: 44, spoil: 78, fear: 80, nature: -59 }))).toEqual([])
    const sick = makeMonster()
    sick.status.sickWeeks = 1
    expect(expressionCues(sick)).toEqual(['sick'])
  })
})
