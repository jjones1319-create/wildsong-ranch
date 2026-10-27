/**
 * SOUND_UPGRADE §11, §10, §8.1: the engine-side glue behind `player.ts`, loaded with the engine chunk. It
 * applies the director's requests (songs, layers, stems, weather, beds, crowds, reverb, pause), plays
 * effects by id in the playing key, bridges battle FxEvents to the element recipes with speed thinning and
 * crowd reactions, plays interrupting stingers in the area key, runs the drill cue, and exposes the
 * read-only `window.__audio` view.
 */
import { AUDIO } from '../data/tuning.ts'
import type { DrillId, Weather } from '../data/types.ts'
import type { DrillOutcome } from '../core/training.ts'
import type { FxEvent } from '../fx/bus.ts'
import type { Request, SongRequest } from './director.ts'
import type { Engine } from './engine/index.ts'
import { allowedAtSpeed, DEFAULT_KEY } from './engine/sfx.ts'
import type { Playback } from './engine/transport.ts'
import { MUSICAL_EFFECTS, type MusicalEffectId } from './music/effects.ts'
import type { Arrangement, Song } from './music/song.ts'
import { loadSong } from './music/songs/index.ts'
import { STINGERS, type StingerId } from './music/stingers.ts'
import type { EffectId, LegacySfxId } from './player.ts'
import type { CrowdReaction } from './recipes/ambience.ts'
import { cueFor, type DrillCueRecipe } from './recipes/drills.ts'
import { battleSfx, strengthOf, UI_SFX, WORLD_SFX, type SfxDef, type UiSfxId, type WorldSfxId } from './recipes/sfx.ts'

let lastRequest: Request | null = null
let musicEnabled = true
let applying: Promise<void> | null = null

/** §10.5: today's ids mapped to the new ones. Battle ids with no element use Physical. */
const LEGACY: Partial<Record<LegacySfxId, EffectId | { battle: FxEvent['kind'] } | { stinger: StingerId }>> = {
  win: { stinger: 'matchWin' },
  lose: { stinger: 'matchLoss' },
  levelUp: 'learnTechnique',
  fire: { battle: 'fire' },
  hit: { battle: 'hit' },
  crit: { battle: 'crit' },
  miss: { battle: 'miss' },
  ko: { battle: 'ko' },
  special: { battle: 'special' },
  drillGreat: 'itemGet',
  drillSuccess: 'echoClear',
  drillCheat: 'wrenReport',
  drillFail: 'echoWrong',
  drillSlacked: 'plannerStop',
}

function defFor(id: EffectId): SfxDef | null {
  if (id in UI_SFX) return UI_SFX[id as UiSfxId]
  if (id in WORLD_SFX) return WORLD_SFX[id as WorldSfxId]
  if (id in MUSICAL_EFFECTS) return MUSICAL_EFFECTS[id as MusicalEffectId]
  return null
}

export function playEffect(engine: Engine, id: EffectId, o: { pan?: number } = {}): void {
  const mapped = LEGACY[id as LegacySfxId]
  if (mapped && typeof mapped === 'object') {
    if ('stinger' in mapped) {
      playStinger(engine, mapped.stinger)
      return
    }
    playBattleFx(engine, { kind: mapped.battle, side: 0, element: 'Physical', from: { x: 0, y: 0 }, to: { x: 0, y: 0 }, strength: 0.5 }, o.pan ?? 0, 1)
    return
  }
  const real = (typeof mapped === 'string' ? mapped : id) as EffectId
  const def = defFor(real)
  if (!def) return
  engine.sfx.play(real, def, { pan: o.pan, key: engine.music.key() ?? DEFAULT_KEY })
}

/** §10.3: a battle FxEvent, thinned by speed, with the crowd's reaction and the KO cut. */
export function playBattleFx(engine: Engine, e: FxEvent, pan: number, speed: 1 | 2 | 4): void {
  const strength = strengthOf(e.strength)
  if (!allowedAtSpeed(e.kind, strength, speed)) return
  const def = battleSfx(e.kind, e.element, strength, e.crit)
  if (def.layers.length) engine.sfx.play(`${e.kind}:${e.element}`, def, { pan, key: engine.music.key() ?? DEFAULT_KEY })
  let reaction: CrowdReaction | null = null
  if ((e.kind === 'hit' && strength === 'heavy') || e.kind === 'crit') reaction = 'cheer'
  else if (e.kind === 'miss') reaction = 'ooh'
  else if (e.kind === 'special') reaction = 'murmur'
  else if (e.kind === 'ko') reaction = 'ko'
  if (reaction && (reaction === 'ko' || allowedAtSpeed('crowd', strength, speed))) engine.ambience.react(reaction)
  if (e.kind === 'special') engine.graph.duck(AUDIO.duck.db, AUDIO.duck.sec)
  if (e.kind === 'ko') engine.music.cut(AUDIO.stingerFadeOutMs / 1000)
}

/** The transposition that moves a piece written in C into the area key, by the nearest road (−6…+5). */
function transposeToArea(engine: Engine): number {
  const tonic = engine.music.key()?.tonic ?? 0
  return tonic > 6 ? tonic - 12 : tonic
}

export function playStinger(engine: Engine, id: StingerId): void {
  const song = STINGERS[id]
  engine.music.interrupt(song, { transpose: transposeToArea(engine), fadeInAfterSec: AUDIO.stingerFadeInSec })
}

/* ---------- the director's requests ---------- */

function arrangementFor(song: Song, r: SongRequest): Arrangement | null {
  const named = r.arrangement ? (song.arrangements?.[r.arrangement] ?? null) : null
  const lobby = r.layers.length === 1 && r.layers[0] === 'lobby' && song.kind === 'battle' ? (song.arrangements?.lobby ?? null) : null
  const base = named ?? lobby
  const out: Arrangement = { ...(base ?? {}) }
  if (r.kit) out.kit = r.kit
  if (r.lead) out.swap = { ...(base?.swap ?? {}), lead: r.lead, lobbyLead: r.lead }
  if (r.tempoNudge) out.tempoNudge = (base?.tempoNudge ?? 0) + r.tempoNudge
  if (r.musicSend !== null) out.musicSend = r.musicSend
  return Object.keys(out).length ? out : null
}

function sameArrangement(a: Arrangement | null, b: Arrangement | null): boolean {
  return JSON.stringify(a ?? {}) === JSON.stringify(b ?? {})
}

interface Applied {
  song: SongId | null
  arrangement: Arrangement | null
  transpose: number
  playback: Playback | null
}
type SongId = SongRequest['id']
let applied: Applied = { song: null, arrangement: null, transpose: 0, playback: null }

export async function applyRequest(engine: Engine, r: Request): Promise<void> {
  lastRequest = r
  // Requests are applied in order; a newer one waits for the song load of the older.
  const prev = applying
  const run = (async () => {
    await prev
    if (lastRequest !== r) return
    await applyNow(engine, r)
  })()
  applying = run
  await run
}

async function applyNow(engine: Engine, r: Request): Promise<void> {
  engine.graph.setPaused(r.paused)
  if (r.drillOwned) return
  if (r.bed !== 'keep') {
    engine.ambience.setWeather(r.weather)
    engine.ambience.setBed(r.bed, AUDIO.bedCrossfadeSec)
    engine.ambience.setCrowd(r.crowd)
    engine.graph.reverbPlace.setPreset(r.reverb)
  }
  if (r.song === 'keep') return
  if (r.song === null || !musicEnabled) {
    if (engine.music.current) engine.music.stop(1)
    applied = { song: null, arrangement: null, transpose: 0, playback: null }
    return
  }
  const req = r.song
  const song = await loadSong(req.id)
  if (lastRequest !== r) return
  const arrangement = arrangementFor(song, req)
  const current = engine.music.current
  const same = current && !current.stopping && applied.song === req.id && applied.transpose === req.transpose && sameArrangement(applied.arrangement, arrangement)
  if (same && current) {
    const wasLobby = current.layers.has('lobby')
    const toMatch = !req.layers.includes('lobby')
    if (song.kind === 'battle' && wasLobby && toMatch) {
      // §7.5 match start: the song restarts at its first battle section on the next beat.
      const p = engine.music.play(song, { arrangement: { ...(arrangement ?? {}), order: undefined, loopFrom: undefined }, layers: req.layers, stem: req.stem, weather: r.weather, transpose: req.transpose, startIndex: Math.max(0, song.order.indexOf('intro')), fadeInSec: 0.05, fadeOutSec: 0.2, onBeatOf: current })
      applied = { song: req.id, arrangement, transpose: req.transpose, playback: p }
      return
    }
    engine.music.setLayers(req.layers)
    engine.music.setStem(req.stem)
    engine.music.setWeather(r.weather)
    return
  }
  const sameKeyAndTempo = current && !current.stopping && current.song.tune.key.tonic + current.transpose === song.tune.key.tonic + req.transpose && current.transport.bpm === song.bpm + (arrangement?.tempoNudge ?? 0)
  const startIndex = song.kind === 'battle' && !req.layers.includes('lobby') ? Math.max(0, song.order.indexOf('intro')) : 0
  const p = engine.music.play(song, {
    arrangement,
    layers: req.layers,
    stem: req.stem,
    weather: r.weather,
    transpose: req.transpose,
    startIndex,
    fadeInSec: sameKeyAndTempo ? 0.3 : req.crossfadeSec,
    fadeOutSec: sameKeyAndTempo ? 0.3 : req.crossfadeSec,
    onBeatOf: sameKeyAndTempo ? current : null,
  })
  applied = { song: req.id, arrangement, transpose: req.transpose, playback: p }
}

/** The Music switch: off stops everything; on re-applies the last request. */
export function setMusicEnabled(engine: Engine, on: boolean): void {
  if (musicEnabled === on) return
  musicEnabled = on
  if (!on) {
    engine.music.stop(0.5)
    applied = { song: null, arrangement: null, transpose: 0, playback: null }
  } else if (lastRequest) void applyRequest(engine, lastRequest)
}

/* ---------- the drill cue (§8.1) ---------- */

interface ActiveCue {
  recipe: DrillCueRecipe
  outcome: DrillOutcome
  resultAt: number
  stingerPlayed: boolean
  foleyTimer: ReturnType<typeof setTimeout> | null
  bed: Playback | null
}
let cue: ActiveCue | null = null

function playOutcome(engine: Engine, c: ActiveCue, at: number, gainDb = 0): void {
  if (c.stingerPlayed) return
  c.stingerPlayed = true
  const stinger = c.recipe.stingers[c.outcome]
  const now = engine.ctx.currentTime
  const when = Math.max(now, at)
  if (c.outcome === 'Slacked' && c.bed) {
    engine.music.sag(c.recipe.sag.rate, c.recipe.sag.seconds)
    if (c.recipe.breath) engine.scheduler.add(when + 0.6, () => engine.sfx.play('drill-breath', c.recipe.breath!, {}))
  }
  const start = () => {
    if (c.bed && !c.bed.stopping) engine.music.stop(0.25)
    engine.music.play(stinger, { once: true, fadeInSec: 0.02, fadeOutSec: 0.2, arrangement: gainDb ? { gainDb } : null })
  }
  if (when - now < 0.01) start()
  else engine.scheduler.add(when, start)
}

function scheduleFoley(engine: Engine, c: ActiveCue): void {
  if (c.recipe.foley.length === 0) return
  // On the audio clock (so an offline render gets the same timeline), until the stinger.
  const tag = `drill-foley-${c.resultAt}`
  const next = (at: number) => {
    if (cue !== c || c.stingerPlayed || at >= c.resultAt - 0.2) return
    engine.scheduler.add(
      at,
      (t) => {
        if (cue !== c || c.stingerPlayed) return
        for (const f of c.recipe.foley) engine.sfx.play(`drill-${f.marker}`, f.sfx, { pan: (engine.rng() - 0.5) * 0.6, at: t })
        const gap = c.recipe.foley[0]!.every
        next(t + gap[0] + (gap[1] - gap[0]) * engine.rng())
      },
      tag,
    )
  }
  next(engine.ctx.currentTime + 0.25)
}

/** Starts the cue and returns the audio-clock time the result should show. */
export function startDrillCue(engine: Engine, drill: DrillId, outcome: DrillOutcome, o: { vignetteMs: number; instant?: boolean }): number {
  const recipe = cueFor(drill)
  const now = engine.ctx.currentTime
  if (o.instant) {
    // Instant speed, or the planner running several weeks: the stinger only, at −6 dB, over whatever plays.
    const c: ActiveCue = { recipe, outcome, resultAt: now, stingerPlayed: false, foleyTimer: null, bed: null }
    const stinger = recipe.stingers[outcome]
    engine.music.interrupt(stinger, { transpose: 0, fadeInAfterSec: AUDIO.stingerFadeInAfterDrillSec, gainDb: AUDIO.drill.instantStingerDb })
    void c
    return now
  }
  endDrillCue(engine, true)
  engine.music.suspendArea(AUDIO.drill.musicFadeOutSec)
  engine.ambience.setBed(recipe.bed, AUDIO.drill.bedFadeInSec)
  engine.graph.reverbPlace.setPreset(recipe.reverb)
  const bed = engine.music.play(recipe.song, { fadeInSec: AUDIO.drill.bedFadeInSec, fadeOutSec: 0.2, arrangement: { gainDb: recipe.musicGainDb } })
  const c: ActiveCue = { recipe, outcome, resultAt: now + o.vignetteMs / 1000, stingerPlayed: false, foleyTimer: null, bed }
  cue = c
  scheduleFoley(engine, c)
  playOutcome(engine, c, c.resultAt)
  return c.resultAt
}

/** Skip: the bed fades in 80 ms and the stinger plays at once. */
export function skipDrillCue(engine: Engine): void {
  const c = cue
  if (!c) return
  if (c.foleyTimer) clearTimeout(c.foleyTimer)
  engine.scheduler.cancel(c.bed?.tag ?? '')
  if (c.bed && !c.bed.stopping) engine.music.stop(AUDIO.drill.skipFadeMs / 1000)
  c.bed = null
  c.resultAt = engine.ctx.currentTime
  playOutcome(engine, c, c.resultAt)
}

/** The result closed: the drill bed fades over 1 s, the ranch bed returns and the music restarts at its next section. */
export function endDrillCue(engine: Engine, silent = false): void {
  const c = cue
  cue = null
  if (!c) return
  if (c.foleyTimer) clearTimeout(c.foleyTimer)
  if (engine.music.current && engine.music.current.song.kind === 'drill') engine.music.stop(AUDIO.drill.endFadeSec)
  if (!silent) {
    engine.music.resumeArea(AUDIO.stingerFadeInAfterDrillSec)
    if (lastRequest && lastRequest.bed !== 'keep') {
      engine.ambience.setBed(lastRequest.bed, AUDIO.bedCrossfadeSec)
      engine.graph.reverbPlace.setPreset(lastRequest.reverb)
    }
  }
}

/** DrillResult reports when it actually switched, for the ±25 ms log. */
export function markResultShown(engine: Engine, resultAt: number): void {
  engine.drillCueErrorMs = Math.round((engine.ctx.currentTime - resultAt) * 1000)
}

/* ---------- the debug view (§4.8) ---------- */

export function installDebugView(engine: Engine): void {
  if (typeof window === 'undefined') return
  const w = window as Window & { __audio?: unknown }
  w.__audio = {
    get state() {
      return { ...engine.debug(), request: lastRequest ? { song: lastRequest.song === 'keep' ? 'keep' : lastRequest.song?.id ?? null, bed: lastRequest.bed, crowd: lastRequest.crowd, standIn: lastRequest.standIn } : null }
    },
    engine,
  }
}

export function lastApplied(): Request | null {
  return lastRequest
}

export function weatherOf(r: Request | null): Weather | null {
  return r?.weather ?? null
}
