import { PerspectiveCamera, Texture, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import { QuadBatch } from './fxBatch.ts'
import { MOVE, ParticlePool, noise, place } from './fxParticles.ts'

/** docs/BATTLE_3D.md §7: the attack effects' particles and their two draws. */
describe('attack effect particles', () => {
  const anchors = [new Vector3(0, 0.5, 0), new Vector3(3, 0.5, 0)]
  const pos = new Vector3()
  const vel = new Vector3()

  it('a projectile arrives on its target at its travel time, flies on past, and veers aside on a miss', () => {
    const pool = new ParticlePool(8)
    const p = pool.spawn()
    Object.assign(p, { move: MOVE.path, from: 0, anchor: 1, t0: 1, travel: 0.25, life: 0.6, arc: 0.2 })
    place(p, 1.25, anchors, pos, vel)
    expect(pos.distanceTo(anchors[1]!)).toBeLessThan(1e-6)
    place(p, 1.375, anchors, pos, vel)
    expect(pos.x).toBeCloseTo(4.5)
    Object.assign(p, { devX: 0, devZ: 0.75, devAt: 1.2 })
    place(p, 1.4, anchors, pos, vel)
    expect(pos.z).toBeCloseTo(0.75)
  })

  it('a missed shot slows from the veer, swings aside and dips to the floor by devSec', () => {
    const pool = new ParticlePool(8)
    const p = pool.spawn()
    Object.assign(p, { move: MOVE.path, from: 0, anchor: 1, t0: 0, travel: 0.3, life: 1, arc: 0 })
    place(p, 0.25, anchors, pos, vel)
    const atVeer = pos.x
    Object.assign(p, { devAt: 0.25, devX: 0, devZ: 0.75, veerSec: 0.1, slow: 0.4, devY: -0.44, devSec: 0.2 })
    place(p, 0.45, anchors, pos, vel)
    // on at 40% of its speed (3 m in 0.3 s → 4 m/s for 0.2 s)
    expect(pos.x - atVeer).toBeCloseTo(0.4 * 10 * 0.2)
    expect(pos.z).toBeCloseTo(0.75)
    expect(pos.y).toBeCloseTo(0.06)
    // halfway down it is still heading down
    place(p, 0.35, anchors, pos, vel)
    expect(pos.y).toBeGreaterThan(0.06)
    expect(vel.y).toBeLessThan(0)
  })

  it('a gust ribbon circles its centre on a widening, rising spiral, heading round it', () => {
    const pool = new ParticlePool(8)
    const g = Object.assign(pool.spawn(), { move: MOVE.orbit, anchor: -1, tx: 1, ty: 0.1, tz: 2, x: 0.5, y: 0.2, z: 0, swirl: 9, widen: 1, vy: 0.5, t0: 0, life: 0.6 })
    place(g, 0, anchors, pos, vel)
    expect(Math.hypot(pos.x - 1, pos.z - 2)).toBeCloseTo(0.5)
    expect(pos.y).toBeCloseTo(0.3)
    // round (tangent), not out
    expect(Math.abs(vel.z)).toBeGreaterThan(Math.abs(vel.x))
    place(g, 0.4, anchors, pos, vel)
    expect(Math.hypot(pos.x - 1, pos.z - 2)).toBeCloseTo(0.5 * 1.4)
    expect(pos.y).toBeCloseTo(0.5)
  })

  it('a gathering mote ends on its anchor; a thrown one falls with gravity', () => {
    const pool = new ParticlePool(8)
    const m = Object.assign(pool.spawn(), { move: MOVE.gather, anchor: 0, x: 0.6, y: 0.2, z: -0.4, swirl: 5, t0: 0, life: 0.3 })
    place(m, 0.3, anchors, pos, vel)
    expect(pos.distanceTo(anchors[0]!)).toBeLessThan(1e-6)
    const f = Object.assign(pool.spawn(), { move: MOVE.free, y: 1, vy: 0, g: 10, t0: 0, life: 1 })
    place(f, 0.2, anchors, pos, vel)
    expect(pos.y).toBeCloseTo(0.8)
  })

  it('reuses dead particles first, then gives way in turn (never the newest); ids tell a reused particle apart', () => {
    const pool = new ParticlePool(3)
    const a = pool.spawn()
    const b = pool.spawn()
    const c = pool.spawn()
    b.alive = false
    expect(pool.spawn()).toBe(b)
    const ids = [a.id, b.id, c.id]
    const next = pool.spawn()
    expect(next).not.toBe(b)
    expect(ids).not.toContain(next.id)
  })

  it('draws everything in at most two draws, writes nothing once they are gone, and the noise repeats', () => {
    const tex = new Texture()
    const glow = new QuadBatch(16, tex, true)
    const solid = new QuadBatch(16, tex, false)
    const camera = new PerspectiveCamera()
    camera.updateMatrixWorld()
    const pool = new ParticlePool(16)
    for (let i = 0; i < 10; i++) Object.assign(pool.spawn(), { glow: i % 2 === 0, t0: 0, life: 1, s0: 0.1, s1: 0.1 })
    const frame = (now: number) => {
      glow.begin()
      solid.begin()
      pool.draw(now, anchors, camera, glow, solid)
      glow.end()
      solid.end()
    }
    frame(0.5)
    expect([glow.count, solid.count]).toEqual([5, 5])
    expect(glow.mesh.visible && solid.mesh.visible).toBe(true)
    frame(2)
    expect(glow.count + solid.count).toBe(0)
    expect(glow.mesh.visible || solid.mesh.visible).toBe(false)
    expect(noise(42)).toBe(noise(42))
    expect(noise(42)).not.toBe(noise(43))
  })
})
