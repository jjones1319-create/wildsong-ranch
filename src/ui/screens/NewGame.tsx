import { useEffect, useMemo, useState } from 'preact/hooks'
import { marketMonster, marketStock } from '../../core/market.ts'
import type { Monster } from '../../core/monster.ts'
import { variantNameOf } from '../../core/variants.ts'
import { monsterFromRoll, rollShrine } from '../../core/shrine.ts'
import { BREED_BY_ID, STARTING_UNLOCKED } from '../../data/breeds.ts'
import { fill } from '../../data/text/format.ts'
import { DIFFICULTY_LABELS, MONTH_NAMES } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { WREN } from '../../data/text/wren.ts'
import { RANGES } from '../../data/tuning.ts'
import { DIFFICULTIES, type BreedId, type Difficulty } from '../../data/types.ts'
import { fileNameForSave, saveJsonText } from '../../save/exportImport.ts'
import { Field, Segmented, Sheet, TopBar } from '../components/Controls.tsx'
import { MonsterPortrait } from '../components/MonsterPortrait.tsx'
import { SpeakerCard } from '../components/RanchBits.tsx'
import { downloadText } from '../lib/files.ts'
import { newId } from '../lib/ids.ts'
import { goBack, navigate, navigateFrom } from '../router.ts'
import { showToast } from '../store/appStore.ts'
import { currentSave, game, startNewGame } from '../store/gameStore.ts'
import { startEditActive } from '../store/labStore.ts'
import { dateOf } from '../../core/calendar.ts'

type Step = 'names' | 'difficulty' | 'monster' | 'meet'

const NEW_GAME_MONTH = 1

/** §21 New Game: names → difficulty → first monster (Guild gift or the Shrine) → meet it, Begin or Edit before you start. */
export function NewGameScreen() {
  const t = UI_TEXT.newGame
  const existing = game.value
  const [step, setStep] = useState<Step>('names')
  const [breeder, setBreeder] = useState('')
  const [ranch, setRanch] = useState<string>(t.defaultRanch)
  const [difficulty, setDifficulty] = useState<Difficulty>('Standard')
  const [mode, setMode] = useState<'gift' | 'shrine'>('gift')
  const [gift, setGift] = useState<BreedId>('puddlepup')
  const [phrase, setPhrase] = useState('')
  const [artist, setArtist] = useState('')
  const [monster, setMonster] = useState<Monster | null>(null)
  const [name, setName] = useState('')
  const [askReplace, setAskReplace] = useState(existing !== null)

  useEffect(() => {
    setAskReplace(existing !== null)
  }, [existing === null])

  const stock = useMemo(() => marketStock(NEW_GAME_MONTH), [])
  const roll = useMemo(() => (phrase.trim() ? rollShrine(phrase, artist, STARTING_UNLOCKED) : null), [phrase, artist])

  const meet = (m: Monster) => {
    setMonster(m)
    setName(m.name)
    setStep('meet')
  }

  const begin = (editFirst: boolean) => {
    if (!monster) return
    const named = { ...monster, name: name.trim().slice(0, RANGES.nameLength.max) || monster.name }
    const state = startNewGame({ difficulty, monster: named, breederName: breeder.trim() || undefined, ranchName: ranch.trim() || undefined })
    if (editFirst && state.monster) {
      startEditActive(state.monster, [])
      navigateFrom('ranch', 'labEdit')
    } else navigate('ranch')
  }

  const exportCurrent = () => {
    const save = currentSave()
    if (!save) return
    const ok = downloadText(fileNameForSave(save, 'json'), saveJsonText(save))
    showToast(ok ? fill(UI_TEXT.lab.export_.downloaded, { file: fileNameForSave(save, 'json') }) : UI_TEXT.lab.export_.downloadFailed)
  }

  return (
    <main class="screen">
      <TopBar title={t.title} onBack={() => (step === 'names' ? goBack() : setStep(step === 'meet' ? 'monster' : step === 'monster' ? 'difficulty' : 'names'))} />

      {step === 'names' && (
        <>
          <Field label={t.breederName}>
            <input class="input" value={breeder} maxLength={24} autoCapitalize="words" onInput={(e) => setBreeder((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          <Field label={t.ranchName} hint={t.namesHint}>
            <input class="input" value={ranch} maxLength={24} autoCapitalize="words" onInput={(e) => setRanch((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" onClick={() => setStep('difficulty')}>
              {t.next}
            </button>
          </div>
        </>
      )}

      {step === 'difficulty' && (
        <>
          <p class="field__label">{t.difficulty}</p>
          <div class="list" role="radiogroup" aria-label={t.difficulty}>
            {DIFFICULTIES.map((d) => (
              <button key={d} type="button" role="radio" aria-checked={difficulty === d} class={`choice ${difficulty === d ? 'choice--on' : ''}`} onClick={() => setDifficulty(d)}>
                <span class="choice__name">{DIFFICULTY_LABELS[d].name}</span>
                <span class="choice__blurb">{DIFFICULTY_LABELS[d].blurb}</span>
              </button>
            ))}
          </div>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" onClick={() => setStep('monster')}>
              {t.next}
            </button>
          </div>
        </>
      )}

      {step === 'monster' && (
        <>
          <p class="field__label">{t.firstMonster}</p>
          <Segmented
            options={[
              { value: 'gift', label: t.modes.gift },
              { value: 'shrine', label: t.modes.shrine },
            ]}
            value={mode}
            onChange={setMode}
            label={t.firstMonster}
          />
          {mode === 'gift' && (
            <>
              <SpeakerCard speaker={UI_TEXT.ines} tone="muted">
                <p>{t.giftHint}</p>
              </SpeakerCard>
              <div class="gift" role="radiogroup" aria-label={t.modes.gift}>
                {stock.map((o) => (
                  <button key={o.breed} type="button" role="radio" aria-checked={gift === o.breed} class={`tile ${gift === o.breed ? 'tile--on' : ''}`} onClick={() => setGift(o.breed)}>
                    <MonsterPortrait breed={o.breed} size={84} label={BREED_BY_ID[o.breed].name} animate={false} />
                    <span class="tile__name">{BREED_BY_ID[o.breed].name}</span>
                    <span class="muted small">{BREED_BY_ID[o.breed].niche}</span>
                    <span class="muted small">{o.seasonal ? `${t.seasonal} · ${t.free}` : t.free}</span>
                  </button>
                ))}
              </div>
              <div class="spacer" />
              <div class="actionbar">
                <button type="button" class="btn btn--primary" onClick={() => meet(marketMonster(gift, newId()))}>
                  {t.next}
                </button>
              </div>
            </>
          )}
          {mode === 'shrine' && (
            <>
              <Field label={t.phrase} hint={t.shrineHint}>
                <input class="input" value={phrase} maxLength={200} autoCapitalize="words" onInput={(e) => setPhrase((e.currentTarget as HTMLInputElement).value)} />
              </Field>
              <Field label={t.artist}>
                <input class="input" value={artist} maxLength={200} onInput={(e) => setArtist((e.currentTarget as HTMLInputElement).value)} />
              </Field>
              {roll ? (
                roll.mainLocked ? (
                  <SpeakerCard speaker={UI_TEXT.wren}>
                    <p>{WREN.shrineSleeping}</p>
                    <p class="muted small">{WREN.shrineTeaser}</p>
                  </SpeakerCard>
                ) : (
                  <div class="preview">
                    <MonsterPortrait monster={monsterFromRoll(roll, 'preview')} size={120} label={roll.variantName} expression="neutral" />
                    <div class="preview__info">
                      <span class="preview__name">{roll.variantName}</span>
                      <span class="muted small">{WREN.shrineHums}</span>
                    </div>
                  </div>
                )
              ) : (
                <p class="empty">{t.stoneWaits}</p>
              )}
              <div class="spacer" />
              <div class="actionbar">
                <button type="button" class="btn btn--primary" disabled={!roll || roll.mainLocked} onClick={() => roll && meet(monsterFromRoll(roll, newId()))}>
                  {t.awaken}
                </button>
              </div>
            </>
          )}
        </>
      )}

      {step === 'meet' && monster && (
        <>
          <h2 class="heading center">{fill(t.meet, { name: name || monster.name })}</h2>
          <div class="farewell__art">
            <MonsterPortrait monster={{ ...monster, name }} size={200} expression="happy" />
          </div>
          <p class="center muted">{variantNameOf(monster)}</p>
          <SpeakerCard speaker={UI_TEXT.wren} tone="muted">
            <p>{mode === 'gift' ? WREN.marketGift : WREN.shrineHums}</p>
          </SpeakerCard>
          <Field label={t.nameLabel}>
            <input class="input" value={name} maxLength={RANGES.nameLength.max} autoCapitalize="words" onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          <div class="spacer" />
          <div class="actionbar actionbar--stack">
            <button type="button" class="btn btn--primary" onClick={() => begin(false)}>
              {t.begin}
            </button>
            <div class="actions__row">
              <button type="button" class="btn btn--half" onClick={() => begin(true)}>
                ✏️ {t.editFirst}
              </button>
              <button type="button" class="btn btn--half btn--ghost" onClick={() => setStep('monster')}>
                {t.chooseAnother}
              </button>
            </div>
          </div>
        </>
      )}

      <Sheet open={askReplace && existing !== null} onClose={goBack}>
        <p class="sheet__text">{existing ? fill(t.replaceAsk, { ranch: existing.breeder.ranchName, year: dateOf(existing.week).year }) : ''}</p>
        <div class="sheet__actions">
          <button type="button" class="btn btn--primary" onClick={exportCurrent}>
            {t.exportFirst}
          </button>
          <button type="button" class="btn btn--danger" onClick={() => setAskReplace(false)}>
            {t.replace}
          </button>
          <button type="button" class="btn" onClick={goBack}>
            {t.keepPlaying}
          </button>
        </div>
      </Sheet>
      <p class="muted small center">{fill(UI_TEXT.ranch.date, { month: MONTH_NAMES[NEW_GAME_MONTH - 1], week: 1 })}</p>
    </main>
  )
}
