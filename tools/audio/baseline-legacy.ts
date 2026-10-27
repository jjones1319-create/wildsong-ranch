/**
 * SOUND_UPGRADE §15 S1 step 1: the numbers of the old sound, measured before it was removed.
 *   node tools/audio/baseline-legacy.ts
 * Renders the nine chiptune loops with the old pure sequencer (`src/audio/music.ts`) and the ZzFX effects
 * with ZzFX's own `buildSamples`, at the old default volumes (master 80, music 55, effects 100), then runs
 * the shared analysers and writes `tools/audio/baseline-legacy.json`.
 *
 * It only runs at the commit before Sound S1 (the old modules and the zzfx package are gone after it), so it
 * is excluded from `tsc -b`; the JSON is the artefact. ZzFX makes an AudioContext when it loads, so Node gets
 * a stub first, and its randomness is seeded so the numbers repeat.
 */
import { execSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { findClicks } from '../../src/audio/analysis/clicks.ts'
import { crestDb, loudness, peakDb } from '../../src/audio/analysis/loudness.ts'
import { bandShares } from '../../src/audio/analysis/spectrum.ts'
import { truePeakDb } from '../../src/audio/analysis/truepeak.ts'
import { renderTrack, sampleCount, stepsOf, TRACK_IDS, TRACKS } from '../../src/audio/music.ts'
import { SFX, SFX_IDS } from '../../src/audio/sfx.ts'
import { AUDIO } from '../../src/data/tuning.ts'

const g = globalThis as unknown as { AudioContext?: unknown }
g.AudioContext ??= class StubAudioContext {}
const { ZZFX } = await import('zzfx')

/** Mulberry32 in place of Math.random while ZzFX renders, so a re-run gives the same file. */
let seed = 0x5eed1234
Math.random = () => {
  seed = (seed + 0x6d2b79f5) | 0
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296
}

const r2 = (n: number) => (Number.isFinite(n) ? Math.round(n * 100) / 100 : null)
const pct = (n: number) => n / 100
const musicGain = pct(AUDIO.defaultVolume.master) * pct(AUDIO.defaultVolume.music)
const sfxGain = pct(AUDIO.defaultVolume.master) * pct(AUDIO.defaultVolume.sfx)
const BANDS = [
  [2000, 6000],
  [8000, 48000],
] as const

function scaled(x: Float32Array, gain: number): Float32Array {
  const out = new Float32Array(x.length)
  for (let i = 0; i < x.length; i++) out[i] = x[i]! * gain
  return out
}

function repeatTo(x: Float32Array, seconds: number, sampleRate: number): Float32Array {
  const n = Math.round(seconds * sampleRate)
  const out = new Float32Array(n)
  for (let i = 0; i < n; i++) out[i] = x[i % x.length]!
  return out
}

const tracks: Record<string, unknown> = {}
for (const id of TRACK_IDS) {
  const track = TRACKS[id]
  const sr = AUDIO.sampleRate
  const loop = scaled(renderTrack(track, sr), musicGain)
  const loopSeconds = sampleCount(track, sr) / sr
  const measured = track.loop ? repeatTo(loop, 45, sr) : loop
  const l = loudness([measured], sr)
  const [mid, high] = bandShares([measured], sr, BANDS)
  tracks[id] = {
    bpm: track.bpm,
    loop: track.loop,
    steps: stepsOf(track),
    loopSeconds: r2(loopSeconds),
    repeatsPerMinute: track.loop ? r2(60 / loopSeconds) : null,
    sampleRate: sr,
    waves: track.voices.map((v) => v.wave),
    lufs: r2(l.integrated),
    shortTermMaxLufs: r2(l.shortTermMax),
    truePeakDbtp: r2(truePeakDb([measured])),
    peakDbfs: r2(peakDb([measured])),
    crestDb: r2(crestDb([measured])),
    share2to6k: r2(mid! * 100),
    shareAbove8k: r2(high! * 100),
  }
}

const effects: Record<string, unknown> = {}
for (const id of SFX_IDS) {
  ZZFX.volume = 0.3 * sfxGain
  const raw = ZZFX.buildSamples(...SFX[id])
  const sr = ZZFX.sampleRate
  const x = new Float32Array(raw.length)
  for (let i = 0; i < raw.length; i++) x[i] = Math.max(-1, Math.min(1, raw[i]!))
  const l = loudness([x], sr)
  const [mid, high] = bandShares([x], sr, BANDS)
  const shape = SFX[id][6] ?? 0
  effects[id] = {
    seconds: r2(x.length / sr),
    shape: ['sine', 'triangle', 'saw', 'tan', 'noise'][shape] ?? String(shape),
    bitCrush: (SFX[id][15] ?? 0) > 0,
    lufs: r2(l.integrated),
    momentaryMaxLufs: r2(l.momentaryMax),
    truePeakDbtp: r2(truePeakDb([x])),
    peakDbfs: r2(peakDb([x])),
    crestDb: r2(crestDb([x])),
    share2to6k: r2(mid! * 100),
    shareAbove8k: r2(high! * 100),
    clicks: findClicks([x], sr, [0]).length,
  }
}

let commit = 'unknown'
try {
  commit = execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim()
} catch {
  /* no git */
}

const out = {
  recordedAt: new Date().toISOString().slice(0, 10),
  commit,
  how: 'node tools/audio/baseline-legacy.ts at the commit before Sound S1: the old chiptune loops rendered by src/audio/music.ts at 22,050 Hz mono (repeated to 45 s) and the ZzFX effects at 44,100 Hz, both at the old default volumes (master 80, music 55, effects 100). Loudness is BS.1770-4 integrated; brightness shares are percent of energy.',
  defaults: { master: AUDIO.defaultVolume.master, music: AUDIO.defaultVolume.music, sfx: AUDIO.defaultVolume.sfx, duckPct: AUDIO.duckPct, duckMs: AUDIO.duckMs },
  tracks,
  effects,
}
writeFileSync('tools/audio/baseline-legacy.json', JSON.stringify(out, null, 2) + '\n')
console.log(`wrote tools/audio/baseline-legacy.json: ${TRACK_IDS.length} tracks, ${SFX_IDS.length} effects`)
for (const id of TRACK_IDS) {
  const t = tracks[id] as { lufs: number; crestDb: number; loopSeconds: number; share2to6k: number }
  console.log(`  ${id.padEnd(12)} ${String(t.lufs).padStart(7)} LUFS  crest ${String(t.crestDb).padStart(5)} dB  loop ${String(t.loopSeconds).padStart(5)} s  2–6k ${t.share2to6k}%`)
}
