import { PLANNER_MAX } from '../../../core/planner.ts'
import { DRILL_BY_ID, DRILLS } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { STAT_KEYS } from '../../../data/types.ts'
import type { PlannerLogEntry, PlannerStep } from '../../../core/state.ts'
import { wrenVars } from '../../../core/report.ts'
import { Sheet } from '../../components/Controls.tsx'
import { gold } from '../../components/RanchBits.tsx'
import { game, plannerAdd, plannerClear, plannerDismissSummary, plannerRemove, plannerRun, plannerView } from '../../store/gameStore.ts'

const t = UI_TEXT.planner

function stepName(step: PlannerStep): string {
  return step.kind === 'rest' ? t.rest : DRILL_BY_ID[step.drill].name
}

/** §3 the planner sheet: pick up to eight weeks of drills and rests, then run them. */
export function PlannerSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const g = game.value
  if (!g?.monster) return null
  const queue = g.planner.queue
  const full = queue.length >= PLANNER_MAX
  return (
    <Sheet open={open} title={t.title} onClose={onClose}>
      <p class="muted small">{fill(WREN.planner.plan, wrenVars(g.monster))}</p>
      <p class="field__label small">{fill(t.queueLabel, { n: queue.length, max: PLANNER_MAX })}</p>
      {queue.length === 0 ? (
        <p class="muted small">{t.empty}</p>
      ) : (
        <ol class="plan">
          {queue.map((step, i) => (
            <li key={i} class="plan__step">
              <span class="plan__no">{i + 1}</span>
              <span class="plan__name">{stepName(step)}</span>
              <button type="button" class="iconbtn iconbtn--small" aria-label={fill(t.remove, { n: i + 1 })} onClick={() => plannerRemove(i)}>
                ×
              </button>
            </li>
          ))}
        </ol>
      )}
      <p class="field__label small">{t.add}</p>
      <div class="chips chips--wrap" role="group" aria-label={t.add}>
        <button type="button" class="chip" disabled={full} onClick={() => plannerAdd({ kind: 'rest' })}>
          {t.rest}
        </button>
        {DRILLS.map((d) => {
          const locked = d.needsTrainingYard && !g.upgrades.trainingYard
          return (
            <button key={d.id} type="button" class="chip" disabled={full || locked} title={locked ? t.unavailable : undefined} onClick={() => plannerAdd({ kind: 'drill', drill: d.id })}>
              {d.name}
            </button>
          )
        })}
      </div>
      <div class="sheet__actions">
        <button
          type="button"
          class="btn btn--primary"
          disabled={queue.length === 0}
          onClick={() => {
            onClose()
            plannerRun()
          }}
        >
          {t.run}
        </button>
        <button type="button" class="btn btn--ghost" disabled={queue.length === 0} onClick={plannerClear}>
          {t.clear}
        </button>
      </div>
    </Sheet>
  )
}

function LogRow({ e }: { e: PlannerLogEntry }) {
  const gains = STAT_KEYS.filter((k) => (e.gains[k] ?? 0) !== 0).map((k) => `${STAT_NAMES[k]} ${e.gains[k]! > 0 ? '+' : ''}${e.gains[k]}`)
  const what = e.step.kind === 'rest' ? t.rested : `${DRILL_BY_ID[e.step.drill].name} · ${e.outcome ? t.outcome[e.outcome] : t.rested}`
  return (
    <li class="plan__log">
      <span>{fill(t.weekRow, { week: e.week + 1, what })}</span>
      {(gains.length > 0 || e.pay > 0) && (
        <span class="muted small">
          {gains.join(' · ')}
          {e.pay > 0 ? `${gains.length ? ' · ' : ''}+${gold(e.pay)}` : ''}
        </span>
      )}
    </li>
  )
}

/** After a run: every week played and why it stopped, with Keep going when steps remain. */
export function PlannerSummary() {
  const g = game.value
  const v = plannerView.value
  if (!g?.monster || v !== 'summary') return null
  const stop = g.planner.lastStop ?? 'empty'
  const more = g.planner.queue.length > 0 && stop !== 'ended' && stop !== 'noMonster'
  return (
    <div class="overlay" role="dialog" aria-label={t.summaryTitle}>
      <div class="overlay__inner">
        <h2 class="heading center">{t.summaryTitle}</h2>
        <section class="card card--muted">
          <p class="speaker">{UI_TEXT.wren}</p>
          <p>{fill(WREN.planner[stop], wrenVars(g.monster))}</p>
        </section>
        {g.planner.log.length === 0 ? (
          <p class="muted small center">{t.noWeeks}</p>
        ) : (
          <ul class="plan plan--log">
            {g.planner.log.map((e, i) => (
              <LogRow key={i} e={e} />
            ))}
          </ul>
        )}
        <div class="spacer" />
        {more && (
          <button
            type="button"
            class="btn btn--primary"
            onClick={() => {
              plannerDismissSummary()
              plannerRun()
            }}
          >
            {t.keepGoing} · {g.planner.queue.length}
          </button>
        )}
        <button type="button" class={`btn ${more ? '' : 'btn--primary'}`} onClick={plannerDismissSummary}>
          {t.done}
        </button>
      </div>
    </div>
  )
}
