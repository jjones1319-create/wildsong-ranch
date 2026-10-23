import { useEffect, useRef, useState } from 'preact/hooks'
import { canPlayOddJob, gapMsAt, slideMsAt, turnipPay, turnipSequence, type Produce } from '../../../core/oddJobs.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { ODD_JOBS } from '../../../data/tuning.ts'
import { TopBar } from '../../components/Controls.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { finishOddJob, game, oddJobSeed } from '../../store/gameStore.ts'

const t = UI_TEXT.oddJobs
const SWIPE_PX = 40

type Phase = 'intro' | 'playing' | 'done'

/**
 * CONTENT §13 Turnip Sort: thirty seconds of produce sliding down the chute. Tap Basket or Rock pile, or swipe
 * the item left or right. Missed items score nothing; there is no fail state. The chute is dealt from a seed the
 * game's RNG hands out, and the pay is a free action once per in-game week.
 */
export function OddJobsScreen() {
  const g = game.value
  const [phase, setPhase] = useState<Phase>('intro')
  const [item, setItem] = useState<Produce | null>(null)
  const [correct, setCorrect] = useState(0)
  const [wrong, setWrong] = useState(0)
  const [timeLeft, setTimeLeft] = useState<number>(ODD_JOBS.seconds)
  const [pay, setPay] = useState(0)
  const [fillPct, setFillPct] = useState(1)
  const run = useRef<{ seq: Produce[]; index: number; start: number; timer: ReturnType<typeof setTimeout> | null; raf: number | null; shownAt: number; window: number; stop: boolean; correct: number; wrong: number } | null>(null)
  const swipe = useRef<{ x: number } | null>(null)

  useEffect(() => {
    if (!g) navigate('town')
    return () => stopRun()
  }, [g === null])

  if (!g) return null
  const can = canPlayOddJob(g)

  function stopRun(): void {
    const r = run.current
    if (!r) return
    r.stop = true
    if (r.timer) clearTimeout(r.timer)
    if (r.raf !== null) cancelAnimationFrame(r.raf)
    run.current = null
  }

  function elapsed(): number {
    return run.current ? performance.now() - run.current.start : 0
  }

  function finishRound(): void {
    const r = run.current
    if (!r) return
    stopRun()
    setItem(null)
    const paid = finishOddJob(r.correct, r.wrong)
    setPay(paid)
    setPhase('done')
  }

  function showNext(): void {
    const r = run.current
    if (!r || r.stop) return
    if (elapsed() >= ODD_JOBS.seconds * 1000 || r.index >= r.seq.length) {
      finishRound()
      return
    }
    const next = r.seq[r.index++]!
    r.shownAt = performance.now()
    r.window = slideMsAt(elapsed())
    setItem(next)
    setFillPct(1)
    r.timer = setTimeout(() => {
      // Missed: it slid past. Nothing lost.
      setItem(null)
      r.timer = setTimeout(showNext, gapMsAt(elapsed()))
    }, r.window)
  }

  function tick(): void {
    const r = run.current
    if (!r || r.stop) return
    const left = Math.max(0, ODD_JOBS.seconds - Math.floor(elapsed() / 1000))
    setTimeLeft(left)
    if (r.timer && r.window > 0) setFillPct(Math.max(0, 1 - (performance.now() - r.shownAt) / r.window))
    if (elapsed() >= ODD_JOBS.seconds * 1000) {
      finishRound()
      return
    }
    r.raf = requestAnimationFrame(tick)
  }

  function start(): void {
    if (!can.ok) return
    const seq = turnipSequence(oddJobSeed())
    run.current = { seq, index: 0, start: performance.now(), timer: null, raf: null, shownAt: 0, window: 0, stop: false, correct: 0, wrong: 0 }
    setCorrect(0)
    setWrong(0)
    setTimeLeft(ODD_JOBS.seconds)
    setPhase('playing')
    showNext()
    run.current.raf = requestAnimationFrame(tick)
  }

  function answer(side: 'left' | 'right'): void {
    const r = run.current
    if (!r || !item) return
    if (r.timer) clearTimeout(r.timer)
    const ok = (item === 'turnip' && side === 'left') || (item === 'rock' && side === 'right')
    if (ok) {
      r.correct += 1
      setCorrect(r.correct)
    } else {
      r.wrong += 1
      setWrong(r.wrong)
    }
    setItem(null)
    r.timer = setTimeout(showNext, gapMsAt(elapsed()))
  }

  const reduce = settings.value.reduceMotion

  return (
    <main class="screen">
      <TopBar title={t.turnipSort} />
      {phase === 'intro' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil} tone="muted">
            <p>{t.intro}</p>
          </SpeakerCard>
          {!can.ok && <p class="notice">{can.reason === 'played' ? t.played : t.noMonster}</p>}
          <p class="muted small center">{t.swipeHint}</p>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" disabled={!can.ok} onClick={start}>
              {t.start}
            </button>
          </div>
        </>
      )}
      {phase === 'playing' && (
        <>
          <div class="chute__score">
            <span>{fill(t.timeLeft, { n: timeLeft })}</span>
            <span>{fill(t.score, { c: correct, w: wrong })}</span>
          </div>
          <div
            class="chute"
            onPointerDown={(e) => {
              swipe.current = { x: e.clientX }
            }}
            onPointerUp={(e) => {
              const s = swipe.current
              swipe.current = null
              if (!s) return
              const dx = e.clientX - s.x
              if (dx <= -SWIPE_PX) answer('left')
              else if (dx >= SWIPE_PX) answer('right')
            }}
          >
            <div class="chute__item" aria-live="polite">
              {item === 'turnip' ? '🥕' : item === 'rock' ? '🪨' : '…'}
            </div>
            <div class="chute__name">{item === 'turnip' ? t.turnip : item === 'rock' ? t.rock : ' '}</div>
            <div class="chute__timer" aria-hidden="true">
              <span class="chute__timer-fill" style={{ transform: `scaleX(${item ? fillPct : 0})`, transition: reduce ? 'none' : undefined }} />
            </div>
            <div class="chute__buttons">
              <button type="button" class="btn btn--primary chute__btn" onClick={() => answer('left')}>
                {t.basket}
              </button>
              <button type="button" class="btn chute__btn" onClick={() => answer('right')}>
                {t.rocks}
              </button>
            </div>
          </div>
          <p class="muted small center">{fill(t.result, { n: gold(turnipPay(correct, wrong)) })}</p>
        </>
      )}
      {phase === 'done' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil}>
            <p>{fill(t.score, { c: correct, w: wrong })}</p>
            <p class="heading">{fill(t.result, { n: gold(pay) })}</p>
          </SpeakerCard>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" onClick={() => navigate('town')}>
              {t.done}
            </button>
          </div>
        </>
      )}
    </main>
  )
}
