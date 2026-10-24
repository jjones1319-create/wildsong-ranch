import { useEffect, useRef, useState } from 'preact/hooks'
import { audioReady, playSfx, unlockAudio } from '../../audio/player.ts'
import { canSwitchDifficulty } from '../../core/game.ts'
import { fill } from '../../data/text/format.ts'
import { AUTO_STYLE_LABELS, DIFFICULTY_LABELS, FX_INTENSITY_LABELS, FX_QUALITY_LABELS, SPEED_LABELS, TRANSPARENCY_LABELS } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { TEXT_SIZES, UI } from '../../data/tuning.ts'
import { AUTO_STYLES, FX_INTENSITIES, FX_QUALITY_SETTINGS, SPEEDS, TRANSPARENCY_MODES, type Difficulty } from '../../data/types.ts'
import { readImport } from '../../save/exportImport.ts'
import type { AnyValidation, AppSettings } from '../../save/schema.ts'
import { Confirm, Segmented, Sheet, Toggle, TopBar } from '../components/Controls.tsx'
import { InstallSheet } from '../components/InstallHelp.tsx'
import { downloadBackup, shareBackup } from '../lib/backup.ts'
import { formatWhen } from '../lib/clock.ts'
import { canShare, readFileText } from '../lib/files.ts'
import { isStandalone } from '../lib/platform.ts'
import { goBack } from '../router.ts'
import { librarySource, persisted, settings, showToast, updateSettings } from '../store/appStore.ts'
import { currentTier, reduceMotionNow, setFxIntensity, setFxQuality } from '../store/fxStore.ts'
import { game, loadSaveFile, sandboxAddMoney, saveSource, setDifficulty, setOnePerWeek } from '../store/gameStore.ts'
import { applyUpdate, checkForUpdate, lastCheck, needRefresh } from '../store/updateStore.ts'

const SANDBOX_MONEY = 10_000

function Volume({ label, field }: { label: string; field: 'masterVolume' | 'musicVolume' | 'sfxVolume' }) {
  const value = settings.value[field]
  return (
    <label class="volume">
      <span class="volume__label">
        {label} <span class="muted small">{value}%</span>
      </span>
      <input
        class="range"
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        aria-label={label}
        onInput={(e) => void updateSettings({ [field]: Number((e.currentTarget as HTMLInputElement).value) } as Partial<AppSettings>)}
      />
    </label>
  )
}

/** §21 Settings: play, display and sound preferences, this ranch's difficulty and item rule, backup and import, storage, updates, Sandbox. */
export function SettingsScreen() {
  const t = UI_TEXT.settings
  const s = settings.value
  const p = persisted.value
  const g = game.value
  const [importOpen, setImportOpen] = useState(false)
  const [installOpen, setInstallOpen] = useState(false)
  const [text, setText] = useState('')
  const [result, setResult] = useState<AnyValidation | null>(null)
  const [confirmMoney, setConfirmMoney] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const check = lastCheck.value

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

  const testSound = async () => {
    await unlockAudio()
    playSfx('drillGreat')
  }

  const difficultyOptions = (['Gentle', 'Standard'] as Difficulty[]).map((d) => ({ value: d, label: DIFFICULTY_LABELS[d].name }))
  const checkText = check === 'checking' ? t.checking : check === 'upToDate' ? t.upToDate : check === 'updateFound' ? t.updateFound : check === 'failed' ? t.updateFailed : null

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
        <p class="field__label small">{t.autoStyle}</p>
        <Segmented options={AUTO_STYLES.map((m) => ({ value: m, label: AUTO_STYLE_LABELS[m].name }))} value={s.autoStyle} onChange={(v) => void updateSettings({ autoStyle: v })} label={t.autoStyle} />
        <p class="field__hint">
          {AUTO_STYLE_LABELS[s.autoStyle].blurb} {t.autoStyleHint}
        </p>
        <Toggle label={t.showThinking} hint={t.showThinkingHint} checked={s.showThinking ?? s.transparency === 'lens'} onChange={(v) => void updateSettings({ showThinking: v })} />
        <Toggle label={t.leftHanded} hint={t.leftHandedHint} checked={s.leftHanded} onChange={(v) => void updateSettings({ leftHanded: v })} />
      </section>

      <section class="card">
        <p class="field__label">{t.sections.display}</p>
        <p class="field__label small">{t.textSize}</p>
        <Segmented options={TEXT_SIZES.map((n) => ({ value: String(n), label: fill(t.textSizeOption, { n }) }))} value={String(s.textSize)} onChange={(v) => void updateSettings({ textSize: Number(v) })} label={t.textSize} />
        <Toggle label={t.reduceMotion} hint={t.reduceMotionHint} checked={s.reduceMotion} onChange={(v) => void updateSettings({ reduceMotion: v })} />
        <Toggle label={t.editedBadge} hint={t.editedBadgeHint} checked={s.showEditedBadge} onChange={(v) => void updateSettings({ showEditedBadge: v })} />
      </section>

      <section class="card">
        <p class="field__label">{t.sections.graphics}</p>
        <p class="field__label small">{t.fxQuality}</p>
        <Segmented options={FX_QUALITY_SETTINGS.map((q) => ({ value: q, label: FX_QUALITY_LABELS[q].name }))} value={s.fxQuality} onChange={setFxQuality} label={t.fxQuality} />
        <p class="field__hint">
          {FX_QUALITY_LABELS[s.fxQuality].blurb} {s.fxQuality === 'auto' && s.fxAutoTier ? fill(t.fxQualityAuto, { tier: FX_QUALITY_LABELS[currentTier()].name }) : ''}
        </p>
        <p class="field__label small">{t.fxIntensity}</p>
        <Segmented options={FX_INTENSITIES.map((i) => ({ value: i, label: FX_INTENSITY_LABELS[i].name }))} value={s.fxIntensity} onChange={setFxIntensity} label={t.fxIntensity} />
        <p class="field__hint">{reduceMotionNow() ? t.fxReducedNote : FX_INTENSITY_LABELS[s.fxIntensity].blurb}</p>
        <p class="field__hint">{t.fxLabLink}</p>
      </section>

      <section class="card">
        <p class="field__label">{t.sections.audio}</p>
        <Toggle label={t.sound} checked={s.sound} onChange={(v) => void updateSettings({ sound: v })} />
        <Toggle label={t.music} checked={s.music} onChange={(v) => void updateSettings({ music: v })} />
        <Toggle label={t.haptics} checked={s.haptics} onChange={(v) => void updateSettings({ haptics: v })} />
        <Volume label={t.masterVolume} field="masterVolume" />
        <Volume label={t.musicVolume} field="musicVolume" />
        <Volume label={t.sfxVolume} field="sfxVolume" />
        <button type="button" class="btn btn--small" data-silent onClick={() => void testSound()}>
          🔔 {t.testSound}
        </button>
        <p class="field__hint">{audioReady() ? t.audioHint : t.audioLocked}</p>
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
        <p class="muted small">{s.lastBackupAt ? fill(UI_TEXT.backup.lastBackup, { when: formatWhen(s.lastBackupAt) }) : UI_TEXT.backup.never}</p>
        <div class="btn-grid">
          <button type="button" class="btn" disabled={!g} onClick={downloadBackup}>
            {t.exportJson}
          </button>
          {canShare() && (
            <button type="button" class="btn" disabled={!g} onClick={() => void shareBackup()}>
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
        <p class="field__label">{t.sections.updates}</p>
        <div class="btn-grid">
          {needRefresh.value ? (
            <button type="button" class="btn btn--primary" onClick={() => void applyUpdate()}>
              {t.restart}
            </button>
          ) : (
            <button type="button" class="btn" disabled={check === 'checking'} onClick={() => void checkForUpdate()}>
              {t.checkUpdates}
            </button>
          )}
          <button type="button" class="btn" onClick={() => setInstallOpen(true)}>
            {t.installHelp}
          </button>
        </div>
        {checkText && <p class={check === 'failed' ? 'notice' : 'muted small'}>{checkText}</p>}
        {isStandalone() && <p class="muted small">{t.alreadyInstalled}</p>}
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

      <InstallSheet open={installOpen} onClose={() => setInstallOpen(false)} />

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
