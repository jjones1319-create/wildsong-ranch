/**
 * SOUND_UPGRADE §14.3: the shapes the render harness (`ui/screens/lab/soundRender.ts`, in the page) and the
 * render tool (`tools/audio/render-review.ts`, in Node) agree on. Pure types, no Web Audio, no Vite.
 */
import type { SongId } from './director.ts'
import type { StingerId } from './music/stingers.ts'
import type { BedId, CrowdSize } from './recipes/ambience.ts'
import type { InstrumentId } from './recipes/instruments.ts'
import type { KitId } from './recipes/kits.ts'
import type { Strength } from './recipes/sfx.ts'
import type { DrillOutcome } from '../core/training.ts'
import type { DrillId, Element, Weather } from '../data/types.ts'
import type { FxEventKind } from '../fx/bus.ts'

export type RenderItem =
  | { kind: 'song'; id: SongId; seconds: number; layers?: string[]; stem?: string | null; weather?: Weather; arrangement?: string; lead?: InstrumentId; kit?: KitId; transpose?: number; startIndex?: number }
  | { kind: 'bed'; id: BedId; seconds: number; weather?: Weather; crowd?: CrowdSize }
  | { kind: 'stinger'; id: StingerId; transpose?: number; chain?: StingerId[] }
  | { kind: 'effect'; id: string; seconds?: number }
  | { kind: 'battleFx'; kinds: FxEventKind[]; element: Element; strength: Strength; seconds?: number }
  | { kind: 'drill'; drill: DrillId; outcome: DrillOutcome; seconds?: number }
  | { kind: 'battleDemo'; seconds: number; layers?: string[]; song?: SongId; crowd?: CrowdSize }
  | { kind: 'loopSeam'; id: SongId; seconds: number }

export interface StemStats {
  lufs: number
  shortTermMax: number
  momentaryMax: number
  truePeakDb: number
  crestDb: number
  share2to6k: number
  shareAbove8k: number
  clicks: number
  /** The first few click times in seconds, for finding them. */
  clickTimes: number[]
  dropouts: number
  /** Short-term loudness every 100 ms. */
  shortTerm: number[]
  momentary: number[]
}

export interface RenderResult {
  seconds: number
  sampleRate: number
  stems: Record<'music' | 'ambience' | 'sfx' | 'ui' | 'master', StemStats>
  /** The scheduled onsets (seconds), the click allow-list. */
  onsets: number[]
  /** Times of the scripted effects (battle demo, effects), for the relative checks. */
  marks: { t: number; what: string }[]
  lateEvents: number
  decodeMs: number
  pcm?: { sampleRate: number; channels: number; chunks: string[] }
}
