import { fill } from '../../data/text/format.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { backupDue } from '../../save/backup.ts'
import { backupMarks, backupNow, snoozeBackup } from '../lib/backup.ts'
import { now } from '../lib/clock.ts'
import { settings } from '../store/appStore.ts'
import { game } from '../store/gameStore.ts'

/** §20 the backup reminder on the quiet ranch: Save a backup (share or download) or Later. */
export function BackupCard() {
  const g = game.value
  const t = UI_TEXT.backup
  if (!g?.monster || !backupDue(backupMarks(), now(), g.week, settings.value.backupBaselineAt)) return null
  return (
    <section class="card backup" role="status">
      <p class="speaker">{UI_TEXT.wren}</p>
      <p class="backup__title">💾 {t.title}</p>
      <p class="small">{fill(t.blurb, { name: g.monster.name })}</p>
      <div class="row">
        <button type="button" class="btn btn--primary btn--half" onClick={() => void backupNow()}>
          {t.exportNow}
        </button>
        <button type="button" class="btn btn--half" onClick={snoozeBackup}>
          {t.later}
        </button>
      </div>
    </section>
  )
}
