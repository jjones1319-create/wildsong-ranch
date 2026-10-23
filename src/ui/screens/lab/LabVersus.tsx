import { signal } from '@preact/signals'
import { useState } from 'preact/hooks'
import { fill } from '../../../data/text/format.ts'
import { PERSONALITY_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { BATTLE } from '../../../data/tuning.ts'
import { PERSONALITIES, type Personality } from '../../../data/types.ts'
import { Chips, Segmented, Select, TopBar } from '../../components/Controls.tsx'
import { PickSlot, type Picked } from '../../components/MonsterPicker.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { navigate, screen } from '../../router.ts'
import { startBattle } from '../../store/battleStore.ts'

/** Preselected side A (the ranch's Battle button sets this to the active monster). */
export const versusSideA = signal<Picked | null>(null)
/** The picks survive a trip to the battle screen and back, so Rematch and Done land on the same setup. */
export const versusSideB = signal<Picked | null>(null)

const PERSONALITY_OPTIONS = PERSONALITIES.map((p) => ({ value: p, label: PERSONALITY_LABELS[p].name }))

/** §19 Versus: any two monsters, You vs CPU or CPU vs CPU, 60 / 90 / 180 s. Exhibition only. */
export function LabVersusScreen() {
  const t = UI_TEXT.versus
  const a = versusSideA.value
  const b = versusSideB.value
  const setA = (p: Picked) => (versusSideA.value = p)
  const setB = (p: Picked) => (versusSideB.value = p)
  const [mode, setMode] = useState<'player' | 'cpu'>('player')
  const [pA, setPA] = useState<Personality>('Steady')
  const [pB, setPB] = useState<Personality>('Steady')
  const [timer, setTimer] = useState<number>(BATTLE.timersSec[0]!)
  const spar = a?.source === 'active'

  const start = () => {
    if (!a || !b) return
    const origin = screen.value
    startBattle({ a: a.monster, b: b.monster, aControl: mode === 'player' ? 'player' : 'ai', personalityA: pA, personalityB: pB, timerSec: timer, origin })
    navigate('battle')
  }

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.pell} tone="muted">
        <p>{spar ? t.sparHint : t.hint}</p>
      </SpeakerCard>
      <PickSlot label={t.sideA} picked={a} onPick={setA} />
      <p class="center muted">{UI_TEXT.battle.vs}</p>
      <PickSlot label={t.sideB} picked={b} onPick={setB} />
      <p class="field__label">{t.mode}</p>
      <Segmented
        options={[
          { value: 'player', label: t.modes.player },
          { value: 'cpu', label: t.modes.cpu },
        ]}
        value={mode}
        onChange={setMode}
        label={t.mode}
      />
      {mode === 'cpu' && <Select label={t.personalityA} value={pA} options={PERSONALITY_OPTIONS} onChange={setPA} hint={PERSONALITY_LABELS[pA].blurb} />}
      <Select label={t.personalityB} value={pB} options={PERSONALITY_OPTIONS} onChange={setPB} hint={PERSONALITY_LABELS[pB].blurb} />
      <p class="field__label">{t.timer}</p>
      <Chips options={BATTLE.timersSec.map((s) => ({ value: String(s), label: fill(t.seconds, { n: s }) }))} value={String(timer)} onChange={(v) => setTimer(Number(v))} label={t.timer} />
      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" disabled={!a || !b} onClick={start}>
          {a && b ? t.start : t.needBoth}
        </button>
      </div>
    </main>
  )
}
