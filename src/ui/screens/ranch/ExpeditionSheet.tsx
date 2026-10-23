import { canStartExpedition, sitesOpenAt, staminaFor } from '../../../core/expedition.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { EXPEDITION } from '../../../data/tuning.ts'
import { Sheet } from '../../components/Controls.tsx'
import { navigate } from '../../router.ts'
import { game, startExpeditionTrip } from '../../store/gameStore.ts'

const t = UI_TEXT.expedition.invite

/** §17: this month's invitation(s) with the letter's thresholds, and Set off (the week's action). */
export function ExpeditionSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const g = game.value
  if (!open || !g || !g.monster) return null
  const m = g.monster
  const sites = sitesOpenAt(g.week)
  return (
    <Sheet open title={t.title} onClose={onClose}>
      <p class="muted small">{t.hint}</p>
      {sites.map((site) => {
        const can = canStartExpedition(g, site.id)
        const whyKey = can.ok ? null : can.reason
        const why = whyKey ? fill((t.why as Record<string, string>)[whyKey] ?? whyKey, { name: m.name }) : null
        return (
          <section class="card" key={site.id}>
            <p class="field__label">{fill(t.open, { site: site.name })}</p>
            <p class="small">{site.blurb}</p>
            <p class="muted small">
              {fill(t.requirements, { g: site.gradeMin, n: site.fameMin })} · {fill(t.yours, { g: m.grade, n: m.fame })}
            </p>
            <p class="muted small">
              {fill(t.stamina, { n: staminaFor(m) })} · {fill(t.fourWeeks, { fatigue: EXPEDITION.after.fatigue, stress: EXPEDITION.after.stress })}
            </p>
            {why && <p class="notice">{fill(t.notYet, { why })}</p>}
            <button
              type="button"
              class="btn btn--primary"
              style={{ marginTop: 8 }}
              disabled={!can.ok}
              onClick={() => {
                onClose()
                if (startExpeditionTrip(site.id)) navigate('expedition')
              }}
            >
              {t.go}
            </button>
          </section>
        )
      })}
    </Sheet>
  )
}
