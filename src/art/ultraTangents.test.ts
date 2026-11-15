import { describe, expect, it } from 'vitest'
import { perpendicular, rebuildTangents, TANGENT_MIN } from '../../tools/art/ultra-tangents.ts'

// a unit quad in the XY plane facing +Z, u along +X and v along +Y: its true tangent is +X
const POS = [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]
const NRM = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1]
const UV = [0, 0, 1, 0, 1, 1, 0, 1]
const IDX = [0, 1, 2, 0, 2, 3]

const unit = (t: number[], i: number) => Math.hypot(t[4 * i]!, t[4 * i + 1]!, t[4 * i + 2]!)

describe('zero-length tangents (tools/art/ultra-tangents.ts)', () => {
  it('rebuilds a zero tangent from the UV direction, keeping its w sign', () => {
    const tan = [0, 0, 0, -1, 1, 0, 0, -1, 1, 0, 0, -1, 1, 0, 0, -1]
    expect(rebuildTangents(POS, NRM, UV, tan, IDX)).toEqual([0])
    expect(tan.slice(0, 4).map((v) => Math.round(v * 1e6) / 1e6)).toEqual([1, 0, 0, -1])
  })

  it('a near-zero tangent counts too; a whole one is left as it was', () => {
    const tan = [1, 0, 0, 1, 0, TANGENT_MIN / 2, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1]
    expect(rebuildTangents(POS, NRM, UV, tan, IDX)).toEqual([1])
    expect(tan.slice(0, 4)).toEqual([1, 0, 0, 1])
    expect(unit(tan, 1)).toBeCloseTo(1, 6)
  })

  it('without UVs it takes its neighbours’ tangent, made perpendicular to its normal', () => {
    const nrm = [...NRM]
    nrm.splice(0, 3, 0, Math.SQRT1_2, Math.SQRT1_2)            // a tilted normal at vertex 0
    const tan = [0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1]
    rebuildTangents(POS, nrm, null, tan, IDX)
    const t = tan.slice(0, 3)
    expect(unit(tan, 0)).toBeCloseTo(1, 6)
    expect(t[0]! * nrm[0]! + t[1]! * nrm[1]! + t[2]! * nrm[2]!).toBeCloseTo(0, 6)
    expect(t[0]).toBeCloseTo(1, 6)
  })

  it('with nothing to go on (a sliver, all tangents zero) it is any perpendicular to the normal; a zero w becomes +1', () => {
    const pos = [0, 0, 0, 1, 0, 0, 2, 0, 0]                     // a sliver: three points in a line
    const nrm = [0, 0, 1, 0, 0, 1, 0, 0, 1]
    const uv = [0, 0, 0.5, 0, 1, 0]
    const tan = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    expect(rebuildTangents(pos, nrm, uv, tan, null)).toEqual([0, 1, 2])
    for (let i = 0; i < 3; i++) {
      expect(unit(tan, i)).toBeCloseTo(1, 6)
      expect(tan[4 * i + 2]).toBeCloseTo(0, 6)
      expect(tan[4 * i + 3]).toBe(1)
    }
  })

  it('leaves NaN and infinite tangents alone (the ship still refuses them)', () => {
    const tan = [Number.NaN, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, Infinity, 0, 0, 1]
    expect(rebuildTangents(POS, NRM, UV, tan, IDX)).toEqual([])
    expect(Number.isNaN(tan[0])).toBe(true)
  })

  it('perpendicular() is a unit vector at right angles to any normal', () => {
    for (const n of [[0, 0, 1], [1, 0, 0], [0, 1, 0], [0.6, 0.8, 0]] as [number, number, number][]) {
      const p = perpendicular(n)
      expect(Math.hypot(...p)).toBeCloseTo(1, 9)
      expect(p[0] * n[0] + p[1] * n[1] + p[2] * n[2]).toBeCloseTo(0, 9)
    }
  })
})
