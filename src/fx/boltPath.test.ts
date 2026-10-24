import { describe, expect, it } from 'vitest'
import { boltPoints, boltWithBranches, polylineLength } from './primitives/boltPath.ts'
import { createFxRng } from './rng.ts'

describe('lightning geometry (pure)', () => {
  it('keeps both endpoints, has 2^levels segments and is longer than the straight line', () => {
    const pts = boltPoints(0, 0, 400, 0, createFxRng(3), 4, 0.25)
    expect(pts.length).toBe((2 ** 4 + 1) * 2)
    expect([pts[0], pts[1]]).toEqual([0, 0])
    expect([pts[pts.length - 2], pts[pts.length - 1]]).toEqual([400, 0])
    expect(polylineLength(pts)).toBeGreaterThan(400)
    expect(polylineLength(pts)).toBeLessThan(800)
  })

  it('is deterministic for a seed and different for another', () => {
    const a = boltPoints(0, 0, 300, 100, createFxRng(9))
    const b = boltPoints(0, 0, 300, 100, createFxRng(9))
    const c = boltPoints(0, 0, 300, 100, createFxRng(10))
    expect(a).toEqual(b)
    expect(a).not.toEqual(c)
  })

  it('branches fork from the trunk and are thinner; none without branches', () => {
    const none = boltWithBranches(0, 0, 400, 0, createFxRng(1), false)
    expect(none).toHaveLength(1)
    const some = boltWithBranches(0, 0, 400, 0, createFxRng(1), true, 1)
    expect(some.length).toBeGreaterThan(1)
    for (const b of some.slice(1)) {
      expect(b.weight).toBeLessThan(1)
      const sx = b.points[0]!
      const sy = b.points[1]!
      // The fork starts on a trunk vertex.
      const trunk = some[0]!.points
      let onTrunk = false
      for (let i = 0; i < trunk.length; i += 2) if (trunk[i] === sx && trunk[i + 1] === sy) onTrunk = true
      expect(onTrunk).toBe(true)
    }
  })

  it('the visual rng is uniform-ish, seeded and separate from core', () => {
    const r = createFxRng(5)
    let min = 1
    let max = 0
    for (let i = 0; i < 2000; i++) {
      const v = r.next()
      min = Math.min(min, v)
      max = Math.max(max, v)
    }
    expect(min).toBeLessThan(0.02)
    expect(max).toBeGreaterThan(0.98)
    expect(createFxRng(5).range(10, 20)).toBeGreaterThanOrEqual(10)
    expect([1, -1]).toContain(createFxRng(5).sign())
    expect(createFxRng(5).pick(['a'])).toBe('a')
  })
})
