import { useEffect, useState } from 'preact/hooks'
import { heartstoneCap, type ConcludeResult } from '../../core/legacy.ts'
import { totalStats } from '../../core/monster.ts'
import { say } from '../../core/report.ts'
import { FOOD_BY_ID } from '../../data/foods.ts'
import { fill } from '../../data/text/format.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { WREN } from '../../data/text/wren.ts'
import { Field, TopBar } from '../components/Controls.tsx'
import { MonsterPortrait } from '../components/MonsterPortrait.tsx'
import { SpeakerCard } from '../components/RanchBits.tsx'
import { now } from '../lib/clock.ts'
import { newId } from '../lib/ids.ts'
import { navigate } from '../router.ts'
import { showToast, upsertEntry } from '../store/appStore.ts'
import { concludeLife, game } from '../store/gameStore.ts'

const EPITAPH_MAX = 80

/**
 * §7 the farewell: the ranch at dusk, the best moments, a one-line epitaph, and the move to the Memorial
 * (and, on Gentle, the Elder Grove) with a Heartstone. The ranch is empty afterwards; the game goes on.
 */
export function FarewellScreen() {
  const g = game.value
  const t = UI_TEXT.farewell
  const [done, setDone] = useState<{ result: ConcludeResult; name: string } | null>(null)
  const [epitaph, setEpitaph] = useState<string | null>(null)
  const [kept, setKept] = useState(false)

  useEffect(() => {
    if (!g) navigate('title')
    else if (!done && (!g.monster || !g.ended)) navigate(g.monster ? 'ranch' : 'ranch')
  }, [g === null, g?.ended, g?.monster === null, done !== null])

  if (!g) return null

  if (done) {
    const { result, name } = done
    const retired = result.cause === 'retired'
    const wild = result.cause === 'wandered'
    return (
      <main class="screen">
        <TopBar title={fill(retired ? t.retired : wild ? t.wandered : t.passed, { name })} />
        <div class="farewell__art dusk">
          <MonsterPortrait monster={result.state.memorial[0]!.monster} size={160} expression={retired ? 'happy' : wild ? 'sad' : 'sleepy'} animate={false} />
        </div>
        <section class="card">
          <p>{fill(retired ? t.elderNow : wild ? t.wildNow : t.restsNow, { name })}</p>
          {result.heartstone ? <p class="notice notice--ok">{fill(t.heartstone, { name })}</p> : result.heartstoneLost ? <p class="notice">{fill(t.heartstoneLost, { n: heartstoneCap(result.state) })}</p> : null}
        </section>
        <div class="spacer" />
        <div class="actionbar actionbar--stack">
          <button type="button" class="btn btn--primary" onClick={() => navigate('ranch')}>
            {t.backToRanch}
          </button>
          <button type="button" class="btn" onClick={() => navigate('pell')}>
            {t.visitPell}
          </button>
        </div>
      </main>
    )
  }

  if (!g.monster || !g.ended) return null
  const m = g.monster
  const retired = g.ended === 'retired'
  const wild = g.ended === 'wandered'
  // §6.10 a life that ended because no one came has its own words.
  const scene = retired ? WREN.retireScene : wild ? WREN.wanderScene : g.ended === 'neglected' ? WREN.neglectScene : WREN.farewellScene
  const pronounLine = say('farewellScene', scene, m).text
  const moments: string[] = []
  if (m.records.highestGrade !== 'E') moments.push(fill(WREN.moments.grade, { grade: m.records.highestGrade }))
  if (m.records.wins > 0) moments.push(fill(WREN.moments.wins, { n: m.records.wins }))
  if (m.records.titles[0]) moments.push(fill(WREN.moments.title, { title: m.records.titles[0] }))
  if (moments.length === 0) moments.push(WREN.moments.quiet)
  const momentLines = moments.slice(0, 2).map((moment) => say('farewellBest', WREN.farewellBest, m, { moment }).text)
  const text = epitaph ?? fill(t.epitaphDefault, { name: m.name, food: FOOD_BY_ID[m.likes.food].name.toLowerCase() }).slice(0, EPITAPH_MAX)

  const goodbye = () => {
    const r = concludeLife(text)
    if (r) setDone({ result: r, name: m.name })
  }

  const keep = async () => {
    const when = now()
    await upsertEntry({ monster: { ...structuredClone(m), id: newId() }, history: [], createdAt: when, updatedAt: when })
    setKept(true)
    showToast(fill(t.kept, { name: m.name }))
  }

  return (
    <main class="screen">
      <TopBar title={fill(retired ? t.retired : wild ? t.wandered : t.passed, { name: m.name })} />
      <div class="farewell__art dusk">
        <MonsterPortrait monster={m} size={200} expression={retired ? 'happy' : wild ? 'sad' : 'sleepy'} live clip={retired ? 'idle_happy' : wild ? 'idle_sad' : 'sleep'} />
      </div>
      <SpeakerCard speaker={UI_TEXT.wren}>
        <p>{pronounLine}</p>
        {momentLines.map((line, i) => (
          <p key={i} class="muted">
            {line}
          </p>
        ))}
      </SpeakerCard>
      <section class="card">
        <p class="field__label">{t.bestMoments}</p>
        <p>{fill(t.lived, { n: m.ageWeeks, total: m.lifespanTotal })}</p>
        <p>{fill(t.total, { n: totalStats(m.stats) })}</p>
        <p>{fill(t.record, { wins: m.records.wins, losses: m.records.losses, cups: m.records.cupsWon })}</p>
        {m.records.highestGrade !== 'E' && <p>{fill(t.highestGrade, { grade: m.records.highestGrade })}</p>}
        <p class="muted small">{m.records.titles.length ? fill(t.titles, { titles: m.records.titles.join(', ') }) : t.noTitles}</p>
        <p class="muted small">{fill(t.care, { drills: g.counters.drillsDone, rests: g.counters.restsTaken, sweets: g.counters.sweetsEaten })}</p>
      </section>
      <Field label={fill(t.epitaph, { name: m.name })} hint={t.epitaphHint}>
        <input class="input" value={text} maxLength={EPITAPH_MAX} onInput={(e) => setEpitaph((e.currentTarget as HTMLInputElement).value)} />
      </Field>
      <div class="spacer" />
      <div class="actionbar actionbar--stack">
        <button type="button" class="btn btn--primary" onClick={goodbye}>
          {retired ? fill(t.retireNow, { them: 'them' }) : t.sayGoodbye}
        </button>
        <button type="button" class="btn btn--ghost" disabled={kept} onClick={() => void keep()}>
          {t.keepCopy}
        </button>
      </div>
    </main>
  )
}
