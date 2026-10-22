import { useState } from 'preact/hooks'
import { starsFor } from '../../../core/monster.ts'
import { drillOdds } from '../../../core/odds.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { DRILLS } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { ODDS_WORDS, STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { DRILL } from '../../../data/tuning.ts'
import type { Drill } from '../../../data/types.ts'
import { Segmented, Sheet } from '../../components/Controls.tsx'
import { settings } from '../../store/appStore.ts'
import { closeTrain, game, takeAction } from '../../store/gameStore.ts'

/** §6.1 and §21: Light and Heavy drills with stat arrows, stars, tags and odds by transparency mode. */
export function TrainSheet({ open }: { open: boolean }) {
  const g = game.value
  const t = UI_TEXT.train
  const [tab, setTab] = useState<'light' | 'heavy'>('light')
  if (!open || !g || !g.monster) return null
  const m = g.monster
  const mode = settings.value.transparency
  const bonusDrill = BREED_BY_ID[m.mainBreed].bonusDrill
  const drills = DRILLS.filter((d) => d.kind === tab)
  const costs = tab === 'light' ? DRILL.light : DRILL.heavy

  const pick = (d: Drill) => {
    closeTrain()
    takeAction({ kind: 'drill', drill: d.id })
  }

  return (
    <Sheet open title={t.title} onClose={closeTrain}>
      <Segmented
        options={[
          { value: 'light', label: t.tabs.light },
          { value: 'heavy', label: t.tabs.heavy },
        ]}
        value={tab}
        onChange={setTab}
        label={t.title}
      />
      <p class="muted small">{tab === 'light' ? t.lightHint : t.heavyHint}</p>
      <div class="list">
        {drills.map((d) => {
          const locked = d.needsTrainingYard && !g.upgrades.trainingYard
          const stars = starsFor(m.stats[d.main])
          const odds = drillOdds(m, d.id, { trainingYard: g.upgrades.trainingYard })
          const pay = costs.pay
          return (
            <button key={d.id} type="button" class={`drill ${locked ? 'drill--locked' : ''}`} disabled={locked} onClick={() => pick(d)}>
              <span class="drill__head">
                <span class="drill__name">{d.name}</span>
                <span class="drill__stars" aria-label={`${t.stars} ${stars}`}>
                  {'★'.repeat(stars)}
                  <span class="muted">{'★'.repeat(3 - stars)}</span>
                </span>
              </span>
              <span class="muted small">{d.vignette}</span>
              <span class="drill__meta">
                <span class="drill__tag drill__tag--up">
                  {STAT_NAMES[d.main]} ▲{d.kind === 'heavy' ? '▲' : ''}
                </span>
                {d.secondary && <span class="drill__tag drill__tag--up">{STAT_NAMES[d.secondary]} ▲</span>}
                {d.lowers && <span class="drill__tag drill__tag--down">{STAT_NAMES[d.lowers]} ▼</span>}
                {m.likes.drill === d.id && <span class="drill__tag drill__tag--love">♥ {t.liked}</span>}
                {m.likes.dislikedDrill === d.id && <span class="drill__tag drill__tag--down">✗ {t.disliked}</span>}
                {bonusDrill === d.id && <span class="drill__tag drill__tag--love">{t.bonus}</span>}
                {(m.status.tonics[d.main] ?? 0) > 0 && <span class="drill__tag drill__tag--love">{t.tonic}</span>}
              </span>
              <span class="drill__meta">
                {locked && <span class="drill__tag">{t.locked}</span>}
                {!locked && mode === 'guided' && <span class="drill__odds">{ODDS_WORDS[odds.word]}</span>}
                {!locked && mode === 'lens' && (
                  <>
                    <span class="drill__odds">{fill(t.exact, { g: odds.pct.great.toFixed(0), s: odds.pct.success.toFixed(0), c: odds.pct.cheat.toFixed(0), f: odds.pct.fail.toFixed(0) })}</span>
                    {odds.truancyPct > 0 && <span class="drill__tag drill__tag--down">{fill(t.truancy, { n: odds.truancyPct.toFixed(0) })}</span>}
                  </>
                )}
                <span class="drill__tag">{fill(t.pay, { n: pay })}</span>
              </span>
            </button>
          )
        })}
      </div>
      <div class="sheet__actions">
        <button type="button" class="btn" onClick={closeTrain}>
          {UI_TEXT.lab.actions.cancel}
        </button>
      </div>
    </Sheet>
  )
}
