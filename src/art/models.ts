import type { BreedId } from '../data/types.ts'
import { formForStage } from './monster/render.ts'

/**
 * Art 2.0 (ART_2_PLAN §3.1, §3.3): which breeds have a Blender-built model, and which look a monster uses.
 * This file lives in the main chunk (never under src/art3d/, which imports three), so the UI can decide
 * Classic vs 3D without loading the 3D code.
 */

export type LookId = 'puddlepup'

export interface ModelLook {
  /** Under the base URL. */
  file: string
  meta: string
  /** Arena units for one metre of the model (a Puddlepup stands about 1 m tall in Blender). */
  unitsPerMetre: number
  /** Secret variants (CONTENT §12) that have their texture set inside this look's file. */
  variants: readonly string[]
}

export const MODEL_LOOKS: Record<LookId, ModelLook> = {
  puddlepup: { file: 'models/monsters/puddlepup.glb', meta: 'models/monsters/puddlepup.json', unitsPerMetre: 150, variants: ['songheart-puddlepup'] },
}

/** Breeds with a model: the young look, and the grown one for breeds with two forms. */
export const MODELS: Partial<Record<BreedId, { young: LookId; grown?: LookId }>> = {
  puddlepup: { young: 'puddlepup' },
}

export interface LookRef {
  look: LookId
  /** The secret variant to show, or null for the breed's own look. */
  variant: string | null
}

/** The look a monster of this breed, variant and stage uses, or null when it has to show Classic. */
export function lookFor(breed: BreedId, variantId: string | null, stage: number): LookRef | null {
  const m = MODELS[breed]
  if (!m) return null
  const look = formForStage(breed, stage) === 'grown' && m.grown ? m.grown : m.young
  if (variantId) {
    if (!MODEL_LOOKS[look].variants.includes(variantId)) return null
    return { look, variant: variantId }
  }
  return { look, variant: null }
}

export function hasModel(breed: BreedId): boolean {
  return MODELS[breed] !== undefined
}

/** A stable id for a (look, variant) pair: file names of build-time portraits and cache keys. */
export function lookKey(ref: LookRef): string {
  return ref.variant ? `${ref.look}.${ref.variant}` : ref.look
}
