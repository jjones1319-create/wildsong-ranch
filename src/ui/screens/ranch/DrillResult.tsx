import { useEffect, useRef, useState } from 'preact/hooks'
import type { Expression } from '../../../art/monster/expressions.ts'
import { propSvg } from '../../../art/props.ts'
import { drillCue, nowSec } from '../../../audio/player.ts'
import { emoteForReaction } from '../../../core/emotes.ts'
import { Emote } from '../../components/Emote.tsx'
import { fatigueLabel, stressLabel } from '../../../core/aging.ts'
import { tipText } from '../../../core/onboarding.ts'
import { DRILL_BY_ID } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { OUTCOME_BANNERS, STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { UI } from '../../../data/tuning.ts'
import { STAT_KEYS } from '../../../data/types.ts'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { TipCard } from '../../components/RanchBits.tsx'
import { settings, speedFactor } from '../../store/appStore.ts'
import { closeResult, dismissTip, reactTo, tipFor, type ResultFlow } from '../../store/gameStore.ts'

function expressionFor(f: ResultFlow): { expression: Expression; mischief: boolean } {
  switch (f.drill.outcome) {
    case 'Great':
    case 'Success':
      return { expression: 'happy', mischief: false }
    case 'Cheat':
      return { expression: 'happy', mischief: true }
    case 'Fail':
      return { expression: 'sad', mischief: false }
    case 'Slacked':
      return { expression: 'sleepy', mischief: false }
  }
}

/** §21 drill result: a short, skippable vignette, the banner, stat deltas, then praise (swipe or tap), scold or skip. */
export function DrillResult({ f }: { f: ResultFlow }) {
  const t = UI_TEXT.result
  const factor = speedFactor()
  const [phase, setPhase] = useState<'vignette' | 'result'>(factor === 0 ? 'result' : 'vignette')
  const start = useRef<{ x: number; y: number } | null>(null)
  const resultAt = useRef<number | null>(null)
  const m = f.state.monster!
  const drill = DRILL_BY_ID[f.drill.drill]
  const mode = settings.value.transparency

  // Sound 2.0 §8.1: the drill cue takes over the music and says when the result should show (the audio
  // clock). Without audio, the vignette keeps its own timer, as before. The cue ends when the result closes.
  useEffect(() => {
    const at = drillCue.start(drill.id, f.drill.outcome, { vignetteMs: UI.vignetteMs * factor, instant: factor === 0 })
    resultAt.current = at
    return () => drillCue.end()
  }, [])

  useEffect(() => {
    if (phase !== 'vignette') return
    const at = resultAt.current
    const wait = at !== null ? Math.max(0, (at - nowSec()) * 1000) : UI.vignetteMs * factor
    const timer = setTimeout(() => setPhase('result'), wait)
    return () => clearTimeout(timer)
  }, [phase])

  useEffect(() => {
    if (phase === 'result' && resultAt.current !== null) drillCue.shown(resultAt.current)
  }, [phase])

  const skip = () => {
    drillCue.skip()
    setPhase('result')
  }

  const face = expressionFor(f)
  const deltas = STAT_KEYS.filter((k) => (f.drill.gains[k] ?? 0) !== 0).map((k) => ({ k, n: f.drill.gains[k]! }))
  const tip = phase === 'result' && !f.reaction ? tipFor({ screen: 'result' }) : null

  const onMove = (e: PointerEvent) => {
    if (f.reaction || !start.current) return
    const dist = Math.hypot(e.clientX - start.current.x, e.clientY - start.current.y)
    if (dist >= UI.petSwipePx) {
      start.current = null
      reactTo('praise')
    }
  }

  if (phase === 'vignette') {
    return (
      <div class="overlay" role="dialog" aria-label={drill.name}>
        <div class="overlay__inner vignette" onClick={skip}>
          <h2 class="heading">{drill.name}</h2>
          <div class="vignette__scene" data-vignette={drill.id}>
            <div class="vignette__mon">
              <MonsterPortrait monster={f.before} size={170} expression="neutral" />
            </div>
            <div class="vignette__prop" dangerouslySetInnerHTML={{ __html: propSvg(drill.id) }} />
          </div>
          <p class="vignette__text">{drill.vignette}</p>
          <div class="spacer" />
          <button type="button" class="btn" onClick={skip}>
            {t.skip}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div class="overlay" role="dialog" aria-label={OUTCOME_BANNERS[f.drill.outcome]}>
      <div class="overlay__inner">
        <h2 class={`banner banner--${f.drill.outcome}`}>{OUTCOME_BANNERS[f.drill.outcome]}</h2>
        <div
          class={`pet ${f.reaction ? 'pet--done' : ''}`}
          onPointerDown={(e) => {
            start.current = { x: e.clientX, y: e.clientY }
          }}
          onPointerMove={onMove}
          onPointerUp={() => {
            start.current = null
          }}
          onPointerCancel={() => {
            start.current = null
          }}
        >
          <MonsterPortrait monster={m} size={180} expression={face.expression} mischief={face.mischief} />
          {f.reaction && <Emote key={f.reaction} kind={emoteForReaction(f.reaction)} name={m.name} />}
          {!f.reaction && <p class="pet__hint">{fill(t.petHint, { name: m.name })}</p>}
        </div>
        <section class="card card--muted">
          <p class="speaker">{UI_TEXT.wren}</p>
          <p>{f.line.text}</p>
        </section>
        <div class="deltas">
          {deltas.length === 0 && <span class="muted">{t.noGains}</span>}
          {deltas.map(({ k, n }) => (
            <span key={k} class={`delta ${n > 0 ? 'delta--up' : 'delta--down'}`}>
              {STAT_NAMES[k]} {n > 0 ? `+${n}` : n}
            </span>
          ))}
          {f.drill.pay > 0 && <span class="delta">{fill(t.pay, { n: f.drill.pay })}</span>}
        </div>
        {mode !== 'classic' && (
          <p class="muted small center">
            {UI_TEXT.ranch.bars.fatigue}: {fatigueLabel(m.fatigue)}
            {mode === 'lens' ? ` (${m.fatigue})` : ''} · {UI_TEXT.ranch.bars.stress}: {stressLabel(m.stress)}
            {mode === 'lens' ? ` (${m.stress})` : ''}
          </p>
        )}
        {tip && <TipCard text={tipText(f.state, tip)} onDismiss={() => dismissTip(tip)} />}
        <div class="spacer" />
        {f.reaction ? (
          <>
            <p class="center">{f.reaction === 'praise' ? fill(t.praised, { name: m.name }) : f.reaction === 'scold' ? fill(t.scolded, { name: m.name }) : ''}</p>
            <button type="button" class="btn btn--primary" onClick={closeResult}>
              {t.continue}
            </button>
          </>
        ) : (
          <div class="reactions">
            <button type="button" class="btn btn--primary" onClick={() => reactTo('praise')}>
              ♥ {t.praise}
            </button>
            <button type="button" class="btn" onClick={() => reactTo('scold')}>
              👉 {t.scold}
            </button>
            <button type="button" class="btn btn--ghost" onClick={closeResult}>
              {t.nothing}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
