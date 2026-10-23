import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
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
    { icon: '🧺', name: t.shop, hint: t.shopHint, go: () => navigate('shop') },
    { icon: '📜', name: t.library, hint: t.libraryHint, go: () => navigate('library') },
    { icon: '✉', name: unread ? `${t.mail} · ${fill(UI_TEXT.mail.unread, { n: unread })}` : t.mail, hint: t.mailHint, go: () => navigate('mail') },
    { icon: '🔬', name: t.lab, hint: t.labHint, go: () => navigateFrom('town', 'lab') },
    { icon: '🐾', name: t.market, hint: t.later },
    { icon: '🪨', name: t.shrine, hint: t.later },
    { icon: '🧊', name: t.pell, hint: t.later },
    { icon: '🥕', name: t.jobs, hint: t.later },
  ]
  return (
    <main class="screen">
      <TopBar title={t.title} right={g ? <span class="calstrip__money">{gold(g.money)}</span> : undefined} />
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
