/**
 * SOUND_UPGRADE §14.3–14.4: the offline render harness behind `window.__audio.render`. The real engine runs
 * on the offline driver in an OfflineAudioContext at 48 kHz with the real samples, the Phone speaker preset
 * and the default volumes, at a fixed seed. One 8-channel render taps the four stems; a second records the
 * master. The analysis runs here, in the page, so only numbers travel to the tool (and the master's PCM as
 * base64 chunks when a review file is wanted).
 */
import { findClicks, findDropouts } from '../../../audio/analysis/clicks.ts'
import { crestDb, loudness } from '../../../audio/analysis/loudness.ts'
import { bandShares } from '../../../audio/analysis/spectrum.ts'
import { truePeakDb } from '../../../audio/analysis/truepeak.ts'
import { createEngine, type Engine } from '../../../audio/engine/index.ts'
import { DEFAULT_KEY } from '../../../audio/engine/sfx.ts'
import { musicalEffectDef } from '../../../audio/music/effects.ts'
import type { Arrangement } from '../../../audio/music/song.ts'
import { loadSong } from '../../../audio/music/songs/index.ts'
import { STINGERS } from '../../../audio/music/stingers.ts'
import { cueFor } from '../../../audio/recipes/drills.ts'
import { battleSfx, UI_SFX, WORLD_SFX, type SfxDef, type Strength, type UiSfxId, type WorldSfxId } from '../../../audio/recipes/sfx.ts'
import type { RenderItem, RenderResult, StemStats } from '../../../audio/renderTypes.ts'
import { startDrillCue } from '../../../audio/runtime.ts'
import { AUDIO } from '../../../data/tuning.ts'
import type { Element } from '../../../data/types.ts'
import type { FxEventKind } from '../../../fx/bus.ts'

export type { RenderItem, RenderResult, StemStats }

const SR = 48000
const DEFAULT_VOLUMES = { master: AUDIO.defaultVolume.master, music: AUDIO.defaultVolume.music, sfx: AUDIO.defaultVolume.sfx, ambience: AUDIO.defaultVolume.ambience, musicOn: true, sfxOn: true, ambienceOn: true, buttonSounds: true }

function stats(channels: Float32Array[], onsets: number[], rests: readonly (readonly [number, number])[]): StemStats {
  const l = loudness(channels, SR)
  const [mid, high] = bandShares(channels, SR, [
    [2000, 6000],
    [8000, 24000],
  ])
  const clicks = findClicks(channels, SR, onsets)
  return {
    lufs: round(l.integrated),
    shortTermMax: round(l.shortTermMax),
    momentaryMax: round(l.momentaryMax),
    truePeakDb: round(truePeakDb(channels)),
    crestDb: round(crestDb(channels)),
    share2to6k: round(mid! * 100),
    shareAbove8k: round(high! * 100),
    clicks: clicks.length,
    clickTimes: clicks.slice(0, 12).map((c) => Math.round(c.t * 1000) / 1000),
    dropouts: findDropouts(channels, SR, -60, 300, rests).length,
    shortTerm: Array.from(l.shortTerm, round),
    momentary: Array.from(l.momentary, round),
  }
}

function round(n: number): number {
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : -120
}

function effectDef(id: string): SfxDef | null {
  if (id in UI_SFX) return UI_SFX[id as UiSfxId]
  if (id in WORLD_SFX) return WORLD_SFX[id as WorldSfxId]
  return musicalEffectDef(id)
}

function secondsOf(item: RenderItem): number {
  switch (item.kind) {
    case 'song':
    case 'bed':
    case 'battleDemo':
    case 'loopSeam':
      return item.seconds
    case 'stinger':
      return item.chain ? 18 : 12
    case 'effect':
      return item.seconds ?? 4
    case 'battleFx':
      return item.seconds ?? 2 + item.kinds.length * 1.5
    case 'drill':
      return item.seconds ?? 9
  }
}

/** Builds the engine on an offline context, loads what the item needs, and scripts it. */
async function prepare(ctx: OfflineAudioContext, item: RenderItem, seed: number, stems: boolean): Promise<{ engine: Engine; marks: { t: number; what: string }[]; rests: [number, number][] }> {
  const engine = createEngine(ctx, { baseUrl: import.meta.env.BASE_URL, seed, stems, driver: 'offline' })
  engine.graph.setVolumes(DEFAULT_VOLUMES)
  engine.graph.setListening('speaker')
  engine.scheduler.log = []
  // The offline driver only ticks (and the scheduler only fills) once the engine is started.
  engine.start()
  await engine.loadCore()
  await engine.loadPack('events')
  const marks: { t: number; what: string }[] = []
  const rests: [number, number][] = []
  const key = DEFAULT_KEY
  switch (item.kind) {
    case 'song': {
      const song = await loadSong(item.id)
      const base = item.arrangement ? (song.arrangements?.[item.arrangement] ?? null) : null
      const arrangement: Arrangement | null = item.kit || item.lead || base ? { ...(base ?? {}), ...(item.kit ? { kit: item.kit } : {}), ...(item.lead ? { swap: { ...(base?.swap ?? {}), lead: item.lead, lobbyLead: item.lead } } : {}) } : null
      engine.music.play(song, { layers: item.layers ?? (song.kind === 'battle' ? ['base', 'drive'] : ['main']), stem: item.stem ?? null, weather: item.weather ?? 'Sunny', arrangement, transpose: item.transpose ?? 0, fadeInSec: 0.02, startIndex: item.startIndex ?? (song.kind === 'battle' && !(item.layers ?? []).includes('lobby') ? Math.max(0, song.order.indexOf('intro')) : 0) })
      break
    }
    case 'loopSeam': {
      const song = await loadSong(item.id)
      engine.music.play(song, { layers: ['main', 'base', 'drive'], weather: 'Sunny', fadeInSec: 0.02 })
      break
    }
    case 'bed':
      engine.ambience.setWeather(item.weather ?? 'Sunny')
      engine.ambience.setBed(item.id, 0.05)
      if (item.crowd) engine.ambience.setCrowd(item.crowd)
      break
    case 'stinger':
      if (item.chain) engine.music.interruptChain(item.chain.map((id) => STINGERS[id]), { transpose: item.transpose ?? 0 })
      else engine.music.play(STINGERS[item.id], { once: true, transpose: item.transpose ?? 0, fadeInSec: 0.02 })
      break
    case 'effect': {
      const def = effectDef(item.id)
      if (def) engine.scheduler.add(0.2, (t) => engine.sfx.play(item.id, def, { at: t, key }))
      marks.push({ t: 0.2, what: item.id })
      break
    }
    case 'battleFx': {
      let t = 0.3
      for (const kind of item.kinds) {
        const def = battleSfx(kind, item.element, item.strength, kind === 'crit')
        const at = t
        engine.scheduler.add(at, (when) => engine.sfx.play(`${kind}:${item.element}`, def, { at: when, key }))
        marks.push({ t: at, what: `${kind}:${item.element}:${item.strength}` })
        t += 1.5
      }
      break
    }
    case 'drill': {
      const recipe = cueFor(item.drill)
      engine.ambience.setBed(recipe.bed, 0.05)
      startDrillCue(engine, item.drill, item.outcome, { vignetteMs: 5000 })
      marks.push({ t: 5, what: `result:${item.outcome}` })
      break
    }
    case 'battleDemo': {
      const song = await loadSong(item.song ?? 'cup')
      engine.ambience.setBed('arena', 0.05)
      engine.ambience.setCrowd(item.crowd ?? 'small')
      engine.music.play(song, { layers: item.layers ?? ['base'], weather: 'Sunny', fadeInSec: 0.02, startIndex: Math.max(0, song.order.indexOf('intro')) })
      engine.scheduler.add(4, () => engine.music.setLayers(['base', 'drive']))
      // A scripted match: hits every 1.2 s with elements in turn, a Special at 20 s, tension at 45 s, a KO at 58 s.
      const elements: Element[] = ['Physical', 'Fire', 'Water', 'Earth', 'Wind', 'Ice', 'Nature', 'Light', 'Dark', 'Lightning', 'Sound']
      let n = 0
      for (let t = 2; t < item.seconds - 3; t += 1.2) {
        const element = elements[n % elements.length]!
        const kind: FxEventKind = n % 7 === 6 ? 'miss' : n % 5 === 4 ? 'crit' : 'hit'
        const strength: Strength = n % 3 === 0 ? 'light' : n % 3 === 1 ? 'medium' : 'heavy'
        const at = t
        engine.scheduler.add(at - 0.4, (when) => engine.sfx.play(`fire:${element}`, battleSfx('fire', element, strength), { at: when, key, pan: -0.3 }))
        engine.scheduler.add(at, (when) => {
          engine.sfx.play(`${kind}:${element}`, battleSfx(kind, element, strength, kind === 'crit'), { at: when, key, pan: 0.3 })
          if (kind === 'crit' || strength === 'heavy') engine.ambience.react('cheer', when)
          if (kind === 'miss') engine.ambience.react('ooh', when)
        })
        marks.push({ t: at, what: `${kind}:${element}:${strength}` })
        n++
      }
      engine.scheduler.add(20, (when) => {
        engine.sfx.play('special:Light', battleSfx('special', 'Light', 'heavy'), { at: when, key })
        engine.graph.duck(AUDIO.duck.db, AUDIO.duck.sec)
        engine.ambience.react('murmur', when)
      })
      marks.push({ t: 20, what: 'special' })
      if (item.seconds > 46) engine.scheduler.add(45, () => engine.music.setLayers(['base', 'drive', 'tension']))
      if (item.seconds > 59) {
        engine.scheduler.add(58, (when) => {
          engine.sfx.play('ko:Physical', battleSfx('ko', 'Physical', 'heavy'), { at: when, key })
          engine.music.cut(0.15)
          engine.ambience.react('ko', when)
        })
        marks.push({ t: 58, what: 'ko' })
        rests.push([57.8, item.seconds])
      }
      break
    }
  }
  return { engine, marks, rests }
}

function toBase64Chunks(buffer: AudioBuffer): string[] {
  const frames = buffer.length
  const chans = buffer.numberOfChannels
  const data = new Int16Array(frames * chans)
  for (let c = 0; c < chans; c++) {
    const ch = buffer.getChannelData(c)
    for (let i = 0; i < frames; i++) data[i * chans + c] = Math.max(-32768, Math.min(32767, Math.round(ch[i]! * 32767)))
  }
  const bytes = new Uint8Array(data.buffer)
  const chunks: string[] = []
  const step = 1 << 20
  for (let at = 0; at < bytes.length; at += step) {
    const slice = bytes.subarray(at, Math.min(bytes.length, at + step))
    let s = ''
    for (let i = 0; i < slice.length; i += 0x8000) s += String.fromCharCode.apply(null, Array.from(slice.subarray(i, i + 0x8000)))
    chunks.push(btoa(s))
  }
  return chunks
}

/** Renders an item twice (stems, then master) and measures everything (§14.3). */
export async function renderItem(item: RenderItem, seed: number, opts: { pcm?: boolean } = {}): Promise<RenderResult> {
  const seconds = secondsOf(item)
  const length = Math.round(seconds * SR)
  const stemsCtx = new OfflineAudioContext({ numberOfChannels: 8, length, sampleRate: SR })
  const a = await prepare(stemsCtx, item, seed, true)
  const stemsBuffer = await a.engine.render()
  const onsets = [...(a.engine.scheduler.log ?? [])]
  const masterCtx = new OfflineAudioContext({ numberOfChannels: 2, length, sampleRate: SR })
  const b = await prepare(masterCtx, item, seed, false)
  const masterBuffer = await b.engine.render()
  const stem = (i: number) => [stemsBuffer.getChannelData(i), stemsBuffer.getChannelData(i + 1)]
  const master = [masterBuffer.getChannelData(0), masterBuffer.getChannelData(1)]
  const result: RenderResult = {
    seconds,
    sampleRate: SR,
    stems: {
      music: stats(stem(0), onsets, a.rests),
      ambience: stats(stem(2), onsets, a.rests),
      sfx: stats(stem(4), onsets, a.rests),
      ui: stats(stem(6), onsets, a.rests),
      master: stats(master, onsets, a.rests),
    },
    onsets: onsets.map(round),
    marks: a.marks,
    lateEvents: a.engine.scheduler.lateEvents + b.engine.scheduler.lateEvents,
    decodeMs: a.engine.bank.decodeMs('core'),
  }
  if (opts.pcm) result.pcm = { sampleRate: SR, channels: 2, chunks: toBase64Chunks(masterBuffer) }
  a.engine.stop()
  b.engine.stop()
  return result
}

/** Decodes every manifest file and compares onset and length with the manifest (§5.4). */
export async function checkDecodedSamples(): Promise<{ file: string; onsetMs: number; lengthMs: number; ok: boolean }[]> {
  const ctx = new OfflineAudioContext({ numberOfChannels: 1, length: 48000, sampleRate: SR })
  const engine = createEngine(ctx, { baseUrl: import.meta.env.BASE_URL, seed: 1, driver: 'offline' })
  const m = await engine.bank.loadManifest()
  const out: { file: string; onsetMs: number; lengthMs: number; ok: boolean }[] = []
  for (const inst of Object.values(m.instruments)) {
    for (const list of Object.values(inst.arts)) {
      for (const s of list) {
        const res = await fetch(`${import.meta.env.BASE_URL}audio/${s.file}`)
        const buf = await ctx.decodeAudioData(await res.arrayBuffer())
        const d = buf.getChannelData(0)
        const thr = Math.pow(10, -50 / 20)
        let first = 0
        while (first < d.length && Math.abs(d[first]!) < thr) first++
        const onsetMs = (first / buf.sampleRate - s.onset) * 1000
        const lengthMs = (buf.duration - s.seconds) * 1000
        out.push({ file: s.file, onsetMs: round(onsetMs), lengthMs: round(lengthMs), ok: Math.abs(onsetMs) <= 1 && Math.abs(lengthMs) <= 20 })
      }
    }
  }
  return out
}
