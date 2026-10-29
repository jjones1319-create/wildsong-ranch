import { DRILLS } from '../../data/drills.ts'
import { JOURNEY_SITES } from '../../data/journeys.ts'
import { fill } from '../../data/text/format.ts'
import { STAT_NAMES } from '../../data/text/labels.ts'
import { STATS_GUIDE } from '../../data/text/stats.ts'
import { STAT_CAP_BY_GRADE } from '../../data/tuning.ts'
import { GRADES, STAT_KEYS, type StatKey } from '../../data/types.ts'

/**
 * The stats guide (v1.11): what each stat does, which drills and Journeys grow it (read from the data, so it never
 * drifts), and how grades, caps and Stat Sweets work. Used by the Monster Card's sheet and the Journal's Stats page.
 */
export function StatsGuide({ focus }: { focus?: StatKey | null }) {
  const t = STATS_GUIDE
  const caps = GRADES.map((g) => `${g} ${STAT_CAP_BY_GRADE[g].toLocaleString('en-US')}`).join(' · ')
  const order = focus ? [focus, ...STAT_KEYS.filter((k) => k !== focus)] : STAT_KEYS
  return (
    <div class="guide">
      <p class="muted">{t.intro}</p>
      {order.map((k) => {
        const main = DRILLS.filter((d) => d.main === k).map((d) => d.name)
        const little = DRILLS.filter((d) => d.secondary === k).map((d) => d.name)
        // Every Journey adds a little Life (GAME_DESIGN §11); the other stats have their own site.
        const sites = k === 'LIF' ? t.labels.everyJourney : JOURNEY_SITES.filter((s) => s.stat === k).map((s) => s.name).join(', ')
        return (
          <section key={k} class={`guide__stat ${k === focus ? 'guide__stat--focus' : ''}`} style={{ '--stat': `var(--stat-${k.toLowerCase()})` }}>
            <h3 class="guide__name">
              <span class="guide__swatch" aria-hidden="true" />
              {k} · {STAT_NAMES[k]}
            </h3>
            <dl class="kv">
              <dt>{t.labels.does}</dt>
              <dd>{t.stats[k].does}</dd>
              <dt>{t.labels.also}</dt>
              <dd>{t.stats[k].also}</dd>
              <dt>{t.labels.grow}</dt>
              <dd>{main.join(', ')}</dd>
              {little.length > 0 && (
                <>
                  <dt>{t.labels.growLittle}</dt>
                  <dd>{little.join(', ')}</dd>
                </>
              )}
              <dt>{t.labels.journeys}</dt>
              <dd>{sites}</dd>
            </dl>
          </section>
        )
      })}
      <section class="guide__stat">
        <h3 class="guide__name">{t.growTitle}</h3>
        <p>{t.grades}</p>
        <p>{fill(t.caps, { caps })}</p>
        <p>{t.sweets}</p>
        <p>{t.pearl}</p>
      </section>
    </div>
  )
}
