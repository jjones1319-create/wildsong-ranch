import { useRef, useState } from 'preact/hooks'
import { canPlayOddJob, turnipPay, type Bin, type TurnipResult } from '../../../core/oddJobs.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { ODD_JOBS } from '../../../data/tuning.ts'
import { TopBar } from '../../components/Controls.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { settings } from '../../store/appStore.ts'
import { finishOddJob, game, oddJobSeed } from '../../store/gameStore.ts'
import { useTurnipRun, type TurnipEnd } from './useTurnipRun.ts'

const t = UI_TEXT.oddJobs
const SWIPE_PX = 40
const ITEM_ICON = { turnip: '🥕', rock: '🪨', weed: '🌿' } as const
const ITEM_NAME = { turnip: t.turnip, rock: t.rock, weed: t.weed } as const
const END_LINE: Record<TurnipEnd, string> = { time: t.endTime, missed: t.endMissed, mixups: t.endMixups }

/**
 * CONTENT §13 Turnip Sort: thirty seconds of produce sliding down the chute. Tap Basket or Rock pile, or swipe
 * the item left or right; missed items score nothing and there is no fail state. Reaching 150G banks it and
 * starts overtime: no clock, weeds join (Compost, or swipe down), each item comes a little faster, and a missed
 * item or the second mix-up ends the job. The chute is dealt from a seed the game's RNG hands out. A paid play is
 * once per in-game week, with no pay cap; Practice pays nothing but keeps the best.
 */
export function TurnipSort({ practice, onDone }: { practice: boolean; onDone: () => void }) {
  const g = game.value
  const [result, setResult] = useState<TurnipResult | null>(null)
  const { view, start, answer, skipIntro, fillRef, reset } = useTurnipRun((correct, wrong) => setResult(finishOddJob(correct, wrong, practice)))
  const swipe = useRef<{ x: number; y: number } | null>(null)

  if (!g) return null
  const can = practice ? ({ ok: true } as const) : canPlayOddJob(g)
  const playing = view.mode === 'clock' || view.mode === 'overtimeIntro' || view.mode === 'overtime'
  const overtime = view.mode === 'overtimeIntro' || view.mode === 'overtime'
  const reduce = settings.value.reduceMotion

  function begin(): void {
    if (!can.ok) return
    setResult(null)
    start(oddJobSeed())
  }

  function onSwipeEnd(x: number, y: number): void {
    const s = swipe.current
    swipe.current = null
    if (!s) return
    const dx = x - s.x
    const dy = y - s.y
    if (Math.max(Math.abs(dx), Math.abs(dy)) < SWIPE_PX) return
    let bin: Bin | null = null
    if (Math.abs(dx) >= Math.abs(dy)) bin = dx < 0 ? 'basket' : 'rocks'
    else if (dy > 0 && overtime) bin = 'compost'
    if (bin) answer(bin)
  }

  return (
    <main class="screen">
      <TopBar title={t.turnipSort} />
      {view.mode === 'idle' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil} tone="muted">
            <p>{t.intro}</p>
          </SpeakerCard>
          {practice && <p class="notice">{t.practiceOnly}</p>}
          {!can.ok && <p class="notice">{'reason' in can && can.reason === 'played' ? t.played : t.noMonster}</p>}
          {g.turnipBest > 0 && <p class="muted small center">{fill(t.bestSorted, { n: g.turnipBest })}</p>}
          <p class="muted small center">{t.swipeHint}</p>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" disabled={!can.ok} onClick={begin}>
              {t.start}
            </button>
          </div>
        </>
      )}
      {playing && (
        <>
          <div class="chute__score">
            <span>{overtime ? t.overtime : fill(t.timeLeft, { n: view.timeLeft })}</span>
            <span>{overtime ? fill(t.mixUpsLeft, { n: ODD_JOBS.overtime.strikes - view.strikes }) : fill(t.score, { c: view.correct, w: view.wrong })}</span>
          </div>
          <div
            class="chute"
            onPointerDown={(e) => {
              swipe.current = { x: e.clientX, y: e.clientY }
            }}
            onPointerUp={(e) => onSwipeEnd(e.clientX, e.clientY)}
            onPointerCancel={() => {
              swipe.current = null
            }}
          >
            {view.mode === 'overtimeIntro' ? (
              <div class="chute__intro" role="status">
                <p>{t.overtimeIntro}</p>
                <button type="button" class="btn btn--small" onClick={skipIntro}>
                  {t.overtimeSkip}
                </button>
              </div>
            ) : (
              <>
                <div class="chute__item" aria-live="polite">
                  {view.item ? ITEM_ICON[view.item] : '…'}
                </div>
                <div class="chute__name">{view.item ? ITEM_NAME[view.item] : ' '}</div>
              </>
            )}
            <div class="chute__timer" aria-hidden="true">
              <span ref={fillRef} class="chute__timer-fill" style={{ transform: 'scaleX(0)', transition: reduce ? 'none' : undefined }} />
            </div>
            <div class={`chute__buttons ${overtime ? 'chute__buttons--three' : ''}`}>
              <button type="button" class="btn btn--primary chute__btn" onClick={() => answer('basket')}>
                {t.basket}
              </button>
              {overtime && (
                <button type="button" class="btn chute__btn chute__btn--compost" onClick={() => answer('compost')}>
                  {t.compost}
                </button>
              )}
              <button type="button" class="btn chute__btn" onClick={() => answer('rocks')}>
                {overtime ? t.rocksShort : t.rocks}
              </button>
            </div>
          </div>
          <p class="muted small center">{overtime ? t.swipeOvertime : t.swipeHint}</p>
          <p class="muted small center">{practice ? t.practiceOnly : fill(t.result, { n: gold(turnipPay(view.correct, view.wrong)) })}</p>
        </>
      )}
      {view.mode === 'done' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil}>
            {view.end && <p>{END_LINE[view.end]}</p>}
            <p>{fill(t.score, { c: view.correct, w: view.wrong + view.strikes })}</p>
            <p class="heading">{practice ? t.practiceResult : fill(t.result, { n: gold(result?.pay ?? 0) })}</p>
            {result?.newBest && <p>{t.newBest}</p>}
          </SpeakerCard>
          <div class="spacer" />
          <div class="actionbar">
            {practice && (
              <button type="button" class="btn btn--half" onClick={reset}>
                {t.practice}
              </button>
            )}
            <button type="button" class={`btn btn--primary ${practice ? 'btn--half' : ''}`} onClick={onDone}>
              {t.done}
            </button>
          </div>
        </>
      )}
    </main>
  )
}
