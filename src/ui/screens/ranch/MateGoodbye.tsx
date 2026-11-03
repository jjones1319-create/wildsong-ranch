import type { WrenLine } from '../../../core/report.ts'
import type { GameState } from '../../../core/state.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { navigate } from '../../router.ts'
import { nextWeek, type DepartedMate } from '../../store/gameStore.ts'
import { pellTab } from '../town/PellLab.tsx'

/**
 * §6.11 a ranch-mate's gentle goodbye in the week summary (no blocking Farewell): its portrait from the Memorial
 * wall, Wren's lines, and a way to the Memorial to write its epitaph.
 */
export function MateGoodbye({ g, mate, lines }: { g: GameState; mate: DepartedMate; lines: WrenLine[] }) {
  const t = HERD_TEXT.goodbye
  const entry = g.memorial.find((e) => e.monster.id === mate.id)
  const retired = mate.how === 'retired'
  return (
    <section class="card goodbye">
      {entry && <MonsterPortrait monster={entry.monster} size={72} expression={retired ? 'happy' : 'sleepy'} animate={false} />}
      <div class="goodbye__body">
        <b>{fill(retired ? t.retired : t.passed, { name: mate.name })}</b>
        {lines.map((l) => (
          <span key={l.key} class="small">
            {l.text}
          </span>
        ))}
        <button
          type="button"
          class="btn btn--small"
          onClick={() => {
            nextWeek()
            pellTab.value = 'memorial'
            navigate('pell')
          }}
        >
          🕯️ {t.memorial}
        </button>
      </div>
    </section>
  )
}
