import { ART } from '../data/tuning.ts'
import type { ClipName, FaceName } from './types.ts'

/**
 * Battles until P11 (ART_2_PLAN §5): the arena's fighter flags and bus events mapped to the nearest ★ clip.
 * Pure, so every branch is unit-tested. Edge flags (`hit`, `hitHeavy`, `lunge`, `shove`, `dash`) are true only
 * on the frame they fire; the player latches the one-shot they start.
 */

export interface FighterSignals {
  ko: boolean
  win: boolean
  hitHeavy: boolean
  hit: boolean
  stunned: boolean
  busy: boolean
  lunge: boolean
  /** Busy with a far technique (the bus said `ranged`). */
  ranged: boolean
  shove: boolean
  dash: boolean
  dawdling: boolean
  /** Arena units per second, signed. */
  vx: number
  /** +1 faces right (toward +x), −1 faces left. */
  facing: 1 | -1
  lowHp: boolean
  /** The screen's own face override, if any. */
  expression?: FaceName | null
}

export type ClipKind = 'hit' | 'action' | 'move' | 'idle'

export interface ClipChoice {
  clip: ClipName
  kind: ClipKind
  face: FaceName | null
  /** The player sets the rate from the real speed and the clip's root speed. */
  speedDriven: boolean
}

export const IDLE_SIGNALS: FighterSignals = {
  ko: false, win: false, hitHeavy: false, hit: false, stunned: false, busy: false, lunge: false, ranged: false,
  shove: false, dash: false, dawdling: false, vx: 0, facing: 1, lowHp: false, expression: null,
}

export function battleClipFor(s: FighterSignals, dashSpeed: number): ClipChoice {
  if (s.ko) return { clip: 'ko', kind: 'hit', face: 'sleepy', speedDriven: false }
  if (s.win) return { clip: 'win', kind: 'idle', face: 'happy', speedDriven: false }
  if (s.hitHeavy) return { clip: 'hit_heavy', kind: 'hit', face: 'strain', speedDriven: false }
  if (s.hit) return { clip: 'hit', kind: 'hit', face: 'surprised', speedDriven: false }
  if (s.stunned) return { clip: 'dizzy', kind: 'idle', face: 'dizzy', speedDriven: false }
  if (s.lunge) return { clip: 'strike', kind: 'action', face: 'angry', speedDriven: false }
  if (s.shove) return { clip: 'shove', kind: 'action', face: null, speedDriven: false }
  if (s.busy && s.ranged) return { clip: 'cast', kind: 'action', face: null, speedDriven: false }
  if (s.busy) return { clip: 'strike', kind: 'action', face: 'angry', speedDriven: false }
  const toward = s.vx * s.facing
  if (s.dash || Math.abs(s.vx) >= dashSpeed * ART.arena.dashShare) return { clip: 'dash', kind: 'move', face: null, speedDriven: true }
  if (s.dawdling) return { clip: 'look_around', kind: 'idle', face: null, speedDriven: false }
  if (toward > ART.arena.standingSpeed) return { clip: 'step_fwd', kind: 'move', face: null, speedDriven: true }
  if (toward < -ART.arena.standingSpeed) return { clip: 'step_back', kind: 'move', face: null, speedDriven: true }
  return { clip: 'battle_idle', kind: 'idle', face: s.lowHp ? 'tired' : (s.expression ?? null), speedDriven: false }
}

/** The ranch's idle picker: the cues' expression chooses the idle; the mood clips carry their own faces. */
export function ranchIdleFor(expression: FaceName, sparkle: boolean, sleeping: boolean): ClipName {
  if (sleeping) return 'sleep'
  if (expression === 'sick') return 'idle_sick'
  if (expression === 'tired') return 'idle_tired'
  if (expression === 'sad') return 'idle_sad'
  if (expression === 'happy' || sparkle) return 'idle_happy'
  return 'idle'
}

/** Picks an occasional ranch action by the tuned weights; `roll` is 0…1 from the stage's own generator. */
export function ranchActionFor(roll: number): ClipName {
  const entries = Object.entries(ART.anim.actWeights) as [ClipName, number][]
  const total = entries.reduce((a, [, w]) => a + w, 0)
  let r = roll * total
  for (const [clip, w] of entries) {
    r -= w
    if (r < 0) return clip
  }
  return entries[entries.length - 1]![0]
}

/** The playback rate for a speed-driven clip: real speed over the clip's root speed, clamped. */
export function locomotionRate(speedUnitsPerSec: number, rootSpeedUnitsPerSec: number): number {
  if (rootSpeedUnitsPerSec <= 0) return 1
  const r = Math.abs(speedUnitsPerSec) / rootSpeedUnitsPerSec
  return Math.min(ART.anim.rateMax, Math.max(ART.anim.rateMin, r))
}
