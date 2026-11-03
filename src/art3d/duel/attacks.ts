import { ART } from '../../data/tuning.ts'

/**
 * docs/BATTLE_3D.md §7: attacks that visibly reach. The owner (Nov 2): "the attacks do not seem to land". The rules
 * were fine (a simple player lands 60% and wins most fights); the picture wasn't: strikes played in place across a 2–3 m
 * gap and ranged moves had nothing travelling. So a melee attack lunges across the gap and back, and a ranged one sends
 * its effects there (attackFx.ts), arriving on the engine's landing tick. Picture only: the engine's positions never change.
 */

const A = ART.duel.attack

export interface Lunge {
  /** Seconds (the stage's clock): the lunge starts, reaches the target on the landing, holds, then returns. */
  start: number
  impact: number
  end: number
}

const ease = (k: number) => k * k * (3 - 2 * k)

/** How far along the gap the attacker is (0 at home, 1 at contact). */
export function lungeReach(now: number, l: Lunge): number {
  if (now <= l.start || now >= l.end) return 0
  if (now < l.impact) return ease((now - l.start) / Math.max(1e-3, l.impact - l.start))
  const hold = l.impact + A.lungeHoldSec
  if (now < hold) return 1
  return 1 - ease((now - hold) / Math.max(1e-3, l.end - hold))
}

/** The lunge for a melee technique fired now that lands after `windupSec` (it leans in over the last part of it). */
export function lungeFor(now: number, windupSec: number): Lunge {
  const lean = Math.min(windupSec, A.lungeSec)
  return { start: now + windupSec - lean, impact: now + windupSec, end: now + windupSec + A.lungeHoldSec + A.lungeBackSec }
}

