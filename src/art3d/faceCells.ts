import { ART } from '../data/tuning.ts'
import type { FaceLayout, FaceName, Rect } from './types.ts'

/**
 * The face controller's pure half (ART_2_PLAN §3.2): which cell of the Blender-made face sheet each head patch
 * shows for an expression, mid-blink or not, and the blink and glance clocks. No three, no DOM.
 */

export const LAYERS = ['white.L', 'pupil.L', 'lid.L', 'white.R', 'pupil.R', 'lid.R', 'mouth'] as const
export type Layer = (typeof LAYERS)[number]

/** A cell as the shader wants it: glTF UV space (v grows downward), plus whether to mirror u. */
export interface CellUv {
  u0: number
  v0: number
  w: number
  h: number
  mirror: boolean
}

export interface FaceState {
  face: FaceName
  /** 0 open, 1 half closed, 2 closed. */
  blink: 0 | 1 | 2
}

export function rectToUv(rect: Rect, sheet: number, mirror: boolean): CellUv {
  const [x, y, w, h] = rect
  return { u0: x / sheet, v0: y / sheet, w: w / sheet, h: h / sheet, mirror }
}

/** True when the expression's eyes are open (so a blink changes them). */
export function eyesOpen(layout: FaceLayout, face: FaceName): boolean {
  const ex = layout.expressions[face]
  return !!ex && (ex.white === 'open' || ex.white === 'wide')
}

/** The cell every layer shows (null = hidden). The right eye mirrors the left. */
export function layerCells(layout: FaceLayout, state: FaceState): Record<Layer, CellUv | null> {
  const ex = layout.expressions[state.face] ?? layout.expressions.neutral!
  const open = eyesOpen(layout, state.face)
  const sheet = layout.sheet
  const cells = layout.cells
  let white = cells.white[ex.white]!
  let lid = cells.lid[ex.lid]!
  let pupil = ex.pupil
  if (open && state.blink === 2) {
    white = cells.white.blink!
    lid = cells.lid.none!
    pupil = false
  } else if (open && state.blink === 1) {
    lid = cells.lid.half!
  }
  const mouth = cells.mouth[ex.mouth]!
  const pupilRect = cells.white.pupil!
  return {
    'white.L': rectToUv(white, sheet, false),
    'pupil.L': pupil ? rectToUv(pupilRect, sheet, false) : null,
    'lid.L': rectToUv(lid, sheet, false),
    'white.R': rectToUv(white, sheet, true),
    'pupil.R': pupil ? rectToUv(pupilRect, sheet, true) : null,
    'lid.R': rectToUv(lid, sheet, true),
    mouth: rectToUv(mouth, sheet, false),
  }
}

export function pupilScale(layout: FaceLayout, face: FaceName): number {
  return layout.expressions[face]?.pupilScale ?? 1
}

/** Random blinks: a gap, then half → closed → half → open, with the odd double blink. */
export class BlinkClock {
  phase: 0 | 1 | 2 = 0
  private wait: number
  private seq: (0 | 1 | 2)[] = []
  private seqT = 0
  private readonly rng: () => number

  constructor(rng: () => number) {
    this.rng = rng
    this.wait = this.gap()
  }

  private gap(): number {
    return ART.face.blinkMinMs + this.rng() * (ART.face.blinkMaxMs - ART.face.blinkMinMs)
  }

  /** Advance by dt ms; returns the eye phase to show. */
  step(dt: number): 0 | 1 | 2 {
    if (this.seq.length === 0) {
      this.wait -= dt
      if (this.wait <= 0) {
        this.seq = [1, 2, 1]
        this.seqT = 0
      }
      this.phase = 0
      return 0
    }
    this.seqT += dt
    const stepMs = ART.face.blinkCloseMs / 3
    const i = Math.floor(this.seqT / stepMs)
    if (i >= this.seq.length) {
      this.seq = []
      this.phase = 0
      this.wait = this.rng() < ART.face.doubleBlinkChance ? 180 : this.gap()
      return 0
    }
    this.phase = this.seq[i]!
    return this.phase
  }
}

export interface Glance {
  /** The pupil slide in cell units (−glanceMax…glanceMax). */
  x: number
  y: number
  /** The head turn in degrees (yaw, pitch). */
  yaw: number
  pitch: number
}

/**
 * Where to look: a direction in the host's plane (−1…1 each) scaled by reach; eyes slide a share of the cell
 * and the head turns a little the same way.
 */
export function glanceToward(dx: number, dy: number, reach: number): Glance {
  const len = Math.hypot(dx, dy) || 1
  const k = Math.min(1, Math.max(0, reach))
  const nx = (dx / len) * k
  const ny = (dy / len) * k
  return { x: nx * ART.face.glanceMax, y: ny * ART.face.glanceMax, yaw: nx * ART.face.headTurnDeg, pitch: ny * ART.face.headTurnDeg }
}

/** Eases a glance back toward rest: returns the new value after dt. */
export function settle(value: number, dt: number): number {
  const k = Math.min(1, dt / ART.face.settleMs)
  return value * (1 - k)
}

/** Idle eye wander: picks a small random target every few seconds. */
export class DriftClock {
  x = 0
  y = 0
  private wait = 0
  private readonly rng: () => number

  constructor(rng: () => number) {
    this.rng = rng
  }

  step(dt: number): { x: number; y: number } {
    this.wait -= dt
    if (this.wait <= 0) {
      this.wait = ART.face.driftMinMs + this.rng() * (ART.face.driftMaxMs - ART.face.driftMinMs)
      this.x = (this.rng() * 2 - 1) * ART.face.driftMax
      this.y = (this.rng() * 2 - 1) * ART.face.driftMax * 0.5
    }
    return { x: this.x, y: this.y }
  }
}

/** A tiny seeded generator for blinks and glances, so review screenshots repeat (never the game RNG). */
export function seededRandom(seed: number): () => number {
  let s = (seed >>> 0) || 1
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 4294967296
  }
}
