import { useEffect, useRef, useState } from 'preact/hooks'
import { playSfx, unlockAudio } from '../../../audio/player.ts'
import { canPlayDash, createDashHeat, dashPay, stepDash, type DashHeat, type DashResult } from '../../../core/meadowDash.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import type { BreedId } from '../../../data/types.ts'
import { DASH } from '../../../data/tuning.ts'
import { Toggle, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { hapticTick } from '../../lib/haptics.ts'
import { settings, updateSettings } from '../../store/appStore.ts'
import { finishMeadowDash, game, oddJobSeed } from '../../store/gameStore.ts'

const t = UI_TEXT.oddJobs
const TICK_MS = 1000 / DASH.ticksPerSecond
const RUNNER_PX = 44
/** One stride of the runners' bob, in track units (about half a metre). */
const STRIDE = 50_000
const COUNT_STEPS = ['3', '2', '1'] as const

type Phase = 'intro' | 'countdown' | 'running' | 'paused' | 'heatOver' | 'done'

interface Loop {
  heat: DashHeat
  raf: number | null
  /** The last frame's time (0 before the first). */
  last: number
  /** Time not yet run as ticks. */
  acc: number
  /** Taps since the last tick. */
  taps: number
  running: boolean
  /** Countdown time left (ms); "Go!" shows for `goLeft` after it. */
  countLeft: number
  goLeft: number
  label: string
}

/**
 * CONTENT §13 Meadow Dash: tap the Run pad and your monster races three rivals down the meadow. Win a heat to
 * run a faster one; the run ends at the first heat not won (or when you stop). The race itself is core rules
 * (`stepDash`, fixed 1/50 s ticks); this component runs the clock in one animation-frame loop (the countdown
 * too, so a hidden page freezes everything), queues the taps for the next tick, and draws the runners between
 * ticks by writing their transforms straight to the elements, so a frame never re-renders Preact.
 */
export function MeadowDash({ practice, onDone }: { practice: boolean; onDone: () => void }) {
  const g = game.value
  const [phase, setPhase] = useState<Phase>('intro')
  const [heatNo, setHeatNo] = useState(1)
  const [count, setCount] = useState('')
  const [won, setWon] = useState(0)
  const [winner, setWinner] = useState<number | null>(null)
  const [breeds, setBreeds] = useState<readonly BreedId[]>([])
  const [locked, setLocked] = useState(false)
  const [result, setResult] = useState<DashResult | null>(null)
  const loop = useRef<Loop | null>(null)
  const runners = useRef<(HTMLDivElement | null)[]>([])
  const pad = useRef<HTMLButtonElement>(null)
  const run = useRef({ seed: 0, won: 0, settled: true, lastInput: 0, lastHaptic: 0, pressTimer: 0 as ReturnType<typeof setTimeout> | 0, lockTimer: 0 as ReturnType<typeof setTimeout> | 0 })
  const relaxed = settings.value.oddJobsRelaxed
  const reduce = settings.value.reduceMotion

  useEffect(() => {
    const onVisibility = (): void => {
      const L = loop.current
      if (!document.hidden || !L || L.raf === null) return
      cancelAnimationFrame(L.raf)
      L.raf = null
      setPhase('paused')
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      const L = loop.current
      if (L?.raf != null) cancelAnimationFrame(L.raf)
      loop.current = null
      const r = run.current
      if (r.pressTimer) clearTimeout(r.pressTimer)
      if (r.lockTimer) clearTimeout(r.lockTimer)
      // Leaving mid-run still pays the heats already won.
      if (!r.settled && r.won > 0) {
        r.settled = true
        finishMeadowDash(r.won, practice)
      }
    }
  }, [])

  if (!g || !g.monster) return null
  const monster = g.monster
  const can = practice ? ({ ok: true } as const) : canPlayDash(g)

  function draw(alpha: number): void {
    const L = loop.current
    if (!L) return
    const { runners: rs, prev } = L.heat
    for (let i = 0; i < rs.length; i++) {
      const el = runners.current[i]
      if (!el) continue
      const pos = prev[i]! + (rs[i]!.pos - prev[i]!) * alpha
      const f = Math.min(1, pos / DASH.track)
      const bob = reduce || rs[i]!.v === 0 ? 0 : -Math.abs(Math.sin((pos / STRIDE) * Math.PI)) * 4
      el.style.transform = `translate(calc(${f.toFixed(4)} * (100cqi - ${RUNNER_PX}px)), ${bob.toFixed(1)}px)`
    }
  }

  function frame(now: number): void {
    const L = loop.current
    if (!L) return
    const dt = L.last ? Math.min(DASH.maxFrameMs, now - L.last) : 0
    L.last = now
    if (!L.running) {
      L.countLeft -= dt
      const step = Math.min(COUNT_STEPS.length - 1, Math.floor(((COUNT_STEPS.length * DASH.countdownStepMs - Math.max(0, L.countLeft)) / DASH.countdownStepMs)))
      if (L.countLeft <= 0) {
        L.running = true
        L.taps = 0
        L.acc = 0
        L.goLeft = DASH.goMs
        L.label = t.dashGo
        setCount(t.dashGo)
        setPhase('running')
        playSfx('dashGo')
      } else if (L.label !== COUNT_STEPS[step]) {
        L.label = COUNT_STEPS[step]!
        setCount(L.label)
        playSfx('timerTick')
      }
    } else {
      if (L.goLeft > 0) {
        L.goLeft -= dt
        if (L.goLeft <= 0) setCount('')
      }
      L.acc += dt
      let first = true
      while (L.acc >= TICK_MS && L.heat.winner === null) {
        L.heat = stepDash(L.heat, first ? L.taps : 0)
        if (first) L.taps = 0
        first = false
        L.acc -= TICK_MS
      }
      if (L.heat.winner !== null) {
        L.raf = null
        draw(1)
        heatOver(L.heat.winner)
        return
      }
    }
    draw(L.running ? L.acc / TICK_MS : 0)
    L.raf = requestAnimationFrame(frame)
  }

  function startLoop(L: Loop): void {
    L.last = 0
    L.running = false
    L.countLeft = COUNT_STEPS.length * DASH.countdownStepMs
    L.label = ''
    L.taps = 0
    setCount('')
    setPhase('countdown')
    L.raf = requestAnimationFrame(frame)
  }

  function startHeat(n: number): void {
    const heat = createDashHeat({ runSeed: run.current.seed, heat: n, spd: monster.stats.SPD, unlocked: g!.unlocked, ownBreed: monster.mainBreed, relaxed })
    const L: Loop = { heat, raf: null, last: 0, acc: 0, taps: 0, running: false, countLeft: 0, goLeft: 0, label: '' }
    loop.current = L
    setHeatNo(n)
    setBreeds(heat.breeds)
    setWinner(null)
    startLoop(L)
  }

  function lockButtons(): void {
    const r = run.current
    setLocked(true)
    if (r.lockTimer) clearTimeout(r.lockTimer)
    r.lockTimer = setTimeout(() => setLocked(false), DASH.resultLockMs)
  }

  function settle(): void {
    const r = run.current
    if (r.settled) return
    r.settled = true
    setResult(finishMeadowDash(r.won, practice))
  }

  function heatOver(lane: number): void {
    setWinner(lane)
    lockButtons()
    if (lane === 0) {
      const r = run.current
      r.won += 1
      setWon(r.won)
      playSfx('jackpotDouble')
      setPhase('heatOver')
      return
    }
    playSfx('jackpotFizzle')
    settle()
    setPhase('done')
  }

  function begin(): void {
    if (!can.ok) return
    void unlockAudio()
    const r = run.current
    r.seed = oddJobSeed()
    r.won = 0
    r.settled = false
    setWon(0)
    setResult(null)
    startHeat(1)
  }

  function stopHere(): void {
    settle()
    setPhase('done')
  }

  function resume(): void {
    const L = loop.current
    if (L) startLoop(L)
  }

  /** One stride: queued for the next tick while the race runs (taps during the countdown don't count). */
  function stride(): void {
    const r = run.current
    const now = performance.now()
    r.lastInput = now
    const L = loop.current
    if (!L || !L.running || L.heat.winner !== null) return
    L.taps += 1
    playSfx('dashStep')
    if (now - r.lastHaptic >= DASH.hapticEveryMs) {
      r.lastHaptic = now
      hapticTick(8)
    }
    // iOS doesn't reliably show :active on a fast tap, so the pad's press is a class.
    const el = pad.current
    if (el) {
      el.classList.add('dash__pad--down')
      if (r.pressTimer) clearTimeout(r.pressTimer)
      r.pressTimer = setTimeout(() => el.classList.remove('dash__pad--down'), 90)
    }
  }

  const rivalName = (b: BreedId | undefined): string => (b ? BREED_BY_ID[b].name : '')
  const racing = phase === 'countdown' || phase === 'running' || phase === 'paused' || phase === 'heatOver'
  const lanes: { name: string; breed?: BreedId }[] = [...breeds.map((b) => ({ name: rivalName(b), breed: b })), { name: fill(t.dashYou, { name: monster.name }) }]
  // The player runs in the bottom lane (next to the pad); the heat's lanes are 0 = player, 1–3 = rivals.
  const laneIndex = (row: number): number => (row === lanes.length - 1 ? 0 : row + 1)
  const payLine = practice ? t.practiceOnly : fill(t.result, { n: gold(dashPay(won)) })

  return (
    <main class="screen">
      <TopBar title={t.dash} />
      {phase === 'intro' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil} tone="muted">
            <p>{fill(t.dashIntro, { name: monster.name })}</p>
          </SpeakerCard>
          {practice && <p class="notice">{t.practiceOnly}</p>}
          {!can.ok && <p class="notice">{'reason' in can && can.reason === 'played' ? t.played : t.noMonster}</p>}
          <section class="card">
            <Toggle label={t.echoRelaxed} hint={t.dashRelaxedHint} checked={relaxed} onChange={(v) => void updateSettings({ oddJobsRelaxed: v })} />
            {g.dashBest > 0 && <p class="muted small">{g.dashBest === 1 ? t.bestHeat : fill(t.bestHeats, { n: g.dashBest })}</p>}
          </section>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" disabled={!can.ok} onClick={begin}>
              {t.dashStart}
            </button>
          </div>
        </>
      )}
      {racing && (
        <>
          <div class="chute__score">
            <span>{fill(t.dashHeat, { n: heatNo })}</span>
            <span>{payLine}</span>
          </div>
          <div class="dash" role="group" aria-label={fill(t.dashHeat, { n: heatNo })}>
            {lanes.map((lane, row) => (
              <div key={row} class={`dash__lane ${row === lanes.length - 1 ? 'dash__lane--you' : ''}`}>
                <span class="dash__name">{lane.name}</span>
                <div class="dash__strip">
                  <div
                    class="dash__runner"
                    ref={(el) => {
                      runners.current[laneIndex(row)] = el
                    }}
                  >
                    {lane.breed ? <MonsterPortrait breed={lane.breed} size={RUNNER_PX} animate={false} label={lane.name} /> : <MonsterPortrait monster={monster} size={RUNNER_PX} animate={false} expression={phase === 'heatOver' ? 'happy' : undefined} />}
                  </div>
                </div>
              </div>
            ))}
            {count && (
              <div class="dash__count" aria-live="assertive">
                {count}
              </div>
            )}
          </div>
          <p class="echo__status" role="status" aria-live="polite">
            {phase === 'heatOver' ? fill(t.dashWon, { n: heatNo, name: monster.name }) : phase === 'paused' ? t.dashPaused : t.dashRunHint}
          </p>
          {phase === 'heatOver' && <p class="muted small center">{fill(t.dashSoFar, { n: won, g: practice ? '—' : gold(dashPay(won)) })}</p>}
          <div class="dash__bar">
            {(phase === 'countdown' || phase === 'running') && (
              <button
                ref={pad}
                type="button"
                class="dash__pad"
                data-silent
                aria-label={t.dashRunLabel}
                onPointerDown={(e) => {
                  if (e.pointerType === 'mouse' && e.button !== 0) return
                  stride()
                }}
                onKeyDown={(e) => {
                  if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
                    e.preventDefault()
                    stride()
                  }
                }}
                onClick={() => {
                  // Screen readers and switch access send only a click; a real tap already counted on pointerdown.
                  if (performance.now() - run.current.lastInput > DASH.clickDedupeMs) stride()
                }}
              >
                {t.dashRun}
              </button>
            )}
            {phase === 'paused' && (
              <button type="button" class="btn btn--primary" onClick={resume}>
                {t.dashResume}
              </button>
            )}
            {phase === 'heatOver' && (
              <>
                <button type="button" class="btn btn--half" disabled={locked} onClick={stopHere}>
                  {t.dashStop}
                </button>
                <button type="button" class="btn btn--primary btn--half" disabled={locked} onClick={() => startHeat(heatNo + 1)}>
                  {t.dashNext}
                </button>
              </>
            )}
          </div>
        </>
      )}
      {phase === 'done' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil}>
            {winner !== null && winner !== 0 && <p>{fill(t.dashLost, { rival: rivalName(breeds[winner - 1]), n: heatNo })}</p>}
            <p>{fill(t.dashResult, { n: won })}</p>
            <p class="heading">{practice ? t.practiceResult : fill(t.result, { n: gold(result?.pay ?? 0) })}</p>
            {result?.newBest && <p>{t.newBest}</p>}
          </SpeakerCard>
          <div class="spacer" />
          <div class="actionbar">
            {practice && (
              <button type="button" class="btn btn--half" disabled={locked} onClick={() => setPhase('intro')}>
                {t.practice}
              </button>
            )}
            <button type="button" class={`btn btn--primary ${practice ? 'btn--half' : ''}`} disabled={locked} onClick={onDone}>
              {t.done}
            </button>
          </div>
        </>
      )}
    </main>
  )
}
