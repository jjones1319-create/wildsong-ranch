/**
 * SOUND_UPGRADE §5.2: packs are computed, not hand-listed. `usageOf()` builds the graph of which context uses
 * which instrument from the songs, stingers, musical effects, drill cues, ambience and effect recipes, and
 * `packOf()` assigns each instrument to `core` (anything the ranch, the town, the UI, the drills, the world
 * effects or the battle effects use), `events` (only event themes and their stingers) or `places` (the rest).
 * The sample pipeline reads this at assembly time; a test checks every context's instruments are in a pack
 * that is loaded there.
 */

export type PackId = 'core' | 'events' | 'places'

export type UsageContext = 'ranch' | 'town' | 'ui' | 'drill' | 'world' | 'battleFx' | 'event' | 'place'

export interface Usage {
  /** instrument id → the contexts that use it. */
  byInstrument: Map<string, Set<UsageContext>>
}

const CORE_CONTEXTS: readonly UsageContext[] = ['ranch', 'town', 'ui', 'drill', 'world', 'battleFx']

export function packFor(contexts: ReadonlySet<UsageContext>): PackId {
  if (CORE_CONTEXTS.some((c) => contexts.has(c))) return 'core'
  if (contexts.has('event')) return 'events'
  return 'places'
}

/** Which pack a context needs loaded (besides core, always). */
export function packsNeededBy(context: UsageContext): readonly PackId[] {
  switch (context) {
    case 'event':
      return ['core', 'events']
    case 'place':
      return ['core', 'places']
    default:
      return ['core']
  }
}

let registry: Usage | null = null

/** The usage graph. Filled in by `recipes/usage.ts` once the songs and recipes exist; empty means "everything is core". */
export function setUsage(u: Usage): void {
  registry = u
}

export function usageOf(): Usage {
  return registry ?? { byInstrument: new Map() }
}

export function packOf(instrument: string): PackId {
  const contexts = usageOf().byInstrument.get(instrument)
  return contexts ? packFor(contexts) : 'core'
}
