import { useEffect, useRef, useState } from 'preact/hooks'
import { toCsv, type LabSummary } from '../../../core/battle/stats.ts'
import { fill } from '../../../data/text/format.ts'
import { PERSONALITY_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { BATTLE } from '../../../data/tuning.ts'
import { PERSONALITIES, type Personality } from '../../../data/types.ts'
import type { LabRequest, LabResponse } from '../../../workers/battleLab.worker.ts'
import { Chips, Field, Segmented, Select, TopBar } from '../../components/Controls.tsx'
import { PickSlot, type Picked } from '../../components/MonsterPicker.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { downloadText } from '../../lib/files.ts'
import { showToast } from '../../store/appStore.ts'

const COUNTS = [100, 500, 1000]
const PERSONALITY_OPTIONS = PERSONALITIES.map((p) => ({ value: p, label: PERSONALITY_LABELS[p].name }))

function randomSeed(): number {
  try {
    const a = new Uint32Array(1)
    crypto.getRandomValues(a)
    return a[0]!
  } catch {
    return Math.floor(Math.random() * 0xffffffff)
  }
}

/** §19 Battle Lab: A vs B, 100 / 500 / 1,000 battles, a seed, a progress bar, the numbers, and a CSV. */
export function LabBattleLabScreen() {
  const t = UI_TEXT.battleLab
  const [a, setA] = useState<Picked | null>(null)
  const [b, setB] = useState<Picked | null>(null)
  const [count, setCount] = useState(100)
  const [seedMode, setSeedMode] = useState<'random' | 'fixed'>('random')
  const [seed, setSeed] = useState(1)
  const [pA, setPA] = useState<Personality>('Steady')
  const [pB, setPB] = useState<Personality>('Steady')
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null)
  const [summary, setSummary] = useState<LabSummary | null>(null)
  const [usedSeed, setUsedSeed] = useState<number | null>(null)
  const worker = useRef<Worker | null>(null)

  useEffect(() => () => worker.current?.terminate(), [])

  const run = () => {
    if (!a || !b) return
    const s = seedMode === 'fixed' ? seed : randomSeed()
    const req: LabRequest = { type: 'run', a: a.monster, b: b.monster, battles: count, seed: s, personalityA: pA, personalityB: pB, timerSec: BATTLE.timersSec[0]! }
    setSummary(null)
    setUsedSeed(s)
    setProgress({ done: 0, total: count })
    try {
      const w = new Worker(new URL('../../../workers/battleLab.worker.ts', import.meta.url), { type: 'module' })
      worker.current = w
      w.onmessage = (e: MessageEvent<LabResponse>) => {
        if (e.data.type === 'progress') setProgress({ done: e.data.done, total: e.data.total })
        else {
          setSummary(e.data.summary)
          setProgress(null)
          w.terminate()
          worker.current = null
        }
      }
      w.onerror = () => {
        w.terminate()
        worker.current = null
        fallback(req)
      }
      w.postMessage(req)
    } catch {
      fallback(req)
    }
  }

  const fallback = (req: LabRequest) => {
    showToast(t.noWorker)
    void import('../../../workers/battleLab.worker.ts').then((m) => {
      setSummary(m.runLab(req))
      setProgress(null)
    })
  }

  const cancel = () => {
    worker.current?.terminate()
    worker.current = null
    setProgress(null)
  }

  const csv = () => {
    if (!summary || !a || !b) return
    const file = `wildsong-battle-lab-${usedSeed ?? 0}.csv`
    showToast(downloadText(file, toCsv(a.monster.name, b.monster.name, summary), 'text/csv') ? fill(t.csvDone, { file }) : UI_TEXT.lab.export_.downloadFailed)
  }

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.pell} tone="muted">
        <p>{t.hint}</p>
      </SpeakerCard>
      <PickSlot label={UI_TEXT.versus.sideA} picked={a} onPick={setA} />
      <PickSlot label={UI_TEXT.versus.sideB} picked={b} onPick={setB} />
      <div class="grid2">
        <Select label={UI_TEXT.versus.personalityA} value={pA} options={PERSONALITY_OPTIONS} onChange={setPA} />
        <Select label={UI_TEXT.versus.personalityB} value={pB} options={PERSONALITY_OPTIONS} onChange={setPB} />
      </div>
      <p class="field__label">{t.battles}</p>
      <Chips options={COUNTS.map((n) => ({ value: String(n), label: n.toLocaleString() }))} value={String(count)} onChange={(v) => setCount(Number(v))} label={t.battles} />
      <p class="field__label">{t.seed}</p>
      <Segmented
        options={[
          { value: 'random', label: t.seedModes.random },
          { value: 'fixed', label: t.seedModes.fixed },
        ]}
        value={seedMode}
        onChange={setSeedMode}
        label={t.seed}
      />
      {seedMode === 'fixed' && (
        <Field label={t.seed} hint={t.seedHint}>
          <input class="input" type="number" inputMode="numeric" min={0} max={4294967295} value={seed} onInput={(e) => setSeed(Math.max(0, Math.floor(Number((e.currentTarget as HTMLInputElement).value) || 0)))} />
        </Field>
      )}

      {progress && (
        <section class="card">
          <p>{fill(t.running, { done: progress.done, total: progress.total })}</p>
          <div class="progress">
            <span class="progress__fill" style={{ width: `${(progress.done / progress.total) * 100}%` }} />
          </div>
          <button type="button" class="btn" style={{ marginTop: 10 }} onClick={cancel}>
            {t.cancel}
          </button>
        </section>
      )}

      {summary && a && b && (
        <section class="card">
          <p class="field__label">
            {t.results} · {t.seed} {usedSeed}
          </p>
          <table class="bresult__table">
            <thead>
              <tr>
                <th />
                <th>{a.monster.name}</th>
                <th>{b.monster.name}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t.metrics.win}</td>
                <td>{summary.winPct[0]}</td>
                <td>{summary.winPct[1]}</td>
              </tr>
              <tr>
                <td>{t.metrics.draw}</td>
                <td colSpan={2}>{summary.drawPct}</td>
              </tr>
              <tr>
                <td>{t.metrics.ko}</td>
                <td>{summary.koPct[0]}</td>
                <td>{summary.koPct[1]}</td>
              </tr>
              <tr>
                <td>{t.metrics.length}</td>
                <td colSpan={2}>{fill(UI_TEXT.battle.seconds, { s: summary.avgSeconds })}</td>
              </tr>
              <tr>
                <td>{t.metrics.attacks}</td>
                <td>{summary.attacksPerBattle[0]}</td>
                <td>{summary.attacksPerBattle[1]}</td>
              </tr>
              <tr>
                <td>{t.metrics.hitRate}</td>
                <td>{summary.hitRatePct[0]}</td>
                <td>{summary.hitRatePct[1]}</td>
              </tr>
              <tr>
                <td>{t.metrics.dmg}</td>
                <td>{summary.damagePerHit[0]}</td>
                <td>{summary.damagePerHit[1]}</td>
              </tr>
              <tr>
                <td>{t.metrics.top}</td>
                <td class="small">{summary.topTechniques[0].map((x) => `${x.name} (${x.uses})`).join(', ')}</td>
                <td class="small">{summary.topTechniques[1].map((x) => `${x.name} (${x.uses})`).join(', ')}</td>
              </tr>
            </tbody>
          </table>
          <button type="button" class="btn" style={{ marginTop: 10 }} onClick={csv}>
            {t.csv}
          </button>
        </section>
      )}

      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" disabled={!a || !b || progress !== null} onClick={run}>
          {a && b ? t.run : UI_TEXT.versus.needBoth}
        </button>
      </div>
    </main>
  )
}
