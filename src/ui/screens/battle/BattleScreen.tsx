import { useEffect, useRef, useState } from 'preact/hooks'
import type { Side } from '../../../core/battle/types.ts'
import { dateOf, seasonOf } from '../../../core/calendar.ts'
import { fill } from '../../../data/text/format.ts'
import { AUTO_STYLE_LABELS, BAND_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { BATTLE } from '../../../data/tuning.ts'
import { AUTO_STYLES } from '../../../data/types.ts'
import { Arena, type ArenaFighter } from '../../battle/Arena.tsx'
import { Confirm, Segmented, Sheet, Toggle } from '../../components/Controls.tsx'
import { navigate } from '../../router.ts'
import { settings, updateSettings } from '../../store/appStore.ts'
import { assistText, dash, effects, finishAndLeave, forfeit, fx, leaveBattle, move, paused, pushOpponent, rematch, resultLine, setAutoStyle, setPaused, setSpeed, setup, skipToEnd, speed, tapTechnique, toggleAuto, view, type FighterView } from '../../store/battleStore.ts'
import { game } from '../../store/gameStore.ts'

const t = UI_TEXT.battle

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
  const lastTap = useRef(0)
  const mode = settings.value.transparency
  const showThinking = settings.value.showThinking ?? mode === 'lens'
  const autoStyle = settings.value.autoStyle
  const leftHanded = settings.value.leftHanded
  const g = game.value
  const season = g ? seasonOf(dateOf(g.week).month) : 'Spring'
  const weather = g?.weather ?? 'Sunny'

  useEffect(() => {
    if (!s) navigate('lab')
    return () => leaveBattle()
  }, [])

  if (!v || !s) return null
  const [a, b] = v.fighters
  const playerSide = s.aControl === 'player' && !a.auto
  const floats = effects.value
  const effectsNow = fx.value
  const has = (side: number, kind: string) => effectsNow.some((e) => e.side === side && e.kind === kind)
  const arenaFighters = v.fighters.map((f, i) => ({
    monster: i === 0 ? s.a : s.b,
    x: f.x,
    expression: f.hp === 0 ? 'sleepy' : v.outcome && v.outcome.winner === i ? 'happy' : f.hp * 4 < f.maxHp ? 'tired' : undefined,
    plan: f.plan,
    busy: !!f.busyTech,
    dawdling: f.dawdling,
    stunned: f.stunned,
    lunge: has(i, 'lunge'),
    hit: has(i, 'hit'),
    ko: f.hp === 0,
    win: !!v.outcome && v.outcome.winner === i,
  })) as [ArenaFighter, ArenaFighter]

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

      <Arena fighters={arenaFighters} floats={floats} showThinking={showThinking} ruler={{ band: v.band, gap: v.gap }} season={season} weather={weather} speed={speed.value} paused={paused.value} />

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
