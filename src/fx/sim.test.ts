import { describe, expect, it } from 'vitest'
import { alphaCurve, dirTo, lerpColor, ParticleSim, rampColor, type SpawnSpec } from './sim.ts'

const base: SpawnSpec = { x: 0, y: 0, vx: 100, vy: 0, gravity: 0, drag: 1, lifeMs: 1000, size0: 10, size1: 2, rotation: 0, spin: 0, fadeIn: 0.1, fadeFrom: 0.5, frame: 0, ramp: 0, seed: 0, additive: 0, bounce: 0, alpha: 1 }

describe('ParticleSim (V1 effects: pure particle maths)', () => {
  it('moves by velocity, pulls with gravity and keeps drag per second', () => {
    const sim = new ParticleSim(8)
    sim.spawn({ ...base, vx: 100, vy: 0, gravity: 1000 })
    sim.update(500)
    expect(sim.x[0]).toBeCloseTo(50, 5)
    expect(sim.vy[0]).toBeCloseTo(500, 5)
    expect(sim.y[0]).toBeCloseTo(250, 5)
    const dragged = new ParticleSim(1)
    dragged.spawn({ ...base, vx: 100, drag: 0.5, lifeMs: 5000 })
    dragged.update(1000)
    expect(dragged.vx[0]).toBeCloseTo(50, 5)
  })

  it('dies at the end of its life and swap-removes, telling the mirror array', () => {
    const sim = new ParticleSim(4)
    sim.spawn({ ...base, lifeMs: 100, x: 1 })
    sim.spawn({ ...base, lifeMs: 1000, x: 2 })
    sim.spawn({ ...base, lifeMs: 100, x: 3 })
    const swaps: [number, number][] = []
    const deaths: number[] = []
    const removed = sim.update(
      150,
      (from, to) => swaps.push([from, to]),
      (last) => deaths.push(last),
    )
    expect(removed).toBe(2)
    expect(sim.count).toBe(1)
    expect(sim.x[0]).toBeCloseTo(2 + 15, 4)
    // The first death pulls #3 into slot 0; it is dead too, so the survivor is pulled in after it.
    expect(swaps).toEqual([
      [2, 0],
      [1, 0],
    ])
    expect(deaths).toEqual([2, 1])
  })

  it('never exceeds its capacity', () => {
    const sim = new ParticleSim(2)
    expect(sim.spawn(base)).toBe(0)
    expect(sim.spawn(base)).toBe(1)
    expect(sim.spawn(base)).toBe(-1)
    expect(sim.count).toBe(2)
  })

  it('bounces off the floor when asked and passes through otherwise', () => {
    const sim = new ParticleSim(2)
    sim.spawn({ ...base, y: -10, vx: 0, vy: 100, bounce: 0.5 })
    sim.spawn({ ...base, y: -10, vx: 0, vy: 100, bounce: 0 })
    sim.update(200)
    expect(sim.y[0]).toBeLessThan(0)
    expect(sim.vy[0]).toBeLessThan(0)
    expect(sim.y[1]).toBeGreaterThan(0)
  })

  it('sizes and alpha follow the curves', () => {
    const sim = new ParticleSim(1)
    sim.spawn({ ...base, size0: 10, size1: 0, fadeIn: 0.2, fadeFrom: 0.5 })
    sim.update(500)
    expect(sim.progress(0)).toBeCloseTo(0.5)
    expect(sim.sizeAt(0)).toBeCloseTo(5)
    expect(sim.alphaAt(0)).toBeCloseTo(1)
    const dim = new ParticleSim(1)
    dim.spawn({ ...base, alpha: 0.3, fadeIn: 0 })
    dim.update(100)
    expect(dim.alphaAt(0)).toBeCloseTo(0.3)
    expect(alphaCurve(0, 0.2, 0.5)).toBe(0)
    expect(alphaCurve(0.1, 0.2, 0.5)).toBeCloseTo(0.5)
    expect(alphaCurve(0.75, 0.2, 0.5)).toBeCloseTo(0.25)
    expect(alphaCurve(1, 0.2, 0.5)).toBe(0)
    expect(alphaCurve(0.9, 0, 1)).toBe(1)
  })

  it('interpolates colour ramps', () => {
    expect(lerpColor(0x000000, 0xffffff, 0.5)).toBe(0x808080)
    expect(rampColor([0xff0000, 0x0000ff], 0)).toBe(0xff0000)
    expect(rampColor([0xff0000, 0x0000ff], 1)).toBe(0x0000ff)
    expect(rampColor([0xff0000, 0x00ff00, 0x0000ff], 0.5)).toBe(0x00ff00)
    expect(rampColor([], 0.3)).toBe(0xffffff)
    expect(rampColor([0x123456], 0.9)).toBe(0x123456)
  })

  it('knows which way the other side is', () => {
    expect(dirTo(-200, 200)).toBe(1)
    expect(dirTo(200, -200)).toBe(-1)
  })
})
