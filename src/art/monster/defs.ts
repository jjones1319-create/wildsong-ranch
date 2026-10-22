import type { Palette, TextureKind } from './palettes.ts'
import { darken, el, lighten } from './svg.ts'

/**
 * The `<defs>` block of one rendered monster (GAME_DESIGN §22 high-end polish): a top-left-lit
 * gradient for the body, belly and accent colours, a soft radial contact shadow, and the optional
 * texture pattern. Ids carry the palette's hash, so several monsters on one page never clash and
 * two monsters with the same palette share identical definitions harmlessly.
 */

function gradient(id: string, color: string): string {
  return el('linearGradient', { id, x1: 0, y1: 0, x2: 1, y2: 1 }, [
    el('stop', { offset: 0, 'stop-color': lighten(color, 22) }),
    el('stop', { offset: 0.5, 'stop-color': color }),
    el('stop', { offset: 1, 'stop-color': darken(color, 16) }),
  ])
}

function pattern(id: string, kind: TextureKind, stroke: string): string {
  const common = { fill: 'none', stroke, 'stroke-width': 1.3, 'stroke-linecap': 'round' }
  switch (kind) {
    case 'scales':
      return el('pattern', { id, patternUnits: 'userSpaceOnUse', width: 14, height: 12 }, [
        el('path', { d: 'M0 4 a7 7 0 0 0 14 0', ...common }),
        el('path', { d: 'M-7 10 a7 7 0 0 0 14 0 M7 10 a7 7 0 0 0 14 0', ...common }),
      ])
    case 'fur':
      return el('pattern', { id, patternUnits: 'userSpaceOnUse', width: 16, height: 16 }, [
        el('path', { d: 'M2 6 l3 -4 M9 4 l3 -4 M5 14 l3 -4 M12 12 l3 -4', ...common }),
      ])
    case 'stone':
      return el('pattern', { id, patternUnits: 'userSpaceOnUse', width: 20, height: 20 }, [
        el('path', { d: 'M2 3 l5 -1 l2 4 l-4 2 Z M12 10 l6 1 l-1 5 l-5 -1 Z M3 14 l4 1 l-1 3 Z', fill: stroke, opacity: 0.8 }),
        el('circle', { cx: 15, cy: 4, r: 1.2, fill: stroke }),
      ])
    case 'feathers':
      return el('pattern', { id, patternUnits: 'userSpaceOnUse', width: 16, height: 14 }, [
        el('path', { d: 'M0 4 l4 4 l4 -4 M8 4 l4 4 l4 -4 M4 11 l4 4 l4 -4', ...common }),
      ])
  }
}

export function buildDefs(pal: Palette, texture: TextureKind | null): string {
  const items = [
    gradient(`${pal.id}-b`, pal.body),
    gradient(`${pal.id}-y`, pal.belly),
    gradient(`${pal.id}-a`, pal.accent),
    el('radialGradient', { id: `${pal.id}-s` }, [el('stop', { offset: 0, 'stop-color': '#000', 'stop-opacity': 0.34 }), el('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': 0 })]),
  ]
  if (texture) items.push(pattern(`${pal.id}-t`, texture, pal.outline))
  return el('defs', {}, items)
}
