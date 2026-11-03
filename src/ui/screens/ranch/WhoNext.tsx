import type { GameState } from '../../../core/state.ts'
import { wrenVars } from '../../../core/report.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { MonsterCard } from '../../components/MonsterCard.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { showToast } from '../../store/appStore.ts'
import { makeStar } from '../../store/herdStore.ts'

/**
 * v16 "Who will you raise next?" after the star's Farewell, and on an empty ranch with ranch-mates: tap one to make
 * it the star. "Later" leaves the ranch empty, and the weeks wait as before.
 */
export function WhoNext({ g, onPicked, onLater }: { g: GameState; onPicked?: () => void; onLater: () => void }) {
  const t = HERD_TEXT.next
  if (g.ranchmates.length === 0) return null
  const pick = (id: string) => {
    const mate = g.ranchmates.find((r) => r.monster.id === id)
    if (!mate) return
    const why = makeStar(id)
    if (why) {
      showToast(HERD_TEXT.star.refused[why])
      return
    }
    showToast(fill(HERD_TEXT.star.first, wrenVars(mate.monster)))
    onPicked?.()
  }
  return (
    <section class="whonext" aria-label={t.title}>
      <h2 class="sheet__title">{t.title}</h2>
      <SpeakerCard speaker={UI_TEXT.wren} tone="muted">
        <p>{t.wren}</p>
      </SpeakerCard>
      <div class="list">
        {g.ranchmates.map((r) => (
          <MonsterCard key={r.monster.id} listed={{ id: r.monster.id, monster: r.monster, source: 'library', history: [], createdAt: 0, updatedAt: 0 }} onTap={(l) => pick(l.id)} />
        ))}
      </div>
      <button type="button" class="btn btn--ghost" onClick={onLater}>
        {t.later}
      </button>
    </section>
  )
}
