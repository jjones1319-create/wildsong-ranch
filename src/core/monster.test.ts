import { describe, expect, it } from 'vitest'
import { BREEDS, BREED_BY_ID } from '../data/breeds.ts'
import { STAGE_END_PCT } from '../data/tuning.ts'
import { GROWTH_TYPES, STAT_KEYS } from '../data/types.ts'
import { divRound } from './mathx.ts'
import { breedBirth, createMonster, gradeFactor100, lifeStage, loyaltyOf, rollLikes, rollOffsets, stageFactor100, starsFor, stepGrade, styleBandOf, styleOf, strainOf, totalStats, type Likes } from './monster.ts'
import { createRng } from './rng.ts'

export const TEST_LIKES: Likes = { food: 'honey-bread', dislikedFood: 'turnips', toy: 'rubber-ball', battle: 0, drill: 'log-toss', dislikedDrill: 'acorn-shower' }

describe('grades and stages (§5)', () => {
  it('uses the §5.2 grade factors', () => {
    expect(['E', 'D', 'C', 'B', 'A', 'S'].map((g) => gradeFactor100(g as 'E'))).toEqual([58, 79, 100, 132, 155, 180])
    expect(stepGrade('A', 1)).toBe('S')
    expect(stepGrade('S', 1)).toBe('S')
    expect(stepGrade('E', -1)).toBe('E')
    expect(stepGrade('C', 1)).toBe('B')
  })

  it('uses the §5.3 stage factors', () => {
    expect(Array.from({ length: 10 }, (_, i) => stageFactor100(i + 1))).toEqual([45, 60, 75, 88, 100, 96, 85, 72, 55, 35])
  })

  it('changes stage exactly at the cumulative percentages for every growth type', () => {
    const total = 100
    for (const growth of GROWTH_TYPES) {
      const bounds = STAGE_END_PCT[growth]
      expect(lifeStage(0, total, growth)).toBe(1)
      for (let stage = 1; stage <= 9; stage++) {
        const end = bounds[stage - 1]!
        expect(lifeStage(end - 1, total, growth)).toBe(stage)
        expect(lifeStage(end, total, growth)).toBe(stage + 1)
      }
      expect(lifeStage(99, total, growth)).toBe(10)
    }
    // Steady, lifespan 418: stage 4 ends at 48% = 200.64, so Prime (stage 5) starts at week 201
    expect(lifeStage(200, 418, 'Steady')).toBe(4)
    expect(lifeStage(201, 418, 'Steady')).toBe(5)
    expect(lifeStage(251, 418, 'Steady')).toBe(6)
  })

  it('maps stat values to stars', () => {
    expect([1, 299, 300, 599, 600, 999].map(starsFor)).toEqual([1, 1, 2, 2, 3, 3])
  })
})

describe('one whole breed (§14.3)', () => {
  it('a Puddlepup keeps its base stats, gets +10% lifespan and its two Basics', () => {
    const birth = breedBirth('puddlepup')
    expect(birth.base).toEqual({ LIF: 120, POW: 70, INT: 60, SKI: 80, SPD: 70, DEF: 70 })
    expect(birth.grades).toEqual({ LIF: 'C', POW: 'C', INT: 'D', SKI: 'B', SPD: 'C', DEF: 'C' })
    expect(birth.lifespan).toBe(418)
    expect(birth.gutsRate).toBe(12)
    expect(birth.name).toBe('Puddlepup')
    expect(birth.techniques).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop'])
  })

  it("every breed is born with its own base, grades and guts and 110% of its lifespan, rounded half-even", () => {
    for (const b of BREEDS) {
      const birth = breedBirth(b.id)
      expect(birth.base).toEqual(b.base)
      expect(birth.grades).toEqual(b.grades)
      expect(birth.gutsRate).toBe(b.gutsRate)
      expect(birth.lifespan).toBe(divRound(b.lifespan * 110, 100))
      expect(birth.name).toBe(b.name)
    }
  })

  it('hands out copies, so changing a newborn never changes the breed', () => {
    const birth = breedBirth('velvesper')
    birth.grades.INT = 'S'
    birth.base.INT = 1
    expect(BREED_BY_ID.velvesper.grades.INT).toBe('A')
    expect(breedBirth('velvesper').base.INT).toBe(BREED_BY_ID.velvesper.base.INT)
  })
})

describe('createMonster and derived values (§4)', () => {
  it('applies offsets, starts fresh and derives loyalty, style, strain and total', () => {
    const m = createMonster({
      id: 'm1',
      mainBreed: 'puddlepup',
      likes: TEST_LIKES,
      offsets: { stats: { LIF: 5, POW: -10, INT: 20, SKI: 0, SPD: 0, DEF: 0 }, lifespan: 12, gutsRate: -1, nature: 30 },
    })
    expect(m.stats).toEqual({ LIF: 125, POW: 60, INT: 80, SKI: 80, SPD: 70, DEF: 70 })
    expect(m.lifespanTotal).toBe(430)
    expect(m.gutsRate).toBe(11)
    expect(m.nature).toBe(30)
    expect(m.name).toBe('Puddlepup')
    expect(m.ageWeeks).toBe(0)
    expect(m.fatigue).toBe(0)
    expect(m.grade).toBe('E')
    expect(m.flags).toEqual({ edited: false, sandbox: false })
    expect(loyaltyOf(m)).toBe(30)
    expect(styleOf(m)).toBe(0)
    expect(styleBandOf(styleOf(m))).toBe('even')
    expect(strainOf(m)).toBe(0)
    expect(totalStats(m.stats)).toBe(485)
    expect(m.techniques.map((t) => t.id)).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop'])
  })

  it('has no sub breed, palette or accent part: the breed is the whole monster', () => {
    const m = createMonster({ id: 'm2', mainBreed: 'cinderlynx', likes: TEST_LIKES })
    expect(m.name).toBe('Cinderlynx')
    expect(Object.keys(m)).not.toContain('subBreed')
    expect(Object.keys(m)).not.toContain('appearance')
  })

  it('maps style to the §6.4 bands', () => {
    expect([80, 50, 20, 0, -20, -50, -80].map(styleBandOf)).toEqual(['doting', 'fond', 'gentle', 'even', 'firm', 'strict', 'spartan'])
    expect([79, 49, 19, -19, -49, -79].map(styleBandOf)).toEqual(['fond', 'gentle', 'even', 'even', 'firm', 'strict'])
  })

  it('rolls likes and offsets deterministically within range', () => {
    const rng = createRng(2024)
    const likes = rollLikes(rng)
    expect(likes.food).not.toBe(likes.dislikedFood)
    expect(likes.drill).not.toBe(likes.dislikedDrill)
    expect([-1, 0, 1]).toContain(likes.battle)
    const again = rollLikes(createRng(2024))
    expect(again).toEqual(likes)
    for (let i = 0; i < 200; i++) {
      const o = rollOffsets(rng)
      for (const k of STAT_KEYS) {
        expect(o.stats[k]).toBeGreaterThanOrEqual(-10)
        expect(o.stats[k]).toBeLessThanOrEqual(20)
      }
      expect(o.lifespan).toBeGreaterThanOrEqual(-10)
      expect(o.lifespan).toBeLessThanOrEqual(30)
      expect(Math.abs(o.gutsRate)).toBeLessThanOrEqual(1)
      expect(Math.abs(o.nature)).toBeLessThanOrEqual(30)
    }
  })
})
