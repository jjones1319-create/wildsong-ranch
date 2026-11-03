import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { senseOfMonster, senseReasons } from '../../../core/battle/duelSense.ts'
import type { Monster } from '../../../core/monster.ts'
import { npcMonster } from '../../../core/npc.ts'
import { BATTLE3D_TEXT as T } from '../../../data/text/battle3d.ts'
import { fill } from '../../../data/text/format.ts'
import { BAND_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { ART, BATTLE, INPUT } from '../../../data/tuning.ts'
import type { ArenaId, Duel3D, DuelCamera, DuelStats } from '../../../art3d/duel/duel3d.ts'
import { navigate } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import {
  dash,
  effects,
  fire,
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
  toggleAuto,
  view,
  type FighterView,
} from '../../store/battleStore.ts'
import { currentTier, reduceMotionNow } from '../../store/fxStore.ts'
import { press } from './press.ts'
import { goSideways, isPortrait, leaveSideways } from './sideways.ts'
import { ThumbStick } from './ThumbStick.tsx'

const B = UI_TEXT.battle

/** §8 the test's arena: the Guild arena, or the Crown Amphitheatre for the big fights (the 🏟️ chip). */
const ARENAS: ArenaId[] = ['guild', 'crown']
let arenaChoice: ArenaId = typeof location !== 'undefined' && new URLSearchParams(location.search).get('arena') === 'crown' ? 'crown' : 'guild'

/**
 * §5 sideways: the card asks each battle that starts upright, because turning the screen needs full screen and that
 * needs a tap; "Stay upright" is remembered for the session (a save setting would need a save version).
 */
let uprightChosen = false

type Upbringing = keyof typeof ART.duel.testUpbringing
const UPBRINGINGS = Object.keys(ART.duel.testUpbringing) as Upbringing[]
let upbringing: Upbringing = 'seasoned'

/** The player's Puddlepup, raised the chosen way (§4.1: its battle sense on Auto comes from this). */
function playerMonster(): Monster {
  const m = npcMonster({ breed: 'puddlepup', total: 1600, seed: 31, name: 'Puddlepup' })
  const u = ART.duel.testUpbringing[upbringing]
  m.records.wins = Math.ceil(u.battles / 2)
  m.records.losses = Math.floor(u.battles / 2)
  m.spoil = u.spoil
  m.fear = u.fear
  return m
}

/** The test's fighters: Puddlepup (the player) against Songheart Puddlepup (the CPU), docs/BATTLE_3D.md §8. */
function startDuel(): void {
  const a = playerMonster()
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
    __battle3d?: { phase: string; setCamera(c: DuelCamera): void; skipIntro(): void; stats(): DuelStats | null; auto(on: boolean): void; speed(x: 1 | 2 | 4): void; playerFires(): number; arena(id: ArenaId): void; crowdFame(fame: number): Promise<void>; preview(tech: string, side: 0 | 1, outcome: 'hit' | 'miss'): number; pause(on: boolean): void; slowMo(k: number): void; clock(): number }
  }
}

export function Battle3DScreen() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const duel = useRef<Duel3D | null>(null)
  const [phase, setPhase] = useState<'loading' | 'intro' | 'fight' | 'error'>('loading')
  const [arenaId, setArenaId] = useState<ArenaId>(arenaChoice)
  const [cam, setCam] = useState<DuelCamera>('side')
  const [stats, setStats] = useState<DuelStats | null>(null)
  // the crowd's Fame (the test chip): how full the Guild arena's stands are
  const [fame, setFame] = useState<number>(ART.duel.crowd.defaultFame)
  const phaseRef = useRef(phase)
  phaseRef.current = phase
  // §5 sideways: follow the phone's turn; ask to turn when upright (not in automated runs); undo it on leaving
  const [portrait, setPortrait] = useState(isPortrait)
  const [askSideways, setAskSideways] = useState(!uprightChosen && !navigator.webdriver)
  const [turnHint, setTurnHint] = useState(false)
  useEffect(() => {
    const mq = matchMedia('(orientation: portrait)')
    const on = () => setPortrait(mq.matches)
    mq.addEventListener('change', on)
    return () => {
      mq.removeEventListener('change', on)
      leaveSideways()
    }
  }, [])
  const playSideways = async () => {
    setAskSideways(false)
    setTurnHint(!(await goSideways()))
  }
  const stayUpright = () => {
    uprightChosen = true
    setAskSideways(false)
  }
  // a tap on an in-range card while the monster is still busy fires as soon as it can (INPUT.tapBufferMs)
  const queued = useRef<{ id: string; until: number } | null>(null)

  useEffect(() => {
    setPhase('loading')
    startDuel()
    let alive = true
    let off: () => void = () => {}
    void (async () => {
      try {
        const m = await import('../../../art3d/duel/duel3d.ts')
        if (!alive || !canvas.current) return
        const d = await m.createDuel3D(
          { canvas: canvas.current, arena: arenaId, me: 0, variants: [null, 'songheart-puddlepup'], lite: currentTier() === 'lite', reduceMotion: reduceMotionNow(), leftHanded: settings.value.leftHanded, speed: () => speed.value, crowdFame: fame },
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
      arena: (id: ArenaId) => {
        arenaChoice = id
        setArenaId(id)
      },
      playerFires: () => liveBattleState()?.log.filter((e) => e.kind === 'fire' && e.side === 0).length ?? 0,
      // §7 review: any technique's effects, picture only (tools/art/attack-fx-review.ts)
      preview: (tech, side, outcome) => duel.current?.preview(tech, side, outcome) ?? 0,
      slowMo: (k) => duel.current?.setTimeScale(k),
      clock: () => duel.current?.clock() ?? 0,
      pause: (on) => setPaused(on),
      async crowdFame(n) {
        setFame(n)
        await duel.current?.setCrowdFame(n)
      },
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
  }, [arenaId])
  const cycleArena = () => {
    arenaChoice = ARENAS[(ARENAS.indexOf(arenaChoice) + 1) % ARENAS.length]!
    setArenaId(arenaChoice)
  }

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
      fire(q.id)
    }
  }, [v])

  /** A card: fire now; in range but busy, fire as soon as it can; out of range, Assist walks there and fires. */
  const tapCard = (id: string) => {
    const now = view.value
    const card = now?.fighters[0].techniques.find((t) => t.id === id)
    queued.current = null
    // the owner (Nov 2): out of range, a tap does nothing; you walk there yourself. No Assist walk in Battle 3D.
    if (!now || !card || !card.affordable || card.range !== now.band) return
    if (card.canFire) fire(id)
    else queued.current = { id, until: performance.now() + INPUT.tapBufferMs }
  }
  const switchCam = () => {
    const next: DuelCamera = cam === 'side' ? 'behind' : 'side'
    duel.current?.setCamera(next)
    setCam(next)
  }
  const [raised, setRaised] = useState<Upbringing>(upbringing)
  const sense = useMemo(() => senseOfMonster(playerMonster()), [raised])
  const cycleUpbringing = () => {
    upbringing = UPBRINGINGS[(UPBRINGINGS.indexOf(upbringing) + 1) % UPBRINGINGS.length]!
    setRaised(upbringing)
    startDuel()
    setPaused(false)
  }
  const cycleFame = () => {
    const steps = ART.duel.crowd.fameSteps
    const next = steps.find((s) => s > fame) ?? steps[0]
    setFame(next)
    void duel.current?.setCrowdFame(next)
  }

  return (
    <main class={`screen b3d ${settings.value.leftHanded ? 'b3d--left' : ''}`}>
      <canvas key={arenaId} ref={canvas} class="b3d__canvas" aria-label={T.title} onClick={() => phase === 'intro' && duel.current?.skipIntro()} />

      {phase === 'loading' && <p class="b3d__note">{T.loading}</p>}
      {phase === 'error' && (
        <div class="b3d__note">
          <p>{T.noWebgl}</p>
          <button type="button" class="btn" onClick={() => navigate('lab')}>
            {T.leave}
          </button>
        </div>
      )}
      {portrait && askSideways && (phase === 'intro' || phase === 'fight') && (
        <div class="b3d__sideways" role="dialog" aria-label={T.sideways.title}>
          <p class="b3d__resultline">📱↻ {T.sideways.title}</p>
          <p class="b3d__sidewaysbody">{T.sideways.body}</p>
          <div class="b3d__resultbtns">
            <button type="button" class="btn btn--primary" onClick={() => void playSideways()}>
              {T.sideways.play}
            </button>
            <button type="button" class="btn" onClick={stayUpright}>
              {T.sideways.stay}
            </button>
          </div>
        </div>
      )}
      {portrait && turnHint && <p class="b3d__turn">📱↻ {T.sideways.turn}</p>}
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
            <button type="button" class="btn b3d__arena" aria-label={T.arena.label(T.arena.names[arenaId])} onClick={cycleArena}>
              {T.arena.chip(T.arena.short[arenaId])}
            </button>
            <button
              type="button"
              class="btn b3d__sense"
              aria-label={T.upbringing.label(sense.sense, senseReasons(sense).map((r) => T.upbringing.why[r]).join(', '))}
              onClick={cycleUpbringing}
            >
              {T.upbringing.chip(T.upbringing.names[raised], sense.sense)}
            </button>
            {stats?.crowd && (
              <button type="button" class="btn b3d__fame" aria-label={T.crowdFameLabel(fame)} onClick={cycleFame}>
                {T.crowdFame(fame)}
              </button>
            )}
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
                        class={`tcard ${c.canFire && playerSide ? 'tcard--fire' : ''} ${!c.affordable || !playerSide ? 'tcard--dim' : ''} ${queued.current?.id === c.id ? 'tcard--queued' : ''}`}
                        disabled={!playerSide}
                        {...press(() => tapCard(c.id))}
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
              <ThumbStick label={T.stickHint} basis={() => duel.current?.basisOnScreen() ?? null} onMove={moveStick} onSidestep={sidestep} onDash={dash} />
              <button type="button" class="pad pad--push b3d__push" disabled={!v.touching} aria-label={v.touching ? T.push : T.pushHint} {...press(pushOpponent)}>
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
          {stats.crowd && T.crowdStats(stats.crowd.people, stats.crowd.cutouts, stats.crowd.cpuMs)}
        </p>
      )}
    </main>
  )
}
