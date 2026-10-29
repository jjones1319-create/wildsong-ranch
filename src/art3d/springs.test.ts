import { describe, expect, it } from 'vitest'
import { ART } from '../data/tuning.ts'
import { AccelTracker, ChainSpring, springParams, stepSpring, type SpringState } from './springs.ts'

const DT = 1 / 60

describe('springs (ART_2_PLAN §3.2 secondary motion)', () => {
  it('a steady push settles the swing against the stiffness, under the cap', () => {
    const p = springParams('ear')
    const s: SpringState = { x: 0, y: 0, vx: 0, vy: 0 }
    for (let i = 0; i < 240; i++) stepSpring(s, 10, 0, DT, p)
    expect(s.x).toBeCloseTo(-(p.gain * 10) / p.stiffness, 3)
    expect(Math.abs(s.x)).toBeLessThanOrEqual((p.maxDeg * Math.PI) / 180 + 1e-9)
  })

  it('a huge push is capped at maxDeg and the swing still comes back', () => {
    const p = springParams('tail')
    const s: SpringState = { x: 0, y: 0, vx: 0, vy: 0 }
    for (let i = 0; i < 30; i++) stepSpring(s, 5000, 0, DT, p)
    expect(Math.abs(s.x)).toBeCloseTo((p.maxDeg * Math.PI) / 180, 6)
    for (let i = 0; i < 240; i++) stepSpring(s, 0, 0, DT, p)
    expect(Math.abs(s.x)).toBeLessThan(0.01)
  })

  it('an impulse rings down to rest within two seconds and never blows up on a long frame', () => {
    const p = springParams('default')
    const s: SpringState = { x: 0.3, y: -0.2, vx: 0, vy: 0 }
    let peak = 0
    for (let i = 0; i < 120; i++) {
      stepSpring(s, 0, 0, DT, p)
      peak = Math.max(peak, Math.abs(s.x))
    }
    expect(peak).toBeLessThanOrEqual(0.3 + 1e-9)
    expect(Math.abs(s.x)).toBeLessThan(0.01)
    expect(Math.abs(s.y)).toBeLessThan(0.01)
    const long: SpringState = { x: 0.3, y: 0, vx: 0, vy: 0 }
    stepSpring(long, 0, 0, 0.5, p)
    expect(Number.isFinite(long.x)).toBe(true)
    expect(Math.abs(long.x)).toBeLessThan(0.3)
  })

  it('a chain lags: the tip peaks after the root', () => {
    const chain = new ChainSpring(2, springParams('ear'))
    let rootPeakAt = -1
    let tipPeakAt = -1
    let rootPeak = 0
    let tipPeak = 0
    for (let i = 0; i < 90; i++) {
      const push = i < 6 ? 40 : 0
      const [root, tip] = chain.update(push, 0, DT)
      if (Math.abs(root!.x) > rootPeak) {
        rootPeak = Math.abs(root!.x)
        rootPeakAt = i
      }
      if (Math.abs(tip!.x) > tipPeak) {
        tipPeak = Math.abs(tip!.x)
        tipPeakAt = i
      }
    }
    expect(rootPeak).toBeGreaterThan(0.02)
    expect(tipPeak).toBeGreaterThan(0.01)
    expect(tipPeakAt).toBeGreaterThan(rootPeakAt)
  })

  it('the acceleration tracker reads a parabola and smooths over the tuned frames', () => {
    const t = new AccelTracker()
    const g = -9.8
    let a: readonly number[] = [0, 0, 0]
    for (let i = 0; i < 60; i++) {
      const time = i * DT
      a = t.push([0, 0.5 * g * time * time, 0], DT)
    }
    expect(a[1]).toBeCloseTo(g, 0)
    expect(ART.arena.velocitySmoothFrames).toBeGreaterThan(0)
  })
})
