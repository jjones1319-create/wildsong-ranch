/**
 * The Vale's ground (docs/WORLD_3D.md §4): Gloamvault's own land assertions (unity/…/Tests/EditMode/LandTests.cs and
 * W17LandTests.cs at commit 588c001) run against Wildsong's TypeScript port, plus the noise against reference values
 * computed by the C# code itself (compiled with PowerShell's Add-Type, Nov 18, 2026), and a golden table of heights
 * frozen after the W0 map check.
 */
import { describe, expect, it } from 'vitest'
import { loadLand } from './data.ts'
import { createLand, SLOT } from './land.ts'
import { fbm, hash, noise, seedHashOf } from './noise.ts'

const data = loadLand()
const land = createLand(data)
const H = (x: number, z: number) => land.heightAt(x, z)
const SEED = seedHashOf(7)

describe('the noise matches Gloamvault’s C#', () => {
  it('hashes bit for bit (float32 values from the C# Hash)', () => {
    const cases: [number, number, number, number][] = [
      [0, 0, 0, 0.4436854], [1, 0, 0, 0.7589826], [0, 1, 0, 0.409970224], [-5, 7, 0, 0.504737854],
      [123456, -98765, 3, 0.06944281], [10, 20, 61, 0.6663754], [-2147483, 2147483, 70, 0.562207758],
    ]
    for (const [ix, iz, salt, want] of cases) expect(hash(SEED, ix, iz, salt)).toBe(Math.fround(want))
  })

  it('samples value noise and fbm to float32 precision', () => {
    const cases: [number, number, number, number, number][] = [
      [123.4, 456.7, 46, 0, -0.19823873], [480, 600, 21, 61, -0.5709208], [1000, 1300, 55, 71, 0.314266562], [-3.5, 12.25, 2.5, 63, 0.3591261],
    ]
    for (const [x, z, scale, salt, want] of cases) expect(noise(SEED, x, z, scale, salt)).toBeCloseTo(want, 5)
    expect(fbm(SEED, 123.4, 456.7, 46, 3)).toBeCloseTo(-0.05916282, 5)
    expect(fbm(SEED, 480, 600, 46, 3)).toBeCloseTo(0.00314606936, 5)
  })
})

describe('the Vale’s ground (Gloamvault LandTests)', () => {
  it('holds the walled town level, sinks the quarry and raises the cave’s knoll', () => {
    const a = H(404, 532)
    expect(Math.abs(a - H(556, 718))).toBeLessThan(0.05)
    expect(Math.abs(a - H(480, 600))).toBeLessThan(0.05)
    expect(H(377, 705)).toBeLessThan(H(377, 735) - 3)
    expect(H(937, 713)).toBeGreaterThan(H(921, 713) + 3)
  })

  it('is the same twice, and the hills rise above the fields', () => {
    const a = H(123.4, 456.7)
    expect(H(123.4, 456.7)).toBe(a)
    expect(createLand(loadLand()).heightAt(123.4, 456.7)).toBe(a)
    expect(H(862, 705)).toBeGreaterThan(H(495, 435) + 8)
    expect(H(480, 600)).toBeGreaterThan(2)
  })

  it('has no cliffs along the King’s Road north (a 2 m step never rises 0.9 m)', () => {
    let prev = H(480, 400)
    for (let z = 398; z >= 60; z -= 2) {
      const h = H(480, z)
      if (land.waterDistance(480, z) > 8) expect(Math.abs(h - prev), `a cliff at z ${z}`).toBeLessThan(0.9)
      prev = h
    }
  })

  it('lays the brook below its banks and fills the pond', () => {
    const level = land.waterLevelAt(480, 321)
    expect(Number.isNaN(level)).toBe(false)
    expect(H(480, 321)).toBeLessThan(level)
    expect(Number.isNaN(land.waterLevelAt(480, 352))).toBe(true)
    expect(H(480, 352)).toBeGreaterThan(level)
    expect(H(588, 354)).toBeLessThan(1.3 - 1.2)
    expect(land.waterLevelAt(588, 354)).toBeCloseTo(1.3, 4)
  })

  it('paves the streets, keeps earth beside them, grass in the churchyard and earth on the door paths', () => {
    expect([SLOT.earth, SLOT.stone]).toContain(land.groundSlot(474.5, 640))
    expect([SLOT.grass, SLOT.grassAlt]).toContain(land.groundSlot(540, 545))
    expect(land.groundSlot(418, 557)).toBe(SLOT.earth)
    expect(land.groundSlot(480, 480)).toBe(SLOT.earth)
    expect([SLOT.grass, SLOT.grassAlt]).toContain(land.groundSlot(455, 480))
    expect(land.groundSlot(480, 700)).toBe(SLOT.stone)
  })

  it('holds the bank’s plot flat', () => {
    const c = H(500.5, 586.5)
    expect(Math.abs(c - H(497, 582))).toBeLessThan(0.02)
    expect(Math.abs(c - H(504, 591))).toBeLessThan(0.02)
  })
})

describe('the Vale’s water and roads (Gloamvault W17LandTests)', () => {
  const road = (id: string) => {
    const r = data.roads.find(x => x.id === id)
    if (!r) throw new Error(`no road ${id}`)
    return r
  }

  it('tells the roads apart', () => {
    expect(land.roadKind(road('kings-road'), 480, 450)).toBe(3)
    expect(land.roadKind(road('kings-road'), 480, 640)).toBe(4)
    expect(land.roadKind(road('field-track'), 435, 495)).toBe(2)
    expect(land.roadKind(road('chapel-path'), 838, 200)).toBe(5)
    expect(land.roadKind(road('boards-mill-jetty'), 602, 370)).toBe(5)
    expect(land.roadKind(road('path-keep'), 418, 556)).toBe(1)
  })

  it('runs the brook west, stills the market and wades the ford', () => {
    const [fx, fz] = land.waterFlowAt(440, 315)
    expect(fx).toBeLessThan(-0.3)
    expect(Math.abs(Math.hypot(fx, fz) - 0.6)).toBeLessThan(0.2)
    expect(land.waterFlowAt(480, 600)).toEqual([0, 0])
    const level = land.waterLevelAt(330, 297.4)
    expect(Number.isNaN(level)).toBe(false)
    expect(H(330, 297.4)).toBeGreaterThan(level - 0.45)
    expect(H(355, 301.3)).toBeLessThan(land.waterLevelAt(355, 301.3) - 0.8)
  })

  it('reads the marsh pools’ levels off their ground', () => {
    const pools = land.water.filter(w => w.id.startsWith('marsh-pool'))
    expect(pools.length).toBeGreaterThanOrEqual(15)
    for (const w of pools) {
      const ground = land.naturalHeight(w.centre[0], w.centre[1])
      expect(w.levelFrom).toBe('')
      expect(w.level).toBeLessThan(ground)
      expect(w.level).toBeGreaterThan(ground - 2.5)
      expect(Number.isNaN(land.waterLevelAt(w.centre[0], w.centre[1]))).toBe(false)
    }
    // The data as loaded stays untouched: the levels were resolved on a copy.
    expect(data.water.find(w => w.id === 'marsh-pool-1')?.levelFrom).toBe('ground')
  })

  it('rises to its edges and runs a deep river east along the south', () => {
    expect(H(300, 1)).toBeGreaterThan(H(300, 45) + 9)
    expect(H(959, 420)).toBeGreaterThan(H(900, 420) + 12)
    expect(H(1, 420)).toBeGreaterThan(H(60, 420) + 4)
    const river = land.waterLevelAt(480, 946)
    expect(Number.isNaN(river)).toBe(false)
    expect(H(480, 925)).toBeGreaterThan(river + 0.8)
    expect(H(480, 946)).toBeLessThan(river - 1)
    expect(land.waterFlowAt(480, 946)[0]).toBeGreaterThan(0.3)
    expect(Math.abs(H(478, 30) - H(478, 24))).toBeLessThan(0.05)
  })
})

describe('the golden heights (frozen Nov 18, 2026, after the W0 map matched Gloamvault’s)', () => {
  it('holds the town, the road north, the brook, the pond, the ranch site, the hills and the edges where they were', () => {
    const golden: [number, number, number][] = [
      [480, 600, 3.917124585], [480, 450, 2.403389475], [480, 321, 0.15], [588, 354, -0.3], [515, 366, 2.504177775],
      [420, 450, 2.714618661], [862, 705, 25.695657667], [377, 705, 3.4802991], [123.4, 456.7, 5.768873034],
      [300, 1, 20.003315332], [480, 946, 1.664379865], [330, 297.4, 0.93], [640, 250, 2.103138057],
    ]
    for (const [x, z, y] of golden) expect(H(x, z), `(${x}, ${z})`).toBeCloseTo(y, 6)
    expect(land.town?.height).toBeCloseTo(3.917124585, 6)
  })
})

describe('the places', () => {
  it('names the market inside the streets, and the area round the town', () => {
    expect(land.placeAt(480, 600)?.id).toBe('market')
    expect(land.placeAt(470, 680)?.id).toBe('ashbrook-streets')
    expect(land.areaAt(480, 600)?.id).toBe('ashbrook')
    expect(land.inStreets(480, 600)).toBe(true)
    expect(land.inStreets(480, 450)).toBe(false)
  })
})
