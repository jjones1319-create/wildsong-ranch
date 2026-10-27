/**
 * SOUND_UPGRADE §4, §10.5: the public audio API the UI uses. Nothing happens before the first tap: the
 * engine chunk is imported on the first `pointerup` / `keydown`, the AudioContext is made inside that
 * gesture, the core pack decodes afterwards (the fallback voices play until each instrument is in). Today's
 * names keep working (`playSfx`, `setMusic`, `playStinger`); the director's requests, battle effects and the
 * drill cue go through the functions below. Everything is a no-op without a DOM or before the unlock.
 */
import { effect, signal } from '@preact/signals'
import { AUDIO } from '../data/tuning.ts'
import type { DrillId, Season } from '../data/types.ts'
import type { DrillOutcome } from '../core/training.ts'
import type { FxEvent } from '../fx/bus.ts'
import type { AppSettings } from '../save/schema.ts'
import { settings } from '../ui/store/appStore.ts'
import type { Request, SongId } from './director.ts'
import type { Engine } from './engine/index.ts'
import type { MusicalEffectId } from './music/effects.ts'
import type { Song } from './music/song.ts'
import type { StingerId } from './music/stingers.ts'
import type { UiSfxId, WorldSfxId } from './recipes/sfx.ts'
import type { Strength } from './recipes/sfx.ts'

export type LegacySfxId = 'tap' | 'select' | 'drillGreat' | 'drillSuccess' | 'drillCheat' | 'drillFail' | 'drillSlacked' | 'fire' | 'hit' | 'crit' | 'miss' | 'ko' | 'special' | 'win' | 'lose' | 'levelUp' | 'coin' | 'mail' | 'stoneHum' | 'growUp' | 'plannerStop' | 'echo1' | 'echo2' | 'echo3' | 'echo4'
export type EffectId = UiSfxId | WorldSfxId | MusicalEffectId | LegacySfxId

type Runtime = typeof import('./runtime.ts')

let ctx: AudioContext | null = null
let engine: Engine | null = null
let runtime: Runtime | null = null
let unlocking: Promise<void> | null = null
let pendingRequest: Request | null = null
let hidden = false

/** The drill whose cue owns the music right now (the director leaves the music alone while it is set). */
export const drillCueActive = signal<DrillId | null>(null)

export function audioReady(): boolean {
  return engine !== null
}

/** The engine, for the Sound Lab and the debug view (null before the unlock). */
export function getEngine(): Engine | null {
  return engine
}

export function getRuntime(): Runtime | null {
  return runtime
}

/** The audio clock, seconds (0 before the unlock). */
export function nowSec(): number {
  return ctx?.currentTime ?? 0
}

function applySettings(s: AppSettings): void {
  if (!engine) return
  engine.graph.setVolumes({ master: s.masterVolume, music: s.musicVolume, sfx: s.sfxVolume, ambience: s.ambienceVolume, musicOn: s.music, sfxOn: s.sound, ambienceOn: s.ambience, buttonSounds: s.buttonSounds })
  engine.graph.setListening(s.listening)
  engine.graph.setMono(s.monoAudio)
  runtime?.setMusicEnabled(engine, s.music)
}

/** Creates the context inside a user gesture and loads the engine chunk. */
export function unlockAudio(): Promise<void> {
  if (unlocking) return unlocking
  unlocking = (async () => {
    if (typeof window === 'undefined' || typeof AudioContext === 'undefined') return
    try {
      ctx = new AudioContext({ latencyHint: 'interactive' })
      const nav = navigator as Navigator & { audioSession?: { type: string } }
      if (nav.audioSession) nav.audioSession.type = 'ambient'
      if (ctx.state === 'suspended') await ctx.resume()
      const [engineMod, runtimeMod] = await Promise.all([import('./engine/index.ts'), import('./runtime.ts')])
      const e = engineMod.createEngine(ctx, { baseUrl: import.meta.env.BASE_URL, meters: true, driver: 'realtime' })
      engine = e
      runtime = runtimeMod
      applySettings(settings.value)
      e.start()
      runtimeMod.installDebugView(e)
      if (pendingRequest) {
        const r = pendingRequest
        pendingRequest = null
        void runtimeMod.applyRequest(e, r)
      }
      void e.loadCore().catch((err: unknown) => console.warn('audio: core pack failed to load', err))
    } catch (err) {
      console.warn('audio: unlock failed', err)
      ctx = null
      engine = null
    }
  })()
  return unlocking
}

/** Installs the one-time unlock and the background pause. Call once from main. */
export function installAudio(doc: Document): void {
  const once = () => {
    void unlockAudio()
  }
  doc.addEventListener('pointerup', once, { once: true, passive: true })
  doc.addEventListener('keydown', once, { once: true, passive: true })
  doc.addEventListener('visibilitychange', () => {
    if (!ctx) return
    hidden = doc.visibilityState === 'hidden'
    // §2 battery: nothing is scheduled while hidden; music continues where it was on return.
    if (hidden) void ctx.suspend()
    else void ctx.resume()
  })
  effect(() => {
    applySettings(settings.value)
  })
}

/** The director's request: what should play now (§11). Applied at once, or when the engine exists. */
export function applyRequest(r: Request): void {
  if (!engine || !runtime) {
    pendingRequest = r
    return
  }
  void runtime.applyRequest(engine, r)
}

/** Legacy: `setMusic(null)` stops the music; a request does the real work now. */
export function setMusic(r: Request | null): void {
  if (r === null) {
    engine?.music.stop(1)
    return
  }
  applyRequest(r)
}

/** The current song id, for tests and the Sound Lab. */
export function currentSong(): SongId | null {
  return (engine?.music.state()?.song as SongId | undefined) ?? null
}

/** A UI, world or musical effect by id (§10.2, §10.4, §7.6), with today's ids mapped per §10.5. */
export function playSfx(id: EffectId, opts: { pan?: number } = {}): void {
  if (!engine || !runtime || hidden) return
  try {
    runtime.playEffect(engine, id, opts)
  } catch {
    /* an effect is never worth an error */
  }
}

export const playEffect = playSfx

/** A battle FxEvent's sound (§10.3): cast, travel, impact by element and strength, crowd reactions, the KO cut. */
export function playBattleFx(e: FxEvent, pan: number, speed: 1 | 2 | 4): void {
  if (!engine || !runtime || hidden) return
  try {
    runtime.playBattleFx(engine, e, pan, speed)
  } catch {
    /* never an error */
  }
}

/** Engine events that are not FxEvents (§10.3): stun, reflect, recoil, jackpot, the Dragonheart trait, the timer ticks. */
export function playBattleEvent(kind: 'stun' | 'reflect' | 'recoil' | 'jackpotDouble' | 'jackpotHeal' | 'jackpotFizzle' | 'traitDragonheart' | 'timerTick', pan = 0): void {
  if (!engine || !runtime || hidden) return
  runtime.playEffect(engine, kind, { pan })
}

/** An interrupting stinger (§4.7): the area music fades, the stinger plays in the area key, the music restarts at its next section. */
export function playStinger(id: StingerId | 'victory' | 'lose'): void {
  if (!engine || !runtime || hidden) return
  const mapped: StingerId = id === 'victory' ? 'matchWin' : id === 'lose' ? 'matchLoss' : id
  runtime.playStinger(engine, mapped)
}

/** The battle pause filter (§4.7). */
export function setBattlePaused(on: boolean): void {
  engine?.graph.setPaused(on)
}

/** A Special's duck (§4.7): 3 dB for 1 s. */
export function duckForSpecial(): void {
  engine?.graph.duck(AUDIO.duck.db, AUDIO.duck.sec)
}

/** The KO: the music cuts over 150 ms (§7.5). */
export function cutMusicForKo(): void {
  engine?.music.cut(AUDIO.stingerFadeOutMs / 1000)
}

/** §8.1 the drill cue. `start` returns the audio-clock time the result should show, or null when audio is off. */
export const drillCue = {
  start(drill: DrillId, outcome: DrillOutcome, o: { vignetteMs: number; instant?: boolean }): number | null {
    if (!engine || !runtime || hidden) return null
    try {
      const at = runtime.startDrillCue(engine, drill, outcome, o)
      if (!o.instant) drillCueActive.value = drill
      return at
    } catch {
      return null
    }
  },
  skip(): void {
    if (engine && runtime) runtime.skipDrillCue(engine)
  },
  /** DrillResult reports when it switched to its result phase, for the ±25 ms log in `window.__audio`. */
  shown(resultAt: number): void {
    if (engine && runtime) runtime.markResultShown(engine, resultAt)
  },
  end(): void {
    if (engine && runtime) runtime.endDrillCue(engine)
    drillCueActive.value = null
  },
}

/** The Settings "Test sound": a short harp-and-ocarina phrase. */
export async function testSound(): Promise<void> {
  await unlockAudio()
  playSfx('learnTechnique')
}

/** Loads a song for the Sound Lab (every song is a lazy chunk). */
export async function loadSongForLab(id: SongId): Promise<Song> {
  const m = await import('./music/songs/index.ts')
  return m.loadSong(id)
}

export type { Season, Strength }
