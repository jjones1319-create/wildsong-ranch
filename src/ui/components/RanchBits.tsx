import type { ComponentChildren } from 'preact'
import { useState } from 'preact/hooks'
import { fatigueLabel, loyaltyLabel, stressLabel } from '../../core/aging.ts'
import { dateOf, seasonOf } from '../../core/calendar.ts'
import { nextUp } from '../../core/calendarView.ts'
import { inDebt } from '../../core/economy.ts'
import { loyaltyOf, stageOf, strainOf, weeksLeft, type Monster } from '../../core/monster.ts'
import type { GameState } from '../../core/state.ts'
import { fill } from '../../data/text/format.ts'
import { MONTH_NAMES, SEASON_NAMES, STAGE_NAMES, WEATHER_GLYPHS, WEATHER_LABELS } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { RANGES, SHOP } from '../../data/tuning.ts'
import type { TransparencyMode } from '../../data/types.ts'
import { LifeBar } from '../screens/lab/LabEditor.tsx'
import { Sheet } from './Controls.tsx'

/** Small ranch-side building blocks shared by several screens. */

export function gold(n: number): string {
  return fill(UI_TEXT.gold, { n: n.toLocaleString() })
}

/** A line Wren (or Basil, or Ines) says. */
export function SpeakerCard({ speaker, children, tone }: { speaker: string; children: ComponentChildren; tone?: 'muted' | 'notice' }) {
  return (
    <section class={`card ${tone === 'muted' ? 'card--muted' : ''}`}>
      <p class="speaker">{speaker}</p>
      {children}
    </section>
  )
}

/** An onboarding tip with a "Got it" button. */
export function TipCard({ text, onDismiss }: { text: string; onDismiss: () => void }) {
  return (
    <section class="card tip">
      <p class="speaker">{UI_TEXT.wren}</p>
      <p>{text}</p>
      <button type="button" class="btn btn--small btn--primary" onClick={onDismiss}>
        {UI_TEXT.gotIt}
      </button>
    </section>
  )
}

/** Year, month, week, season, weather and the purse (§21 calendar strip). */
/** The "Next:" line under the date: the next notable cup the monster can enter, or a sooner ★ reminder. */
export function nextLine(state: GameState): string | null {
  const n = nextUp(state)
  if (!n) return null
  const c = UI_TEXT.calendar
  const when = n.inWeeks === 0 ? c.whenThisWeek : n.inWeeks === 1 ? c.whenNextWeek : fill(c.whenIn, { n: n.inWeeks })
  return fill(n.pinned ? c.nextPinned : c.next, { event: n.name, when })
}

export function CalendarStrip({ state, onSettings, onCalendar }: { state: GameState; onSettings?: () => void; onCalendar?: () => void }) {
  const t = UI_TEXT.ranch
  const d = dateOf(state.week)
  const season = seasonOf(d.month)
  const next = onCalendar ? nextLine(state) : null
  const body = (
    <>
      <span class="calstrip__year">{fill(t.year, { year: d.year })}</span>
      <span>{fill(t.date, { month: MONTH_NAMES[d.month - 1], week: d.week })}</span>
      <span class="muted small">
        {SEASON_NAMES[season]} · <span aria-hidden="true">{WEATHER_GLYPHS[state.weather]}</span> {WEATHER_LABELS[state.weather]}
      </span>
      {next && <span class="calstrip__next">{next}</span>}
    </>
  )
  return (
    <header class={`calstrip calstrip--${season.toLowerCase()}`}>
      {onCalendar ? (
        <button type="button" class="calstrip__date calstrip__date--button" onClick={onCalendar} aria-label={`${UI_TEXT.calendar.openCalendar}. ${fill(t.date, { month: MONTH_NAMES[d.month - 1], week: d.week })}${next ? `. ${next}` : ''}`}>
          {body}
        </button>
      ) : (
        <div class="calstrip__date">{body}</div>
      )}
      <div class="calstrip__right">
        <span class={`calstrip__money ${inDebt(state) ? 'calstrip__money--debt' : ''}`}>{gold(state.money)}</span>
        {onSettings && (
          <button type="button" class="iconbtn iconbtn--small" aria-label={UI_TEXT.menu.settings} onClick={onSettings}>
            ⚙
          </button>
        )}
      </div>
    </header>
  )
}

function Bar({ label, value, max, word, exact, tone }: { label: string; value: number; max: number; word: string; exact: boolean; tone: 'fatigue' | 'stress' | 'loyalty' }) {
  return (
    <div class={`bar bar--${tone}`}>
      <span class="bar__label">{label}</span>
      <span class="bar__track" role="img" aria-label={`${label}: ${word}`}>
        <span class="bar__fill" style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
      </span>
      <span class="bar__word">
        {word}
        {exact ? ` · ${value}` : ''}
      </span>
    </div>
  )
}

/** §6.8: condition bars by transparency mode. Classic shows the life bar only (Wren's words carry the rest). */
export function ConditionBars({ m, mode }: { m: Monster; mode: TransparencyMode }) {
  const t = UI_TEXT.ranch.bars
  const stage = stageOf(m)
  const exact = mode === 'lens'
  return (
    <div class="bars">
      {mode !== 'classic' && (
        <>
          <Bar label={t.fatigue} value={m.fatigue} max={RANGES.condition.max} word={fatigueLabel(m.fatigue)} exact={exact} tone="fatigue" />
          <Bar label={t.stress} value={m.stress} max={RANGES.condition.max} word={stressLabel(m.stress)} exact={exact} tone="stress" />
          <Bar label={t.loyalty} value={loyaltyOf(m)} max={RANGES.condition.max} word={loyaltyLabel(loyaltyOf(m))} exact={exact} tone="loyalty" />
        </>
      )}
      <div class="bar bar--life">
        <span class="bar__label">{t.life}</span>
        <span class="bar__track bar__track--life">
          <LifeBar m={m} />
        </span>
        <span class="bar__word">
          {STAGE_NAMES[stage - 1]}
          {exact ? ` · ${fill(UI_TEXT.ranch.lifeLeft, { n: weeksLeft(m) })} · ${fill(UI_TEXT.ranch.strain, { n: strainOf(m) })}` : ''}
        </span>
      </div>
    </div>
  )
}

/** ×1 / ×5 / ×10 / Max quantity picker (§8 use flow and the Shop's multi-buy). */
export function QuantitySheet({
  open,
  title,
  hint,
  max,
  unitLabel,
  confirmLabel,
  totalFor,
  onConfirm,
  onClose,
  children,
}: {
  open: boolean
  title: string
  hint?: ComponentChildren
  max: number
  unitLabel?: string
  confirmLabel: (n: number) => string
  totalFor?: (n: number) => string
  onConfirm: (n: number) => void
  onClose: () => void
  children?: ComponentChildren
}) {
  const [qty, setQty] = useState(1)
  const n = Math.max(0, Math.min(qty, max))
  const options = [...SHOP.quantities.filter((q) => q <= max), max].filter((q, i, a) => q > 0 && a.indexOf(q) === i)
  return (
    <Sheet open={open} title={title} onClose={onClose}>
      {hint && <p class="muted small">{hint}</p>}
      {children}
      <p class="field__label">{UI_TEXT.bag.howMany}</p>
      <div class="qty" role="group" aria-label={UI_TEXT.bag.howMany}>
        {options.map((q) => (
          <button key={q} type="button" class={`chip ${n === q ? 'chip--on' : ''}`} aria-pressed={n === q} onClick={() => setQty(q)}>
            {q === max && max > 1 && !SHOP.quantities.includes(max) ? fill(UI_TEXT.bag.max, { n: max }) : `×${q}`}
            {unitLabel && q !== max ? ` ${unitLabel}` : ''}
          </button>
        ))}
      </div>
      {totalFor && n > 0 && <p class="field__label">{totalFor(n)}</p>}
      <div class="sheet__actions">
        <button type="button" class="btn btn--primary" disabled={n < 1} onClick={() => onConfirm(n)}>
          {confirmLabel(n)}
        </button>
        <button type="button" class="btn" onClick={onClose}>
          {UI_TEXT.lab.actions.cancel}
        </button>
      </div>
    </Sheet>
  )
}
