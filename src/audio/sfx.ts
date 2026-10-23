/**
 * GAME_DESIGN §23 sound effects: ZzFX parameter lists, all written for this game. Pure data: the player
 * (`player.ts`) feeds them to the engine. Order: volume, randomness, frequency, attack, sustain, release,
 * shape (0 sine · 1 triangle · 2 saw · 3 tan · 4 noise), shapeCurve, slide, deltaSlide, pitchJump,
 * pitchJumpTime, repeatTime, noise, modulation, bitCrush, delay, sustainVolume, decay, tremolo, filter.
 */

export const SFX_IDS = [
  'tap',
  'select',
  'drillGreat',
  'drillSuccess',
  'drillCheat',
  'drillFail',
  'drillSlacked',
  'fire',
  'hit',
  'crit',
  'miss',
  'ko',
  'special',
  'win',
  'lose',
  'levelUp',
  'coin',
  'mail',
  'stoneHum',
  'growUp',
  'plannerStop',
] as const
export type SfxId = (typeof SFX_IDS)[number]

export const SFX: Record<SfxId, readonly number[]> = {
  /* UI */
  tap: [0.5, 0, 880, 0, 0.015, 0.04, 1, 1.6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.9, 0.01],
  select: [0.45, 0, 660, 0, 0.02, 0.05, 1, 1.4, 0, 0, 110, 0.03, 0, 0, 0, 0, 0, 0.8, 0.01],
  /* drill stingers */
  drillGreat: [0.9, 0.02, 523, 0.01, 0.07, 0.22, 0, 1.3, 0, 0, 131, 0.07, 0.07, 0, 0, 0, 0.04, 1, 0.02],
  drillSuccess: [0.8, 0.02, 440, 0.01, 0.09, 0.16, 1, 1.2, 0, 0, 110, 0.1, 0, 0, 0, 0, 0, 0.9, 0.02],
  drillCheat: [0.7, 0.08, 330, 0.01, 0.12, 0.2, 2, 1.8, -6, 0, 0, 0, 0, 0, 12, 0, 0, 0.8, 0.03],
  drillFail: [0.8, 0.04, 262, 0.02, 0.14, 0.26, 1, 1.5, -14, 0, 0, 0, 0, 0, 0, 0, 0, 0.7, 0.05],
  drillSlacked: [0.6, 0.1, 196, 0.02, 0.2, 0.3, 1, 2, -3, 0, 0, 0, 0, 0, 5, 0, 0, 0.7, 0.05],
  /* battle */
  fire: [0.35, 0.1, 420, 0.01, 0.04, 0.09, 4, 1, 12, 0, 0, 0, 0, 1, 0, 0, 0, 0.8, 0.02],
  hit: [0.9, 0.1, 180, 0, 0.04, 0.12, 3, 1.5, -6, 0, 0, 0, 0, 0.4, 0, 0.1, 0, 0.9, 0.02],
  crit: [1.1, 0.1, 140, 0, 0.06, 0.26, 3, 1.8, -10, 0, 0, 0, 0, 0.8, 0, 0.2, 0.05, 1, 0.03],
  miss: [0.45, 0.05, 720, 0, 0.05, 0.1, 0, 1, 24, 0, 0, 0, 0, 0.15, 0, 0, 0, 0.6, 0.02],
  ko: [1.1, 0.05, 110, 0.01, 0.2, 0.5, 3, 2, -8, 0, 0, 0, 0, 0.5, 0, 0.3, 0.1, 1, 0.1],
  special: [0.85, 0, 494, 0.04, 0.18, 0.3, 0, 1, 2, 0, 247, 0.14, 0.1, 0, 8, 0, 0.05, 1, 0.03],
  win: [1, 0, 392, 0.02, 0.14, 0.3, 0, 1.4, 0, 0, 98, 0.11, 0.11, 0, 0, 0, 0.05, 1, 0.02],
  lose: [0.9, 0.04, 294, 0.02, 0.2, 0.4, 1, 1.6, -4, 0, -49, 0.16, 0.16, 0, 0, 0, 0, 0.9, 0.05],
  /* ranch and town */
  levelUp: [0.9, 0, 523, 0.02, 0.1, 0.26, 0, 1.2, 0, 0, 131, 0.08, 0.08, 0, 0, 0, 0.04, 1, 0.02],
  coin: [0.7, 0, 1047, 0, 0.05, 0.15, 0, 1.3, 0, 0, 262, 0.05, 0, 0, 0, 0, 0, 0.9, 0.01],
  mail: [0.7, 0, 659, 0.02, 0.08, 0.2, 1, 1.5, 0, 0, 220, 0.1, 0, 0, 0, 0, 0, 0.9, 0.02],
  stoneHum: [0.8, 0.02, 110, 0.3, 0.6, 0.7, 0, 1, 0, 0, 0, 0, 0, 0, 3, 0, 0.1, 0.8, 0.1],
  growUp: [0.9, 0, 349, 0.05, 0.25, 0.4, 0, 1, 1, 0, 175, 0.2, 0.2, 0, 6, 0, 0.06, 1, 0.03],
  plannerStop: [0.6, 0, 587, 0.01, 0.06, 0.12, 1, 1.3, 0, 0, -98, 0.08, 0, 0, 0, 0, 0, 0.8, 0.02],
}
