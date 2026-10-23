import { useEffect } from 'preact/hooks'
import { dateOf } from '../../../core/calendar.ts'
import { bondCharmId, canEnterSite, chanceTier, isSiteOpen, journeyCost, journeyForecast, requirementScore, requirementValue, techniqueCandidates, techniqueChancePct } from '../../../core/journey.ts'
import { countOf } from '../../../core/items.ts'
import { JOURNEY_SITES } from '../../../data/journeys.ts'
import { fill } from '../../../data/text/format.ts'
import { STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { JOURNEY } from '../../../data/tuning.ts'
import { TopBar } from '../../components/Controls.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { game, menu, takeAction } from '../../store/gameStore.ts'

/** §11 the Mentor's Ledger: every site with its techniques, requirements, your score, the chance tier and the forecast. */
export function JourneyLedgerScreen() {
  const g = game.value
  const t = UI_TEXT.journey
  useEffect(() => {
    if (!g || !g.monster) navigate('ranch')
  }, [g === null])
  if (!g || !g.monster) return null
  const m = g.monster
  const month = dateOf(g.week).month
  const lens = settings.value.transparency === 'lens'
  const canAct = menu.value?.train ?? false
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.wren} tone="muted">
        <p>{t.hint}</p>
      </SpeakerCard>
      {JOURNEY_SITES.map((site) => {
        const open = isSiteOpen(site.id, month)
        const gate = canEnterSite(m, site.id)
        const cost = journeyCost(g.saleMonths, month)
        const charms = countOf(g.inventory, bondCharmId(site.id))
        const forecast = journeyForecast(m, site.id)
        const cands = techniqueCandidates(m, site.id)
        const can = open && gate.ok && g.money >= cost && canAct
        const done = g.journeysBySite[site.id]
        return (
          <section class="card" key={site.id}>
            <p class="field__label">
              {site.name} <span class="muted small">· {site.mentor}</span>
            </p>
            <p class="muted small">
              {fill(t.stat, { stat: STAT_NAMES[site.stat] })} · {site.family}
              {!open ? ` · ${t.closed}` : ''}
              {!gate.ok ? ` · ${fill(t.gate, { g: site.gradeMin ?? 'B' })}` : ''}
            </p>
            <p class="small">
              {t.forecast}: {forecast.map((p) => `${Math.round(p)}%`).join(' · ')}
            </p>
            <p class="muted small">{fill(t.bond, { n: done, next: Math.ceil((done + 1) / JOURNEY.bond.every) * JOURNEY.bond.every })}</p>
            {cands.length === 0 ? (
              <p class="muted small">{t.noTechniques}</p>
            ) : (
              cands.map((tech) => {
                const pct = techniqueChancePct(m, tech, false, charms)
                return (
                  <div class="item" key={tech.id}>
                    <span class="item__body">
                      <span class="item__name">{tech.name}</span>
                      <span class="item__meta">
                        {tech.family} · {tech.type} · {fill(t.requirement, { req: requirementValue(tech, charms), score: requirementScore(m, tech) })}
                      </span>
                    </span>
                    <span class="pill">{lens ? fill(t.pct, { n: pct }) : t.tiers[chanceTier(pct)]}</span>
                  </div>
                )
              })
            )}
            <button type="button" class="btn btn--primary" style={{ marginTop: 10 }} disabled={!can} onClick={() => can && (navigate('ranch'), takeAction({ kind: 'journey', site: site.id }))}>
              {g.money < cost ? t.poor : fill(t.start, { n: cost })}
              {g.saleMonths.includes(month) ? ` · ${t.sale}` : ''}
            </button>
          </section>
        )
      })}
      <p class="muted small center">{fill(t.cost, { n: gold(JOURNEY.cost) })}</p>
    </main>
  )
}
