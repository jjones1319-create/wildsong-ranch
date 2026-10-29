import { describe, expect, it } from 'vitest'
import { STAGE_END_PCT } from '../data/tuning.ts'
import { GROWTH_TYPES, STAT_KEYS } from '../data/types.ts'
import { createMonster, gradeFactor100, lifeStage, loyaltyOf, mixBreeds, rollLikes, rollOffsets, stageFactor100, starsFor, stepGrade, styleBandOf, styleOf, strainOf, totalStats, type Likes } from './monster.ts'
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

describe('mixing (§14.3)', () => {
  it('a pure Puddlepup keeps its base stats, gets +10% lifespan and its two Basics', () => {
    const mix = mixBreeds('puddlepup', 'puddlepup')
    expect(mix.base).toEqual({ LIF: 120, POW: 70, INT: 60, SKI: 80, SPD: 70, DEF: 70 })
    expect(mix.grades).toEqual({ LIF: 'C', POW: 'C', INT: 'D', SKI: 'B', SPD: 'C', DEF: 'C' })
    expect(mix.lifespan).toBe(418)
    expect(mix.gutsRate).toBe(12)
    expect(mix.pure).toBe(true)
    expect(mix.variantName).toBe('Puddlepup')
    expect(mix.techniques).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop'])
  })

  it('blends a Cinder Tumblefox 75/25 with half-even rounding, grade steps and the sub quirk', () => {
    const mix = mixBreeds('tumblefox', 'cinderlynx')
    expect(mix.base).toEqual({ LIF: 90, POW: 78, INT: 72, SKI: 78, SPD: 102, DEF: 48 })
    // Cinderlynx grades D A D C B E: best POW (+1 on Tumblefox's D → C), worst DEF (−1: D → E)
    expect(mix.grades).toEqual({ LIF: 'D', POW: 'C', INT: 'C', SKI: 'B', SPD: 'B', DEF: 'E' })
    expect(mix.gutsRate).toBe(11)
    expect(mix.lifespan).toBe(352)
    expect(mix.pure).toBe(false)
    expect(mix.variantName).toBe('Cinder Tumblefox')
    expect(mix.techniques).toEqual(['tumblefox.scamper-swipe', 'tumblefox.foxfire-flicker', 'cinderlynx.spark-pounce'])
  })

  it('breaks grade ties in LIF, POW, INT, SKI, SPD, DEF order', () => {
    // Cobblemaw grades B A E D E B: worst is INT (first E), not SPD
    const mix = mixBreeds('puddlepup', 'cobblemaw')
    expect(mix.grades.POW).toBe('B')
    expect(mix.grades.INT).toBe('E')
    expect(mix.grades.SPD).toBe('C')
    // Aurelwyrm B A A C C C: best is POW (first A)
    const mix2 = mixBreeds('moatshell', 'aurelwyrm')
    expect(mix2.grades.POW).toBe('B')
    expect(mix2.grades.INT).toBe('D')
  })

  it('a sub can lift an A to S (v1.11), and steps stop at S and E', () => {
    // Wishlume sub (E E A C B E): best INT; Velvesper main INT is already A, so it becomes S
    expect(mixBreeds('velvesper', 'wishlume').grades.INT).toBe('S')
    expect(mixBreeds('velvesper', 'wishlume').grades.LIF).toBe('E')
    // Nothing goes past S.
    expect(mixBreeds('velvesper', 'velvesper').grades.INT).toBe('A')
  })
})

describe('createMonster and derived values (§4)', () => {
  it('applies offsets, starts fresh and derives loyalty, style, strain and total', () => {
    const m = createMonster({
      id: 'm1',
      mainBreed: 'puddlepup',
      subBreed: 'puddlepup',
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
    expect(m.flags.pure).toBe(true)
    expect(loyaltyOf(m)).toBe(30)
    expect(styleOf(m)).toBe(0)
    expect(styleBandOf(styleOf(m))).toBe('even')
    expect(strainOf(m)).toBe(0)
    expect(totalStats(m.stats)).toBe(485)
    expect(m.techniques.map((t) => t.id)).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop'])
  })

  it('names variants and keeps the sub accent on mixed monsters', () => {
    const m = createMonster({ id: 'm2', mainBreed: 'puddlepup', subBreed: 'cinderlynx', likes: TEST_LIKES })
    expect(m.name).toBe('Cinder Puddlepup')
    expect(m.appearance).toEqual({ paletteBreed: 'cinderlynx', accentPart: 'ember ear tufts' })
    expect(m.flags.pure).toBe(false)
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
