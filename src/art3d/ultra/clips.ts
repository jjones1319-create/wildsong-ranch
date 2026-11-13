/**
 * Art 2.1 Ultra clips (docs/BATTLE_3D.md §7, ART_2_DETAIL §9): what Battle 3D and the 3D Gallery ask a model for, and
 * what stands in when a breed's file lacks one. Plain data (no three), so the registry's tests can read it.
 */

/** Every clip Battle 3D plays; a file must have each of these, except `dash`, which may fall back. */
export const DUEL_REQUIRED_CLIPS = ['battle_idle', 'walk', 'step_fwd', 'step_back', 'strike', 'cast', 'hit', 'hit_heavy', 'ko', 'win'] as const
export const DUEL_FALLBACK_OK = ['dash'] as const

/** The 3D Gallery's move buttons, in order (`blink` plays over whatever is playing). */
export const GALLERY_CLIPS = ['idle', 'walk', 'strike', 'cast', 'hit', 'hit_heavy', 'ko', 'win', 'blink'] as const
export type GalleryClip = (typeof GALLERY_CLIPS)[number]

/**
 * Flight (the owner, Nov 12: Hearthwing "should fly in a special attack"): in-place clips (the root stays at the
 * origin; the game raises and lowers the monster). A look flies only when its sidecar lists all four and its file
 * holds them; any other look keeps its ground moves (no flight).
 */
export const FLY_CLIPS = ['fly_takeoff', 'fly', 'fly_cast', 'fly_land'] as const
export type FlyClip = (typeof FLY_CLIPS)[number]

/** Whether a look can fly: `has` says whether its sidecar lists a clip and its file holds it. */
export function canFly(has: (clip: string) => boolean): boolean {
  return FLY_CLIPS.every(has)
}

/** A Gallery move button: a ground move, or (for a look that flies) a flying one, shown after the ground moves. */
export type GalleryMove = GalleryClip | FlyClip

/** The Gallery's loops; every other move plays once and settles back into idle. */
export const GALLERY_LOOPS: ReadonlySet<string> = new Set(['idle', 'walk'])

/** For each clip, what to play instead when the file lacks it (first match wins; the clip itself comes first). */
export const CLIP_FALLBACK: Readonly<Record<string, readonly string[]>> = {
  battle_idle: ['battle_idle', 'idle'],
  idle: ['idle', 'battle_idle'],
  walk: ['walk', 'step_fwd', 'run'],
  step_fwd: ['step_fwd', 'walk'],
  step_back: ['step_back', 'walk'],
  dash: ['dash', 'run', 'step_fwd', 'walk'],
  strike: ['strike', 'shove'],
  cast: ['cast', 'strike'],
  hit: ['hit', 'hit_heavy'],
  hit_heavy: ['hit_heavy', 'hit'],
  win: ['win', 'celebrate', 'idle_happy'],
  strafe_l: ['strafe_l', 'walk', 'step_fwd'],
  strafe_r: ['strafe_r', 'walk', 'step_fwd'],
  sidestep_l: ['sidestep_l', 'hop', 'dash'],
  sidestep_r: ['sidestep_r', 'hop', 'dash'],
}

/** The clip to play for `name`: itself, else its first fallback the file has, else null. */
export function resolveClipName(has: (clip: string) => boolean, name: string): string | null {
  for (const n of CLIP_FALLBACK[name] ?? [name]) if (has(n)) return n
  return has(name) ? name : null
}
