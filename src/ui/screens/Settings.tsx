import { UI_TEXT } from '../../data/text/ui.ts'
import { Toggle, TopBar } from '../components/Controls.tsx'
import { librarySource, persisted, settings, updateSettings } from '../store/appStore.ts'

/** The M2 slice of Settings (§21): the edited badge, reduced motion and the storage status. The rest comes with M3. */
export function SettingsScreen() {
  const t = UI_TEXT.settings
  const s = settings.value
  const p = persisted.value
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <section class="card">
        <Toggle label={t.editedBadge} hint={t.editedBadgeHint} checked={s.showEditedBadge} onChange={(v) => void updateSettings({ showEditedBadge: v })} />
        <Toggle label={t.reduceMotion} hint={t.reduceMotionHint} checked={s.reduceMotion} onChange={(v) => void updateSettings({ reduceMotion: v })} />
      </section>
      <section class="card">
        <p class="field__label">{t.storage}</p>
        <p class={p === false ? 'notice' : 'muted small'}>{p === true ? t.persisted : p === false ? t.notPersisted : t.unknown}</p>
        <p class="muted small">{t.librarySource[librarySource.value]}</p>
      </section>
      <section class="card card--muted">
        <p class="speaker">{UI_TEXT.wren}</p>
        <p>{t.more}</p>
      </section>
      <div class="spacer" />
      <p class="version version--center">
        {UI_TEXT.versionPrefix}
        {__APP_VERSION__}
      </p>
    </main>
  )
}
