import { PerspectiveCamera, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import { ART } from '../data/tuning.ts'
import { worldToScreenX, worldToScreenY } from '../fx/camera.ts'
import { zoomBounds } from '../ui/battle/camera.ts'
import { cameraNumbers, floorScreenX, portraitCamera, sameStageCamera, type StageCamera } from './arenaCamera.ts'

/** Pixel position (from the left, from the bottom) of a world point through the three camera these numbers make. */
function project(c: StageCamera, x: number, y: number, z: number): { px: number; pyFromBottom: number } {
  const n = cameraNumbers(c)
  const cam = new PerspectiveCamera(n.fovDeg, n.aspect, n.near, n.far)
  cam.position.set(...n.position)
  cam.lookAt(new Vector3(...n.lookAt))
  cam.updateMatrixWorld(true)
  cam.updateProjectionMatrix()
  const v = new Vector3(x, y, z).project(cam)
  return { px: ((v.x + 1) / 2) * c.width, pyFromBottom: ((v.y + 1) / 2) * c.height }
}

describe('the stage camera (ART_2_PLAN §7.3: feet on the floor line at every zoom)', () => {
  it('reproduces the arena mapping on the floor plane for every phone size and zoom', () => {
    for (const width of [320, 360, 412, 430]) {
      for (const height of [190, 220, 260, 300]) {
        const { min, max } = zoomBounds(width, height)
        for (const pxPerUnit of [min, (min + max) / 2, max]) {
          for (const centre of [-150, 0, 220]) {
            const c: StageCamera = { centre, pxPerUnit, width, height, floorPx: 40 }
            const fx = { centre, pxPerUnit, width, height, floorPx: 40 }
            for (const x of [-500, -120, 0, 90, 480]) {
              const feet = project(c, x, 0, 0)
              expect(feet.px).toBeCloseTo(worldToScreenX(x, fx), 3)
              expect(feet.px).toBeCloseTo(floorScreenX(x, c), 3)
              expect(feet.pyFromBottom).toBeCloseTo(40, 3)
              // a point 100 units up sits 100 · pxPerUnit above the floor (the fx layer's y grows downward)
              const chest = project(c, x, 100, 0)
              expect(chest.pyFromBottom).toBeCloseTo(height - worldToScreenY(-100, fx), 3)
            }
          }
        }
      }
    }
  })

  it('keeps a long lens: the field of view stays narrow across the zoom range', () => {
    const { min, max } = zoomBounds(360, 240)
    expect(cameraNumbers({ centre: 0, pxPerUnit: min, width: 360, height: 240, floorPx: 40 }).fovDeg).toBeLessThan(24)
    expect(cameraNumbers({ centre: 0, pxPerUnit: max, width: 430, height: 300, floorPx: 40 }).fovDeg).toBeGreaterThan(4)
  })

  it('depth is mild: a point 60 units toward the camera moves less than 3 % at the widest zoom', () => {
    const { min } = zoomBounds(360, 240)
    const c: StageCamera = { centre: 0, pxPerUnit: min, width: 360, height: 240, floorPx: 40 }
    const flat = project(c, 200, 0, 0)
    const near = project(c, 200, 0, 60)
    expect(Math.abs(near.px - flat.px) / 200).toBeLessThan(0.03 * min)
  })

  it('the portrait camera frames the body with its feet on the Classic ground line', () => {
    const c = portraitCamera(200, 150)
    expect(c.width).toBe(200)
    expect(c.floorPx).toBeCloseTo(200 * ART.portrait.floorFrac)
    expect(c.pxPerUnit * 150).toBeCloseTo(200 * ART.portrait.bodyFrac)
    const flat = { ...c, pitchDeg: 0 }
    expect(project(flat, 0, 0, 0).pyFromBottom).toBeCloseTo(c.floorPx, 3)
    expect(sameStageCamera(c, { ...c })).toBe(true)
    expect(sameStageCamera(c, { ...c, pitchDeg: 0 })).toBe(false)
    expect(sameStageCamera(null, c)).toBe(false)
  })
})
