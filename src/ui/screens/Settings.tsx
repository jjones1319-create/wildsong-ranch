import { useEffect, useRef, useState } from 'preact/hooks'
import { canSwitchDifficulty } from '../../core/game.ts'
import { fill } from '../../data/text/format.ts'
import { DIFFICULTY_LABELS, SPEED_LABELS, TRANSPARENCY_LABELS } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { TEXT_SIZES, UI } from '../../data/tuning.ts'
import { SPEEDS, TRANSPARENCY_MODES, type Difficulty } from '../../data/types.ts'
import { fileNameForSave, readImport, saveJsonText, saveShareText } from '../../save/exportImport.ts'
import type { AnyValidation } from '../../save/schema.ts'
import { Confirm, Segmented, Sheet, Toggle, TopBar } from '../components/Controls.tsx'
import { canShare, downloadText, readFileText, shareText } from '../lib/files.ts'
import { goBack } from '../router.ts'
import { librarySource, persisted, settings, showToast, updateSettings } from '../store/appStore.ts'
import { currentSave, game, loadSaveFile, sandboxAddMoney, saveSource, setDifficulty, setOnePerWeek } from '../store/gameStore.ts'

const SANDBOX_MONEY = 10_000

/** §21 Settings: play, display and sound preferences, this ranch's difficulty and item rule, backup and import, storage, Sandbox. */
export function SettingsScreen() {
  const t = UI_TEXT.settings
  const s = settings.value
  const p = persisted.value
  const g = game.value
  const [importOpen, setImportOpen] = useState(false)
  const [text, setText] = useState('')
  const [result, setResult] = useState<AnyValidation | null>(null)
  const [confirmMoney, setConfirmMoney] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!importOpen) return
    let alive = true
    const timer = setTimeout(() => {
      void readImport(text).then((r) => {
        if (alive) setResult(text.trim() ? r : null)
      })
    }, UI.importDebounceMs)
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [text, importOpen])

  const exportJson = () => {
    const save = currentSave()
    if (!save) return showToast(t.noRanch)
    const name = fileNameForSave(save, 'json')
    showToast(downloadText(name, saveJsonText(save)) ? fill(UI_TEXT.lab.export_.downloaded, { file: name }) : UI_TEXT.lab.export_.downloadFailed)
  }

  const share = async () => {
    const save = currentSave()
    if (!save) return showToast(t.noRanch)
    const r = await shareText(fileNameForSave(save, 'txt'), saveShareText(save), UI_TEXT.title)
    if (r === 'shared') showToast(UI_TEXT.lab.export_.shared)
    else if (r !== 'cancelled') showToast(UI_TEXT.lab.export_.shareFailed)
  }

  const pickFile = async (file: File | undefined) => {
    if (!file) return
    const content = await readFileText(file)
    if (content === null) showToast(UI_TEXT.errors.fileUnreadable)
    else setText(content)
  }

  const doImport = () => {
    if (!result?.ok || result.kind !== 'save') return
    loadSaveFile(result.save)
    setImportOpen(false)
    setText('')
    showToast(fill(t.imported, { ranch: result.save.game.breeder.ranchName }))
    goBack()
  }

  const difficultyOptions = (['Gentle', 'Standard'] as Difficulty[]).map((d) => ({ value: d, label: DIFFICULTY_LABELS[d].name }))

  return (
    <main class="screen">
      <TopBar title={t.title} />

      <section class="card">
        <p class="field__label">{t.sections.play}</p>
        <p class="field__label small">{t.transparency}</p>
        <Segmented options={TRANSPARENCY_MODES.map((m) => ({ value: m, label: TRANSPARENCY_LABELS[m].name }))} value={s.transparency} onChange={(v) => void updateSettings({ transparency: v })} label={t.transparency} />
        <p class="field__hint">{TRANSPARENCY_LABELS[s.transparency].blurb}</p>
        <p class="field__label small">{t.speed}</p>
        <Segmented options={SPEEDS.map((v) => ({ value: v, label: SPEED_LABELS[v] }))} value={s.speed} onChange={(v) => void updateSettings({ speed: v })} label={t.speed} />
        <Toggle label={t.assist} hint={t.assistHint} checked={s.assist} onChange={(v) => void updateSettings({ assist: v })} />
      </section>

      <section class="card">
        <p class="field__label">{t.sections.display}</p>
        <p class="field__label small">{t.textSize}</p>
        <Segmented options={TEXT_SIZES.map((n) => ({ value: String(n), label: fill(t.textSizeOption, { n }) }))} value={String(s.textSize)} onChange={(v) => void updateSettings({ textSize: Number(v) })} label={t.textSize} />
        <Toggle label={t.reduceMotion} hint={t.reduceMotionHint} checked={s.reduceMotion} onChange={(v) => void updateSettings({ reduceMotion: v })} />
        <Toggle label={t.editedBadge} hint={t.editedBadgeHint} checked={s.showEditedBadge} onChange={(v) => void updateSettings({ showEditedBadge: v })} />
      </section>

      <section class="card">
        <p class="field__label">{t.sections.audio}</p>
        <Toggle label={t.sound} checked={s.sound} onChange={(v) => void updateSettings({ sound: v })} />
        <Toggle label={t.music} checked={s.music} onChange={(v) => void updateSettings({ music: v })} />
        <Toggle label={t.haptics} checked={s.haptics} onChange={(v) => void updateSettings({ haptics: v })} />
        <p class="field__hint">{t.audioHint}</p>
      </section>

      <section class="card">
        <p class="field__label">{t.sections.ranch}</p>
        <p class="field__label small">{t.difficulty}</p>
        {!g && <p class="muted small">{t.difficultyNone}</p>}
        {g && g.difficulty === 'Classic' && <p class="muted small">{t.difficultyLocked}</p>}
        {g && g.difficulty !== 'Classic' && (
          <Segmented
            options={difficultyOptions}
            value={g.difficulty as 'Gentle' | 'Standard'}
            onChange={(v) => {
              if (canSwitchDifficulty(g, v) && setDifficulty(v)) showToast(fill(t.difficultyChanged, { name: DIFFICULTY_LABELS[v].name }))
            }}
            label={t.difficulty}
          />
        )}
        {g && <Toggle label={t.onePerWeek} hint={t.onePerWeekHint} checked={g.settings.onePerWeek} onChange={setOnePerWeek} />}
      </section>

      <section class="card">
        <p class="field__label">{t.sections.backup}</p>
        <div class="btn-grid">
          <button type="button" class="btn" disabled={!g} onClick={exportJson}>
            {t.exportJson}
          </button>
          {canShare() && (
            <button type="button" class="btn" disabled={!g} onClick={() => void share()}>
              {t.shareTxt}
            </button>
          )}
          <button type="button" class="btn" onClick={() => setImportOpen(true)}>
            {t.importSave}
          </button>
        </div>
      </section>

      <section class="card">
        <p class="field__label">{t.sections.storage}</p>
        <p class={p === false ? 'notice' : 'muted small'}>{p === true ? t.persisted : p === false ? t.notPersisted : t.unknown}</p>
        <p class="muted small">{t.saveSource[saveSource.value]}</p>
        <p class="muted small">{t.librarySource[librarySource.value]}</p>
      </section>

      <section class="card">
        <p class="field__label">{t.sections.sandbox}</p>
        <p class="muted small">{t.sandboxHint}</p>
        {g?.sandbox && <p class="muted small">{t.sandboxOn}</p>}
        <button type="button" class="btn" disabled={!g} onClick={() => setConfirmMoney(true)}>
          {t.addMoney}
        </button>
      </section>

      <div class="spacer" />
      <p class="version version--center">
        {UI_TEXT.versionPrefix}
        {__APP_VERSION__}
      </p>

      <Sheet open={importOpen} title={t.importTitle} onClose={() => setImportOpen(false)}>
        <p class="muted small">{t.importHint}</p>
        <textarea class="textarea" value={text} rows={4} spellcheck={false} autoCapitalize="off" onInput={(e) => setText((e.currentTarget as HTMLTextAreaElement).value)} />
        <button type="button" class="btn" onClick={() => fileRef.current?.click()}>
          {UI_TEXT.lab.import_.pickFile}
        </button>
        <input ref={fileRef} class="file-input" type="file" accept=".json,.txt,application/json,text/plain" onChange={(e) => void pickFile((e.currentTarget as HTMLInputElement).files?.[0])} />
        {result && !result.ok && <p class="notice">{result.error}</p>}
        {result?.ok && result.kind !== 'save' && <p class="notice">{t.importNotSave}</p>}
        {result?.ok && result.kind === 'save' && (
          <p class="notice notice--ok">
            {fill(UI_TEXT.menu.continueInfo, {
              breeder: result.save.game.breeder.name,
              ranch: result.save.game.breeder.ranchName,
              year: Math.floor(result.save.game.week / 48) + 1,
              month: '',
            })}
          </p>
        )}
        <div class="sheet__actions">
          <button type="button" class="btn btn--danger" disabled={!(result?.ok && result.kind === 'save')} onClick={doImport}>
            {t.importReplace}
          </button>
          <button type="button" class="btn" onClick={() => setImportOpen(false)}>
            {UI_TEXT.lab.actions.cancel}
          </button>
        </div>
      </Sheet>
      <Confirm
        open={confirmMoney}
        text={t.addMoney}
        confirmLabel={t.addMoney}
        onConfirm={() => {
          setConfirmMoney(false)
          sandboxAddMoney(SANDBOX_MONEY)
          showToast(t.addedMoney)
        }}
        onCancel={() => setConfirmMoney(false)}
      />
    </main>
  )
}
