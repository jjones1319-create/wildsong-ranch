/** Real-world time for timestamps in saves and the edit history. Core never calls this. */
export function now(): number {
  return Date.now()
}

/** "22 Oct 2026, 14:05" in the phone's own locale. */
export function formatWhen(ms: number): string {
  if (!ms) return ''
  try {
    return new Date(ms).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return new Date(ms).toISOString()
  }
}
