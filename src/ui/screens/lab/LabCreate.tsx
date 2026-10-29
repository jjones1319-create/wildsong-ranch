import { useMemo, useState } from 'preact/hooks'
import { blankMonster, DEFAULT_LIKES } from '../../../core/lab.ts'
import { createMonster } from '../../../core/monster.ts'
import { monsterFromRoll, rollShrine } from '../../../core/shrine.ts'
import { BREED_BY_ID, STARTING_UNLOCKED } from '../../../data/breeds.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { BREED_IDS, type BreedId } from '../../../data/types.ts'
import { Confirm, Field, Segmented, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { newId } from '../../lib/ids.ts'
import { navigate } from '../../router.ts'
import { startNew } from '../../store/labStore.ts'

type Mode = 'breed' | 'phrase' | 'blank'

export function isDiscovered(id: BreedId): boolean {
  return STARTING_UNLOCKED.includes(id)
}

/** A grid of breed tiles with portraits. Locked breeds ask "Not discovered yet. Use anyway?" (§19). */
export function BreedTiles({ value, onChange, label }: { value: BreedId; onChange: (id: BreedId) => void; label: string }) {
  const [asking, setAsking] = useState<BreedId | null>(null)
  const pick = (id: BreedId) => {
    if (id === value || isDiscovered(id)) onChange(id)
    else setAsking(id)
  }
  return (
    <div class="field">
      <span class="field__label">{label}</span>
      <div class="tiles" role="radiogroup" aria-label={label}>
        {BREED_IDS.map((id) => (
          <button key={id} type="button" role="radio" aria-checked={id === value} class={`tile ${id === value ? 'tile--on' : ''} ${isDiscovered(id) ? '' : 'tile--locked'}`} onClick={() => pick(id)} title={isDiscovered(id) ? undefined : UI_TEXT.lab.lockedTile}>
            <MonsterPortrait breed={id} size={56} label={BREED_BY_ID[id].name} animate={false} />
            <span class="tile__name">
              {isDiscovered(id) ? '' : '🔒 '}
              {BREED_BY_ID[id].name}
            </span>
          </button>
        ))}
      </div>
      <Confirm
        open={asking !== null}
        text={fill(UI_TEXT.lab.lockedAsk, { name: asking ? BREED_BY_ID[asking].name : '' })}
        confirmLabel={UI_TEXT.lab.useAnyway}
        cancelLabel={UI_TEXT.lab.keepSurprise}
        onConfirm={() => {
          if (asking) onChange(asking)
          setAsking(null)
        }}
        onCancel={() => setAsking(null)}
      />
    </div>
  )
}

/** §19 Create: from a breed, from a song (the Shrine's own roll), or from the blank template. Opens the Editor. */
export function LabCreateScreen() {
  const t = UI_TEXT.lab.create_
  const [mode, setMode] = useState<Mode>('breed')
  const [breed, setBreed] = useState<BreedId>('puddlepup')
  const [phrase, setPhrase] = useState('')
  const [artist, setArtist] = useState('')

  const roll = useMemo(() => (phrase.trim() ? rollShrine(phrase, artist, BREED_IDS) : null), [phrase, artist])
  const breedInfo = BREED_BY_ID[breed]

  const begin = () => {
    if (mode === 'breed') startNew(createMonster({ id: newId(), mainBreed: breed, likes: DEFAULT_LIKES }))
    else if (mode === 'phrase' && roll) startNew(monsterFromRoll(roll, newId()))
    else if (mode === 'blank') startNew(blankMonster(newId(), t.blankName))
    else return
    navigate('labEdit')
  }

  const canBegin = mode !== 'phrase' || roll !== null

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <Segmented
        options={[
          { value: 'breed', label: t.modes.breed },
          { value: 'phrase', label: t.modes.phrase },
          { value: 'blank', label: t.modes.blank },
        ]}
        value={mode}
        onChange={setMode}
      />

      {mode === 'breed' && (
        <>
          <div class="preview">
            <MonsterPortrait breed={breed} size={120} label={breedInfo.name} />
            <div class="preview__info">
              <span class="preview__name">{breedInfo.name}</span>
              <span class="muted small">{breedInfo.niche}</span>
            </div>
          </div>
          <BreedTiles value={breed} onChange={setBreed} label={t.breed} />
        </>
      )}

      {mode === 'phrase' && (
        <>
          <Field label={t.phrase} hint={t.phraseHint}>
            <input class="input" value={phrase} maxLength={200} autoCapitalize="words" onInput={(e) => setPhrase((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          <Field label={t.artist}>
            <input class="input" value={artist} maxLength={200} onInput={(e) => setArtist((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          {roll ? (
            <div class="preview">
              <MonsterPortrait breed={roll.mainBreed} size={120} label={roll.variantName} />
              <div class="preview__info">
                <span class="preview__name">{roll.variantName}</span>
                <span class="muted small">
                  {t.suggested}: {roll.suggestedName}
                </span>
                {!isDiscovered(roll.mainBreed) && <span class="muted small">🔒 {UI_TEXT.lab.lockedTile}</span>}
              </div>
            </div>
          ) : (
            <p class="empty">{t.stoneWaits}</p>
          )}
        </>
      )}

      {mode === 'blank' && (
        <div class="preview">
          <MonsterPortrait breed="puddlepup" size={120} label={t.blankName} />
          <div class="preview__info">
            <span class="preview__name">{t.blankName}</span>
            <span class="muted small">{t.blankHint}</span>
          </div>
        </div>
      )}

      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" disabled={!canBegin} onClick={begin}>
          {t.start}
        </button>
      </div>
    </main>
  )
}
