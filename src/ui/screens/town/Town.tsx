import { canPlayEchoStones } from '../../../core/echoStones.ts'
import { canPlayOddJob } from '../../../core/oddJobs.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
import { SceneBanner } from '../../components/SceneBanner.tsx'
import { gold } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { game } from '../../store/gameStore.ts'

interface Row {
  icon: string
  name: string
  hint: string
  go?: () => void
}

/** §21 Town: the Shop, the Guild Library and the Monster Lab now; the rest of Tunewick opens with later milestones. */
export function TownScreen() {
  const t = UI_TEXT.town
  const g = game.value
  const unread = g?.mail.filter((m) => !m.read).length ?? 0
  const rows: Row[] = [
    { icon: '🏛', name: t.guild, hint: t.guildHint, go: () => navigate('guild') },
    { icon: '📅', name: t.calendar, hint: t.calendarHint, go: g ? () => navigateFrom('town', 'calendar') : undefined },
    { icon: '📔', name: t.journal, hint: t.journalHint, go: () => navigate('journal') },
    { icon: '🧺', name: t.shop, hint: t.shopHint, go: () => navigate('shop') },
    { icon: '📜', name: t.library, hint: t.libraryHint, go: () => navigate('library') },
    { icon: '✉', name: unread ? `${t.mail} · ${fill(UI_TEXT.mail.unread, { n: unread })}` : t.mail, hint: t.mailHint, go: () => navigate('mail') },
    { icon: '🔬', name: t.lab, hint: t.labHint, go: () => navigateFrom('town', 'lab') },
    { icon: '🐾', name: t.market, hint: t.marketHint, go: () => navigate('market') },
    { icon: '🪨', name: t.shrine, hint: t.shrineHint, go: () => navigate('shrine') },
    { icon: '🧊', name: t.pell, hint: t.pellHint, go: () => navigate('pell') },
    { icon: '🥕', name: t.jobs, hint: g && (canPlayOddJob(g).ok || canPlayEchoStones(g).ok) ? t.jobsHint : t.jobsPlayed, go: g ? () => navigate('oddJobs') : undefined },
  ]
  return (
    <main class="screen">
      <TopBar title={t.title} right={g ? <span class="calstrip__money">{gold(g.money)}</span> : undefined} />
      <SceneBanner scene="town" />
      <div class="list">
        {rows.map((r) => (
          <button key={r.name} type="button" class={`townrow ${r.go ? '' : 'townrow--off'}`} disabled={!r.go} onClick={r.go}>
            <span class="townrow__icon" aria-hidden="true">
              {r.icon}
            </span>
            <span class="townrow__body">
              <span class="townrow__name">{r.name}</span>
              <span class="townrow__hint">{r.hint}</span>
            </span>
          </button>
        ))}
      </div>
    </main>
  )
}
