import { useEffect, useState } from 'preact/hooks'
import { totalStats } from '../../core/monster.ts'
import { say } from '../../core/report.ts'
import { fill } from '../../data/text/format.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { WREN } from '../../data/text/wren.ts'
import { TopBar } from '../components/Controls.tsx'
import { MonsterPortrait } from '../components/MonsterPortrait.tsx'
import { SpeakerCard } from '../components/RanchBits.tsx'
import { now } from '../lib/clock.ts'
import { newId } from '../lib/ids.ts'
import { navigate } from '../router.ts'
import { showToast, upsertEntry } from '../store/appStore.ts'
import { game } from '../store/gameStore.ts'

/** The end of a life, as a placeholder: the full farewell scene, the Memorial and Heartstones arrive with M6. */
export function FarewellScreen() {
  const g = game.value
  const t = UI_TEXT.farewell
  const [kept, setKept] = useState(false)
  useEffect(() => {
    if (!g || !g.monster) navigate('title')
    else if (!g.ended) navigate('ranch')
  }, [g === null, g?.ended])
  if (!g || !g.monster || !g.ended) return null
  const m = g.monster
  const retired = g.ended === 'retired'
  const pct = Math.round((m.ageWeeks * 100) / Math.max(1, m.lifespanTotal))

  const keep = async () => {
    const when = now()
    await upsertEntry({ monster: { ...structuredClone(m), id: newId() }, history: [], createdAt: when, updatedAt: when })
    setKept(true)
    showToast(fill(t.kept, { name: m.name }))
  }

  return (
    <main class="screen">
      <TopBar title={fill(retired ? t.retired : t.passed, { name: m.name })} onBack={() => navigate('title')} />
      <div class="farewell__art">
        <MonsterPortrait monster={m} size={200} expression={retired ? 'happy' : 'sleepy'} />
      </div>
      <SpeakerCard speaker={UI_TEXT.wren}>
        <p>{say(retired ? 'retire' : 'farewell', retired ? WREN.retire : WREN.farewell, m).text}</p>
        <p class="muted small">{fill(WREN.farewellSoon, { name: m.name })}</p>
      </SpeakerCard>
      <section class="card">
        <p>{fill(t.lived, { n: m.ageWeeks, pct, total: m.lifespanTotal })}</p>
        <p>{fill(t.total, { n: totalStats(m.stats) })}</p>
        <p class="muted small">{fill(t.care, { drills: g.counters.drillsDone, rests: g.counters.restsTaken, sweets: g.counters.sweetsEaten })}</p>
      </section>
      <div class="spacer" />
      <div class="actionbar actionbar--stack">
        <button type="button" class="btn btn--primary" onClick={() => navigate('newGame')}>
          {t.newRanch}
        </button>
        <div class="actions__row">
          <button type="button" class="btn btn--half" disabled={kept} onClick={() => void keep()}>
            {t.keepCopy}
          </button>
          <button type="button" class="btn btn--half btn--ghost" onClick={() => navigate('title')}>
            {t.toTitle}
          </button>
        </div>
      </div>
    </main>
  )
}
