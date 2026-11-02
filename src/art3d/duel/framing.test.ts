import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { bandNeed, sideFraming } from './framing.ts'

/** docs/BATTLE_3D.md §6: the side-on camera framed for an upright or a sideways phone. */
describe('side-on framing', () => {
  const P = ART.duel.side.portrait
  const L = ART.duel.side.landscape

  it('upright is the three-quarter view, sideways nearly square, and it blends between', () => {
    expect(sideFraming(412 / 892)).toEqual({ yawDeg: P.yawDeg, elevationDeg: P.elevationDeg, band: P.band })
    expect(sideFraming(892 / 412)).toEqual({ yawDeg: L.yawDeg, elevationDeg: L.elevationDeg, band: L.band })
    const mid = sideFraming((P.aspect + L.aspect) / 2)
    expect(mid.yawDeg).toBeCloseTo((P.yawDeg + L.yawDeg) / 2)
    expect(mid.band.right).toBeLessThan(P.band.right)
    expect(mid.band.right).toBeGreaterThan(L.band.right)
  })

  it('sideways keeps the pair left of the cards', () => {
    const b = sideFraming(2).band
    expect((b.left + b.right) / 2).toBeLessThan(0)
    expect(b.right).toBeLessThan(0.5)
  })

  it('bandNeed: 1 on the band edge, under 1 inside, over 1 outside', () => {
    const b = { left: -0.9, right: 0.3, top: 0.5, bottom: -0.6 }
    expect(bandNeed(0.3, -0.05, b)).toBeCloseTo(1)
    expect(bandNeed(-0.9, -0.05, b)).toBeCloseTo(1)
    expect(bandNeed(-0.3, 0.5, b)).toBeCloseTo(1)
    expect(bandNeed(-0.3, -0.05, b)).toBeCloseTo(0)
    expect(bandNeed(0.6, 0, b)).toBeGreaterThan(1)
  })
})
