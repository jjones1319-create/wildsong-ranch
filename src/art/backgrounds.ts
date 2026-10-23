import { BACKGROUND } from '../data/tuning.ts'
import type { Season, Weather } from '../data/types.ts'
import { circle, el, ellipse, g, path, rect } from './monster/svg.ts'

/**
 * GAME_DESIGN §22 backgrounds: layered SVG strings drawn in code (sky · far hills · the barn and fence ·
 * a tree that follows the season · ground) with weather overlays (drifting clouds, rain, snow, a storm
 * flash) as CSS-animated groups. Pure: positions come from a tiny seeded generator, so the same week
 * always draws the same sky. The viewBox is 360 × 220 and the picture stretches to the stage.
 */

export type SceneKind = 'ranch' | 'town' | 'shrine' | 'arena'

export interface BackgroundOptions {
  season: Season
  weather: Weather
  /** Fewer drops and flakes on weaker phones. */
  lite?: boolean
  seed?: number
  scene?: SceneKind
}

const W = 360
const H = 220
const BANNER_TOP = 72
const BANNER_HEIGHT = 112

interface Palette {
  skyTop: string
  skyBottom: string
  hillFar: string
  hillNear: string
  ground: string
  foliage: string | null
  trunk: string
}

const SEASON_PALETTES: Record<Season, Palette> = {
  Spring: { skyTop: '#5f9fd6', skyBottom: '#cfe7f3', hillFar: '#6f9d6a', hillNear: '#5f8f52', ground: '#73a652', foliage: '#86c25e', trunk: '#6b4a32' },
  Summer: { skyTop: '#3f86cf', skyBottom: '#bfe3f7', hillFar: '#6a9a55', hillNear: '#58893f', ground: '#86ad4c', foliage: '#4f9a3c', trunk: '#6b4a32' },
  Autumn: { skyTop: '#7a8fb8', skyBottom: '#f0d2a8', hillFar: '#9a8a62', hillNear: '#8d7646', ground: '#b08a46', foliage: '#d9843a', trunk: '#5e3f2a' },
  Winter: { skyTop: '#5f7390', skyBottom: '#d8e2ea', hillFar: '#b9c6d2', hillNear: '#cfd9e2', ground: '#e8eef3', foliage: null, trunk: '#4e3a2c' },
}

/** Weather dims the sky: cloudy is flatter, rain greyer, storm dark, snow pale. */
function skyFor(p: Palette, weather: Weather): { top: string; bottom: string } {
  switch (weather) {
    case 'Sunny':
      return { top: p.skyTop, bottom: p.skyBottom }
    case 'Cloudy':
      return { top: '#7f8fa2', bottom: '#cbd3da' }
    case 'Rain':
      return { top: '#5a6775', bottom: '#9aa6b1' }
    case 'Storm':
      return { top: '#2d3440', bottom: '#5d6673' }
    case 'Snow':
      return { top: '#8793a4', bottom: '#dde4ea' }
  }
}

function lcg(seed: number): () => number {
  let s = (seed >>> 0) || 1
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 4294967296
  }
}

function hills(p: Palette): string {
  return [
    path(`M0 ${H * 0.62} Q ${W * 0.2} ${H * 0.46} ${W * 0.42} ${H * 0.6} T ${W * 0.8} ${H * 0.56} T ${W} ${H * 0.62} V ${H} H 0 Z`, { fill: p.hillFar, class: 'ws-bg__hill ws-bg__hill--far' }),
    path(`M0 ${H * 0.74} Q ${W * 0.25} ${H * 0.6} ${W * 0.55} ${H * 0.72} T ${W} ${H * 0.68} V ${H} H 0 Z`, { fill: p.hillNear, class: 'ws-bg__hill ws-bg__hill--near' }),
  ].join('')
}

function ground(p: Palette): string {
  return rect(0, H * 0.8, W, H * 0.2, 0, { fill: p.ground, class: 'ws-bg__ground' })
}

function barn(): string {
  const x = 236
  const y = 118
  return g({ class: 'ws-bg__barn' }, [
    rect(x, y + 18, 70, 42, 3, { fill: '#9a4a3a', stroke: '#4a2a22', 'stroke-width': 2 }),
    path(`M${x - 4} ${y + 20} L${x + 35} ${y - 6} L${x + 74} ${y + 20} Z`, { fill: '#6b3a2e', stroke: '#4a2a22', 'stroke-width': 2, 'stroke-linejoin': 'round' }),
    rect(x + 26, y + 34, 18, 26, 2, { fill: '#4a2a22' }),
    rect(x + 8, y + 28, 10, 10, 1, { fill: '#f3e6c4', stroke: '#4a2a22', 'stroke-width': 1.5 }),
    rect(x + 52, y + 28, 10, 10, 1, { fill: '#f3e6c4', stroke: '#4a2a22', 'stroke-width': 1.5 }),
  ])
}

function fence(): string {
  const posts: string[] = []
  for (let x = 14; x < 150; x += 22) posts.push(rect(x, 150, 5, 24, 1.5, { fill: '#c9a66b', stroke: '#6b4a32', 'stroke-width': 1.5 }))
  posts.push(rect(10, 156, 142, 4, 1.5, { fill: '#c9a66b', stroke: '#6b4a32', 'stroke-width': 1.5 }))
  posts.push(rect(10, 166, 142, 4, 1.5, { fill: '#c9a66b', stroke: '#6b4a32', 'stroke-width': 1.5 }))
  return g({ class: 'ws-bg__fence' }, posts)
}

function tree(p: Palette, season: Season): string {
  const x = 318
  const parts: string[] = [path(`M${x} 176 V 128 M${x} 144 L${x - 12} 128 M${x} 150 L${x + 11} 136`, { stroke: p.trunk, 'stroke-width': 6, 'stroke-linecap': 'round', fill: 'none' })]
  if (p.foliage) {
    parts.push(ellipse(x, 118, 30, 24, { fill: p.foliage, class: 'ws-bg__leaves' }))
    parts.push(ellipse(x - 16, 130, 18, 14, { fill: p.foliage, class: 'ws-bg__leaves' }))
    parts.push(ellipse(x + 16, 132, 16, 13, { fill: p.foliage, class: 'ws-bg__leaves' }))
    if (season === 'Spring') for (const [dx, dy] of [[-10, 108], [8, 104], [20, 120], [-20, 126]] as const) parts.push(circle(x + dx, dy, 2.5, { fill: '#f6c7d6' }))
  } else {
    parts.push(path(`M${x} 128 L${x - 8} 112 M${x} 128 L${x + 9} 110 M${x - 12} 128 L${x - 20} 118 M${x + 11} 136 L${x + 22} 128`, { stroke: p.trunk, 'stroke-width': 3, 'stroke-linecap': 'round', fill: 'none' }))
  }
  return g({ class: 'ws-bg__tree' }, parts)
}

function sun(weather: Weather, season: Season): string {
  if (weather !== 'Sunny') return ''
  const color = season === 'Winter' ? '#fff3d6' : '#ffd66b'
  return g({ class: 'ws-bg__sun' }, [circle(62, 46, 18, { fill: color, opacity: 0.95 }), circle(62, 46, 30, { fill: color, opacity: 0.18 })])
}

function clouds(rand: () => number, weather: Weather): string {
  if (weather === 'Sunny') return ''
  const n = BACKGROUND.clouds
  const items: string[] = []
  for (let i = 0; i < n; i++) {
    const x = 20 + rand() * 300
    const y = 24 + rand() * 50
    const s = 0.7 + rand() * 0.8
    const dur = 26 + rand() * 20
    const fill = weather === 'Storm' ? '#3c4552' : weather === 'Rain' ? '#aeb8c2' : '#ffffff'
    items.push(
      g({ class: 'ws-bg__cloud', style: `animation-duration:${dur.toFixed(1)}s;animation-delay:-${(rand() * dur).toFixed(1)}s`, transform: `translate(${x.toFixed(1)} ${y.toFixed(1)}) scale(${s.toFixed(2)})` }, [
        ellipse(0, 0, 26, 12, { fill, opacity: 0.9 }),
        ellipse(-14, 4, 16, 10, { fill, opacity: 0.9 }),
        ellipse(16, 4, 18, 11, { fill, opacity: 0.9 }),
      ]),
    )
  }
  return g({ class: 'ws-bg__clouds' }, items)
}

function rain(rand: () => number, lite: boolean): string {
  const n = lite ? BACKGROUND.drops.lite : BACKGROUND.drops.full
  const drops: string[] = []
  for (let i = 0; i < n; i++) {
    const x = rand() * W
    const dur = 0.7 + rand() * 0.5
    drops.push(el('line', { x1: x.toFixed(1), y1: 0, x2: (x - 6).toFixed(1), y2: 16, class: 'ws-bg__drop', style: `animation-duration:${dur.toFixed(2)}s;animation-delay:-${(rand() * dur).toFixed(2)}s` }))
  }
  return g({ class: 'ws-bg__rain', stroke: '#dfeaf5', 'stroke-width': 1.5, 'stroke-linecap': 'round', opacity: 0.7 }, drops)
}

function snow(rand: () => number, lite: boolean): string {
  const n = lite ? BACKGROUND.flakes.lite : BACKGROUND.flakes.full
  const flakes: string[] = []
  for (let i = 0; i < n; i++) {
    const x = rand() * W
    const dur = 5 + rand() * 4
    const r = 1.5 + rand() * 2
    flakes.push(circle(x, 0, r, { class: 'ws-bg__flake', fill: '#ffffff', opacity: 0.9, style: `animation-duration:${dur.toFixed(2)}s;animation-delay:-${(rand() * dur).toFixed(2)}s` }))
  }
  return g({ class: 'ws-bg__snow' }, flakes)
}

function storm(): string {
  return g({ class: 'ws-bg__storm' }, [
    rect(0, 0, W, H, 0, { fill: '#ffffff', class: 'ws-bg__flash', style: `animation-duration:${BACKGROUND.lightningCycleS}s` }),
    path('M214 10 L198 54 L212 52 L196 96', { stroke: '#fff7c2', 'stroke-width': 3, fill: 'none', 'stroke-linejoin': 'round', class: 'ws-bg__bolt', style: `animation-duration:${BACKGROUND.lightningCycleS}s` }),
  ])
}

/** Town: rooftops instead of the barn. Shrine: standing stones. Arena: a flat ring. */
function sceneExtras(scene: SceneKind, p: Palette): string {
  switch (scene) {
    case 'ranch':
      return barn() + fence() + tree(p, 'Spring')
    case 'town':
      return g({ class: 'ws-bg__town' }, [
        rect(40, 128, 60, 48, 3, { fill: '#b98c5a', stroke: '#4a2a22', 'stroke-width': 2 }),
        path('M36 130 L70 104 L104 130 Z', { fill: '#9a4a3a', stroke: '#4a2a22', 'stroke-width': 2 }),
        rect(120, 120, 70, 56, 3, { fill: '#d6c2a0', stroke: '#4a2a22', 'stroke-width': 2 }),
        path('M116 122 L155 92 L194 122 Z', { fill: '#6b7f9e', stroke: '#4a2a22', 'stroke-width': 2 }),
        rect(214, 134, 54, 42, 3, { fill: '#c9a66b', stroke: '#4a2a22', 'stroke-width': 2 }),
        path('M210 136 L241 112 L272 136 Z', { fill: '#9a4a3a', stroke: '#4a2a22', 'stroke-width': 2 }),
        rect(150, 146, 12, 30, 2, { fill: '#4a2a22' }),
      ])
    case 'shrine':
      return g({ class: 'ws-bg__shrine' }, [
        rect(120, 112, 22, 64, 6, { fill: '#8d94a1', stroke: '#3b4049', 'stroke-width': 2 }),
        rect(170, 100, 24, 76, 6, { fill: '#9aa2ae', stroke: '#3b4049', 'stroke-width': 2 }),
        rect(222, 116, 20, 60, 6, { fill: '#8d94a1', stroke: '#3b4049', 'stroke-width': 2 }),
        circle(182, 96, 5, { fill: '#f2b544', class: 'ws-bg__glow' }),
      ])
    case 'arena':
      return g({ class: 'ws-bg__arena' }, [ellipse(W / 2, 182, 150, 14, { fill: '#c9a66b', opacity: 0.5 }), rect(40, 150, 280, 4, 2, { fill: '#6b4a32' })])
  }
}

/** The background for the ranch stage (and the lighter scenes). */
export function sceneBackground(o: BackgroundOptions): string {
  const scene = o.scene ?? 'ranch'
  const p = SEASON_PALETTES[o.season]
  const sky = skyFor(p, o.weather)
  const rand = lcg(o.seed ?? 1)
  const lite = o.lite ?? false
  const layers: string[] = [
    el('defs', {}, el('linearGradient', { id: 'ws-bg-sky', x1: 0, y1: 0, x2: 0, y2: 1 }, [el('stop', { offset: '0', 'stop-color': sky.top }), el('stop', { offset: '1', 'stop-color': sky.bottom })])),
    rect(0, 0, W, H, 0, { fill: 'url(#ws-bg-sky)', class: 'ws-bg__sky' }),
    sun(o.weather, o.season),
    clouds(rand, o.weather),
    hills(p),
    ground(p),
    scene === 'ranch' ? barn() + fence() + tree(p, o.season) : sceneExtras(scene, p),
    o.weather === 'Rain' || o.weather === 'Storm' ? rain(rand, lite) : '',
    o.weather === 'Snow' ? snow(rand, lite) : '',
    o.weather === 'Storm' ? storm() : '',
  ]
  // Banners (Town, the Shrine) are short and wide: show the middle band, where the buildings and stones stand.
  const banner = scene === 'town' || scene === 'shrine'
  return el(
    'svg',
    {
      xmlns: 'http://www.w3.org/2000/svg',
      viewBox: banner ? `0 ${BANNER_TOP} ${W} ${BANNER_HEIGHT}` : `0 0 ${W} ${H}`,
      preserveAspectRatio: banner ? 'xMidYMid slice' : 'xMidYMax slice',
      class: `ws-bg ws-bg--${o.season.toLowerCase()} ws-bg--${o.weather.toLowerCase()} ws-bg--${scene}`,
      'aria-hidden': 'true',
    },
    layers,
  )
}

export const ranchBackground = (o: Omit<BackgroundOptions, 'scene'>) => sceneBackground({ ...o, scene: 'ranch' })
