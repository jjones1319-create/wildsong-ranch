import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { Sheet } from '../../components/Controls.tsx'
import { MonsterCard } from '../../components/MonsterCard.tsx'
import { navigate } from '../../router.ts'
import { showToast } from '../../store/appStore.ts'
import { game } from '../../store/gameStore.ts'
import { freezerToPen } from '../../store/herdStore.ts'

/** v16 the empty pen's "+": move a frozen monster in (time starts again for it), or go and find one. */
export function PenSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const g = game.value
  if (!open || !g) return null
  const t = HERD_TEXT.pen
  const frozen = g.freezer
  const move = (id: string, name: string) => {
    const refused = freezerToPen(id)
    onClose()
    showToast(refused === 'full' ? HERD_TEXT.move.pensFull : refused ? HERD_TEXT.star.refused.notFound : fill(HERD_TEXT.move.toPen, { name }))
  }
  return (
    <Sheet open title={t.title} onClose={onClose}>
      <p class="muted small">{frozen.length > 0 ? t.intro : t.none}</p>
      <div class="list">
        {frozen.map((m) => (
          <MonsterCard key={m.id} listed={{ id: m.id, monster: m, source: 'freezer', history: [], createdAt: 0, updatedAt: 0, badge: 'frozen' }} onTap={() => move(m.id, m.name)} />
        ))}
      </div>
      <div class="sheet__actions">
        {frozen.length === 0 && (
          <>
            <button
              type="button"
              class="btn"
              onClick={() => {
                onClose()
                navigate('shrine')
              }}
            >
              🪨 {UI_TEXT.emptyRanch.shrine}
            </button>
            <button
              type="button"
              class="btn"
              onClick={() => {
                onClose()
                navigate('market')
              }}
            >
              🐾 {UI_TEXT.emptyRanch.market}
            </button>
          </>
        )}
        <button type="button" class="btn btn--ghost" onClick={onClose}>
          {UI_TEXT.lab.actions.cancel}
        </button>
      </div>
    </Sheet>
  )
}
