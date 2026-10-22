import type { Monster } from '../../core/monster.ts'
import { BREED_BY_ID } from '../../data/breeds.ts'
import type { BreedId } from '../../data/types.ts'
import { darken, lighten, luma } from './svg.ts'

/**
 * GAME_DESIGN §22 palettes and the §14.3 rule: the sub breed's palette goes on the main body,
 * the main breed's eyes stay. A pure monster wears its classic palette.
 */

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
}

export function buildPalette(base: { body: string; belly: string; accent: string; eye: string }, eye = base.eye): Palette {
  const dark = luma(base.body) < 70
  return {
    body: base.body,
    belly: base.belly,
    accent: base.accent,
    eye,
    outline: dark ? darken(base.body, 35) : darken(base.body, 58),
    shade: darken(base.body, 16),
    light: lighten(base.body, 28),
  }
}

export function paletteOfBreed(id: BreedId): Palette {
  return buildPalette(BREED_BY_ID[id].art.palette)
}

/** The palette a monster is drawn with: its appearance's palette breed (the sub by default) with the main breed's eyes. */
export function paletteFor(m: Monster): Palette {
  const paletteBreed = BREED_BY_ID[m.appearance.paletteBreed] ?? BREED_BY_ID[m.subBreed]
  const eye = BREED_BY_ID[m.mainBreed].art.palette.eye
  return buildPalette(paletteBreed.art.palette, eye)
}
