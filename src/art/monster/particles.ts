import type { Sockets } from './bodyPlans.ts'
import { circle, g, line, path } from './svg.ts'

/**
 * GAME_DESIGN §22 signature particles: a small group of shapes with staggered CSS animations
 * (embers rise, petals fall, glints twinkle…). Positions are deterministic (a tiny seeded
 * generator), so the same monster always gets the same cloud. The CSS hides the whole group under
 * reduced motion, in lite mode and when the picture is static.
 */

export const PARTICLE_KINDS = ['ember', 'glint', 'mote', 'twinkle', 'petal', 'bubble', 'puff', 'flake', 'rain', 'spark', 'steam', 'leaf', 'ash', 'coin', 'feather'] as const
export type ParticleKind = (typeof PARTICLE_KINDS)[number]

type Motion = 'rise' | 'fall' | 'twinkle' | 'puff' | 'steam'

const MOTION: Record<ParticleKind, Motion> = {
  ember: 'rise',
  glint: 'twinkle',
  mote: 'rise',
  twinkle: 'twinkle',
  petal: 'fall',
  bubble: 'rise',
  puff: 'puff',
  flake: 'fall',
  rain: 'fall',
  spark: 'twinkle',
  steam: 'steam',
  leaf: 'fall',
  ash: 'fall',
  coin: 'twinkle',
  feather: 'fall',
}

const COUNT: Record<Motion, number> = { rise: 7, fall: 7, twinkle: 6, puff: 4, steam: 5 }

function lcg(seed: number): () => number {
  let s = seed >>> 0 || 1
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 4294967296
  }
}

const star = (x: number, y: number, r: number, fill: string) => path(`M${x} ${y - r} Q${x} ${y} ${x + r} ${y} Q${x} ${y} ${x} ${y + r} Q${x} ${y} ${x - r} ${y} Q${x} ${y} ${x} ${y - r} Z`, { fill })

function shape(kind: ParticleKind, x: number, y: number, r: number): string {
  switch (kind) {
    case 'ember':
      return circle(x, y, r, { fill: '#FF8A3D' }) + circle(x, y, r * 0.45, { fill: '#FFE3A3' })
    case 'glint':
      return star(x, y, r * 1.6, '#F5E663')
    case 'mote':
      return circle(x, y, r, { fill: '#FFF2B0', opacity: 0.9 })
    case 'twinkle':
      return star(x, y, r * 1.5, '#E8F1FF')
    case 'petal':
      return path(`M${x} ${y - r * 1.4} C${x + r * 1.3} ${y - r * 0.6} ${x + r * 1.2} ${y + r} ${x} ${y + r * 1.2} C${x - r * 1.2} ${y + r} ${x - r * 1.3} ${y - r * 0.6} ${x} ${y - r * 1.4} Z`, { fill: '#F4A7B9', opacity: 0.95 })
    case 'bubble':
      return circle(x, y, r * 1.2, { fill: '#fff', opacity: 0.25 }) + circle(x, y, r * 1.2, { fill: 'none', stroke: '#DDF2F8', 'stroke-width': 1.2 }) + circle(x - r * 0.4, y - r * 0.4, r * 0.3, { fill: '#fff', opacity: 0.8 })
    case 'puff':
      return circle(x, y, r * 2, { fill: '#B8B2A8', opacity: 0.5 })
    case 'flake':
      return path(`M${x - r} ${y} h${2 * r} M${x} ${y - r} v${2 * r} M${x - r * 0.7} ${y - r * 0.7} l${1.4 * r} ${1.4 * r} M${x + r * 0.7} ${y - r * 0.7} l${-1.4 * r} ${1.4 * r}`, { stroke: '#fff', 'stroke-width': 1.3, 'stroke-linecap': 'round' })
    case 'rain':
      return line(x, y - r * 2, x - r * 0.5, y + r * 2, { stroke: '#8FB8F2', 'stroke-width': 1.6, 'stroke-linecap': 'round', opacity: 0.8 })
    case 'spark':
      return star(x, y, r * 1.3, '#FFE14D')
    case 'steam':
      return circle(x, y, r * 2.2, { fill: '#E6E6E6', opacity: 0.32 })
    case 'leaf':
      return path(`M${x} ${y} c-${r * 2} -${r} -${r * 2.6} -${r * 2.6} -${r * 1.2} -${r * 3.4} c${r * 2} ${r * 0.6} ${r * 2.4} ${r * 2.2} ${r * 1.2} ${r * 3.4} Z`, { fill: '#D9733B', opacity: 0.9 })
    case 'ash':
      return circle(x, y, r * 0.8, { fill: '#CFCAC6', opacity: 0.8 })
    case 'coin':
      return circle(x, y, r, { fill: '#F2C94C', stroke: '#B8860B', 'stroke-width': 1 })
    case 'feather':
      return path(`M${x} ${y + r * 1.6} c-${r * 1.2} -${r} -${r * 1.2} -${r * 2.4} 0 -${r * 3.2} c${r * 1.2} ${r * 0.8} ${r * 1.2} ${r * 2.2} 0 ${r * 3.2} Z`, { fill: '#F5F8FC', opacity: 0.9 })
  }
}

export function drawParticles(kind: ParticleKind, s: Sockets, seed: number): string {
  const motion = MOTION[kind]
  const rnd = lcg(seed)
  const b = s.body
  const items: string[] = []
  const n = COUNT[motion]
  for (let i = 0; i < n; i++) {
    const spread = motion === 'puff' ? 0.9 : 1.15
    const x = b.x + (rnd() * 2 - 1) * b.rx * spread
    const y = motion === 'puff' ? 226 : motion === 'fall' ? b.y - b.ry - 10 + rnd() * 20 : b.y + b.ry * (rnd() * 0.8 - 0.2)
    const r = 2 + rnd() * 2.2
    const dur = (motion === 'twinkle' ? 1.2 : motion === 'puff' ? 2.2 : 2.8) + rnd() * 1.6
    const delay = -rnd() * dur
    items.push(g({ class: `ws-p ws-p--${motion}`, style: `animation-duration:${dur.toFixed(2)}s;animation-delay:${delay.toFixed(2)}s` }, shape(kind, x, y, r)))
  }
  return g({ class: 'ws-mon__particles' }, items)
}
