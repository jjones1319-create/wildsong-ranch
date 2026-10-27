/**
 * SOUND_UPGRADE §4.2–4.3: the buses and the master chain.
 *
 *   songs → musicBus: HP 35 Hz · high shelf −1.5 dB @ 7 kHz · duck · pause lowpass ─┐
 *   beds  → ambienceBus ─────────────────────────────────────────────────────────────┴→ mix: glue 1.5:1 @ −20 dB
 *   sfx   → sfxBus: compressor 2:1 @ −16 dB ───────────────────────────────────────────┐
 *   ui    → uiBus ────────────────────────────────────────────────────────────────────┤  (effects join after the glue)
 *   mix → listening EQ → limiter (−4 dB, 20:1) → master gain → width → (mono) → out
 *
 * Reverbs: a music slot (hall or room) and a place slot (outdoor, room, cave, underwater). Effects and UI join
 * after the glue so a hit never pulls the music down. Volume sliders map to gain = (v/100)². Works on an
 * AudioContext and on an OfflineAudioContext; with `stems` the four buses also feed an 8-channel tap.
 */
import { makeCompressor, makeFilter, makeGain, rampTo } from './nodes.ts'
import { Meters } from './meters.ts'
import { ReverbSlot } from './reverb.ts'

export type ListeningPreset = 'speaker' | 'headphones'

export interface VolumeSettings {
  master: number
  music: number
  sfx: number
  ambience: number
  /** Switches. */
  musicOn: boolean
  sfxOn: boolean
  ambienceOn: boolean
  buttonSounds: boolean
}

export interface Graph {
  ctx: BaseAudioContext
  /** Songs connect here. */
  music: GainNode
  /** Beds connect here. */
  ambience: GainNode
  /** Effects connect here. */
  sfx: GainNode
  /** UI ticks connect here. */
  ui: GainNode
  master: GainNode
  reverbMusic: ReverbSlot
  reverbPlace: ReverbSlot
  musicDuck: GainNode
  musicFilter: BiquadFilterNode
  /** The 8-channel stem tap, in render mode. */
  stems: ChannelMergerNode | null
  meters: Meters | null
  listening: ListeningPreset
  mono: boolean
  setVolumes(v: VolumeSettings): void
  setListening(p: ListeningPreset): void
  setMono(on: boolean): void
  /** The battle pause: lowpass to 700 Hz and −4 dB over 300 ms; off reverses it. */
  setPaused(on: boolean): void
  /** The only duck: a Special dips the music `db` for `seconds`. */
  duck(db: number, seconds: number): void
  /** Current filter cutoff and duck in dB, for the debug view. */
  musicFilterHz(): number
  duckDb(): number
  /** The glue's gain reduction right now, dB (realtime only). */
  glueReductionDb(): number
}

export const LISTENING: Record<ListeningPreset, { hpHz: number; peakDb: number; peakHz: number; shelfDb: number; shelfHz: number; width: number }> = {
  speaker: { hpHz: 90, peakDb: -2.5, peakHz: 3200, shelfDb: -2, shelfHz: 8000, width: 0.7 },
  headphones: { hpHz: 30, peakDb: -1, peakHz: 3200, shelfDb: -1, shelfHz: 9000, width: 1 },
}

export function sliderGain(v: number): number {
  const x = Math.max(0, Math.min(100, v)) / 100
  return x * x
}

export function createGraph(ctx: BaseAudioContext, opts: { stems?: boolean; seed?: number; meters?: boolean } = {}): Graph {
  const seed = opts.seed ?? 0x1e5e4b
  const music = makeGain(ctx, 1)
  const musicHp = makeFilter(ctx, 'highpass', 35, 0.707)
  const musicShelf = makeFilter(ctx, 'highshelf', 7000, 0.707, -1.5)
  const musicDuck = makeGain(ctx, 1)
  const musicFilter = makeFilter(ctx, 'lowpass', 20000, 0.5)
  const musicOut = makeGain(ctx, 1)
  music.connect(musicHp)
  musicHp.connect(musicShelf)
  musicShelf.connect(musicDuck)
  musicDuck.connect(musicFilter)
  musicFilter.connect(musicOut)

  const ambience = makeGain(ctx, 1)
  const ambienceOut = makeGain(ctx, 1)
  ambience.connect(ambienceOut)

  const mix = makeGain(ctx, 1)
  musicOut.connect(mix)
  ambienceOut.connect(mix)
  const glue = makeCompressor(ctx, { thresholdDb: -20, kneeDb: 6, ratio: 1.5, attackSec: 0.03, releaseSec: 0.3 })
  mix.connect(glue.input)

  const sfx = makeGain(ctx, 1)
  const sfxComp = makeCompressor(ctx, { thresholdDb: -16, kneeDb: 6, ratio: 2, attackSec: 0.003, releaseSec: 0.15 })
  sfx.connect(sfxComp.input)
  const ui = makeGain(ctx, 1)

  // Listening preset EQ, then the limiter, the master gain and the width stage.
  const eqHp = makeFilter(ctx, 'highpass', 90, 0.707)
  const eqPeak = makeFilter(ctx, 'peaking', 3200, 0.9, -2.5)
  const eqShelf = makeFilter(ctx, 'highshelf', 8000, 0.707, -2)
  glue.output.connect(eqHp)
  sfxComp.output.connect(eqHp)
  ui.connect(eqHp)
  eqHp.connect(eqPeak)
  eqPeak.connect(eqShelf)
  const limiter = makeCompressor(ctx, { thresholdDb: -4, kneeDb: 0, ratio: 20, attackSec: 0.001, releaseSec: 0.12 })
  eqShelf.connect(limiter.input)
  const master = makeGain(ctx, 1)
  limiter.output.connect(master)
  // Width: L' = L(1+w)/2 + R(1−w)/2, R' = L(1−w)/2 + R(1+w)/2.
  const split = ctx.createChannelSplitter(2)
  const merge = ctx.createChannelMerger(2)
  const ll = makeGain(ctx, 1)
  const lr = makeGain(ctx, 0)
  const rl = makeGain(ctx, 0)
  const rr = makeGain(ctx, 1)
  master.connect(split)
  split.connect(ll, 0)
  split.connect(lr, 0)
  split.connect(rl, 1)
  split.connect(rr, 1)
  ll.connect(merge, 0, 0)
  rl.connect(merge, 0, 0)
  lr.connect(merge, 0, 1)
  rr.connect(merge, 0, 1)
  const monoStage = makeGain(ctx, 1)
  monoStage.channelCountMode = 'explicit'
  monoStage.channelCount = 2
  monoStage.channelInterpretation = 'speakers'
  merge.connect(monoStage)

  let stems: ChannelMergerNode | null = null
  if (opts.stems) {
    stems = ctx.createChannelMerger(8)
    const tap = (node: AudioNode, base: number) => {
      const s = ctx.createChannelSplitter(2)
      node.connect(s)
      s.connect(stems!, 0, base)
      s.connect(stems!, 1, base + 1)
    }
    tap(musicOut, 0)
    tap(ambienceOut, 2)
    tap(sfxComp.output, 4)
    tap(ui, 6)
    stems.connect(ctx.destination)
  } else monoStage.connect(ctx.destination)

  const reverbMusic = new ReverbSlot(ctx, music, 'hall', seed)
  const reverbPlace = new ReverbSlot(ctx, ambience, 'outdoor', seed + 1)

  let meters: Meters | null = null
  if (opts.meters) {
    meters = new Meters()
    meters.attach(ctx, 'music', musicOut)
    meters.attach(ctx, 'ambience', ambienceOut)
    meters.attach(ctx, 'sfx', sfxComp.output)
    meters.attach(ctx, 'ui', ui)
    meters.attach(ctx, 'master', monoStage)
  }

  let duckUntil = 0
  let duckLevel = 0
  let paused = false
  const graph: Graph = {
    ctx,
    music,
    ambience,
    sfx,
    ui,
    master,
    reverbMusic,
    reverbPlace,
    musicDuck,
    musicFilter,
    stems,
    meters,
    listening: 'speaker',
    mono: false,
    setVolumes(v) {
      const now = ctx.currentTime
      rampTo(master.gain, sliderGain(v.master), now, 0.05)
      rampTo(music.gain, v.musicOn ? sliderGain(v.music) : 0, now, 0.05)
      rampTo(sfx.gain, v.sfxOn ? sliderGain(v.sfx) : 0, now, 0.05)
      rampTo(ambience.gain, v.ambienceOn ? sliderGain(v.ambience) : 0, now, 0.05)
      rampTo(ui.gain, v.sfxOn && v.buttonSounds ? sliderGain(v.sfx) : 0, now, 0.05)
    },
    setListening(p) {
      const s = LISTENING[p]
      graph.listening = p
      eqHp.frequency.value = s.hpHz
      eqPeak.frequency.value = s.peakHz
      eqPeak.gain.value = s.peakDb
      eqShelf.frequency.value = s.shelfHz
      eqShelf.gain.value = s.shelfDb
      const w = s.width
      ll.gain.value = (1 + w) / 2
      rr.gain.value = (1 + w) / 2
      lr.gain.value = (1 - w) / 2
      rl.gain.value = (1 - w) / 2
    },
    setMono(on) {
      graph.mono = on
      monoStage.channelCount = on ? 1 : 2
    },
    setPaused(on) {
      if (paused === on) return
      paused = on
      const now = ctx.currentTime
      musicFilter.frequency.cancelScheduledValues(now)
      musicFilter.frequency.setValueAtTime(musicFilter.frequency.value, now)
      musicFilter.frequency.exponentialRampToValueAtTime(on ? 700 : 20000, now + 0.3)
      rampTo(musicDuck.gain, on ? Math.pow(10, -4 / 20) * (duckUntil > now ? duckLevel : 1) : duckUntil > now ? duckLevel : 1, now, 0.3)
    },
    duck(db, seconds) {
      const now = ctx.currentTime
      duckLevel = Math.pow(10, -Math.abs(db) / 20)
      duckUntil = now + seconds
      const pausedGain = paused ? Math.pow(10, -4 / 20) : 1
      rampTo(musicDuck.gain, duckLevel * pausedGain, now, 0.05)
      musicDuck.gain.setValueAtTime(duckLevel * pausedGain, now + seconds - 0.2)
      musicDuck.gain.linearRampToValueAtTime(pausedGain, now + seconds)
    },
    musicFilterHz: () => musicFilter.frequency.value,
    duckDb: () => {
      const g = musicDuck.gain.value
      return g > 0 ? 20 * Math.log10(g) : -Infinity
    },
    glueReductionDb: () => glue.input.reduction,
  }
  graph.setListening('speaker')
  return graph
}
