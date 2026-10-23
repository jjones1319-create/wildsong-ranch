import { describe, expect, it } from 'vitest'
import { SAVES } from '../data/tuning.ts'
import { backupDue, DAY_MS } from './backup.ts'

const T0 = 1_700_000_000_000

describe('backup reminders (§20)', () => {
  it('a fresh ranch is quiet until 7 real days or 8 in-game weeks have passed', () => {
    const fresh = { lastBackupAt: 0, lastBackupWeek: null, backupSnoozedAt: 0 }
    expect(backupDue(fresh, T0, 0, T0)).toBe(false)
    expect(backupDue(fresh, T0 + 6 * DAY_MS, 3, T0)).toBe(false)
    expect(backupDue(fresh, T0 + 7 * DAY_MS, 3, T0)).toBe(true)
    // An old ranch that has never been backed up is not nagged on its first launch: the day rule decides.
    expect(backupDue(fresh, T0 + DAY_MS, SAVES.backupReminderWeeks * 10, T0)).toBe(false)
  })

  it('an export resets both counters', () => {
    const marks = { lastBackupAt: T0, lastBackupWeek: 20, backupSnoozedAt: 0 }
    expect(backupDue(marks, T0 + 2 * DAY_MS, 24, 0)).toBe(false)
    expect(backupDue(marks, T0 + 2 * DAY_MS, 28, 0)).toBe(true)
    expect(backupDue(marks, T0 + 8 * DAY_MS, 21, 0)).toBe(true)
  })

  it('Later snoozes the card for a reminder period, then it returns', () => {
    const marks = { lastBackupAt: T0, lastBackupWeek: 0, backupSnoozedAt: T0 + 8 * DAY_MS }
    expect(backupDue(marks, T0 + 9 * DAY_MS, 30, 0)).toBe(false)
    expect(backupDue(marks, T0 + 15 * DAY_MS, 30, 0)).toBe(true)
  })
})
