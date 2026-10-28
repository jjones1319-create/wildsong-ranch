import { useEffect, useRef, useState } from 'preact/hooks'
import { binFor, gapMsAt, inOvertime, overtimeWindowMs, slideMsAt, turnipDealer, type Bin, type Produce, type TurnipDealer } from '../../../core/oddJobs.ts'
import { ODD_JOBS } from '../../../data/tuning.ts'

export type TurnipMode = 'idle' | 'clock' | 'overtimeIntro' | 'overtime' | 'done'
export type TurnipEnd = 'time' | 'missed' | 'mixups'

export interface TurnipView {
  mode: TurnipMode
  item: Produce | null
  /** Items sorted right (overtime included). */
  correct: number
  /** First-phase mix-ups (they cost pay). */
  wrong: number
  /** Overtime mix-ups (strikes; the second ends the job). */
  strikes: number
  timeLeft: number
  end: TurnipEnd | null
}

interface Run {
  dealer: TurnipDealer
  started: number
  mode: TurnipMode
  item: Produce | null
  shownAt: number
  window: number
  /** Overtime items dealt so far (the window shrinks with each). */
  dealt: number
  correct: number
  wrong: number
  strikes: number
  timeLeft: number
  timer: ReturnType<typeof setTimeout> | null
  raf: number | null
}

const IDLE: TurnipView = { mode: 'idle', item: null, correct: 0, wrong: 0, strikes: 0, timeLeft: ODD_JOBS.seconds, end: null }

/**
 * CONTENT §13 Turnip Sort's clock: the 30-second first phase, then (at 150G) the overtime intro and overtime,
 * which ends on a missed item or the second mix-up. The item stream and the ramps are core rules; this hook
 * owns the timers and the animation frame. The timer bar is written straight to `fillRef` each frame; the view
 * state changes only when something happens (and the seconds left once a second).
 */
export function useTurnipRun(onEnd: (correct: number, wrong: number, end: TurnipEnd) => void) {
  const [view, setView] = useState<TurnipView>(IDLE)
  const run = useRef<Run | null>(null)
  const fillRef = useRef<HTMLSpanElement>(null)
  const endRef = useRef(onEnd)
  endRef.current = onEnd

  function sync(r: Run, end: TurnipEnd | null = null): void {
    setView({ mode: r.mode, item: r.item, correct: r.correct, wrong: r.wrong, strikes: r.strikes, timeLeft: r.timeLeft, end })
  }

  function elapsed(r: Run): number {
    return performance.now() - r.started
  }

  function stop(r: Run): void {
    if (r.timer) clearTimeout(r.timer)
    if (r.raf !== null) cancelAnimationFrame(r.raf)
    r.timer = null
    r.raf = null
  }

  function finish(r: Run, end: TurnipEnd): void {
    stop(r)
    r.mode = 'done'
    r.item = null
    run.current = null
    sync(r, end)
    endRef.current(r.correct, r.wrong, end)
  }

  function showNext(): void {
    const r = run.current
    if (!r) return
    if (r.mode === 'clock' && elapsed(r) >= ODD_JOBS.seconds * 1000) {
      finish(r, 'time')
      return
    }
    const overtime = r.mode === 'overtime'
    r.item = r.dealer.next(overtime)
    r.window = overtime ? overtimeWindowMs(r.dealt++) : slideMsAt(elapsed(r))
    r.shownAt = performance.now()
    r.timer = setTimeout(slidPast, r.window)
    sync(r)
  }

  function nextAfterGap(r: Run): void {
    r.timer = setTimeout(showNext, r.mode === 'overtime' ? ODD_JOBS.overtime.gapMs : gapMsAt(elapsed(r)))
  }

  /** The item slid past: nothing lost in the first phase; in overtime it ends the job. */
  function slidPast(): void {
    const r = run.current
    if (!r) return
    if (r.mode === 'overtime') {
      finish(r, 'missed')
      return
    }
    r.item = null
    sync(r)
    nextAfterGap(r)
  }

  function beginOvertime(): void {
    const r = run.current
    if (!r || r.mode !== 'overtimeIntro') return
    if (r.timer) clearTimeout(r.timer)
    r.mode = 'overtime'
    showNext()
  }

  function frame(): void {
    const r = run.current
    if (!r) return
    const now = performance.now()
    const fill = fillRef.current
    if (fill) fill.style.transform = `scaleX(${r.item && r.window > 0 ? Math.max(0, 1 - (now - r.shownAt) / r.window) : 0})`
    if (r.mode === 'clock') {
      const left = Math.max(0, ODD_JOBS.seconds - Math.floor(elapsed(r) / 1000))
      if (left !== r.timeLeft) {
        r.timeLeft = left
        sync(r)
      }
      if (elapsed(r) >= ODD_JOBS.seconds * 1000) {
        finish(r, 'time')
        return
      }
    }
    r.raf = requestAnimationFrame(frame)
  }

  function start(seed: number): void {
    if (run.current) stop(run.current)
    const r: Run = { dealer: turnipDealer(seed), started: performance.now(), mode: 'clock', item: null, shownAt: 0, window: 0, dealt: 0, correct: 0, wrong: 0, strikes: 0, timeLeft: ODD_JOBS.seconds, timer: null, raf: null }
    run.current = r
    showNext()
    r.raf = requestAnimationFrame(frame)
  }

  /** Sorts the item on the chute into `bin`. Reads the item from the run, so a swipe and a tap can't both count. */
  function answer(bin: Bin): void {
    const r = run.current
    if (!r || !r.item || (r.mode !== 'clock' && r.mode !== 'overtime')) return
    if (r.timer) clearTimeout(r.timer)
    const right = binFor(r.item) === bin
    r.item = null
    if (right) r.correct += 1
    else if (r.mode === 'overtime') {
      r.strikes += 1
      if (r.strikes >= ODD_JOBS.overtime.strikes) {
        finish(r, 'mixups')
        return
      }
    } else r.wrong += 1
    if (r.mode === 'clock' && inOvertime(r.correct, r.wrong)) {
      r.mode = 'overtimeIntro'
      r.timer = setTimeout(beginOvertime, ODD_JOBS.overtime.introMs)
      sync(r)
      return
    }
    sync(r)
    nextAfterGap(r)
  }

  useEffect(() => {
    // In overtime a hidden page would let the item slide past unseen: pause it, and show it again in full on return.
    const onVisibility = (): void => {
      const r = run.current
      if (!r || r.mode !== 'overtime') return
      if (document.hidden) {
        if (r.timer) clearTimeout(r.timer)
        r.timer = null
        return
      }
      if (r.timer) return
      if (r.item) {
        r.shownAt = performance.now()
        r.timer = setTimeout(slidPast, r.window)
      } else nextAfterGap(r)
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      if (run.current) stop(run.current)
      run.current = null
    }
  }, [])

  return { view, start, answer, skipIntro: beginOvertime, fillRef, reset: () => setView(IDLE) }
}
