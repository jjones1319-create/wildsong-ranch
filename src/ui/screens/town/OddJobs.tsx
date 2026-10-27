import { useEffect, useState } from 'preact/hooks'
import { canPlayEchoStones } from '../../../core/echoStones.ts'
import { canPlayOddJob } from '../../../core/oddJobs.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { ECHO_STONES, ODD_JOBS } from '../../../data/tuning.ts'
import { TopBar } from '../../components/Controls.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { oddJobMode } from '../../lib/audioDirector.ts'
import { navigate } from '../../router.ts'
import { game } from '../../store/gameStore.ts'
import { EchoStones } from './EchoStones.tsx'
import { TurnipSort } from './TurnipSort.tsx'

const t = UI_TEXT.oddJobs

type JobId = 'turnip' | 'echo'

/**
 * CONTENT §13 Basil's board: every Odd Job with its status. Each job pays once per in-game week; Practice
 * replays any job for fun with no pay. The games themselves live in their own components.
 */
export function OddJobsScreen() {
  const g = game.value
  const [job, setJob] = useState<{ id: JobId; practice: boolean } | null>(null)

  useEffect(() => {
    if (!g) navigate('town')
  }, [g === null])

  // Sound 2.0 §11: the director hears which job is open (Turnip Sort and Echo Stones have their own sound).
  useEffect(() => {
    oddJobMode.value = job?.id ?? null
    return () => {
      oddJobMode.value = null
    }
  }, [job?.id])

  if (!g) return null
  if (job?.id === 'turnip') return <TurnipSort practice={job.practice} onDone={() => setJob(null)} />
  if (job?.id === 'echo') return <EchoStones practice={job.practice} onDone={() => setJob(null)} />

  const turnip = canPlayOddJob(g)
  const echo = canPlayEchoStones(g)
  const noMonster = !g.monster || g.ended !== null
  const jobs: { id: JobId; icon: string; name: string; blurb: string; can: { ok: boolean }; cap: number; best: string | null }[] = [
    { id: 'turnip', icon: '🥕', name: t.turnipSort, blurb: t.turnipBlurb, can: turnip, cap: ODD_JOBS.cap, best: null },
    { id: 'echo', icon: '🔔', name: t.echoStones, blurb: t.echoBlurb, can: echo, cap: ECHO_STONES.cap, best: g.echoStonesBest > 0 ? fill(t.bestRound, { n: g.echoStonesBest }) : null },
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
                <p class={`small ${j.can.ok ? 'jobcard__status' : 'muted'}`}>{j.can.ok ? fill(t.paysUpTo, { n: gold(j.cap) }) : noMonster ? t.noMonster : t.paidThisWeek}</p>
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
