import { describe, expect, it } from 'vitest'
import { INPUT } from '../../../data/tuning.ts'
import { flickIntent, stickIntent, type ScreenBasis } from './stickMath.ts'

/** docs/BATTLE_3D.md §5: the stick reads against the camera. */

// side-on: the opponent is to the right on screen, the monster's left is "up" the screen (away from the camera)
const side: ScreenBasis = { fwd: { x: 1, y: 0 }, left: { x: 0, y: -1 } }
// behind: the opponent is up the screen, the monster's left is the screen's left
const behind: ScreenBasis = { fwd: { x: 0, y: -1 }, left: { x: -1, y: 0 } }

describe('the Battle 3D stick', () => {
  it('walks toward the opponent and strafes, whatever the camera', () => {
    expect(stickIntent({ x: 0.9, y: 0 }, side)).toEqual({ dir: 1, side: 0 })
    expect(stickIntent({ x: 0, y: -0.9 }, behind)).toEqual({ dir: 1, side: 0 })
    expect(stickIntent({ x: -0.9, y: 0 }, side)).toEqual({ dir: -1, side: 0 })
    expect(stickIntent({ x: 0, y: -0.9 }, side)).toEqual({ dir: 0, side: 1 })
    expect(stickIntent({ x: -0.9, y: 0 }, behind)).toEqual({ dir: 0, side: 1 })
    expect(stickIntent({ x: 0.7, y: -0.7 }, side)).toEqual({ dir: 1, side: 1 })
  })

  it('ignores small wobbles near the centre', () => {
    expect(stickIntent({ x: INPUT.stick.dead * 0.9, y: 0 }, side)).toEqual({ dir: 0, side: 0 })
  })

  it('a quick sideways flick sidesteps; a quick forward flick dashes; slow drags do neither', () => {
    expect(flickIntent({ x: -1, y: 0 }, 120, behind)).toEqual({ kind: 'sidestep', dir: 1 })
    expect(flickIntent({ x: 1, y: 0 }, 120, behind)).toEqual({ kind: 'sidestep', dir: -1 })
    expect(flickIntent({ x: 0, y: -1 }, 120, behind)).toEqual({ kind: 'dash' })
    expect(flickIntent({ x: 0, y: 1 }, 120, behind)).toBeNull()
    expect(flickIntent({ x: -1, y: 0 }, INPUT.stick.flickMs + 50, behind)).toBeNull()
    expect(flickIntent({ x: -0.5, y: 0 }, 120, behind)).toBeNull()
  })
})
