import { describe, expect, it } from 'vitest'
import { createRng } from './rng.ts'

describe('mulberry32 rng', () => {
  it('produces a fixed, known sequence for a seed', () => {
    const r = createRng(12345)
    expect([r.nextU32(), r.nextU32(), r.nextU32(), r.nextU32(), r.nextU32(), r.nextU32()]).toEqual([
      739843950, 1189082928, 4280334484, 4160707172, 1919576849, 3703171909,
    ])
    const dice = createRng(1)
    expect(Array.from({ length: 10 }, () => dice.nextInt(1, 6))).toEqual([1, 2, 4, 6, 3, 1, 5, 6, 4, 2])
  })

  it('spreads nearby seeds apart (the first pick is not correlated across seeds 1000, 1001, …)', () => {
    const firsts = Array.from({ length: 40 }, (_, i) => createRng(1000 + i).nextU32() % 7)
    const counts = new Map<number, number>()
    for (const f of firsts) counts.set(f, (counts.get(f) ?? 0) + 1)
    expect(Math.max(...counts.values())).toBeLessThanOrEqual(12)
    expect(counts.size).toBeGreaterThanOrEqual(5)
  })

  it('is deterministic: two generators with the same seed agree', () => {
    const a = createRng(99)
    const b = createRng(99)
    for (let i = 0; i < 1000; i++) expect(a.nextU32()).toBe(b.nextU32())
  })

  it('resumes identically from a saved state', () => {
    const a = createRng(7)
    for (let i = 0; i < 50; i++) a.nextFloat()
    const saved = a.getState()
    const continued = [a.nextU32(), a.nextU32(), a.nextU32()]
    const b = createRng(0)
    b.setState(saved)
    expect([b.nextU32(), b.nextU32(), b.nextU32()]).toEqual(continued)
  })

  it('keeps nextInt inclusive on both ends and nextFloat in [0, 1)', () => {
    const r = createRng(3)
    const seen = new Set<number>()
    for (let i = 0; i < 2000; i++) {
      const v = r.nextInt(-1, 1)
      expect(v).toBeGreaterThanOrEqual(-1)
      expect(v).toBeLessThanOrEqual(1)
      seen.add(v)
      const f = r.nextFloat()
      expect(f).toBeGreaterThanOrEqual(0)
      expect(f).toBeLessThan(1)
    }
    expect(seen).toEqual(new Set([-1, 0, 1]))
  })

  it('chance(0) is never true, chance(100) always, and ~50% lands near half', () => {
    const r = createRng(11)
    let hits = 0
    for (let i = 0; i < 4000; i++) {
      expect(r.chance(0)).toBe(false)
      expect(r.chance(100)).toBe(true)
      if (r.chance(50)) hits++
    }
    expect(hits).toBeGreaterThan(1800)
    expect(hits).toBeLessThan(2200)
  })

  it('weightedPick follows the weights and shuffle keeps every element', () => {
    const r = createRng(5)
    const counts = { a: 0, b: 0, c: 0 }
    for (let i = 0; i < 3000; i++) counts[r.weightedPick(['a', 'b', 'c'] as const, (x) => ({ a: 1, b: 2, c: 7 })[x])]++
    expect(counts.c).toBeGreaterThan(counts.b)
    expect(counts.b).toBeGreaterThan(counts.a)
    expect(counts.a).toBeGreaterThan(150)
    const shuffled = r.shuffle([1, 2, 3, 4, 5, 6, 7, 8])
    expect([...shuffled].sort((x, y) => x - y)).toEqual([1, 2, 3, 4, 5, 6, 7, 8])
  })
})
