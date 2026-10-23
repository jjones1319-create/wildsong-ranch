import { trialReward } from '../../../core/journey.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { JOURNEY_SITE_BY_ID } from '../../../data/journeys.ts'
import { TECHNIQUE_BY_ID } from '../../../data/techniques.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { Sheet } from '../../components/Controls.tsx'
import { game } from '../../store/gameStore.ts'
import { dismissTrialOutcome, settlePendingTechnique, startTrial, trialOutcome } from '../../store/tournamentStore.ts'

/** §11: the Trial waiting at the end of a Journey, its result, and the "make room" prompt for a technique earned with a full list. */
export function TrialCard() {
  const g = game.value
  const t = UI_TEXT.journey.trial
  const res = trialOutcome.value
  if (!g || !g.monster) return null
  const m = g.monster
  const pending = g.journey?.pendingTechnique ?? g.trial?.pendingTechnique ?? null

  if (pending) {
    return (
      <Sheet open title={UI_TEXT.songbook.makeRoom} onClose={() => undefined}>
        <p class="muted small">{fill(UI_TEXT.journey.makeRoom, { name: m.name, technique: TECHNIQUE_BY_ID[pending]?.name ?? pending })}</p>
        {m.techniques.map((slot) => (
          <div class="item" key={slot.id}>
            <span class="item__body">
              <span class="item__name">{TECHNIQUE_BY_ID[slot.id]?.name ?? slot.id}</span>
            </span>
            <button type="button" class="btn btn--small" onClick={() => settlePendingTechnique(slot.id)}>
              {UI_TEXT.songbook.forget}
            </button>
          </div>
        ))}
        <div class="sheet__actions">
          <button type="button" class="btn" onClick={() => settlePendingTechnique(null)}>
            {UI_TEXT.journey.letGo}
          </button>
        </div>
      </Sheet>
    )
  }

  if (res) {
    return (
      <Sheet open title={t.title} onClose={dismissTrialOutcome}>
        <section class="card card--muted">
          <p class="speaker">{UI_TEXT.wren}</p>
          <p>{fill(res.won ? WREN.trialWin : WREN.trialLoss, { name: m.name })}</p>
        </section>
        <p>{res.won ? fill(t.won, { n: res.reward }) : t.lost}</p>
        {res.drop && <p class="food__tag">{fill(t.drop, { item: ITEM_BY_ID[res.drop]?.name ?? res.drop })}</p>}
        {res.injuredWeeks > 0 && <p class="food__tag--bad">{fill(t.injured, { n: res.injuredWeeks })}</p>}
        <div class="sheet__actions">
          <button type="button" class="btn btn--primary" onClick={dismissTrialOutcome}>
            {t.continue}
          </button>
        </div>
      </Sheet>
    )
  }

  if (!g.trial) return null
  const site = JOURNEY_SITE_BY_ID[g.trial.site]
  return (
    <Sheet open title={t.title} onClose={() => undefined}>
      <p class="muted small">{fill(t.hint, { breed: BREED_BY_ID[site.trialBreeds[0]].name, n: trialReward(m) })}</p>
      <div class="sheet__actions">
        <button type="button" class="btn btn--primary" onClick={() => startTrial('manual')}>
          {t.fight}
        </button>
        <button type="button" class="btn" onClick={() => startTrial('auto')}>
          {fill(t.auto, { name: m.name })}
        </button>
        <button type="button" class="btn btn--ghost" onClick={() => startTrial('skip')}>
          {t.skip}
        </button>
      </div>
    </Sheet>
  )
}
