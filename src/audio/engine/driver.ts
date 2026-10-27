/**
 * SOUND_UPGRADE §4.4: the scheduler never reads timers itself; a driver feeds it. The realtime driver ticks
 * every 25 ms and reads the context clock; the offline driver suspends the OfflineAudioContext every 100 ms
 * of render time, ticks, then resumes, so the real engine renders faster than real time; the fake driver
 * drives the unit tests.
 */

export interface Driver {
  /** The audio clock, seconds. */
  now(): number
  start(tick: () => void): void
  stop(): void
}

export function realtimeDriver(ctx: BaseAudioContext, intervalMs = 25): Driver {
  let timer: ReturnType<typeof setInterval> | null = null
  return {
    now: () => ctx.currentTime,
    start(tick) {
      if (timer) clearInterval(timer)
      timer = setInterval(tick, intervalMs)
      tick()
    },
    stop() {
      if (timer) clearInterval(timer)
      timer = null
    },
  }
}

export interface OfflineDriver extends Driver {
  /** Renders the whole context, ticking at every step. */
  render(): Promise<AudioBuffer>
}

export function offlineDriver(ctx: OfflineAudioContext, stepSec = 0.1): OfflineDriver {
  let tick: (() => void) | null = null
  return {
    now: () => ctx.currentTime,
    start(fn) {
      tick = fn
    },
    stop() {
      tick = null
    },
    async render() {
      const total = ctx.length / ctx.sampleRate
      const quantum = 128 / ctx.sampleRate
      const promises: Promise<void>[] = []
      for (let t = stepSec; t < total - quantum; t += stepSec) {
        // Suspend times must land on render quanta; round down to one.
        const at = Math.floor(t / quantum) * quantum
        promises.push(
          ctx.suspend(at).then(() => {
            tick?.()
            void ctx.resume()
          }),
        )
      }
      tick?.()
      const buffer = await ctx.startRendering()
      await Promise.all(promises)
      return buffer
    },
  }
}

export interface FakeDriver extends Driver {
  /** Moves the clock forward and ticks once at the new time. */
  advance(seconds: number): void
  /** Moves the clock forward in `stepSec` slices, ticking at each. */
  run(seconds: number, stepSec?: number): void
}

export function fakeDriver(): FakeDriver {
  let t = 0
  let tick: (() => void) | null = null
  return {
    now: () => t,
    start(fn) {
      tick = fn
      tick()
    },
    stop() {
      tick = null
    },
    advance(seconds) {
      t += seconds
      tick?.()
    },
    run(seconds, stepSec = 0.025) {
      const end = t + seconds
      while (t + stepSec <= end + 1e-9) {
        t += stepSec
        tick?.()
      }
    },
  }
}
