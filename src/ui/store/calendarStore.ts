import { signal } from '@preact/signals'
import { togglePin } from '../../core/calendarView.ts'
import { commit, game } from './gameStore.ts'

/**
 * §3 the Calendar screen's state for this session: the view, the month being browsed and the two filters.
 * The ★ reminders themselves live in the save (`calendarPins`).
 */
export type CalendarViewKind = 'agenda' | 'month' | 'year'

export const calendarView = signal<CalendarViewKind>('agenda')
/** The first week (absolute) of the month being browsed; null means "this month". */
export const calendarCursor = signal<number | null>(null)
export const onlyEnterable = signal(true)
export const showExpeditions = signal(true)

/** ★ on or off for an event or expedition occurrence. */
export function toggleCalendarPin(key: string): void {
  const g = game.value
  if (!g) return
  const next = togglePin(g, key)
  if (next !== g) commit(next)
}
