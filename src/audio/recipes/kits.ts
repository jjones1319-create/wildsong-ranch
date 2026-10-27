/**
 * SOUND_UPGRADE §6.4: a kit maps the percussion roles a battle song writes (low, mid, high, shaker, accent)
 * to instruments, so an arrangement can swap the whole kit. Pure data.
 */
import type { InstrumentId } from './instruments.ts'

export const KIT_IDS = ['meadow', 'festival', 'harvest', 'frost', 'ceremony', 'knockout', 'wild'] as const
export type KitId = (typeof KIT_IDS)[number]

export const PERC_ROLES = ['low', 'mid', 'high', 'shaker', 'accent'] as const
export type PercRole = (typeof PERC_ROLES)[number]

export type Kit = Record<PercRole, InstrumentId | null>

export const KITS: Record<KitId, Kit> = {
  meadow: { low: 'frame-drum', mid: null, high: null, shaker: 'shaker', accent: 'tambourine' },
  festival: { low: 'cajon', mid: 'bongos', high: null, shaker: 'shaker', accent: 'claps' },
  harvest: { low: 'frame-drum', mid: 'darbuka', high: 'woodblock', shaker: null, accent: 'tambourine' },
  frost: { low: 'timpani', mid: null, high: 'sleigh-bells', shaker: null, accent: 'finger-cymbals' },
  ceremony: { low: 'timpani', mid: 'bass-drum', high: 'triangle', shaker: null, accent: 'cymbal-swell' },
  knockout: { low: 'cajon', mid: 'darbuka', high: 'claves', shaker: null, accent: 'claps' },
  wild: { low: 'frame-drum', mid: 'darbuka', high: null, shaker: 'shaker', accent: 'bass-drum' },
}

export function isKitId(id: string): id is KitId {
  return (KIT_IDS as readonly string[]).includes(id)
}
