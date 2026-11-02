import { useEffect, useRef, useState } from 'preact/hooks'
import { npcMonster } from '../../../core/npc.ts'
import { BATTLE3D_TEXT as T } from '../../../data/text/battle3d.ts'
import { fill } from '../../../data/text/format.ts'
import { BAND_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { BATTLE, INPUT } from '../../../data/tuning.ts'
import type { Duel3D, DuelCamera, DuelStats } from '../../../art3d/duel/duel3d.ts'
import { navigate } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import {
  dash,
  effects,
  leaveBattle,
  liveBattleState,
  moveStick,
  onBattleEvents,
  paused,
  pushOpponent,
  rematch,
  resultLine,
  setPaused,
  setSpeed,
  sidestep,
  skipToEnd,
  speed,
  startBattle,
  tapTechnique,
  toggleAuto,
  view,
  type FighterView,
} from '../../store/battleStore.ts'
import { currentTier, reduceMotionNow } from '../../store/fxStore.ts'
import { ThumbStick } from './ThumbStick.tsx'

const B = UI_TEXT.battle

/** The test's fighters: Puddlepup (the player) against Songheart Puddlepup (the CPU), docs/BATTLE_3D.md §8. */
function startDuel(): void {
  const a = npcMonster({ breed: 'puddlepup', total: 1600, seed: 31, name: 'Puddlepup' })
  const b = npcMonster({ breed: 'puddlepup', total: 1600, seed: 32, name: 'Songheart' })
  b.variantId = 'songheart-puddlepup'
  startBattle({ a, b, aControl: 'player', personalityA: 'Steady', personalityB: 'Steady', tierA: 'expert', tierB: 'skilled', timerSec: 60, origin: 'lab', mode: 'duel' })
  setPaused(true)
}

function Bars({ f, right }: { f: FighterView; right?: boolean }) {
  const hpPct = (f.hp / f.maxHp) * 100
  const cls = hpPct <= 20 ? 'hpbar__fill--crit' : hpPct <= 50 ? 'hpbar__fill--low' : ''
  return (
    <div class={`bhead__side ${right ? 'bhead__side--b' : ''}`}>
      <span class="bhead__name">{f.name}</span>
      <span class="hpbar" role="img" aria-label={`${B.hp} ${f.hp} / ${f.maxHp}`}>
        <span class={`hpbar__fill ${cls}`} style={{ width: `${hpPct}%` }} />
      </span>
      <span class="gutsbar" role="img" aria-label={`${B.guts} ${f.guts}`}>
        <span class="gutsbar__fill" style={{ width: `${(f.guts / BATTLE.guts.cap) * 100}%` }} />
      </span>
    </div>
  )
}

declare global {
  interface Window {
    /** For the review recordings (tools/art/battle3d-review.ts). */
    __battle3d?: { phase: string; setCamera(c: DuelCamera): void; skipIntro(): void; stats(): DuelStats | null; auto(on: boolean): void; speed(x: 1 | 2 | 4): void }
  }
}

export function Battle3DScreen() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const duel = useRef<Duel3D | null>(null)
  const [phase, setPhase] = useState<'loading' | 'intro' | 'fight' | 'error'>('loading')
  const [cam, setCam] = useState<DuelCamera>('side')
  const [stats, setStats] = useState<DuelStats | null>(null)
  const phaseRef = useRef(phase)
  phaseRef.current = phase
  // a tap on an in-range card while the monster is still busy fires as soon as it can (INPUT.tapBufferMs)
  const queued = useRef<{ id: string; until: number } | null>(null)

  useEffect(() => {
    startDuel()
    let alive = true
    let off: () => void = () => {}
    void (async () => {
      try {
        const m = await import('../../../art3d/duel/duel3d.ts')
        if (!alive || !canvas.current) return
        const d = await m.createDuel3D(
          { canvas: canvas.current, me: 0, variants: [null, 'songheart-puddlepup'], lite: currentTier() === 'lite', reduceMotion: reduceMotionNow(), speed: () => speed.value },
          liveBattleState,
        )
        if (!alive) {
          d.dispose()
          return
        }
        duel.current = d
        off = onBattleEvents((e) => d.onEvents(e))
        setPhase('intro')
        await d.playIntro()
        if (!alive) return
        setPhase('fight')
        setPaused(false)
      } catch (err) {
        console.error(err)
        if (alive) setPhase('error')
      }
    })()
    const timer = setInterval(() => duel.current && setStats(duel.current.stats()), 500)
    window.__battle3d = {
      get phase() {
        return phaseRef.current
      },
      setCamera(c) {
        duel.current?.setCamera(c)
        setCam(c)
      },
      skipIntro: () => duel.current?.skipIntro(),
      stats: () => duel.current?.stats() ?? null,
      auto(on) {
        if ((view.value?.fighters[0].auto ?? false) !== on) toggleAuto()
      },
      speed: (x) => setSpeed(x),
    }
    return () => {
      alive = false
      off()
      clearInterval(timer)
      duel.current?.dispose()
      duel.current = null
      delete window.__battle3d
      leaveBattle()
    }
  }, [])

  const v = view.value
  const a = v?.fighters[0]
  const b = v?.fighters[1]
  const playerSide = !!a && !a.auto && phase === 'fight' && !v?.outcome

  useEffect(() => {
    const q = queued.current
    if (!q) return
    const card = v?.fighters[0].techniques.find((t) => t.id === q.id)
    if (!card || performance.now() > q.until || v?.fighters[0].auto) queued.current = null
    else if (card.canFire) {
      queued.current = null
      tapTechnique(q.id)
    }
  }, [v])

  /** A card: fire now; in range but busy, fire as soon as it can; out of range, Assist walks there and fires. */
  const tapCard = (id: string) => {
    const now = view.value
    const card = now?.fighters[0].techniques.find((t) => t.id === id)
    if (!now || !card) return
    queued.current = null
    if (!card.canFire && card.affordable && card.range === now.band) queued.current = { id, until: performance.now() + INPUT.tapBufferMs }
    else tapTechnique(id)
  }
  /** The stick: letting go doesn't cancel a walk that Assist started for a tapped card. */
  const onStick = (dir: -1 | 0 | 1, side: -1 | 0 | 1) => {
    if (dir === 0 && side === 0 && view.value?.fighters[0].assistTech) return
    moveStick(dir, side)
  }
  const switchCam = () => {
    const next: DuelCamera = cam === 'side' ? 'behind' : 'side'
    duel.current?.setCamera(next)
    setCam(next)
  }

  return (
    <main class={`screen b3d ${settings.value.leftHanded ? 'b3d--left' : ''}`}>
      <canvas ref={canvas} class="b3d__canvas" aria-label={T.title} onClick={() => phase === 'intro' && duel.current?.skipIntro()} />

      {phase === 'loading' && <p class="b3d__note">{T.loading}</p>}
      {phase === 'error' && (
        <div class="b3d__note">
          <p>{T.noWebgl}</p>
          <button type="button" class="btn" onClick={() => navigate('lab')}>
            {T.leave}
          </button>
        </div>
      )}
      {phase === 'intro' && (
        <button type="button" class="b3d__skip" onClick={() => duel.current?.skipIntro()}>
          {T.tapToSkip}
        </button>
      )}

      {v && a && b && phase === 'fight' && (
        <>
          <header class="bhead b3d__head">
            <Bars f={a} />
            <span class="bhead__timer" aria-label={fill(B.seconds, { s: v.secondsLeft })}>
              {v.secondsLeft}
            </span>
            <Bars f={b} right />
          </header>

          <div class="b3d__top">
            <button type="button" class={`btn ${a.auto ? 'btn--on' : ''}`} onClick={toggleAuto}>
              {B.auto}
            </button>
            {([1, 2, 4] as const).map((x) => (
              <button key={x} type="button" class={`btn ${speed.value === x ? 'btn--on' : ''}`} onClick={() => setSpeed(x)}>
                {fill(B.speed, { n: x })}
              </button>
            ))}
            <button type="button" class="btn" aria-label={T.cameraLabel} onClick={switchCam}>
              {T.camera[cam]}
            </button>
            <button type="button" class="btn" onClick={skipToEnd} disabled={!!v.outcome}>
              {T.skip}
            </button>
            <button type="button" class={`btn ${paused.value ? 'btn--on' : ''}`} aria-label={paused.value ? B.resume : B.pause} onClick={() => setPaused(!paused.value)} disabled={!!v.outcome}>
              {paused.value ? '▶' : '⏸'}
            </button>
          </div>

          {effects.value.map((e) => {
            const p = duel.current?.project(e.side)
            return p ? (
              <span key={e.id} class={`b3d__float b3d__float--${e.tone}`} style={{ left: `${p.x}px`, top: `${p.y}px` }}>
                {e.text}
              </span>
            ) : null
          })}

          <p class="b3d__range" aria-live="polite">
            {T.range(BAND_LABELS[v.band as 1 | 2 | 3 | 4], (v.gap / 100).toFixed(1))}
          </p>
          <section class="tpanel b3d__tpanel" aria-label={B.title}>
            {[1, 2, 3, 4].map((band) => {
              const cards = a.techniques.filter((c) => c.range === band)
              return (
                <div key={band} class={`tcol ${v.band === band ? 'tcol--on' : ''}`}>
                  <span class="tcol__head">{BAND_LABELS[band as 1 | 2 | 3 | 4]}</span>
                  <div class="tcol__cards">
                    {cards.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        class={`tcard ${c.canFire && playerSide ? 'tcard--fire' : ''} ${!c.affordable || !playerSide ? 'tcard--dim' : ''} ${queued.current?.id === c.id ? 'tcard--queued' : ''} ${a.assistTech === c.id ? 'tcard--assist' : ''}`}
                        disabled={!playerSide}
                        onClick={() => tapCard(c.id)}
                      >
                        <span class="tcard__name">{c.name}</span>
                        <span class="tcard__meta">
                          <span>{fill(B.cost, { n: c.cost })}</span>
                          <span>{fill(B.hit, { pct: c.hitPct })}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
          </section>

          {playerSide && (
            <>
              <ThumbStick label={T.stickHint} basis={() => duel.current?.basisOnScreen() ?? null} onMove={onStick} onSidestep={sidestep} onDash={dash} />
              <button type="button" class="pad pad--push b3d__push" disabled={!v.touching} aria-label={v.touching ? T.push : T.pushHint} onClick={pushOpponent}>
                {T.push}
              </button>
            </>
          )}

          {v.outcome && (
            <div class="b3d__result" role="status">
              <p class="b3d__resultline">{resultLine.value}</p>
              <div class="b3d__resultbtns">
                <button
                  type="button"
                  class="btn"
                  onClick={() => {
                    rematch()
                    setPaused(false)
                  }}
                >
                  {T.rematch}
                </button>
                <button type="button" class="btn" onClick={() => navigate('lab')}>
                  {T.leave}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {stats && (
        <p class="b3d__stats" aria-hidden="true">
          {T.stats(stats.fps, stats.dpr, stats.backend, stats.level)}
          {stats.arena === 'stand-in' && <span> · {T.stand.arena}</span>}
          {stats.monster === 'art2' && <span> · {T.stand.monster}</span>}
          {settings.value.reduceMotion ? ` · ${T.reduceMotion}` : ''}
        </p>
      )}
    </main>
  )
}
