import { describe, expect, it } from 'vitest'
import { LAB, RANGES, SONGBOOK } from '../data/tuning.ts'
import { STAT_KEYS, type Grades } from '../data/types.ts'
import {
  addableTechniques,
  applyBreedChange,
  blankMonster,
  breedBaseStats,
  duplicateMonster,
  finishEdit,
  isEditedChange,
  maxAllStats,
  pushHistory,
  randomizeStats,
  resetGrowthToBreed,
  restoreFromHistory,
  scaleToTotal,
  techniquesOutsideKit,
} from './lab.ts'
import { mixBreeds, totalStats } from './monster.ts'
import { createRng } from './rng.ts'
import { makeMonster } from './test-helpers.ts'

const grades = (LIF: Grades['LIF'], POW: Grades['POW'], INT: Grades['INT'], SKI: Grades['SKI'], SPD: Grades['SPD'], DEF: Grades['DEF']): Grades => ({ LIF, POW, INT, SKI, SPD, DEF })

describe('scaleToTotal (§19 Stats)', () => {
  it('hits the total exactly and stays inside 1–999 for every grade mix', () => {
    const mixes = [grades('C', 'C', 'C', 'C', 'C', 'C'), grades('A', 'A', 'A', 'A', 'A', 'A'), grades('E', 'E', 'E', 'E', 'E', 'E'), grades('A', 'E', 'B', 'D', 'C', 'A'), grades('E', 'A', 'E', 'A', 'E', 'A')]
    for (const g of mixes) {
      for (const total of [6, 7, 100, 470, 999, 1000, 2345, 3000, 5000, 5990, 5994]) {
        const s = scaleToTotal(g, total)
        expect(totalStats(s)).toBe(total)
        for (const k of STAT_KEYS) {
          expect(s[k]).toBeGreaterThanOrEqual(RANGES.stat.min)
          expect(s[k]).toBeLessThanOrEqual(RANGES.stat.max)
          expect(Number.isInteger(s[k])).toBe(true)
        }
      }
    }
  })

  it('gives better grades more points and clamps silly totals', () => {
    const s = scaleToTotal(grades('A', 'E', 'C', 'C', 'C', 'C'), 1200)
    expect(s.LIF).toBeGreaterThan(s.INT)
    expect(s.INT).toBeGreaterThan(s.POW)
    expect(s.INT).toBe(s.SKI)
    expect(totalStats(scaleToTotal(grades('C', 'C', 'C', 'C', 'C', 'C'), -50))).toBe(6)
    expect(totalStats(scaleToTotal(grades('C', 'C', 'C', 'C', 'C', 'C'), 99_999))).toBe(5994)
  })
})

describe('stat buttons', () => {
  it('breed base, max all and a seeded randomize', () => {
    const m = makeMonster({ main: 'cobblemaw', sub: 'wishlume' })
    expect(breedBaseStats(m)).toEqual(mixBreeds('cobblemaw', 'wishlume').base)
    expect(Object.values(maxAllStats()).every((v) => v === RANGES.stat.max)).toBe(true)
    const a = randomizeStats(m.stats, createRng(5))
    const b = randomizeStats(m.stats, createRng(5))
    expect(a).toEqual(b)
    for (const k of STAT_KEYS) {
      const spread = Math.floor((m.stats[k] * LAB.randomizeSpreadPct) / 100)
      expect(a[k]).toBeGreaterThanOrEqual(Math.max(1, m.stats[k] - spread))
      expect(a[k]).toBeLessThanOrEqual(Math.min(999, m.stats[k] + spread))
    }
    const tiny = randomizeStats({ LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 }, createRng(1))
    expect(Object.values(tiny).every((v) => v === 1)).toBe(true)
  })

  it('reset to breed default restores grades, growth, guts and lifespan only', () => {
    const m = makeMonster({ main: 'galeheron', sub: 'moatshell' })
    m.grades.LIF = 'A'
    m.growthType = 'Late'
    m.gutsRate = 20
    m.lifespanTotal = 1
    m.stats.POW = 777
    const r = resetGrowthToBreed(m)
    const mix = mixBreeds('galeheron', 'moatshell')
    expect(r.grades).toEqual(mix.grades)
    expect(r.growthType).toBe('Steady')
    expect(r.gutsRate).toBe(mix.gutsRate)
    expect(r.lifespanTotal).toBe(mix.lifespan)
    expect(r.stats.POW).toBe(777)
  })
})

describe('blank and duplicate', () => {
  it('blank is a plain, round-numbered monster', () => {
    const b = blankMonster('b1', 'Blank')
    expect(b.id).toBe('b1')
    expect(b.name).toBe('Blank')
    expect(Object.values(b.stats).every((v) => v === LAB.blank.stat)).toBe(true)
    expect(Object.values(b.grades).every((g) => g === LAB.blank.grade)).toBe(true)
    expect(b.lifespanTotal).toBe(LAB.blank.lifespan)
    expect(b.flags.pure).toBe(true)
  })

  it('duplicate keeps everything but the id and lineage', () => {
    const m = makeMonster({ id: 'orig', main: 'coilfang' })
    m.parents = ['a', 'b']
    m.stats.SPD = 512
    const d = duplicateMonster(m, 'copy')
    expect(d.id).toBe('copy')
    expect(d.parents).toEqual([])
    expect(d.stats.SPD).toBe(512)
    expect(d.mainBreed).toBe('coilfang')
    d.stats.SPD = 1
    expect(m.stats.SPD).toBe(512)
  })
})

describe('techniques in the editor', () => {
  it('lists the kit, the sub quirk and universals, or everything with Allow any', () => {
    const m = makeMonster({ main: 'puddlepup', sub: 'tumblefox' })
    const normal = addableTechniques(m, false)
    expect(normal.every((t) => t.breed === 'puddlepup' || t.breed === 'universal' || (t.breed === 'tumblefox' && t.subQuirk))).toBe(true)
    expect(normal.some((t) => t.id === 'puddlepup.splash-nip')).toBe(false)
    expect(normal.some((t) => t.family === 'Signature')).toBe(false)
    const any = addableTechniques(m, true)
    expect(any.length).toBe(294 - m.techniques.length)
    expect(any.some((t) => t.breed === 'aurelwyrm')).toBe(true)
  })

  it('breed change removes techniques outside the new kits unless Keep all is ticked', () => {
    const m = makeMonster({ main: 'puddlepup', sub: 'puddlepup' })
    m.techniques.push({ id: 'universal.beat-bump', uses: 0, level: 1 })
    const r = applyBreedChange(m, 'coilfang', 'galeheron', false)
    expect(r.removed).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop'])
    expect(r.monster.techniques.map((t) => t.id)).toEqual(['universal.beat-bump'])
    expect(r.monster.flags.pure).toBe(false)
    expect(r.monster.appearance.paletteBreed).toBe('galeheron')
    expect(r.monster.appearance.accentPart).toBe('crest plumes')
    expect(r.monster.growthType).toBe('Early')
    const kept = applyBreedChange(m, 'coilfang', 'galeheron', true)
    expect(kept.removed).toEqual([])
    expect(kept.monster.techniques).toHaveLength(3)
    expect(techniquesOutsideKit(kept.monster)).toEqual(['puddlepup.splash-nip', 'puddlepup.bubble-pop'])
    const same = applyBreedChange(m, 'puddlepup', 'puddlepup', false)
    expect(same.removed).toEqual([])
    expect(same.monster.appearance.accentPart).toBeNull()
  })
})

describe('the edited flag and edit history (§19)', () => {
  it('ignores the name and the flag itself, notices anything else', () => {
    const a = makeMonster()
    const b = structuredClone(a)
    b.name = 'Renamed'
    expect(isEditedChange(a, b)).toBe(false)
    b.flags.edited = true
    expect(isEditedChange(a, b)).toBe(false)
    const c = structuredClone(a)
    c.stats.LIF += 1
    expect(isEditedChange(a, c)).toBe(true)
    const renamedOnly = structuredClone(a)
    renamedOnly.name = 'Renamed'
    expect(finishEdit(a, renamedOnly).flags.edited).toBe(false)
    expect(finishEdit(a, c).flags.edited).toBe(true)
    const already = structuredClone(a)
    already.flags.edited = true
    expect(finishEdit(already, structuredClone(already)).flags.edited).toBe(true)
  })

  it('keeps the last ten versions and can restore any of them', () => {
    let history = pushHistory([], makeMonster(), 1)
    for (let i = 2; i <= LAB.historyLimit + 3; i++) {
      const v = makeMonster()
      v.name = `v${i}`
      history = pushHistory(history, v, i)
    }
    expect(history).toHaveLength(LAB.historyLimit)
    expect(history[0]!.savedAt).toBe(4)
    expect(history.at(-1)!.monster.name).toBe(`v${LAB.historyLimit + 3}`)
    const current = makeMonster({ id: 'cur' })
    current.name = 'Current'
    const restored = restoreFromHistory(current, history, 0, 99)
    expect(restored).not.toBeNull()
    expect(restored!.monster.name).toBe('v4')
    expect(restored!.monster.id).toBe('cur')
    expect(restored!.history.at(-1)!.monster.name).toBe('Current')
    expect(restored!.history).toHaveLength(LAB.historyLimit)
    expect(restoreFromHistory(current, history, 42, 1)).toBeNull()
    expect(SONGBOOK.maxTechniques).toBe(12)
  })
})
