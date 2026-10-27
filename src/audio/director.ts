/**
 * SOUND_UPGRADE §11: the director's decision. A pure function turns the scene (the screen and its context)
 * into a request: which song, arrangement, layers and stem, which bed, crowd and reverb. Every Screen and
 * every event in EVENTS has an explicit row; pieces not yet written (S2, S3) map to stand-ins tagged
 * TODO_S2 / TODO_S3. The controller that applies it lives in `ui/lib/audioDirector.ts`.
 */
import type { Screen } from '../ui/router.ts'
import type { Season, Weather, DrillId, JourneySiteId, ExpeditionSiteId } from '../data/types.ts'
import { EVENT_ARRANGEMENT_BY_ID, PRACTICE_ARRANGEMENT, TRIAL_ARRANGEMENT, type EventArrangement } from './recipes/events.ts'
import type { BedId, CrowdSize } from './recipes/ambience.ts'
import type { ReverbPreset } from './engine/reverb.ts'
import type { InstrumentId } from './recipes/instruments.ts'
import type { KitId } from './recipes/kits.ts'

export const SONG_IDS = ['wildsong', 'ranch-spring', 'ranch-summer', 'ranch-autumn', 'ranch-winter', 'town', 'cup'] as const
export type SongId = (typeof SONG_IDS)[number]

export type BattlePhase = 'lobby' | 'match' | 'result'
export type BattleOrigin = 'cup' | 'trial' | 'lab' | 'versus'

export interface Scene {
  screen: Screen
  season: Season
  weather: Weather
  /** A cup in progress (its event id) and the current opponent's rival id. */
  eventId: string | null
  opponentRivalId: string | null
  battle: {
    phase: BattlePhase
    origin: BattleOrigin
    /** HP shares 0..1 for the two fighters. */
    hp: readonly [number, number]
    secondsLeft: number
    matchSeconds: number
    paused: boolean
    speed: 1 | 2 | 4
  } | null
  /** A drill cue has taken over the music (§8.1). */
  drill: DrillId | null
  journeySite: JourneySiteId | null
  expeditionSite: ExpeditionSiteId | null
  oddJob: 'turnip' | 'echo' | null
}

export interface SongRequest {
  id: SongId
  arrangement: string | null
  layers: readonly string[]
  stem: string | null
  transpose: number
  tempoNudge: number
  kit: KitId | null
  lead: InstrumentId | null
  musicSend: number | null
  /** Crossfade seconds when this replaces another song. */
  crossfadeSec: number
}

export interface Request {
  /** `keep` leaves the music as it is (settings, calendar). */
  song: SongRequest | null | 'keep'
  bed: BedId | null | 'keep'
  crowd: CrowdSize
  reverb: ReverbPreset
  /** The scene's weather (ranch songs and beds follow it). */
  weather: Weather
  /** The drill cue owns the music. */
  drillOwned: boolean
  standIn: 'TODO_S2' | 'TODO_S3' | null
  /** The pause filter wanted. */
  paused: boolean
}

export const TENSION_HP = 0.3
export const TENSION_SECONDS = 10

const SEASON_SONG: Record<Season, SongId> = { Spring: 'ranch-spring', Summer: 'ranch-summer', Autumn: 'ranch-autumn', Winter: 'ranch-winter' }
const SEASON_BED: Record<Season, BedId> = { Spring: 'meadow', Summer: 'summer-field', Autumn: 'autumn-wind', Winter: 'winter-yard' }

/** Town stems by screen (§7.3). */
export const TOWN_STEMS: Partial<Record<Screen, string>> = {
  town: 'town',
  mail: 'mail',
  upgrades: 'upgrades',
  oddJobs: 'oddJobs',
  shop: 'shop',
  market: 'market',
  guild: 'guild',
  library: 'library',
  journal: 'journal',
}

const TOWN_BEDS: Partial<Record<Screen, BedId>> = { shop: 'shop', market: 'market', guild: 'guild', library: 'library', journal: 'library' }

function song(id: SongId, extra: Partial<SongRequest> = {}): SongRequest {
  return { id, arrangement: null, layers: ['main'], stem: null, transpose: 0, tempoNudge: 0, kit: null, lead: null, musicSend: null, crossfadeSec: 1.5, ...extra }
}

function battleLayers(s: NonNullable<Scene['battle']>): string[] {
  if (s.phase !== 'match') return ['lobby']
  // §7.5: base for bars 1–2 (about 4 s at the cup tempo), then drive.
  const elapsed = s.matchSeconds - s.secondsLeft
  const layers = ['base']
  if (elapsed >= 4) layers.push('drive')
  const tension = s.hp[0] <= TENSION_HP || s.hp[1] <= TENSION_HP || s.secondsLeft <= TENSION_SECONDS
  if (tension) layers.push('tension')
  return layers
}

/** The arrangement row for the battle's origin. Matches against Corin take `rival` (S2); until then the event's cup. */
export function arrangementFor(scene: Scene): { row: EventArrangement; standIn: 'TODO_S2' | null } {
  const origin = scene.battle?.origin ?? (scene.eventId ? 'cup' : 'versus')
  if (origin === 'trial') return { row: TRIAL_ARRANGEMENT, standIn: 'TODO_S2' }
  if (origin === 'lab' || origin === 'versus') return { row: PRACTICE_ARRANGEMENT, standIn: 'TODO_S2' }
  const row = scene.eventId ? EVENT_ARRANGEMENT_BY_ID[scene.eventId] : undefined
  if (!row) return { row: PRACTICE_ARRANGEMENT, standIn: 'TODO_S2' }
  const corin = scene.opponentRivalId === 'corin-hale'
  return { row, standIn: corin || row.status === 'TODO_S2' ? 'TODO_S2' : null }
}

function cupSong(scene: Scene, layers: readonly string[]): { song: SongRequest; crowd: CrowdSize; standIn: 'TODO_S2' | null } {
  const { row, standIn } = arrangementFor(scene)
  return {
    song: song('cup', { layers, transpose: row.transpose, tempoNudge: row.tempoNudge, kit: row.kit, lead: row.lead, musicSend: row.musicSend, arrangement: `palette-${row.palette.toLowerCase()}` }),
    crowd: scene.battle?.origin === 'trial' || scene.battle?.origin === 'lab' || scene.battle?.origin === 'versus' ? 'none' : row.crowd,
    standIn,
  }
}

export function decide(scene: Scene): Request {
  const base: Request = { song: null, bed: null, crowd: 'none', reverb: 'outdoor', weather: scene.weather, drillOwned: false, standIn: null, paused: false }
  if (scene.drill) return { ...base, song: 'keep', bed: 'keep', drillOwned: true }
  const ranch = (): Request => ({ ...base, song: song(SEASON_SONG[scene.season], { crossfadeSec: 2.5 }), bed: SEASON_BED[scene.season], reverb: 'outdoor' })
  const town = (stem: string, bed: BedId = 'town', reverb: ReverbPreset = 'outdoor'): Request => ({ ...base, song: song('town', { stem }), bed, reverb })
  switch (scene.screen) {
    case 'title':
    case 'credits':
      return { ...base, song: song('wildsong'), bed: 'meadow', reverb: 'outdoor' }
    case 'newGame':
      return { ...base, song: song('wildsong', { arrangement: 'lobby' }), bed: 'meadow', reverb: 'outdoor' }
    case 'creditsRoll':
      return { ...base, song: song('wildsong', { arrangement: 'credits' }), bed: null, reverb: 'outdoor' }
    case 'ranch':
    case 'ranchCard':
    case 'bag':
    case 'songbook':
      return ranch()
    case 'town':
    case 'mail':
    case 'upgrades':
      return town(TOWN_STEMS[scene.screen]!)
    case 'oddJobs':
      if (scene.oddJob === 'echo') return { ...base, song: null, bed: 'guild', reverb: 'cave', standIn: 'TODO_S3' }
      if (scene.oddJob === 'turnip') return { ...base, song: song('town', { stem: 'oddJobs' }), bed: 'market', reverb: 'room', standIn: 'TODO_S3' }
      return town('oddJobs')
    case 'shop':
    case 'market':
    case 'guild':
      return town(TOWN_STEMS[scene.screen]!, TOWN_BEDS[scene.screen], scene.screen === 'market' ? 'outdoor' : 'room')
    case 'library':
    case 'journal':
      return town(TOWN_STEMS[scene.screen]!, 'library', 'room')
    case 'shrine':
      return { ...base, song: song('town', { stem: 'library' }), bed: null, reverb: 'cave', standIn: 'TODO_S3' }
    case 'pell':
      return { ...base, song: song('town', { stem: 'upgrades' }), bed: 'shop', reverb: 'room', standIn: 'TODO_S3' }
    case 'lab':
    case 'labCreate':
    case 'labView':
    case 'labEdit':
    case 'labImport':
    case 'labExport':
    case 'labEffects':
    case 'labBattleLab':
      return { ...base, song: song('town', { stem: 'shop' }), bed: null, reverb: 'room', standIn: 'TODO_S3' }
    case 'labVersus':
      return { ...base, song: song('town', { stem: 'shop' }), bed: null, reverb: 'room', standIn: 'TODO_S3' }
    case 'labSound':
      return { ...base, song: null, bed: null, reverb: 'room' }
    case 'journey':
    case 'expedition':
      return { ...ranch(), standIn: 'TODO_S3', reverb: scene.expeditionSite === 'hollowmoon-caverns' ? 'cave' : scene.expeditionSite === 'sunken-library' ? 'underwater' : 'outdoor' }
    case 'farewell':
      return { ...base, song: song(SEASON_SONG[scene.season], { crossfadeSec: 2.5 }), bed: 'meadow', reverb: 'outdoor', standIn: 'TODO_S3' }
    case 'tournament': {
      const c = cupSong({ ...scene, battle: null, eventId: scene.eventId }, ['lobby'])
      return { ...base, song: c.song, bed: 'arena-out', crowd: 'none', reverb: 'outdoor', standIn: c.standIn }
    }
    case 'tournamentPlay':
    case 'tournamentResults': {
      const c = cupSong({ ...scene, battle: null }, ['lobby'])
      return { ...base, song: c.song, bed: 'arena', crowd: c.crowd, reverb: 'outdoor', standIn: c.standIn }
    }
    case 'battle': {
      const b = scene.battle
      if (!b) return { ...base, song: null, bed: 'arena', reverb: 'room' }
      const c = cupSong(scene, battleLayers(b))
      const arenaBed: BedId | null = b.origin === 'trial' || b.origin === 'lab' || b.origin === 'versus' ? null : 'arena'
      return { ...base, song: c.song, bed: arenaBed, crowd: c.crowd, reverb: 'room', standIn: c.standIn, paused: b.paused }
    }
    case 'settings':
    case 'calendar':
      return { ...base, song: 'keep', bed: 'keep' }
  }
}

/** Every stand-in in the S1 table, for PROGRESS and the tests. */
export const STAND_INS: readonly { what: string; uses: string; stage: 'TODO_S2' | 'TODO_S3' }[] = [
  { what: 'every event theme but the regular cup (Opens, Ascensions, Crowns, the Legend, the Masquerade, the Rival Showdown, the Summit, the Rallies, Sprout and Elders, Journey Trials, the Lab)', uses: 'cup in the season palette', stage: 'TODO_S2' },
  { what: 'the Shrine', uses: 'the Town library stem (harp and music box), no bed', stage: 'TODO_S3' },
  { what: "Pell's Lab", uses: 'the Town workshop stem with the shop bed', stage: 'TODO_S3' },
  { what: 'the Monster Lab screens', uses: 'the Town shop stem, no bed', stage: 'TODO_S3' },
  { what: 'Journeys and Expeditions', uses: 'the ranch song of the season', stage: 'TODO_S3' },
  { what: 'the Farewell', uses: 'the ranch song of the season', stage: 'TODO_S3' },
  { what: 'Turnip Sort', uses: 'the Town fair stem with the market bed', stage: 'TODO_S3' },
  { what: 'Echo Stones', uses: 'no music (the stones sing), the guild bed', stage: 'TODO_S3' },
  { what: 'the other ten drills', uses: 'the generic cue and its outcome stingers', stage: 'TODO_S3' },
]
