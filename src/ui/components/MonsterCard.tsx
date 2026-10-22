import { isPure, mixBreeds, totalStats } from '../../core/monster.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { settings } from '../store/appStore.ts'
import type { Listed } from '../store/labStore.ts'
import { Badge } from './Controls.tsx'
import { MonsterPortrait } from './MonsterPortrait.tsx'

export function variantNameOf(l: Listed['monster']): string {
  return mixBreeds(l.mainBreed, l.subBreed).variantName
}

/** A row in the Library: portrait, name, variant, total, grade and badges. */
export function MonsterCard({ listed, onTap }: { listed: Listed; onTap: (l: Listed) => void }) {
  const m = listed.monster
  const t = UI_TEXT.lab
  const showEdited = settings.value.showEditedBadge && m.flags.edited
  return (
    <button type="button" class="mcard" onClick={() => onTap(listed)}>
      <MonsterPortrait monster={m} size={84} class="mcard__art" animate={false} />
      <span class="mcard__body">
        <span class="mcard__name">{m.name}</span>
        <span class="mcard__sub">
          {variantNameOf(m)}
          {listed.tier && listed.tier !== 'baby' ? ` · ${listed.tier}` : ''}
        </span>
        <span class="mcard__meta">
          <span>
            {t.total} {totalStats(m.stats)}
          </span>
          <span>
            {t.grade} {m.grade}
          </span>
          {isPure(m) && <Badge tone="pure">✦ {t.badges.pure}</Badge>}
          {showEdited && <Badge tone="edited">🔧 {t.badges.edited}</Badge>}
        </span>
      </span>
    </button>
  )
}
