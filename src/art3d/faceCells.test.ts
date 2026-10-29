import { describe, expect, it } from 'vitest'
import { ART } from '../data/tuning.ts'
import { BlinkClock, DriftClock, eyesOpen, glanceToward, layerCells, LAYERS, rectToUv, seededRandom, settle } from './faceCells.ts'
import { FACES, type FaceLayout } from './types.ts'

/** The layout build.py writes (the cell numbers are the real ones from tools/blender/lib/face.py). */
const WHITES = ['open', 'wide', 'arc', 'closed', 'blink', 'strain', 'dizzy', 'pupil']
const LIDS = ['none', 'tired', 'sad', 'angry', 'sick', 'stressed', 'half', 'happy']
const MOUTHS = ['smile', 'grin', 'flat', 'worried', 'frown', 'angry', 'small_o', 'wobble', 'grit', 'wavy', 'big_o', 'spare']
const layout: FaceLayout = {
  sheet: 512,
  cells: {
    white: Object.fromEntries(WHITES.map((n, i) => [n, [(i % 4) * 128, Math.floor(i / 4) * 80, 128, 80]])),
    lid: Object.fromEntries(LIDS.map((n, i) => [n, [(i % 4) * 128, 160 + Math.floor(i / 4) * 80, 128, 80]])),
    mouth: Object.fromEntries(MOUTHS.map((n, i) => [n, [(i % 4) * 128, 320 + Math.floor(i / 4) * 48, 128, 48]])),
    small: { sparkle: [0, 464, 48, 48], sweat: [48, 464, 48, 48] },
  },
  expressions: {
    neutral: { white: 'open', lid: 'none', mouth: 'smile', pupil: true, pupilScale: 1 },
    happy: { white: 'arc', lid: 'happy', mouth: 'grin', pupil: false, pupilScale: 1 },
    tired: { white: 'open', lid: 'tired', mouth: 'flat', pupil: true, pupilScale: 1 },
    stressed: { white: 'open', lid: 'stressed', mouth: 'worried', pupil: true, pupilScale: 0.8 },
    sad: { white: 'open', lid: 'sad', mouth: 'frown', pupil: true, pupilScale: 1 },
    angry: { white: 'open', lid: 'angry', mouth: 'angry', pupil: true, pupilScale: 0.9 },
    sleepy: { white: 'closed', lid: 'none', mouth: 'small_o', pupil: false, pupilScale: 1 },
    sick: { white: 'open', lid: 'sick', mouth: 'wobble', pupil: true, pupilScale: 0.9 },
    strain: { white: 'strain', lid: 'none', mouth: 'grit', pupil: false, pupilScale: 1 },
    dizzy: { white: 'dizzy', lid: 'none', mouth: 'wavy', pupil: false, pupilScale: 1 },
    surprised: { white: 'wide', lid: 'none', mouth: 'big_o', pupil: true, pupilScale: 0.7 },
  },
  layers: [...LAYERS],
  eyeColor: '#24323A',
}

describe('face cells (ART_2_PLAN §3.2)', () => {
  it('every face has a cell for every layer, and the right eye mirrors the left', () => {
    for (const face of FACES) {
      const cells = layerCells(layout, { face, blink: 0 })
      for (const layer of LAYERS) {
        if (layer.startsWith('pupil')) continue
        expect(cells[layer], `${face} ${layer}`).not.toBeNull()
      }
      expect(cells['white.R']!.mirror).toBe(true)
      expect(cells['white.L']!.mirror).toBe(false)
      expect(cells['white.R']!.u0).toBe(cells['white.L']!.u0)
    }
  })

  it('cells are in glTF UV space (v grows downward)', () => {
    expect(rectToUv([128, 320, 128, 48], 512, false)).toEqual({ u0: 0.25, v0: 0.625, w: 0.25, h: 0.09375, mirror: false })
  })

  it('a blink closes open eyes only, and hides the pupils while shut', () => {
    const shut = layerCells(layout, { face: 'neutral', blink: 2 })
    expect(shut['white.L']).toEqual(rectToUv(layout.cells.white.blink!, 512, false))
    expect(shut['pupil.L']).toBeNull()
    const half = layerCells(layout, { face: 'tired', blink: 1 })
    expect(half['lid.L']).toEqual(rectToUv(layout.cells.lid.half!, 512, false))
    expect(half['pupil.L']).not.toBeNull()
    const happy = layerCells(layout, { face: 'happy', blink: 2 })
    expect(happy['white.L']).toEqual(rectToUv(layout.cells.white.arc!, 512, false))
    expect(eyesOpen(layout, 'happy')).toBe(false)
    expect(eyesOpen(layout, 'surprised')).toBe(true)
  })

  it('the blink clock waits, then runs half → closed → half → open, deterministically', () => {
    const clock = new BlinkClock(seededRandom(7))
    const seen: number[] = []
    for (let t = 0; t < 20_000; t += 16) seen.push(clock.step(16))
    expect(seen.includes(2)).toBe(true)
    expect(seen.includes(1)).toBe(true)
    // never jumps straight from open to closed
    for (let i = 1; i < seen.length; i++) expect(Math.abs(seen[i]! - seen[i - 1]!)).toBeLessThanOrEqual(1)
    const closed = seen.filter((p) => p === 2).length * 16
    expect(closed).toBeLessThan(ART.face.blinkCloseMs * 6)
    const again = new BlinkClock(seededRandom(7))
    const seen2: number[] = []
    for (let t = 0; t < 20_000; t += 16) seen2.push(again.step(16))
    expect(seen2).toEqual(seen)
  })

  it('glances slide the pupils a bounded amount and turn the head the same way; they settle back', () => {
    const g = glanceToward(1, 0, 1)
    expect(g.x).toBeCloseTo(ART.face.glanceMax)
    expect(g.yaw).toBeCloseTo(ART.face.headTurnDeg)
    const far = glanceToward(300, 400, 5)
    expect(Math.hypot(far.x, far.y)).toBeCloseTo(ART.face.glanceMax)
    expect(settle(1, ART.face.settleMs)).toBe(0)
    expect(settle(1, ART.face.settleMs / 2)).toBeCloseTo(0.5)
  })

  it('the drift clock wanders within its bounds', () => {
    const d = new DriftClock(seededRandom(3))
    for (let t = 0; t < 30_000; t += 50) {
      const p = d.step(50)
      expect(Math.abs(p.x)).toBeLessThanOrEqual(ART.face.driftMax)
      expect(Math.abs(p.y)).toBeLessThanOrEqual(ART.face.driftMax)
    }
  })
})
