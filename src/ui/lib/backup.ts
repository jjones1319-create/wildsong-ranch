import { UI_TEXT } from '../../data/text/ui.ts'
import { fill } from '../../data/text/format.ts'
import { fileNameForSave, saveJsonText, saveShareText } from '../../save/exportImport.ts'
import { settings, showToast, updateSettings } from '../store/appStore.ts'
import { currentSave, game } from '../store/gameStore.ts'
import { now } from './clock.ts'
import { canShare, downloadText, shareText } from './files.ts'

/** §20: one place that exports the ranch (Settings and the reminder card both use it) and stamps the backup time. */

export function stampBackup(): void {
  void updateSettings({ lastBackupAt: now(), lastBackupWeek: game.value?.week ?? null, backupSnoozedAt: 0 })
}

export function snoozeBackup(): void {
  void updateSettings({ backupSnoozedAt: now() })
}

export function downloadBackup(): boolean {
  const save = currentSave()
  if (!save) {
    showToast(UI_TEXT.settings.noRanch)
    return false
  }
  const name = fileNameForSave(save, 'json')
  const ok = downloadText(name, saveJsonText(save))
  showToast(ok ? fill(UI_TEXT.lab.export_.downloaded, { file: name }) : UI_TEXT.lab.export_.downloadFailed)
  if (ok) stampBackup()
  return ok
}

export async function shareBackup(): Promise<boolean> {
  const save = currentSave()
  if (!save) {
    showToast(UI_TEXT.settings.noRanch)
    return false
  }
  const r = await shareText(fileNameForSave(save, 'txt'), saveShareText(save), UI_TEXT.title)
  if (r === 'shared') {
    showToast(UI_TEXT.lab.export_.shared)
    stampBackup()
    return true
  }
  if (r !== 'cancelled') showToast(UI_TEXT.lab.export_.shareFailed)
  return false
}

/** The reminder card's one button: share where phones can, download elsewhere. */
export function backupNow(): Promise<boolean> {
  return canShare() ? shareBackup() : Promise.resolve(downloadBackup())
}

export function backupMarks() {
  const s = settings.value
  return { lastBackupAt: s.lastBackupAt, lastBackupWeek: s.lastBackupWeek, backupSnoozedAt: s.backupSnoozedAt }
}
