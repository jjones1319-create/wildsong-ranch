import { outlined, type Sockets } from './bodyPlans.ts'
import type { Palette } from './palettes.ts'
import { lagGroup, type PartPiece } from './parts.ts'
import { circle, darken, ellipse, g, line, mix, path, polygon } from './svg.ts'

/**
 * Parts for the breeds added after launch (CONTENT §2.2, 31–32): Stripeneck's giraffe patches, zebra stripes,
 * ossicones, banded mane and tufted tail; Plumdrake's cloud ruff, tail puff, belly freckles and little fangs.
 * Every colour comes from the palette (or a fixed neutral both variants share), so the secret variants recolour.
 */

const st = (pal: Palette, width: number, color = pal.outline) => ({ fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })

/* ---------- Stripeneck ---------- */

/** Rounded patches on the neck and the front of the body, outlined in the belly colour. */
export function giraffePatches(s: Sockets, pal: Palette): PartPiece {
  const b = s.body
  const patch = mix(pal.body, pal.accent, 45)
  const neckFrom = { x: b.x + 38, y: b.y - 26 }
  const neckTo = { x: s.head.x - 4, y: s.head.y + 14 }
  const onNeck = [0.2, 0.5, 0.78].map((t, i) => ({ x: neckFrom.x + (neckTo.x - neckFrom.x) * t + (i % 2 ? 4 : -4), y: neckFrom.y + (neckTo.y - neckFrom.y) * t, r: 6.5 - i }))
  const onBody = [
    { x: b.x + 14, y: b.y - 16, r: 8 },
    { x: b.x + 34, y: b.y - 2, r: 7.5 },
    { x: b.x + 18, y: b.y + 10, r: 7 },
    { x: b.x + 42, y: b.y + 18, r: 5.5 },
  ]
  return { over: g({}, [...onNeck, ...onBody].map((p) => ellipse(p.x, p.y, p.r * 1.15, p.r, { fill: patch, stroke: pal.belly, 'stroke-width': 1.8 }))) }
}

/** Charcoal stripes curving round the back half of the body, kept inside its outline, and a few on the hind legs. */
export function zebraStripes(s: Sockets, pal: Palette): PartPiece {
  const b = s.body
  const stripes: string[] = []
  for (const dx of [-0.82, -0.62, -0.42, -0.22, -0.04]) {
    const x = b.x + dx * b.rx
    const h = b.ry * Math.sqrt(Math.max(0, 1 - dx * dx)) * 0.86
    stripes.push(path(`M${x - 2} ${b.y - h} Q${x + 7} ${b.y} ${x - 1} ${b.y + h}`, st(pal, dx < -0.7 ? 3.5 : 5, pal.accent)))
  }
  for (const lx of [b.x - 28, b.x - 10]) for (const y of [206, 214]) stripes.push(line(lx - 7, y, lx + 7, y - 2, st(pal, 3, pal.accent)))
  return { over: g({ opacity: 0.92 }, stripes) }
}

/** Two short furry horn nubs on top of the head, each with a charcoal tuft. */
export function ossicones(s: Sockets, pal: Palette): PartPiece {
  const c = s.crown
  const one = (x: number, lean: number) =>
    path(`M${x} ${c.y + 6} L${x + lean} ${c.y - 14}`, st(pal, 10)) +
    path(`M${x} ${c.y + 6} L${x + lean} ${c.y - 14}`, st(pal, 6, pal.paint(pal.body))) +
    circle(x + lean, c.y - 17, 5.5, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) })
  return { back: one(c.x - 9, -3) + one(c.x + 9, 3) }
}

/** A short upright brush mane down the back of the neck, banded charcoal and cream. */
export function bandedMane(s: Sockets, pal: Palette): PartPiece {
  const b = s.body
  const from = { x: b.x + 30, y: b.y - 36 }
  const to = { x: s.head.x - 16, y: s.head.y - 6 }
  const d = `M${from.x} ${from.y} L${to.x} ${to.y}`
  return {
    back: lagGroup('ws-mon__mane', from, -0.15, path(d, st(pal, 15)) + path(d, st(pal, 10, pal.belly)) + path(d, { ...st(pal, 10, pal.accent), 'stroke-linecap': 'butt', 'stroke-dasharray': '6 5' })),
  }
}

/** A thin zebra tail ending in a long wavy charcoal tuft. */
export function tuftTail(s: Sockets, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 4} ${t.y} C${t.x - 10} ${t.y + 8} ${t.x - 14} ${t.y + 24} ${t.x - 12} ${t.y + 38}`
  const tuft = `M${t.x - 12} ${t.y + 34} c-6 6 -8 14 -4 22 c3 -6 6 -9 10 -10 c-1 -6 -3 -9 -6 -12 Z`
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 4}px ${t.y}px` }, path(d, st(pal, 7)) + path(d, st(pal, 3.5, pal.paint(pal.body))) + path(tuft, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) })) }
}

/* ---------- Plumdrake ---------- */

/** A fluffy cloud-white ruff round the neck and shoulders. */
export function cloudRuff(s: Sockets, white: string, pal: Palette): PartPiece {
  const h = s.head
  const cy = h.y + h.r * 0.92
  const puffs = [-1, -0.66, -0.33, 0, 0.33, 0.66, 1].map((f) => ({ x: h.x + f * h.r * 0.95, y: cy + Math.abs(f) * -4, r: 9 + (1 - Math.abs(f)) * 3 }))
  return { front: g({}, [...puffs.map((p) => circle(p.x, p.y, p.r, { fill: white, ...outlined(pal, { 'stroke-width': 2.5 }) })), ...puffs.map((p) => circle(p.x, p.y, p.r - 2.2, { fill: white }))]) }
}

/** A fluffy puff on the tip of the thick tail (thickTail's tip). */
export function tailPuff(s: Sockets, white: string, pal: Palette): PartPiece {
  const t = { x: s.tail.x - 44, y: s.tail.y + 20 }
  const puffs = [
    [t.x, t.y, 9],
    [t.x - 8, t.y + 6, 7],
    [t.x + 6, t.y + 8, 7],
    [t.x - 2, t.y - 7, 7],
  ] as const
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${s.tail.x + 10}px ${s.tail.y}px` }, [...puffs.map(([x, y, r]) => circle(x, y, r, { fill: white, ...outlined(pal, { 'stroke-width': 2.2 }) })), ...puffs.map(([x, y, r]) => circle(x, y, r - 2, { fill: white }))]) }
}

/** Tiny darker freckles dusted over the soft belly. */
export function bellyFreckles(s: Sockets, pal: Palette): PartPiece {
  const b = s.body
  const dots: [number, number, number][] = [
    [b.x - 12, b.y + 2, 1.8],
    [b.x + 4, b.y - 6, 1.5],
    [b.x + 14, b.y + 8, 1.9],
    [b.x - 4, b.y + 16, 1.6],
    [b.x + 22, b.y - 2, 1.4],
    [b.x - 18, b.y + 18, 1.4],
  ]
  return { over: g({}, dots.map(([x, y, r]) => circle(x, y, r, { fill: darken(pal.belly, 22), opacity: 0.85 }))) }
}

/** Two little rounded fangs peeking out of the smile. */
export function littleFangs(s: Sockets, pal: Palette): PartPiece {
  const m = s.mouth
  const fang = (x: number) => polygon([[x - 3, m.y + 1], [x + 3, m.y + 1], [x, m.y + 6]], { fill: '#FFFDF7', ...outlined(pal, { 'stroke-width': 1.4 }) })
  return { front: g({}, [fang(m.x - 6), fang(m.x + 6)]) }
}
