import { SAVES } from '../data/tuning.ts'

/**
 * GAME_DESIGN §20 backup reminders: every 7 real days or 8 in-game weeks since the last export. With no
 * export ever, the real-day rule counts from the first save on this phone (the week rule needs a stamp
 * to count from, so it waits for the first backup). "Later" snoozes the card for a full reminder period.
 * Pure, so the rule is tested without a clock.
 */

export interface BackupMarks {
  /** When the last export or share happened (ms since the epoch; 0 = never). */
  lastBackupAt: number
  /** The in-game week of that export, or null. */
  lastBackupWeek: number | null
  /** When "Later" was last tapped (0 = never). */
  backupSnoozedAt: number
}

export const DAY_MS = 24 * 60 * 60 * 1000

export function backupDue(marks: BackupMarks, now: number, week: number, firstSaveAt: number): boolean {
  if (marks.backupSnoozedAt > 0 && now - marks.backupSnoozedAt < SAVES.backupReminderDays * DAY_MS) return false
  const since = marks.lastBackupAt > 0 ? marks.lastBackupAt : firstSaveAt
  if (since > 0 && now - since >= SAVES.backupReminderDays * DAY_MS) return true
  if (marks.lastBackupWeek !== null && week - marks.lastBackupWeek >= SAVES.backupReminderWeeks) return true
  return false
}
