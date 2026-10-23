import type { GameState } from '../../../core/state.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { CalendarStrip, SpeakerCard } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'

/** §21 the ranch with nobody on it (after a farewell or a freeze): the weeks wait until a monster is home. */
export function EmptyRanch({ g }: { g: GameState }) {
  const t = UI_TEXT.emptyRanch
  const stored = g.freezer.length + g.elderGrove.length
  const rows = [
    { icon: '🧊', name: fill(t.freezer, { n: stored }), hint: UI_TEXT.town.pellHint, go: () => navigate('pell') },
    { icon: '🐾', name: t.market, hint: UI_TEXT.town.marketHint, go: () => navigate('market') },
    { icon: '🪨', name: t.shrine, hint: UI_TEXT.town.shrineHint, go: () => navigate('shrine') },
    { icon: '🔬', name: t.lab, hint: UI_TEXT.town.labHint, go: () => navigateFrom('ranch', 'lab') },
  ]
  return (
    <main class="screen">
      <CalendarStrip state={g} onSettings={() => navigateFrom('ranch', 'settings')} />
      <section class="stage stage--empty" aria-label={t.title}>
        <p class="stage__caption">{t.title}</p>
        <p class="stage__hint">{t.time}</p>
      </section>
      <SpeakerCard speaker={UI_TEXT.wren}>
        <p>{WREN.emptyRanch}</p>
      </SpeakerCard>
      <div class="list">
        {rows.map((r) => (
          <button key={r.name} type="button" class="townrow" onClick={r.go}>
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
      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn" onClick={() => navigate('town')}>
          {UI_TEXT.ranch.actions.town}
        </button>
      </div>
    </main>
  )
}
