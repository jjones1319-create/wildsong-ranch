/**
 * SOUND_UPGRADE §4: the engine. Wires the graph, the sample bank, the scheduler on a driver, the music
 * player, the ambience and the effect player on any BaseAudioContext, so the same code plays in the game
 * (AudioContext, realtime driver) and renders the review files (OfflineAudioContext, offline driver).
 * Only this folder touches Web Audio.
 */
import { AUDIO } from '../../data/tuning.ts'
import LEVELS from '../levels.json'
import { Ambience } from './ambience.ts'
import { createGraph, type Graph } from './context.ts'
import { fakeDriver, offlineDriver, realtimeDriver, type Driver, type OfflineDriver } from './driver.ts'
import { SampleBank } from './samples.ts'
import { Scheduler } from './scheduler.ts'
import { SfxEngine } from './sfx.ts'
import { MusicPlayer } from './transport.ts'
import { createRng, type Rng } from './rng.ts'
import type { PackId } from '../recipes/packs.ts'

export interface EngineOptions {
  /** The app's base URL (import.meta.env.BASE_URL), where public/audio lives. */
  baseUrl: string
  seed?: number
  /** Render mode: an 8-channel stem tap instead of the master output. */
  stems?: boolean
  meters?: boolean
  /** Which driver: realtime (the game), offline (renders) or fake (tests). */
  driver?: 'realtime' | 'offline' | 'fake'
  fetchFn?: typeof fetch
}

export interface AudioDebugView {
  song: string | null
  section: string
  bar: number
  layers: string[]
  stem: string | null
  weather: string | null
  bpm: number
  bed: string | null
  crowd: string
  musicFilterHz: number
  duckDb: number
  lateEvents: number
  voices: { music: number; ambience: number; sfx: number }
  meters: Record<string, { peakDb: number; rmsDb: number }>
  packs: { pack: string; state: string; decodeMs: number }[]
  listening: string
  mono: boolean
  glueReductionDb: number
  drillCueErrorMs: number | null
}

export interface Engine {
  ctx: BaseAudioContext
  graph: Graph
  bank: SampleBank
  scheduler: Scheduler
  driver: Driver
  music: MusicPlayer
  ambience: Ambience
  sfx: SfxEngine
  rng: Rng
  start(): void
  stop(): void
  loadCore(): Promise<void>
  loadPack(pack: PackId): Promise<void>
  render(): Promise<AudioBuffer>
  debug(): AudioDebugView
  /** The last drill cue's timing error, set by the cue. */
  drillCueErrorMs: number | null
}

export function createEngine(ctx: BaseAudioContext, o: EngineOptions): Engine {
  const rng = createRng(o.seed ?? ((Date.now() ^ 0x5eed) >>> 0))
  const graph = createGraph(ctx, { stems: o.stems, seed: o.seed, meters: o.meters })
  const bank = new SampleBank(ctx, o.baseUrl, o.fetchFn)
  const driverKind = o.driver ?? ('startRendering' in ctx ? 'offline' : 'realtime')
  const driver: Driver | OfflineDriver = driverKind === 'offline' ? offlineDriver(ctx as OfflineAudioContext, 0.1) : driverKind === 'fake' ? fakeDriver() : realtimeDriver(ctx, AUDIO.tickMs)
  const scheduler = new Scheduler(driver, AUDIO.lookaheadSec, AUDIO.lateToleranceMs / 1000)
  const music = new MusicPlayer(ctx, graph, bank, scheduler, rng)
  const ambience = new Ambience(ctx, graph.ambience, graph.reverbPlace.input, bank, rng)
  const sfx = new SfxEngine(ctx, graph, bank, rng)
  // §14.3 the calibration trims.
  music.trims = { ...LEVELS.songs }
  sfx.trims = { ...LEVELS.effects }
  ambience.bedTrims = { ...LEVELS.beds }
  let lastSweep = 0
  scheduler.addFiller((until) => {
    const now = ctx.currentTime
    ambience.tick(now, until)
    if (now - lastSweep > 10) {
      lastSweep = now
      bank.sweep(now)
    }
    const key = music.key()
    if (key) sfx.key = key
  })
  const engine: Engine = {
    ctx,
    graph,
    bank,
    scheduler,
    driver,
    music,
    ambience,
    sfx,
    rng,
    drillCueErrorMs: null,
    start: () => scheduler.start(),
    stop: () => {
      scheduler.stop()
      music.stopAll()
      ambience.stopAll()
      sfx.stopAll()
    },
    loadCore: async () => {
      await bank.loadManifest()
      await bank.loadPack('core', ctx.currentTime)
    },
    loadPack: (pack) => bank.loadPack(pack, ctx.currentTime),
    render: () => {
      if (!('render' in driver)) throw new Error('render needs the offline driver')
      return (driver as OfflineDriver).render()
    },
    debug: () => {
      const s = music.state()
      return {
        song: s?.song ?? null,
        section: s?.section ?? '',
        bar: s?.bar ?? 0,
        layers: s?.layers ?? [],
        stem: s?.stem ?? null,
        weather: s?.weather ?? null,
        bpm: s?.bpm ?? 0,
        bed: ambience.bedId,
        crowd: ambience.crowdSize,
        musicFilterHz: Math.round(graph.musicFilterHz()),
        duckDb: Math.round(graph.duckDb() * 10) / 10,
        lateEvents: scheduler.lateEvents,
        voices: { music: music.voices(), ambience: ambience.voices(), sfx: sfx.voices() },
        meters: graph.meters?.readAll() ?? {},
        packs: bank.packReport(),
        listening: graph.listening,
        mono: graph.mono,
        glueReductionDb: Math.round(graph.glueReductionDb() * 10) / 10,
        drillCueErrorMs: engine.drillCueErrorMs,
      }
    },
  }
  return engine
}
