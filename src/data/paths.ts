import type { Technique } from './types.ts'

/**
 * docs/BATTLE_3D.md §3: the shape of a technique's path in the duel.
 * - **line**: it travels straight from the attacker at where the defender stood when it was fired. A sidestep
 *   timed in the wind-up makes it harder to hit, and one that carries the defender out of the path makes it miss.
 * - **sweep**: it covers a wide area (clouds, auras, quakes, spins, barrages). A sidestep does nothing.
 * A technique with no force (a pure heal) is a sweep too, since there is nothing to dodge.
 *
 * The rule, in order:
 * 1. the overrides below;
 * 2. no force, or the Wither family (clouds, auras and roars spread out) → sweep;
 * 3. three or more hits (a barrage) → sweep;
 * 4. a word of the name that names an area → sweep;
 * 5. everything else → line.
 */
export type TechPath = 'line' | 'sweep'

/** Words (whole words or their start) that name a wide technique. */
const SWEEP_WORDS = [
  'spin', 'sweep', 'whirl', 'wave', 'quake', 'stomp', 'storm', 'tempest', 'blizzard', 'cyclone', 'tornado', 'avalanche',
  'flood', 'tide', 'shower', 'rain', 'nova', 'burst', 'ring', 'gust', 'squall', 'gale', 'landslide', 'rockfall',
  'mountainfall', 'downpour', 'tsunami', 'eruption', 'shockwave', 'roar', 'howl', 'chorus', 'crescendo', 'cascade',
  'spiral', 'tremor', 'embrace',
] as const

/** Techniques whose name misleads the rule: a lance, a dive, a thrown feather and a grab travel in a line. */
const OVERRIDES: Readonly<Record<string, TechPath>> = {
  'galeheron.gale-lance': 'line',
  'galeheron.tempest-dive': 'line',
  'galeheron.gust-feather': 'line',
  'reefclaw.tidebreaker-clamp': 'line',
}

function words(name: string): string[] {
  return name.toLowerCase().replace(/['’]/g, '').split(/[^a-z]+/).filter(Boolean)
}

export function pathOf(t: Pick<Technique, 'id' | 'name' | 'family' | 'force' | 'effect'>): TechPath {
  const o = OVERRIDES[t.id]
  if (o) return o
  if (t.force <= 0 || t.family === 'Wither') return 'sweep'
  if (t.effect?.kind === 'multi' && t.effect.hits >= 3) return 'sweep'
  const ws = words(t.name)
  if (ws.some((w) => SWEEP_WORDS.some((k) => w.startsWith(k)))) return 'sweep'
  return 'line'
}
