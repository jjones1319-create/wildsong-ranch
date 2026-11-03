import { useState } from 'preact/hooks'
import type { Monster } from '../../../core/monster.ts'
import { wrenVars } from '../../../core/report.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { Sheet, Toggle } from '../../components/Controls.tsx'
import { now } from '../../lib/clock.ts'
import { newId } from '../../lib/ids.ts'
import { showToast, upsertEntry } from '../../store/appStore.ts'
import { freeMonster } from '../../store/herdStore.ts'

/**
 * v16 🕊️ Set free (a ranch-mate, or a frozen monster from Pell's Lab): a danger confirm that can keep a copy in the
 * Lab Library first (a new id, as the Farewell's copy). The star must be swapped first; the caller hides the button.
 */
export function FreeSheet({ monster, onDone, onCancel }: { monster: Monster | null; onDone: () => void; onCancel: () => void }) {
  const [keep, setKeep] = useState(false)
  if (!monster) return null
  const m = monster
  const vars = wrenVars(m, { They: 'They', Their: 'Their' })
  const go = async () => {
    if (keep) {
      const when = now()
      await upsertEntry({ monster: { ...structuredClone(m), id: newId() }, history: [], createdAt: when, updatedAt: when })
    }
    const refused = freeMonster(m.id)
    setKeep(false)
    onDone()
    showToast(refused === 'star' ? fill(HERD_TEXT.free.star, vars) : refused ? HERD_TEXT.star.refused.notFound : fill(HERD_TEXT.free.done, vars))
  }
  return (
    <Sheet open title={fill(HERD_TEXT.free.title, vars)} onClose={onCancel}>
      <p class="sheet__text">{fill(HERD_TEXT.free.body, vars)}</p>
      <Toggle label={HERD_TEXT.free.keepCopy} checked={keep} onChange={setKeep} />
      <div class="sheet__actions" style={{ marginTop: 12 }}>
        <button type="button" class="btn btn--danger" onClick={() => void go()}>
          🕊️ {HERD_TEXT.free.confirm}
        </button>
        <button type="button" class="btn" onClick={onCancel}>
          {UI_TEXT.lab.actions.cancel}
        </button>
      </div>
    </Sheet>
  )
}
