import type { DrillId } from '../data/types.ts'

/**
 * GAME_DESIGN §22 drill vignettes: "a prop plus a motion". These are the props: tiny original SVG drawings
 * (viewBox 0 0 160 100) in the storybook style, drawn in code. The moving pieces carry `ws-prop__*` classes
 * so `vignette.css` can animate them (transforms and opacity only); the monster's own motion is CSS on the
 * figure beside them, chosen by the scene's `data-vignette`.
 */

const OUTLINE = '#2b2b2b'
const WOOD = '#8a5a3c'
const WOOD_DARK = '#5e3a24'
const STONE = '#8d94a1'
const STONE_DARK = '#5f6673'
const LEAF = '#7faf5a'
const WATER = '#5aa9d6'
const GOURD = '#e8963a'

const svg = (body: string) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 100" width="160" height="100" aria-hidden="true" stroke="${OUTLINE}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" overflow="visible">${body}</svg>`

const PROPS: Record<DrillId, string> = {
  'hill-sprints': svg(
    `<path d="M4 90 Q60 18 156 90 Z" fill="${LEAF}"/><path d="M30 86 Q70 46 130 86" fill="none" stroke="#e9dcb4" stroke-dasharray="8 7" class="ws-prop__trail"/><circle cx="128" cy="26" r="11" fill="#f2b544" class="ws-prop__sun"/>`,
  ),
  'log-toss': svg(
    `<g class="ws-prop__log" style="transform-origin:80px 67px"><rect x="22" y="52" width="116" height="30" rx="15" fill="${WOOD}"/><ellipse cx="138" cy="67" rx="10" ry="15" fill="#d8b48c"/><ellipse cx="138" cy="67" rx="5" ry="8" fill="none"/><path d="M40 60 h40 M48 72 h60" fill="none" stroke="${WOOD_DARK}"/></g><path d="M8 88 h144" fill="none" stroke="${WOOD_DARK}"/>`,
  ),
  'puzzle-stones': svg(
    `<rect x="14" y="30" width="46" height="46" rx="9" fill="${STONE}"/><circle cx="37" cy="53" r="9" fill="${STONE_DARK}" stroke="none"/><g class="ws-prop__stone" style="transform-origin:86px 42px"><rect x="66" y="22" width="40" height="40" rx="9" fill="${STONE}" transform="rotate(12 86 42)"/><path d="M78 42 l8 -10 l8 10 z" fill="${STONE_DARK}" stroke="none"/></g><rect x="112" y="40" width="40" height="40" rx="9" fill="${STONE}"/><rect x="124" y="52" width="16" height="16" rx="3" fill="${STONE_DARK}" stroke="none"/>`,
  ),
  'target-toss': svg(
    `<rect x="76" y="56" width="8" height="40" fill="${WOOD}"/><g class="ws-prop__target" style="transform-origin:80px 42px"><circle cx="80" cy="42" r="34" fill="#f3e6c4"/><circle cx="80" cy="42" r="24" fill="#e86a7c"/><circle cx="80" cy="42" r="14" fill="#f3e6c4"/><circle cx="80" cy="42" r="6" fill="#e86a7c"/></g><ellipse cx="30" cy="80" rx="9" ry="12" fill="${WOOD}" class="ws-prop__cone"/>`,
  ),
  'dodge-the-gourds': svg(
    `<g class="ws-prop__gourd ws-prop__gourd--1" style="transform-origin:40px 0px"><path d="M40 2 v30" fill="none"/><ellipse cx="40" cy="46" rx="14" ry="18" fill="${GOURD}"/></g><g class="ws-prop__gourd ws-prop__gourd--2" style="transform-origin:80px 0px"><path d="M80 2 v22" fill="none"/><ellipse cx="80" cy="38" rx="12" ry="16" fill="${GOURD}"/></g><g class="ws-prop__gourd ws-prop__gourd--3" style="transform-origin:120px 0px"><path d="M120 2 v34" fill="none"/><ellipse cx="120" cy="50" rx="15" ry="19" fill="${GOURD}"/></g><path d="M8 92 h144" fill="none" stroke="${WOOD_DARK}"/>`,
  ),
  'acorn-shower': svg(
    `<path d="M80 96 v-40" fill="none" stroke="${WOOD_DARK}" stroke-width="8"/><ellipse cx="80" cy="36" rx="56" ry="30" fill="${LEAF}" class="ws-prop__canopy" style="transform-origin:80px 36px"/><g class="ws-prop__acorns"><ellipse cx="40" cy="78" rx="6" ry="8" fill="${WOOD}" class="ws-prop__acorn ws-prop__acorn--1"/><ellipse cx="118" cy="70" rx="6" ry="8" fill="${WOOD}" class="ws-prop__acorn ws-prop__acorn--2"/><ellipse cx="128" cy="90" rx="6" ry="8" fill="${WOOD}" class="ws-prop__acorn ws-prop__acorn--3"/><ellipse cx="54" cy="92" rx="6" ry="8" fill="${WOOD}" class="ws-prop__acorn ws-prop__acorn--4"/></g>`,
  ),
  'plow-pull': svg(
    `<g class="ws-prop__plow"><path d="M20 70 h70 l20 -30 h30" fill="none" stroke="${WOOD}" stroke-width="7"/><path d="M90 70 l-14 22 h34 z" fill="${STONE_DARK}"/></g><path d="M4 92 q20 -6 40 0 t40 0 t40 0 t36 0" fill="none" stroke="${WOOD_DARK}" class="ws-prop__furrow"/>`,
  ),
  'moon-meditation': svg(
    `<g class="ws-prop__moon" style="transform-origin:112px 34px"><circle cx="112" cy="34" r="24" fill="#f3e6c4"/><circle cx="124" cy="28" r="20" fill="#131a1e" stroke="none"/></g><circle cx="30" cy="20" r="2" fill="#f3e6c4" stroke="none" class="ws-prop__star ws-prop__star--1"/><circle cx="60" cy="10" r="2" fill="#f3e6c4" stroke="none" class="ws-prop__star ws-prop__star--2"/><circle cx="150" cy="72" r="2" fill="#f3e6c4" stroke="none" class="ws-prop__star ws-prop__star--3"/><rect x="26" y="66" width="108" height="26" rx="12" fill="${STONE}"/>`,
  ),
  'wind-chase': svg(
    `<path d="M10 40 q30 -24 60 0 t60 0" fill="none" stroke="#a9b3ba" class="ws-prop__gust ws-prop__gust--1"/><path d="M20 66 q30 -24 60 0 t60 0" fill="none" stroke="#a9b3ba" class="ws-prop__gust ws-prop__gust--2"/><path d="M118 20 q14 -12 22 0 q-8 12 -22 0 z" fill="${LEAF}" class="ws-prop__leaf ws-prop__leaf--1"/><path d="M60 80 q14 -12 22 0 q-8 12 -22 0 z" fill="${GOURD}" class="ws-prop__leaf ws-prop__leaf--2"/><path d="M134 62 q14 -12 22 0 q-8 12 -22 0 z" fill="${LEAF}" class="ws-prop__leaf ws-prop__leaf--3"/>`,
  ),
  'waterfall-stand': svg(
    `<rect x="100" y="0" width="60" height="100" fill="${STONE_DARK}"/><g class="ws-prop__water"><path d="M106 0 v100 M122 0 v100 M138 0 v100" fill="none" stroke="${WATER}" stroke-width="9" stroke-dasharray="14 10"/></g><path d="M4 88 q30 -10 60 0 t60 0 t32 0" fill="none" stroke="${WATER}" stroke-width="8"/><circle cx="92" cy="80" r="4" fill="#f3f7fa" stroke="none" class="ws-prop__spray ws-prop__spray--1"/><circle cx="72" cy="84" r="3" fill="#f3f7fa" stroke="none" class="ws-prop__spray ws-prop__spray--2"/>`,
  ),
  'quarry-haul': svg(
    `<rect x="20" y="56" width="44" height="34" rx="6" fill="${STONE}"/><rect x="70" y="40" width="40" height="50" rx="6" fill="${STONE_DARK}" class="ws-prop__block" style="transform-origin:90px 90px"/><rect x="116" y="62" width="34" height="28" rx="6" fill="${STONE}"/><path d="M4 92 h152" fill="none" stroke="${WOOD_DARK}"/>`,
  ),
}

export function propSvg(drill: DrillId): string {
  return PROPS[drill]
}
