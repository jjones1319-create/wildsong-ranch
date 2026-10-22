/** Fresh monster ids for the UI layer. Core never makes ids itself (it has no randomness of its own). */
export function newId(): string {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  } catch {
    /* fall through */
  }
  const rand = Math.floor(Math.random() * 0xffffffff).toString(16).padStart(8, '0')
  return `m-${Date.now().toString(36)}-${rand}`
}
