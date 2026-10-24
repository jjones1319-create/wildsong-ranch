import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { sceneBackground } from '../../../art/backgrounds.ts'
import type { Side } from '../../../core/battle/types.ts'
import { dateOf, seasonOf } from '../../../core/calendar.ts'
import { fill } from '../../../data/text/format.ts'
import { AUTO_STYLE_LABELS, BAND_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { BATTLE, BATTLE_CAMERA } from '../../../data/tuning.ts'
import { AUTO_STYLES } from '../../../data/types.ts'
import { frameCamera, spriteScale, stepCamera, type Camera } from '../../battle/camera.ts'
import { Confirm, Segmented, Sheet, Toggle } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { navigate } from '../../router.ts'
import { settings, updateSettings } from '../../store/appStore.ts'
import { assistText, dash, effects, finishAndLeave, forfeit, fx, leaveBattle, move, pushOpponent, rematch, resultLine, setAutoStyle, setPaused, setSpeed, setup, shake, skipToEnd, speed, tapTechnique, toggleAuto, view, type FighterView } from '../../store/battleStore.ts'
import { game } from '../../store/gameStore.ts'
import { lite } from '../../store/perf.ts'

const t = UI_TEXT.battle
/** Height of a shot above the floor, in arena units (about the middle of the sprite box). */
const SHOT_HEIGHT = BATTLE_CAMERA.spriteHalf

/** The two fence posts that mark the walls (§12.11): an original rope fence, drawn in world units at basePx scale. */
function Wall({ side }: { side: -1 | 1 }) {
  return (
    <span class={`wall ${side === 1 ? 'wall--right' : ''}`} style={{ '--wx': side * BATTLE.arena.halfWidth }} aria-hidden="true">
      <svg viewBox="0 0 48 120" width="48" height="120">
        <path d="M24 112 C 34 104, 44 96, 48 84" fill="none" stroke="#b08a5a" stroke-width="3" stroke-linecap="round" />
        <path d="M24 70 C 34 64, 44 58, 48 48" fill="none" stroke="#b08a5a" stroke-width="3" stroke-linecap="round" />
        <rect x="18" y="14" width="12" height="104" rx="3" fill="#7a5436" />
        <rect x="20" y="16" width="4" height="100" rx="2" fill="#9a6f48" />
        <path d="M14 14 L24 4 L34 14 Z" fill="#5f3f29" />
        <circle cx="24" cy="70" r="3.5" fill="#d6b27a" />
        <circle cx="24" cy="112" r="3.5" fill="#d6b27a" />
      </svg>
    </span>
  )
}

/**
 * Runs the arena camera (M10): one requestAnimationFrame loop per battle, writing three CSS variables on
 * the world layer. No Preact render happens per frame; the fighters read the variables through calc().
 */
function useArenaCamera(arenaRef: { current: HTMLElement | null }, worldRef: { current: HTMLElement | null }, live: boolean): void {
  useEffect(() => {
    if (!live || typeof requestAnimationFrame !== 'function') return
    let raf = 0
    let last = 0
    let cam: Camera | null = null
    let written = ''
    const tick = (time: number) => {
      raf = 0
      const arena = arenaRef.current
      const world = worldRef.current
      const v = view.value
      if (!arena || !world || !v) return
      const dt = last ? Math.min(100, time - last) : 0
      last = time
      const target = frameCamera({ xA: v.fighters[0].x, xB: v.fighters[1].x, width: arena.clientWidth, height: arena.clientHeight })
      cam = stepCamera(cam, target, dt, settings.value.reduceMotion)
      const next = `${cam.centre.toFixed(2)}|${cam.pxPerUnit.toFixed(4)}`
      if (next !== written) {
        written = next
        world.style.setProperty('--cam-x', cam.centre.toFixed(2))
        world.style.setProperty('--cam-px', cam.pxPerUnit.toFixed(4))
        world.style.setProperty('--cam-s', spriteScale(cam).toFixed(4))
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => {
      if (raf) cancelAnimationFrame(raf)
    }
  }, [live])
}

function Bars({ f, side, mode }: { f: FighterView; side: Side; mode: string }) {
  const hpPct = (f.hp / f.maxHp) * 100
  const cls = hpPct <= 20 ? 'hpbar__fill--crit' : hpPct <= 50 ? 'hpbar__fill--low' : ''
  return (
    <div class={`bhead__side ${side === 1 ? 'bhead__side--b' : ''}`}>
      <span class="bhead__name">
        {f.name} {f.special && <span class="bhead__badge">{t.specials[f.special as keyof typeof t.specials] ?? f.special}</span>}
      </span>
      <span class="hpbar" role="img" aria-label={`${t.hp} ${f.hp} / ${f.maxHp}`}>
        <span class={`hpbar__fill ${cls}`} style={{ width: `${hpPct}%` }} />
      </span>
      <span class="gutsbar" role="img" aria-label={`${t.guts} ${f.guts}`}>
        <span class="gutsbar__fill" style={{ width: `${(f.guts / BATTLE.guts.cap) * 100}%` }} />
      </span>
      <span class="bhead__nums">
        <span>{mode === 'lens' ? `${t.hp} ${f.hp}` : `${Math.round(hpPct)}%`}</span>
        <span>{mode === 'lens' ? `${t.guts} ${f.guts}` : ''}</span>
      </span>
    </div>
  )
}

/** §12.11: the battle screen. Everything interactive sits in the bottom 45 %. */
export function BattleScreen() {
  const v = view.value
  const s = setup.value
  const [pauseOpen, setPauseOpen] = useState(false)
  const [confirmForfeit, setConfirmForfeit] = useState(false)
  const [shaking, setShaking] = useState(false)
  const lastTap = useRef(0)
  const arenaRef = useRef<HTMLElement>(null)
  const worldRef = useRef<HTMLDivElement>(null)
  const mode = settings.value.transparency
  const showThinking = settings.value.showThinking ?? mode === 'lens'
  const autoStyle = settings.value.autoStyle
  const leftHanded = settings.value.leftHanded
  const g = game.value
  const season = g ? seasonOf(dateOf(g.week).month) : 'Spring'
  const weather = g?.weather ?? 'Sunny'
  const liteMode = lite.value
  const backdrop = useMemo(() => sceneBackground({ scene: 'arena', season, weather, lite: liteMode, seed: 3 }), [season, weather, liteMode])

  useEffect(() => {
    if (!s) navigate('lab')
    return () => leaveBattle()
  }, [])

  useEffect(() => {
    if (!shake.value || settings.value.reduceMotion) return
    setShaking(true)
    const timer = setTimeout(() => setShaking(false), 170)
    return () => clearTimeout(timer)
  }, [shake.value])

  useArenaCamera(arenaRef, worldRef, !!(v && s))

  if (!v || !s) return null
  const [a, b] = v.fighters
  const playerSide = s.aControl === 'player' && !a.auto
  const floats = effects.value
  const effectsNow = fx.value
  const bandAt = (gap: number) => Math.min(100, (Math.max(0, gap) / BATTLE.bandEnds[3]!) * 100)
  const has = (side: number, kind: string) => effectsNow.some((e) => e.side === side && e.kind === kind)

  const onPadDown = (dir: -1 | 1) => (e: PointerEvent) => {
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
    if (dir === 1) {
      const now = Date.now()
      if (now - lastTap.current < 320) dash()
      lastTap.current = now
    }
    move(dir)
  }
  const onPadUp = () => move(0)

  const outcomeHow = v.outcome ? (v.outcome.how === 'ko' ? t.result.ko : v.outcome.how === 'time' ? t.result.time : t.result.forfeit) : ''
  const wrenLine = v.outcome
    ? v.outcome.winner === null
      ? fill(WREN.battleDraw, { name: a.name })
      : v.outcome.winner === 0
        ? fill(WREN.battleWin, { name: a.name })
        : fill(WREN.battleLoss, { name: a.name })
    : ''

  return (
    <main class={`screen battle ${leftHanded ? 'battle--left' : ''}`}>
      <header class="bhead">
        <Bars f={a} side={0} mode={mode} />
        <span class="bhead__timer" aria-label={fill(t.seconds, { s: v.secondsLeft })}>
          {v.secondsLeft}
        </span>
        <Bars f={b} side={1} mode={mode} />
      </header>

      <section ref={arenaRef} class={`arena ${shaking ? 'arena--shake' : ''}`} aria-label={t.title}>
        <div class="arena__bg" dangerouslySetInnerHTML={{ __html: backdrop }} />
        <div class="arena__floor" />
        <div ref={worldRef} class="arena__world">
          <Wall side={-1} />
          <Wall side={1} />
          {effectsNow
            .filter((e) => e.kind === 'shot' && e.fromX !== undefined && e.toX !== undefined)
            .map((e) => (
              <span key={e.id} class={`shot ${e.side === 1 ? 'shot--b' : ''}`} style={{ '--wx': e.fromX!, '--wy': SHOT_HEIGHT, '--dx': `calc(${e.toX! - e.fromX!} * var(--cam-px) * 1px)` }} />
            ))}
          {v.fighters.map((f, i) => (
            <div
              key={i}
              class={`fighter ${i === 1 ? 'fighter--b' : ''} ${f.busyTech ? 'fighter--busy' : ''} ${f.dawdling ? 'fighter--dawdle' : ''} ${f.stunned ? 'fighter--stun' : ''} ${has(i, 'lunge') ? 'fighter--lunge' : ''} ${has(i, 'hit') ? 'fighter--hit' : ''} ${f.hp === 0 ? 'fighter--ko' : ''} ${v.outcome && v.outcome.winner === i ? 'fighter--win' : ''}`}
              style={{ '--wx': f.x }}
            >
              {showThinking && f.plan && (
                <span class="fighter__plan" role="img" aria-label={t.thinking[f.plan].label}>
                  {t.thinking[f.plan].icon}
                </span>
              )}
              <div class="fighter__art">
                <MonsterPortrait monster={i === 0 ? s.a : s.b} size={BATTLE_CAMERA.basePx} mirror={i === 1} expression={f.hp === 0 ? 'sleepy' : v.outcome && v.outcome.winner === i ? 'happy' : f.hp * 4 < f.maxHp ? 'tired' : undefined} />
                {has(i, 'hit') && <span class="fighter__flash" aria-hidden="true" />}
                {has(i, 'crit') && (
                  <span class="fighter__sparkle" aria-hidden="true">
                    <i>✦</i>
                    <i>✦</i>
                    <i>✦</i>
                    <i>✦</i>
                    <i>✦</i>
                  </span>
                )}
              </div>
              {floats
                .filter((e) => e.side === i)
                .map((e, k) => (
                  <span key={e.id} class={`fighter__float float--${e.tone}`} style={{ '--stack': k }}>
                    {e.text}
                  </span>
                ))}
            </div>
          ))}
        </div>
        <div class="ruler" role="img" aria-label={BAND_LABELS[v.band as 1 | 2 | 3 | 4 | 5]}>
          {[1, 2, 3, 4].map((band) => (
            <span key={band} class={`ruler__band ruler__band--${band} ${v.band === band ? 'ruler__band--on' : ''}`}>
              {BAND_LABELS[band as 1 | 2 | 3 | 4]}
            </span>
          ))}
          <span class="ruler__marker" style={{ left: `${bandAt(v.gap)}%` }} />
        </div>
      </section>

      <div class="bctrl">
        {s.aControl === 'player' && (
          <button type="button" class={`btn ${a.auto ? 'btn--on' : ''}`} onClick={toggleAuto}>
            {t.auto}
          </button>
        )}
        {([1, 2, 4] as const).map((x) => (
          <button key={x} type="button" class={`btn ${speed.value === x ? 'btn--on' : ''}`} onClick={() => setSpeed(x)}>
            {fill(t.speed, { n: x })}
          </button>
        ))}
        <button
          type="button"
          class="btn"
          onClick={() => {
            setPaused(true)
            setPauseOpen(true)
          }}
        >
          ⏸
        </button>
      </div>

      <section class="tpanel" aria-label={t.title}>
        {[1, 2, 3, 4].map((band) => {
          const cards = a.techniques.filter((c) => c.range === band)
          return (
            <div key={band} class={`tcol ${v.band === band ? 'tcol--on' : ''}`}>
              <span class="tcol__head">{BAND_LABELS[band as 1 | 2 | 3 | 4]}</span>
              <div class="tcol__cards">
                {cards.length === 0 && <span class="tcol__empty">{t.noTech}</span>}
                {cards.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    class={`tcard ${c.canFire && playerSide ? 'tcard--fire' : ''} ${!c.affordable || !playerSide ? 'tcard--dim' : ''} ${a.assistTech === c.id ? 'tcard--assist' : ''}`}
                    disabled={!playerSide}
                    onClick={() => tapTechnique(c.id)}
                  >
                    <span class="tcard__name">{c.name}</span>
                    <span class="tcard__meta">
                      <span>{fill(t.cost, { n: c.cost })}</span>
                      <span>{fill(t.hit, { pct: c.hitPct })}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </section>

      {playerSide ? (
        <>
          {assistText() && <p class="assistline">{assistText()}</p>}
          <div class="pads">
            <button type="button" class="pad" aria-label={t.padBack} onPointerDown={onPadDown(-1)} onPointerUp={onPadUp} onPointerCancel={onPadUp} onContextMenu={(e) => e.preventDefault()}>
              ◀
            </button>
            <button type="button" class="pad pad--push" disabled={!v.touching} onClick={pushOpponent}>
              {t.push}
            </button>
            <button type="button" class="pad" aria-label={`${t.padForward}. ${t.padForwardHint}`} onPointerDown={onPadDown(1)} onPointerUp={onPadUp} onPointerCancel={onPadUp} onContextMenu={(e) => e.preventDefault()}>
              ▶
            </button>
          </div>
        </>
      ) : (
        <p class="muted small center">{s.aControl === 'player' ? t.autoOn : t.cpuSide}</p>
      )}

      <Sheet
        open={pauseOpen}
        title={t.pause}
        onClose={() => {
          setPauseOpen(false)
          setPaused(false)
        }}
      >
        <Toggle label={UI_TEXT.settings.assist} hint={UI_TEXT.settings.assistHint} checked={settings.value.assist} onChange={(on) => void updateSettings({ assist: on })} />
        <p class="field__label small">{UI_TEXT.settings.autoStyle}</p>
        <Segmented options={AUTO_STYLES.map((m) => ({ value: m, label: AUTO_STYLE_LABELS[m].name }))} value={autoStyle} onChange={setAutoStyle} label={UI_TEXT.settings.autoStyle} />
        <p class="field__hint">{AUTO_STYLE_LABELS[autoStyle].blurb}</p>
        <Toggle label={UI_TEXT.settings.showThinking} hint={UI_TEXT.settings.showThinkingHint} checked={showThinking} onChange={(on) => void updateSettings({ showThinking: on })} />
        <div class="sheet__actions">
          <button
            type="button"
            class="btn btn--primary"
            onClick={() => {
              setPauseOpen(false)
              setPaused(false)
            }}
          >
            {t.resume}
          </button>
          <button
            type="button"
            class="btn"
            onClick={() => {
              setPauseOpen(false)
              skipToEnd()
            }}
          >
            {t.skip}
          </button>
          <button
            type="button"
            class="btn btn--ghost"
            onClick={() => {
              setPauseOpen(false)
              setConfirmForfeit(true)
            }}
          >
            {t.forfeit}
          </button>
        </div>
      </Sheet>
      <Confirm
        open={confirmForfeit}
        text={t.forfeitAsk}
        confirmLabel={t.forfeit}
        danger
        onConfirm={() => {
          setConfirmForfeit(false)
          forfeit()
        }}
        onCancel={() => {
          setConfirmForfeit(false)
          setPaused(false)
        }}
      />

      {v.outcome && (
        <div class="bresult" role="dialog" aria-label={resultLine.value}>
          <div class="bresult__card">
            <h2 class="bresult__title">{resultLine.value}</h2>
            <p class="bresult__how">{outcomeHow}</p>
            <section class="card card--muted">
              <p class="speaker">{UI_TEXT.wren}</p>
              <p>{wrenLine}</p>
            </section>
            <table class="bresult__table">
              <thead>
                <tr>
                  <th />
                  <th>{a.name}</th>
                  <th>{b.name}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{t.result.hpLeft}</td>
                  <td>{(v.outcome.hpPct[0] / 10).toFixed(1)}%</td>
                  <td>{(v.outcome.hpPct[1] / 10).toFixed(1)}%</td>
                </tr>
                <tr>
                  <td>{t.result.attacks}</td>
                  <td>{a.attacks}</td>
                  <td>{b.attacks}</td>
                </tr>
                <tr>
                  <td>{t.result.hits}</td>
                  <td>{a.hits}</td>
                  <td>{b.hits}</td>
                </tr>
                <tr>
                  <td>{t.result.damage}</td>
                  <td>{a.damage}</td>
                  <td>{b.damage}</td>
                </tr>
              </tbody>
            </table>
            {!s.onFinished && <p class="muted small center">{t.result.exhibition}</p>}
            <div class="row">
              {!s.onFinished && (
                <button type="button" class="btn btn--half" onClick={rematch}>
                  {t.result.rematch}
                </button>
              )}
              <button type="button" class="btn btn--primary btn--half" onClick={() => finishAndLeave(navigate)}>
                {s.onFinished ? t.result.continue : t.result.done}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
