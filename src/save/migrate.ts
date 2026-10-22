/**
 * Save migrations. Every schema change bumps SAVE_VERSION and adds one step here, with a test.
 * A migration takes the previous version's raw object and returns the next version's raw object.
 */
export const SAVE_VERSION = 1

type RawSave = Record<string, unknown>

type Migration = (raw: RawSave) => RawSave

/** Keyed by the version it upgrades FROM. Version 0 means "no version field" (pre-release saves). */
const MIGRATIONS: Record<number, Migration> = {
  0: (raw) => ({ ...raw, schemaVersion: 1 }),
}

export function isRawSave(raw: unknown): raw is RawSave {
  return typeof raw === 'object' && raw !== null && !Array.isArray(raw)
}

/** Brings any older save up to SAVE_VERSION. Unknown input is returned untouched for the validator to reject. */
export function migrate(raw: unknown): unknown {
  if (!isRawSave(raw)) return raw
  let current: RawSave = { ...raw }
  let version = typeof current.schemaVersion === 'number' && Number.isFinite(current.schemaVersion) ? Math.floor(current.schemaVersion) : 0
  if (version > SAVE_VERSION) return current
  while (version < SAVE_VERSION) {
    const step = MIGRATIONS[version]
    if (!step) break
    current = step(current)
    version += 1
  }
  return current
}
