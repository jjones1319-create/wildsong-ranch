import { signal } from '@preact/signals'
import type { LightPreset } from '../../art3d/materials.ts'
import type { MonsterMode, Season, Weather } from '../../data/types.ts'

/** The ranch's and arena's light by season and weather (ART_2_PLAN §3.5; scenes bring their own from P2). */
export function lightPreset(season: Season, weather: Weather): LightPreset {
  if (weather === 'Snow') return 'snow'
  if (weather === 'Rain' || weather === 'Storm') return 'rain'
  if (weather === 'Cloudy') return 'overcast'
  return season === 'Autumn' ? 'goldenHour' : 'day'
}

/**
 * Art 2.0 (ART_2_PLAN §3.2, §3.3): the 3D monsters' session state and the one rule that decides what a
 * portrait shows. The main chunk never imports three; the 3D branch is loaded lazily by the components.
 */

/** True once WebGL could not start on this device: everything shows Classic and Settings says why. */
export const art3dUnavailable = signal(false)
/** True while the WebGL context is lost (iOS backgrounding, memory pressure): hosts fall back to Classic. */
export const art3dLost = signal(false)
/** Live frame stats from the stage, for the Lab's fps counter. */
export const art3dStats = signal<{ fps: number; tris: number; drawCalls: number; tier: string } | null>(null)

export type PortraitMode = 'classic' | 'image' | 'live'

/**
 * `live` renders the model on a canvas (subject screens), `image` a cached picture of it (lists), `classic`
 * the SVG. Reduce motion turns subject screens into stills; no WebGL turns them into Classic.
 */
export function portraitMode(hasLook: boolean, mode: MonsterMode, unavailable: boolean, reduceMotion: boolean, live: boolean): PortraitMode {
  if (!hasLook || mode !== '3d') return 'classic'
  if (live && !unavailable && !reduceMotion) return 'live'
  return 'image'
}
