import { describe, expect, it } from 'vitest'
import { createRng } from '../../core/rng.ts'
import { BATTLE, BATTLE_CAMERA } from '../../data/tuning.ts'
import { frameCamera, screenX, spriteScale, stepCamera, WORLD_HALF, zoomBounds, type Camera, type CameraTarget } from './camera.ts'

const EPS = 1e-6
const WALL = BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius
const HALF = BATTLE_CAMERA.spriteHalf

/** A random position inside the engine's wall clamp (|x| ≤ halfWidth − bodyRadius). */
const randomX = (rng: ReturnType<typeof createRng>) => rng.nextInt(-WALL, WALL)

function boxes(xA: number, xB: number, width: number, cam: CameraTarget): [number, number][] {
  return [xA, xB].map((x) => [screenX(x - HALF, cam, width), screenX(x + HALF, cam, width)] as [number, number])
}

describe('frameCamera', () => {
  it('keeps both sprite boxes inside the arena and the zoom inside its bounds for 10,000 random frames', () => {
    const rng = createRng(1210)
    for (let i = 0; i < 10_000; i++) {
      const xA = randomX(rng)
      const xB = randomX(rng)
      const width = rng.nextInt(320, 1024)
      const height = rng.nextInt(190, 400)
      const cam = frameCamera({ xA, xB, width, height })
      const bounds = zoomBounds(width, height)
      expect(cam.pxPerUnit).toBeGreaterThanOrEqual(bounds.min - EPS)
      expect(cam.pxPerUnit).toBeLessThanOrEqual(bounds.max + EPS)
      for (const [l, r] of boxes(xA, xB, width, cam)) {
        expect(l).toBeGreaterThanOrEqual(-EPS)
        expect(r).toBeLessThanOrEqual(width + EPS)
      }
      // Never past the walls (plus the overhang) either.
      const visibleHalf = width / (2 * cam.pxPerUnit)
      if (visibleHalf <= WORLD_HALF) {
        expect(cam.centre - visibleHalf).toBeGreaterThanOrEqual(-WORLD_HALF - EPS)
        expect(cam.centre + visibleHalf).toBeLessThanOrEqual(WORLD_HALF + EPS)
      } else expect(cam.centre).toBe(0)
    }
  })

  it('centres on the midpoint and fills the width with the span plus margins when unclamped', () => {
    const cam = frameCamera({ xA: -230, xB: 230, width: 360, height: 240 })
    expect(cam.centre).toBe(0)
    const span = 460 + 2 * HALF + 2 * BATTLE_CAMERA.margin
    expect(cam.pxPerUnit).toBeCloseTo(360 / span, 9)
    expect(screenX(-230 - HALF, cam, 360)).toBeCloseTo(BATTLE_CAMERA.margin * cam.pxPerUnit, 9)
    expect(screenX(230 + HALF, cam, 360)).toBeCloseTo(360 - BATTLE_CAMERA.margin * cam.pxPerUnit, 9)
  })

  it('caps the zoom so a sprite is at most maxSpritePct of the width and leaves reservePx of height', () => {
    const tight = frameCamera({ xA: -40, xB: 40, width: 360, height: 400 })
    expect(tight.pxPerUnit * 2 * HALF).toBeCloseTo((360 * BATTLE_CAMERA.maxSpritePct) / 100, 9)
    const short = frameCamera({ xA: -40, xB: 40, width: 360, height: 190 })
    expect(short.pxPerUnit * 2 * HALF).toBeCloseTo(190 - BATTLE_CAMERA.reservePx, 9)
    expect(spriteScale(short)).toBeCloseTo((190 - BATTLE_CAMERA.reservePx) / BATTLE_CAMERA.basePx, 9)
  })

  it('shows the whole arena, and no further, when the monsters are at opposite walls', () => {
    const cam = frameCamera({ xA: -WALL, xB: WALL, width: 360, height: 240 })
    expect(cam.pxPerUnit).toBeCloseTo(360 / (2 * WORLD_HALF), 9)
    expect(cam.centre).toBe(0)
    expect(screenX(-WORLD_HALF, cam, 360)).toBeCloseTo(0, 9)
    expect(screenX(WORLD_HALF, cam, 360)).toBeCloseTo(360, 9)
  })

  it('clamps the view at a wall when both monsters are in one corner', () => {
    const cam = frameCamera({ xA: WALL - 200, xB: WALL, width: 360, height: 240 })
    const visibleHalf = 360 / (2 * cam.pxPerUnit)
    expect(cam.centre + visibleHalf).toBeCloseTo(WORLD_HALF, 9)
    expect(cam.centre).toBeLessThan((2 * WALL - 200) / 2)
  })

  it('is continuous: one unit of movement moves the centre by at most 2 units and the zoom by under 1 %', () => {
    const rng = createRng(77)
    for (let i = 0; i < 5000; i++) {
      const xA = rng.nextInt(-WALL, WALL - 1)
      const xB = randomX(rng)
      const width = rng.nextInt(320, 1024)
      const height = rng.nextInt(190, 400)
      const a = frameCamera({ xA, xB, width, height })
      const b = frameCamera({ xA: xA + 1, xB, width, height })
      expect(Math.abs(b.centre - a.centre)).toBeLessThanOrEqual(2)
      expect(Math.abs(b.pxPerUnit - a.pxPerUnit) / a.pxPerUnit).toBeLessThan(0.01)
    }
  })
})

describe('stepCamera', () => {
  const from: Camera = { centre: -200, pxPerUnit: 0.4, vCentre: 0, vPx: 0 }
  const to: CameraTarget = { centre: 100, pxPerUnit: 0.7 }

  it('snaps to the target on the first call', () => {
    expect(stepCamera(null, to, 16, false)).toEqual({ ...to, vCentre: 0, vPx: 0 })
  })

  it('springs to the target without overshooting and settles exactly', () => {
    let cam = from
    let prev = from.centre
    for (let i = 0; i < 400; i++) {
      cam = stepCamera(cam, to, 16.7, false)
      expect(cam.centre).toBeGreaterThanOrEqual(prev - EPS)
      expect(cam.centre).toBeLessThanOrEqual(to.centre + EPS)
      expect(cam.pxPerUnit).toBeGreaterThanOrEqual(from.pxPerUnit - EPS)
      expect(cam.pxPerUnit).toBeLessThanOrEqual(to.pxPerUnit + EPS)
      prev = cam.centre
    }
    expect(cam.centre).toBe(to.centre)
    expect(cam.pxPerUnit).toBe(to.pxPerUnit)
    expect(cam.vCentre).toBe(0)
    // Converged within about a second.
    let fast = from
    for (let i = 0; i < 60; i++) fast = stepCamera(fast, to, 16.7, false)
    expect(Math.abs(fast.centre - to.centre)).toBeLessThan(1)
  })

  it('is stable for a long frame', () => {
    const cam = stepCamera(from, to, 100, false)
    expect(cam.centre).toBeGreaterThanOrEqual(from.centre)
    expect(cam.centre).toBeLessThanOrEqual(to.centre)
    expect(Number.isFinite(cam.vCentre)).toBe(true)
  })

  it('stays put at rest', () => {
    const at: Camera = { ...to, vCentre: 0, vPx: 0 }
    expect(stepCamera(at, to, 16, false)).toEqual(at)
    expect(stepCamera(at, to, 16, true)).toEqual(at)
  })

  it('eases monotonically with reduced motion', () => {
    let cam = from
    let prev = from.centre
    for (let i = 0; i < 200; i++) {
      cam = stepCamera(cam, to, 16.7, true)
      expect(cam.centre).toBeGreaterThanOrEqual(prev - EPS)
      expect(cam.centre).toBeLessThanOrEqual(to.centre + EPS)
      expect(cam.vCentre).toBe(0)
      prev = cam.centre
    }
    expect(cam.centre).toBe(to.centre)
    expect(cam.pxPerUnit).toBe(to.pxPerUnit)
  })
})
