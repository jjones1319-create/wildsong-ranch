import { effect } from '@preact/signals'
import { AUDIO } from '../data/tuning.ts'
import type { AppSettings } from '../save/schema.ts'
import { settings } from '../ui/store/appStore.ts'
import { renderTrack, TRACKS, type TrackId } from './music.ts'
import { SFX, type SfxId } from './sfx.ts'

/**
 * GAME_DESIGN §23: the only module that touches Web Audio. Audio unlocks on the first `pointerup` (phones
 * require a gesture); ZzFX is imported then, because the library creates an AudioContext when it loads.
 * Music loops are rendered once from `music.ts` and cached. On iOS the session is `ambient`, so the
 * player's own music keeps playing and the silent switch is respected. Everything is a no-op without a DOM.
 */

type Zz = typeof import('zzfx')

let ctx: AudioContext | null = null
let zz: Zz | null = null
let unlocking: Promise<void> | null = null
let musicGain: GainNode | null = null
let current: { id: TrackId; source: AudioBufferSourceNode; gain: GainNode } | null = null
let wanted: TrackId | null = null
let stingerUntil = 0
let duckTimer: ReturnType<typeof setTimeout> | null = null
const buffers = new Map<TrackId, AudioBuffer>()

export function audioReady(): boolean {
  return ctx !== null && zz !== null
}

function pct(n: number): number {
  return Math.max(0, Math.min(100, n)) / 100
}

function musicLevel(s: AppSettings = settings.value): number {
  return s.music ? pct(s.masterVolume) * pct(s.musicVolume) : 0
}

function sfxLevel(s: AppSettings = settings.value): number {
  return s.sound ? pct(s.masterVolume) * pct(s.sfxVolume) : 0
}

/** Creates the context inside a user gesture, loads ZzFX and points it at our context. */
export function unlockAudio(): Promise<void> {
  if (unlocking) return unlocking
  unlocking = (async () => {
    if (typeof window === 'undefined' || typeof AudioContext === 'undefined') return
    try {
      ctx = new AudioContext()
      const nav = navigator as Navigator & { audioSession?: { type: string } }
      if (nav.audioSession) nav.audioSession.type = 'ambient'
      musicGain = ctx.createGain()
      musicGain.gain.value = musicLevel()
      musicGain.connect(ctx.destination)
      const mod = await import('zzfx')
      mod.ZZFX.audioContext = ctx
      zz = mod
      if (ctx.state === 'suspended') await ctx.resume()
      applyWanted()
    } catch {
      ctx = null
      zz = null
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
    if (doc.visibilityState === 'hidden') void ctx.suspend()
    else void ctx.resume()
  })
  // Volume and mute changes apply at once.
  effect(() => {
    const s = settings.value
    if (musicGain && ctx) musicGain.gain.setTargetAtTime(musicLevel(s), ctx.currentTime, 0.05)
    if (!s.music && current) stopCurrent()
    if (s.music && !current && wanted) applyWanted()
  })
}

/* ---------- effects ---------- */

export function playSfx(id: SfxId): void {
  if (!ctx || !zz) return
  const level = sfxLevel()
  if (level <= 0) return
  try {
    zz.ZZFX.volume = 0.3 * level
    zz.ZZFX.play(...SFX[id])
    duck()
  } catch {
    /* an effect is never worth an error */
  }
}

/** Music steps aside for a moment under a burst of effects. */
function duck(): void {
  if (!ctx || !musicGain) return
  const base = musicLevel()
  musicGain.gain.setTargetAtTime(base * (AUDIO.duckPct / 100), ctx.currentTime, 0.02)
  if (duckTimer) clearTimeout(duckTimer)
  duckTimer = setTimeout(() => {
    if (ctx && musicGain) musicGain.gain.setTargetAtTime(musicLevel(), ctx.currentTime, 0.08)
  }, AUDIO.duckMs)
}

/* ---------- music ---------- */

function bufferFor(id: TrackId): AudioBuffer | null {
  if (!ctx) return null
  let b = buffers.get(id)
  if (!b) {
    const samples = renderTrack(TRACKS[id], AUDIO.sampleRate)
    b = ctx.createBuffer(1, samples.length, AUDIO.sampleRate)
    b.getChannelData(0).set(samples)
    buffers.set(id, b)
  }
  return b
}

function stopCurrent(): void {
  if (!current || !ctx) return
  const { source, gain } = current
  current = null
  const fade = AUDIO.fadeMs / 1000
  gain.gain.setTargetAtTime(0, ctx.currentTime, fade / 3)
  setTimeout(() => {
    try {
      source.stop()
      source.disconnect()
      gain.disconnect()
    } catch {
      /* already stopped */
    }
  }, AUDIO.fadeMs)
}

function startTrack(id: TrackId, loop: boolean): void {
  if (!ctx || !musicGain) return
  const buffer = bufferFor(id)
  if (!buffer) return
  const source = ctx.createBufferSource()
  source.buffer = buffer
  source.loop = loop
  const gain = ctx.createGain()
  gain.gain.value = 0
  gain.gain.setTargetAtTime(1, ctx.currentTime, AUDIO.fadeMs / 3000)
  source.connect(gain)
  gain.connect(musicGain)
  source.start()
  current = { id, source, gain }
}

function applyWanted(): void {
  if (!ctx || !zz || Date.now() < stingerUntil) return
  if (musicLevel() <= 0) return
  if (wanted === null) {
    stopCurrent()
    return
  }
  if (current?.id === wanted) return
  stopCurrent()
  startTrack(wanted, TRACKS[wanted].loop)
}

/** Asks for a track (or silence). Takes effect once audio is unlocked; switching fades. */
export function setMusic(id: TrackId | null): void {
  wanted = id
  applyWanted()
}

/** Plays a one-shot track (the victory fanfare) over the music, then brings the music back. */
export function playStinger(id: TrackId): void {
  if (!ctx || !zz || musicLevel() <= 0) return
  stopCurrent()
  startTrack(id, false)
  stingerUntil = Date.now() + AUDIO.stingerMs
  setTimeout(() => {
    stingerUntil = 0
    if (current?.id === id) {
      current = null
    }
    applyWanted()
  }, AUDIO.stingerMs)
}

/** The track playing right now (for tests and the Settings preview). */
export function currentTrack(): TrackId | null {
  return current?.id ?? null
}
