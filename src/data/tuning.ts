/**
 * ALL tuning numbers for Wildsong Ranch live in this file (CLAUDE.md golden rule 4).
 * Game rules in src/core/ import from here and never hard-code a number.
 * Every value starts from docs/GAME_DESIGN.md; balance changes happen here, not in the logic.
 */

/** App-shell timings (milliseconds). */
export const UI = {
  /** How long the "Ready to play offline" toast stays up. */
  offlineToastMs: 4000,
  /** How often the installed app asks GitHub Pages for a newer build while open. */
  updateCheckIntervalMs: 60 * 60 * 1000,
} as const
