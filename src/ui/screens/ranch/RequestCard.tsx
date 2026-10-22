import { tipText } from '../../../core/onboarding.ts'
import { say } from '../../../core/report.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { Sheet } from '../../components/Controls.tsx'
import { TipCard } from '../../components/RanchBits.tsx'
import { answer, dismissTip, game, tipFor } from '../../store/gameStore.ts'

/** §6.7: the monster asks for rest, play or a treat. Accepting rest or play uses the week; denying adds stress. */
export function RequestCard({ open }: { open: boolean }) {
  const g = game.value
  const t = UI_TEXT.request
  if (!open || !g || !g.monster || !g.pendingRequest) return null
  const m = g.monster
  const r = g.pendingRequest
  const line = r.kind === 'rest' ? say('requestRest', WREN.requestRest, m) : r.kind === 'play' ? say('requestPlay', WREN.requestPlay, m) : say('requestTreat', WREN.requestTreat, m)
  const vars = { name: m.name, them: 'them', toy: r.toy ? (ITEM_BY_ID[r.toy]?.name ?? r.toy) : '' }
  const accept = r.kind === 'rest' ? fill(t.rest, vars) : r.kind === 'play' ? fill(t.play, vars) : fill(t.treat, vars)
  const tip = tipFor({ screen: 'request' })
  return (
    <Sheet open title={fill(t.title, { name: m.name })} onClose={() => undefined}>
      <section class="card card--muted">
        <p class="speaker">{UI_TEXT.wren}</p>
        <p>{line.text}</p>
      </section>
      {tip && <TipCard text={tipText(g, tip)} onDismiss={() => dismissTip(tip)} />}
      <div class="sheet__actions">
        <button type="button" class="btn btn--primary" onClick={() => answer(true)}>
          {accept}
        </button>
        <button type="button" class="btn" onClick={() => answer(false)}>
          {t.deny}
        </button>
      </div>
    </Sheet>
  )
}
