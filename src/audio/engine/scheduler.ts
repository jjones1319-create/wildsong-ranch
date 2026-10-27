/**
 * SOUND_UPGRADE §4.4: the look-ahead scheduler. Every event due within the next 400 ms is handed to its
 * player at each tick; an event up to 5 ms late still plays, a later one is dropped and counted in
 * `lateEvents`. One transport per song (tempo, meter, start time) so two songs with different tempos can
 * crossfade; changes quantise to now, the beat, the bar or the section. Pure, driven by a Driver.
 */
import type { Driver } from './driver.ts'

export interface Scheduled {
  time: number
  play: (time: number) => void
  /** Optional tag so a whole group can be cancelled (a stopped song). */
  tag?: string
}

export class Scheduler {
  readonly driver: Driver
  readonly lookahead: number
  readonly lateTolerance: number
  lateEvents = 0
  played = 0
  /** When set, every played event's time is appended (the render checks allow clicks only at these onsets). */
  log: number[] | null = null
  private queue: Scheduled[] = []
  /** Called at every tick after the due events, with the time up to which events should exist. */
  private fillers = new Set<(until: number) => void>()

  constructor(driver: Driver, lookahead = 0.4, lateTolerance = 0.005) {
    this.driver = driver
    this.lookahead = lookahead
    this.lateTolerance = lateTolerance
  }

  start(): void {
    this.driver.start(() => this.tick())
  }

  stop(): void {
    this.driver.stop()
    this.queue = []
  }

  now(): number {
    return this.driver.now()
  }

  /** The horizon events should be scheduled up to. */
  horizon(): number {
    return this.driver.now() + this.lookahead
  }

  add(time: number, play: (time: number) => void, tag?: string): void {
    const ev: Scheduled = { time, play, tag }
    // Binary insert, time-ordered.
    let lo = 0
    let hi = this.queue.length
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (this.queue[mid]!.time <= time) lo = mid + 1
      else hi = mid
    }
    this.queue.splice(lo, 0, ev)
  }

  cancel(tag: string): number {
    const before = this.queue.length
    this.queue = this.queue.filter((e) => e.tag !== tag)
    return before - this.queue.length
  }

  /** A filler is asked at each tick to schedule anything due before the horizon (a song's next bar). */
  addFiller(fn: (until: number) => void): () => void {
    this.fillers.add(fn)
    return () => {
      this.fillers.delete(fn)
    }
  }

  pending(): number {
    return this.queue.length
  }

  tick(): void {
    const now = this.driver.now()
    const until = now + this.lookahead
    for (const f of [...this.fillers]) f(until)
    while (this.queue.length && this.queue[0]!.time <= until) {
      const ev = this.queue.shift()!
      if (ev.time < now - this.lateTolerance) {
        this.lateEvents++
        continue
      }
      this.played++
      this.log?.push(ev.time)
      ev.play(Math.max(ev.time, now))
    }
  }
}

export type Quantise = 'now' | 'beat' | 'bar' | 'section'

export interface Transport {
  /** Audio-clock time of beat 0. */
  startTime: number
  /** Quarter-note BPM. */
  bpm: number
  beatsPerBar: number
}

export function beatToTime(t: Transport, beat: number): number {
  return t.startTime + (beat * 60) / t.bpm
}

/**
 * The beats of a transport in [from, to) with their index in the bar. Compound meters (6/8, 9/8, 12/8) count
 * dotted quarters. Pure: the crowd's clap-along (§9.4) and the tests read it.
 */
export function beatGrid(t: Transport, meter: readonly [number, number], from: number, to: number): { time: number; beat: number }[] {
  const compound = meter[1] === 8 && meter[0] % 3 === 0
  const step = compound ? 1.5 : 1
  const perBar = Math.max(1, Math.round(t.beatsPerBar / step))
  const out: { time: number; beat: number }[] = []
  let k = Math.max(0, Math.ceil(((from - t.startTime) * t.bpm) / 60 / step - 1e-9))
  for (let guard = 0; guard < 256; guard++, k++) {
    const time = beatToTime(t, k * step)
    if (time >= to) break
    if (time >= from) out.push({ time, beat: k % perBar })
  }
  return out
}

export function timeToBeat(t: Transport, time: number): number {
  return ((time - t.startTime) * t.bpm) / 60
}

/** The first beat (or bar) boundary strictly after `time`, as a beat number. */
export function nextBoundary(t: Transport, time: number, q: 'beat' | 'bar'): number {
  const beat = timeToBeat(t, time)
  if (q === 'beat') return Math.floor(beat + 1e-6) + 1
  const bar = Math.floor(beat / t.beatsPerBar + 1e-6) + 1
  return bar * t.beatsPerBar
}

/** The time a change lands at, given its quantisation. */
export function quantisedTime(t: Transport, now: number, q: Quantise, sectionEndBeat?: number): number {
  if (q === 'now') return now
  if (q === 'section') return sectionEndBeat !== undefined ? Math.max(now, beatToTime(t, sectionEndBeat)) : now
  return beatToTime(t, nextBoundary(t, now, q))
}
