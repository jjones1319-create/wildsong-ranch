import { totalStats } from '../../core/monster.ts'
import { variantNameOf as coreVariantName } from '../../core/variants.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { settings } from '../store/appStore.ts'
import type { Listed } from '../store/labStore.ts'
import { Badge } from './Controls.tsx'
import { MonsterPortrait } from './MonsterPortrait.tsx'

export function variantNameOf(l: Listed['monster']): string {
  return coreVariantName(l)
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
          {showEdited && <Badge tone="edited">🔧 {t.badges.edited}</Badge>}
          {listed.badge === 'elder' && <Badge>🌳 {UI_TEXT.pellLab.elderBadge}</Badge>}
          {listed.badge === 'frozen' && <Badge>❄️ {UI_TEXT.labSources.freezer}</Badge>}
          {listed.badge === 'memorial' && <Badge>🕯️ {listed.cause ? UI_TEXT.pellLab.cause[listed.cause] : UI_TEXT.labSources.memorial}</Badge>}
        </span>
      </span>
    </button>
  )
}
