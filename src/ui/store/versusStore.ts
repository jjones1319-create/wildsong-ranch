import { signal } from '@preact/signals'
import type { Picked } from '../components/MonsterPicker.tsx'

/** Versus picks live here (not in the lazy-loaded screen), so the ranch's Battle button can preselect side A. */
export const versusSideA = signal<Picked | null>(null)
/** The picks survive a trip to the battle screen and back, so Rematch and Done land on the same setup. */
export const versusSideB = signal<Picked | null>(null)
