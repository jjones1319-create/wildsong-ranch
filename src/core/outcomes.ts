/**
 * GAME_DESIGN §6.2 the result levels of a drill, best first. 'Success' is shown as "Fine". Superb needs loyalty 50
 * and Perfect loyalty 70. Kept apart from `training.ts` (no imports), so the audio chunk can map a level to its
 * drill cue without pulling in the rules and their data.
 */
export type DrillOutcome = 'Perfect' | 'Superb' | 'Great' | 'Good' | 'Success' | 'Cheat' | 'Fail' | 'Slacked'
export const ROLLED_OUTCOMES = ['Perfect', 'Superb', 'Great', 'Good', 'Success', 'Cheat', 'Fail'] as const
export type RolledOutcome = (typeof ROLLED_OUTCOMES)[number]

/** The four buckets of §6.2 step 2 that the levels split (plus truancy): the drill cues and reactions are written per bucket. */
export type BaseOutcome = 'Great' | 'Success' | 'Cheat' | 'Fail' | 'Slacked'

export function baseOutcome(o: DrillOutcome): BaseOutcome {
  return o === 'Perfect' || o === 'Superb' ? 'Great' : o === 'Good' ? 'Success' : o
}

/** True for every result that trains in full: Fine and up. */
export function isGoodOutcome(o: DrillOutcome): boolean {
  return o === 'Success' || o === 'Good' || o === 'Great' || o === 'Superb' || o === 'Perfect'
}
