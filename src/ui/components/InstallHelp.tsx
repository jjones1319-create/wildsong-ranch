import { useEffect, useState } from 'preact/hooks'
import { INSTALL } from '../../data/tuning.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { DAY_MS } from '../../save/backup.ts'
import { now } from '../lib/clock.ts'
import { canPromptInstall, currentPlatform, isStandalone, onInstallPromptChange, promptInstall } from '../lib/platform.ts'
import { settings, showToast, updateSettings } from '../store/appStore.ts'
import { Sheet } from './Controls.tsx'

/** Should the title show the install card? Not when installed, and not for two weeks after "Later". */
export function installCardDue(): boolean {
  if (isStandalone()) return false
  const at = settings.value.installHelpDismissedAt
  return at === 0 || now() - at >= INSTALL.dismissDays * DAY_MS
}

function Steps() {
  const t = UI_TEXT.install
  const platform = currentPlatform()
  const steps = platform === 'ios' ? t.ios : platform === 'android' ? t.android : t.other
  return (
    <>
      <ol class="install__steps">
        {steps.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ol>
      <p class="muted small">{t.tip}</p>
    </>
  )
}

/** The card on the title screen (§21): the native prompt on Android when Chrome offers it, else the steps. */
export function InstallCard() {
  const t = UI_TEXT.install
  const [open, setOpen] = useState(false)
  const [canPrompt, setCanPrompt] = useState(canPromptInstall())
  useEffect(() => onInstallPromptChange(() => setCanPrompt(canPromptInstall())), [])
  if (!installCardDue()) return null
  const later = () => void updateSettings({ installHelpDismissedAt: now() })
  const install = async () => {
    const r = await promptInstall()
    if (r === 'accepted') showToast(t.installed)
    else if (r === 'unavailable') setOpen(true)
  }
  return (
    <section class="card install" role="region" aria-label={t.title}>
      <p class="install__title">📲 {t.title}</p>
      <p class="muted small">{t.blurb}</p>
      <div class="row">
        {canPrompt ? (
          <button type="button" class="btn btn--primary btn--half" onClick={() => void install()}>
            {t.installNow}
          </button>
        ) : (
          <button type="button" class="btn btn--primary btn--half" onClick={() => setOpen(true)}>
            {t.showSteps}
          </button>
        )}
        <button type="button" class="btn btn--half" onClick={later}>
          {t.later}
        </button>
      </div>
      <InstallSheet open={open} onClose={() => setOpen(false)} />
    </section>
  )
}

/** The same steps as a sheet, also reachable from Settings. */
export function InstallSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = UI_TEXT.install
  return (
    <Sheet open={open} title={t.title} onClose={onClose}>
      {isStandalone() ? <p class="notice notice--ok">{UI_TEXT.settings.alreadyInstalled}</p> : <Steps />}
      <div class="sheet__actions">
        <button type="button" class="btn btn--primary" onClick={onClose}>
          {t.done}
        </button>
      </div>
    </Sheet>
  )
}
