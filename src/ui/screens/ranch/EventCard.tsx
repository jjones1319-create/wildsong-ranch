import { say } from '../../../core/report.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { Sheet } from '../../components/Controls.tsx'
import { answerEvent, game } from '../../store/gameStore.ts'

/** CONTENT §11 the storm spark: yes uses the week (and brings Stormglass); no lets it go until the next storm. */
export function EventCard({ open }: { open: boolean }) {
  const g = game.value
  const t = UI_TEXT.event
  if (!open || !g || !g.monster || !g.pendingEvent) return null
  const m = g.monster
  return (
    <Sheet open title={t.stormTitle} onClose={() => undefined}>
      <section class="card card--muted">
        <p class="speaker">{UI_TEXT.wren}</p>
        <p>{say('stormSpark', WREN.stormSpark, m).text}</p>
      </section>
      <p class="muted small">{UI_TEXT.rumors['storm-chase'].heard}</p>
      <div class="sheet__actions">
        <button type="button" class="btn btn--primary" onClick={() => answerEvent(true)}>
          {t.chase}
        </button>
        <button type="button" class="btn" onClick={() => answerEvent(false)}>
          {t.ignore}
        </button>
      </div>
    </Sheet>
  )
}
