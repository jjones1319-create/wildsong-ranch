import { useEffect, useState } from 'preact/hooks'
import { canPlayEchoStones } from '../../../core/echoStones.ts'
import { canPlayDash } from '../../../core/meadowDash.ts'
import { canPlayOddJob } from '../../../core/oddJobs.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import type { OddJobId } from '../../../data/types.ts'
import { TopBar } from '../../components/Controls.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { oddJobMode } from '../../lib/audioDirector.ts'
import { navigate } from '../../router.ts'
import { game } from '../../store/gameStore.ts'
import { EchoStones } from './EchoStones.tsx'
import { MeadowDash } from './MeadowDash.tsx'
import { TurnipSort } from './TurnipSort.tsx'

const t = UI_TEXT.oddJobs

/**
 * CONTENT §13 Basil's board: every Odd Job with its status, pay and best. Each job pays once per in-game week,
 * with no limit; Practice replays any job for fun with no pay. The games themselves live in their own components.
 */
export function OddJobsScreen() {
  const g = game.value
  const [job, setJob] = useState<{ id: OddJobId; practice: boolean } | null>(null)

  useEffect(() => {
    if (!g) navigate('town')
  }, [g === null])

  // Sound 2.0 §11: the director hears which job is open (each job has its own sound).
  useEffect(() => {
    oddJobMode.value = job?.id ?? null
    return () => {
      oddJobMode.value = null
    }
  }, [job?.id])

  if (!g) return null
  if (job?.id === 'turnip') return <TurnipSort practice={job.practice} onDone={() => setJob(null)} />
  if (job?.id === 'echo') return <EchoStones practice={job.practice} onDone={() => setJob(null)} />
  if (job?.id === 'dash') return <MeadowDash practice={job.practice} onDone={() => setJob(null)} />

  const noMonster = !g.monster || g.ended !== null
  const jobs: { id: OddJobId; icon: string; name: string; blurb: string; can: { ok: boolean }; pays: string; best: string | null }[] = [
    { id: 'turnip', icon: '🥕', name: t.turnipSort, blurb: t.turnipBlurb, can: canPlayOddJob(g), pays: t.turnipPays, best: g.turnipBest > 0 ? fill(t.bestSorted, { n: g.turnipBest }) : null },
    { id: 'echo', icon: '🔔', name: t.echoStones, blurb: t.echoBlurb, can: canPlayEchoStones(g), pays: t.echoPays, best: g.echoStonesBest > 0 ? fill(t.bestRound, { n: g.echoStonesBest }) : null },
    { id: 'dash', icon: '🏁', name: t.dash, blurb: t.dashBlurb, can: canPlayDash(g), pays: t.dashPays, best: g.dashBest > 1 ? fill(t.bestHeats, { n: g.dashBest }) : g.dashBest === 1 ? t.bestHeat : null },
  ]

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.basil} tone="muted">
        <p>{t.board}</p>
      </SpeakerCard>
      {noMonster && <p class="notice">{t.noMonster}</p>}
      <div class="list">
        {jobs.map((j) => (
          <section key={j.id} class="card jobcard" aria-label={j.name}>
            <div class="jobcard__head">
              <span class="jobcard__icon" aria-hidden="true">
                {j.icon}
              </span>
              <div class="jobcard__body">
                <p class="jobcard__name">{j.name}</p>
                <p class="muted small">{j.blurb}</p>
                <p class={`small ${j.can.ok ? 'jobcard__status' : 'muted'}`}>{j.can.ok ? j.pays : noMonster ? t.noMonster : t.paidThisWeek}</p>
                {j.best && <p class="small muted">{j.best}</p>}
              </div>
            </div>
            <div class="row">
              <button type="button" class="btn btn--primary btn--half" disabled={!j.can.ok} onClick={() => setJob({ id: j.id, practice: false })}>
                {t.play}
              </button>
              <button type="button" class="btn btn--half" disabled={noMonster} onClick={() => setJob({ id: j.id, practice: true })}>
                {t.practice}
              </button>
            </div>
          </section>
        ))}
      </div>
    </main>
  )
}
