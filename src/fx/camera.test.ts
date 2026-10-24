import { describe, expect, it } from 'vitest'
import { DEFAULT_CAMERA, sameCamera, worldToScreenX, worldToScreenY, worldTransform } from './camera.ts'

describe('fx camera (world ↔ screen, glued to the arena camera)', () => {
  it('maps the arena centre to the middle and the floor to floorPx above the bottom', () => {
    const cam = { centre: 100, pxPerUnit: 0.5, width: 400, height: 240, floorPx: 40 }
    expect(worldToScreenX(100, cam)).toBe(200)
    expect(worldToScreenX(300, cam)).toBe(300)
    expect(worldToScreenY(0, cam)).toBe(200)
    expect(worldToScreenY(-100, cam)).toBe(150)
    expect(worldTransform(cam)).toEqual({ x: 150, y: 200, scale: 0.5 })
  })

  it('compares cameras by value', () => {
    expect(sameCamera(DEFAULT_CAMERA, { ...DEFAULT_CAMERA })).toBe(true)
    expect(sameCamera(DEFAULT_CAMERA, { ...DEFAULT_CAMERA, centre: 1 })).toBe(false)
  })
})
