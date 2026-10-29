import { cyrb53 } from '../../core/hash.ts'
import { BREED_BY_ID } from '../../data/breeds.ts'
import type { BreedId } from '../../data/types.ts'
import { darken, lighten, luma } from './svg.ts'

/**
 * GAME_DESIGN §22 palettes: every monster wears its own breed's palette (a secret variant has its own, variants.ts).
 * With the high-end polish, the three palette colours are painted as top-left-lit gradients
 * (see defs.ts); `paint()` maps a flat colour to its gradient so parts never need to know.
 */

export const TEXTURE_KINDS = ['scales', 'fur', 'stone', 'feathers'] as const
export type TextureKind = (typeof TEXTURE_KINDS)[number]

export interface Palette {
  body: string
  belly: string
  accent: string
  eye: string
  /** Thick storybook outline, derived from the body colour. */
  outline: string
  /** The one soft shading layer. */
  shade: string
  /** Highlights (eye glints, shell shine). */
  light: string
  /** Unique id prefix for this palette's gradient and pattern defs. */
  id: string
  /** Gradient paint for a palette colour (`url(#…)`), or the colour itself when gradients are off. */
  paint: (color: string) => string
  /** The texture pattern paint, or null. */
  texture: string | null
}

export interface PaletteOptions {
  gradients?: boolean
  texture?: TextureKind | null
}

export function buildPalette(base: { body: string; belly: string; accent: string; eye: string }, eye = base.eye, o: PaletteOptions = {}): Palette {
  const dark = luma(base.body) < 70
  const texture = o.texture ?? null
  const id = `ws${cyrb53(`${base.body}${base.belly}${base.accent}${eye}${texture ?? ''}`).toString(36).slice(0, 9)}`
  const gradients = o.gradients ?? false
  const urls: Record<string, string> = { [base.body]: `url(#${id}-b)`, [base.belly]: `url(#${id}-y)`, [base.accent]: `url(#${id}-a)` }
  return {
    body: base.body,
    belly: base.belly,
    accent: base.accent,
    eye,
    outline: dark ? darken(base.body, 35) : darken(base.body, 58),
    shade: darken(base.body, 16),
    light: lighten(base.body, 28),
    id,
    paint: (color) => (gradients ? (urls[color] ?? color) : color),
    texture: texture ? `url(#${id}-t)` : null,
  }
}

export function paletteOfBreed(id: BreedId, o: PaletteOptions = {}): Palette {
  return buildPalette(BREED_BY_ID[id].art.palette, undefined, o)
}

