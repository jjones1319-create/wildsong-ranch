import type { ExpressionCue } from '../../core/aging.ts'
import type { EyeMood, MouthStyle } from './parts.ts'

/**
 * GAME_DESIGN §22 expressions: neutral, happy, tired, stressed, sad, angry, sleepy, sick, plus the
 * sparkle overlay, mapped from the §6.6 cues. The editor can pick any of them for the preview.
 */

export const EXPRESSIONS = ['neutral', 'happy', 'tired', 'stressed', 'sad', 'angry', 'sleepy', 'sick'] as const
export type Expression = (typeof EXPRESSIONS)[number]

export interface FaceState {
  eyes: EyeMood
  /** The mouth to draw, or null to keep the breed's own. */
  mouth: MouthStyle | null
  sweat: boolean
  sick: boolean
}

/** Mouths that are part of the breed's anatomy (a beak, a chewing larva, a lid) never change with mood. */
const FIXED_MOUTHS: readonly MouthStyle[] = ['beak', 'chew', 'none']

export function faceFor(expression: Expression, breedMouth: MouthStyle, mischief: boolean): FaceState {
  const fixed = FIXED_MOUTHS.includes(breedMouth)
  const mouth = (m: MouthStyle | null) => (fixed ? null : m)
  let state: FaceState
  switch (expression) {
    case 'neutral':
      state = { eyes: 'open', mouth: null, sweat: false, sick: false }
      break
    case 'happy':
      state = { eyes: 'happy', mouth: null, sweat: false, sick: false }
      break
    case 'tired':
      state = { eyes: 'droopy', mouth: mouth('flat'), sweat: false, sick: false }
      break
    case 'stressed':
      state = { eyes: 'open', mouth: mouth('worried'), sweat: true, sick: false }
      break
    case 'sad':
      state = { eyes: 'sad', mouth: mouth('frown'), sweat: false, sick: false }
      break
    case 'angry':
      state = { eyes: 'angry', mouth: mouth('frown'), sweat: false, sick: false }
      break
    case 'sleepy':
      state = { eyes: 'closed', mouth: mouth('flat'), sweat: false, sick: false }
      break
    case 'sick':
      state = { eyes: 'droopy', mouth: mouth('wobble'), sweat: false, sick: true }
      break
  }
  if (mischief && (expression === 'neutral' || expression === 'happy')) {
    state = { ...state, eyes: 'narrow', mouth: mouth('grin') }
  }
  return state
}

export interface CueResult {
  expression: Expression
  sparkle: boolean
  mischief: boolean
}

/** §6.6: sick beats tired beats stressed; sparkle and the mischievous grin ride on top. */
export function expressionFromCues(cues: readonly ExpressionCue[]): CueResult {
  const has = (c: ExpressionCue) => cues.includes(c)
  const expression: Expression = has('sick') ? 'sick' : has('droopy') ? 'tired' : has('sweat') ? 'stressed' : 'neutral'
  return { expression, sparkle: has('sparkle'), mischief: has('grin') }
}
