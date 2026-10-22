import { limb, outlined, type Pt, type Sockets } from './bodyPlans.ts'
import type { Palette } from './palettes.ts'
import { lagGroup, type PartPiece } from './parts.ts'
import { circle, darken, ellipse, g, lighten, line, path, polygon, polyline, rect } from './svg.ts'

/**
 * Parts for breeds 21–30 (docs/NEW_MONSTERS.md §3): dragon wings and horns, geode crystals, the fan
 * crest, the halo and four wings, the aurora mane, petal ears and the trunk bud, spectacles and the
 * scholar's cap, bat wings and rune lines, spiral horns and the scarf, the ice tusk and frost fins.
 */

const st = (pal: Palette, width: number, color = pal.outline) => ({ fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })

/** A glowing element: pulses softly (class ws-mon__glow). */
export const glow = (inner: string) => g({ class: 'ws-mon__glow' }, inner)

/* ---------- Hearthwing ---------- */

export function littleWings(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.back
  const wing = (dir: number) => {
    const x = b.x + dir * 10
    const y = b.y + 4
    const d = `M${x} ${y} C${x + dir * 8} ${y - 26} ${x + dir * 40} ${y - 30} ${x + dir * 36} ${y - 4} C${x + dir * 28} ${y + 6} ${x + dir * 10} ${y + 8} ${x} ${y} Z`
    return lagGroup('ws-mon__wing', { x, y }, dir * 0.25, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + path(`M${x + dir * 6} ${y - 2} L${x + dir * 24} ${y - 16} M${x + dir * 12} ${y} L${x + dir * 30} ${y - 8}`, { ...st(pal, 1.5), opacity: 0.5 }))
  }
  return { back: wing(-1) + wing(1) }
}

export function dragonWings(s: Sockets, fill: string, edge: string, pal: Palette): PartPiece {
  const b = s.back
  const wing = (dir: number, scale: number) => {
    const x = b.x + dir * 12
    const y = b.y + 6
    const w = 104 * scale
    const h = 100 * scale
    const d = `M${x} ${y} C${x + dir * w * 0.2} ${y - h * 0.8} ${x + dir * w * 0.7} ${y - h} ${x + dir * w} ${y - h * 0.62} L${x + dir * w * 0.82} ${y - h * 0.44} L${x + dir * w * 0.66} ${y - h * 0.2} L${x + dir * w * 0.4} ${y - h * 0.04} Z`
    const fingers = `M${x + dir * 6} ${y - 6} L${x + dir * w} ${y - h * 0.62} M${x + dir * 6} ${y - 6} L${x + dir * w * 0.82} ${y - h * 0.44} M${x + dir * 6} ${y - 6} L${x + dir * w * 0.66} ${y - h * 0.2}`
    const emberEdge = `M${x + dir * w} ${y - h * 0.62} L${x + dir * w * 0.82} ${y - h * 0.44} L${x + dir * w * 0.66} ${y - h * 0.2} L${x + dir * w * 0.4} ${y - h * 0.04}`
    return lagGroup('ws-mon__wing', { x, y }, dir * 0.3, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + path(fingers, st(pal, 2.5)) + path(emberEdge, { ...st(pal, 4, edge), opacity: 0.85 }) + glow(path(emberEdge, { ...st(pal, 9, edge), opacity: 0.25 })))
  }
  return { back: wing(-1, 1) + wing(1, 0.8) }
}

export function nubHorns(s: Sockets, fill: string, pal: Palette): PartPiece {
  return { over: g({}, [circle(s.earL.x + 4, s.earL.y, 6, { fill, ...outlined(pal, { 'stroke-width': 2.5 }) }), circle(s.earR.x - 4, s.earR.y, 6, { fill, ...outlined(pal, { 'stroke-width': 2.5 }) })]) }
}

export function sweptHorns(s: Sockets, fill: string, pal: Palette): PartPiece {
  const horn = (p: Pt, dy: number) => {
    const d = `M${p.x} ${p.y + 6} C${p.x - 4} ${p.y - 8 + dy} ${p.x - 28} ${p.y - 14 + dy} ${p.x - 44} ${p.y - 30 + dy}`
    return path(d, st(pal, 11)) + path(d, st(pal, 6.5, fill)) + path(d, { ...st(pal, 2, lighten(fill, 40)), opacity: 0.6 })
  }
  return { back: horn(s.earL, 2) + horn(s.earR, -4) }
}

export function chestGlow(s: Sockets, color: string): PartPiece {
  const c = { x: s.body.x + s.body.rx * 0.5, y: s.body.y - 2 }
  return { over: glow(circle(c.x, c.y, 16, { fill: color, opacity: 0.35 }) + circle(c.x, c.y, 8, { fill: lighten(color, 35), opacity: 0.9 })) }
}

export function chestGrate(s: Sockets, color: string, pal: Palette): PartPiece {
  const c = { x: s.body.x + s.body.rx * 0.5, y: s.body.y - 4 }
  const slits = [-10, 0, 10].map((dx) => rect(c.x + dx - 3, c.y - 12, 6, 24, 3, { fill: color }))
  return {
    over: g({}, [glow(circle(c.x, c.y, 24, { fill: color, opacity: 0.28 })), rect(c.x - 18, c.y - 16, 36, 32, 8, { fill: darken(pal.body, 22), ...outlined(pal) }), ...slits, glow(g({}, [-10, 0, 10].map((dx) => rect(c.x + dx - 2, c.y - 8, 4, 10, 2, { fill: lighten(color, 45), opacity: 0.9 }))))]),
  }
}

export function spadeTail(s: Sockets, fill: string, tip: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 12} ${t.y + 6} C${t.x - 14} ${t.y + 4} ${t.x - 36} ${t.y + 16} ${t.x - 36} ${t.y + 40}`
  const spade = polygon(
    [
      [t.x - 36, t.y + 34],
      [t.x - 48, t.y + 50],
      [t.x - 36, t.y + 62],
      [t.x - 24, t.y + 50],
    ],
    { fill: pal.paint(tip), ...outlined(pal) },
  )
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 10}px ${t.y + 6}px` }, [path(d, st(pal, 18)), path(d, st(pal, 12, pal.paint(fill))), spade]) }
}

/* ---------- Grumblestone ---------- */

export function geodeCracks(s: Sockets, crystal: string, pal: Palette): PartPiece {
  const b = s.body
  const cracks = [
    `M${b.x - 40} ${b.y - 20} l12 8 l-4 12 l14 6`,
    `M${b.x + 10} ${b.y - 34} l6 12 l12 4 l2 12`,
    `M${b.x - 10} ${b.y + 10} l10 10 l-2 12`,
    `M${b.x + 36} ${b.y + 8} l-10 10 l4 10`,
  ]
  const crystalAt = (x: number, y: number, size: number) =>
    glow(
      polygon(
        [
          [x, y - size],
          [x + size * 0.6, y - size * 0.3],
          [x + size * 0.35, y + size * 0.5],
          [x - size * 0.35, y + size * 0.5],
          [x - size * 0.6, y - size * 0.3],
        ],
        { fill: crystal, ...outlined(pal, { 'stroke-width': 2 }) },
      ) + polygon(
        [
          [x, y - size * 0.6],
          [x + size * 0.25, y - size * 0.2],
          [x - size * 0.1, y + size * 0.2],
        ],
        { fill: lighten(crystal, 45), opacity: 0.9 },
      ),
    )
  return {
    over: g({}, [...cracks.map((d) => path(d, { ...st(pal, 2.5), opacity: 0.8 })), crystalAt(b.x - 26, b.y - 6, 12), crystalAt(b.x + 30, b.y - 18, 10), crystalAt(b.x + 4, b.y + 22, 11), crystalAt(b.x - 4, b.y - 30, 8)]),
  }
}

export function ledgeBrows(s: Sockets, fill: string, pal: Palette): PartPiece {
  return { front: g({}, [rect(s.eyeL.x - 16, s.eyeL.y - 18, 30, 10, 3, { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) }), rect(s.eyeR.x - 14, s.eyeR.y - 18, 30, 10, 3, { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) })]) }
}

export function crystalKnuckles(crystal: string, pal: Palette): PartPiece {
  const hand = (x: number, y: number) => g({}, [-10, 0, 10].map((dx) => polygon([[x + dx, y - 10], [x + dx + 5, y], [x + dx - 5, y]], { fill: crystal, ...outlined(pal, { 'stroke-width': 1.5 }) })))
  return { front: hand(66, 210) + hand(190, 210) }
}

export function crystalShoulders(s: Sockets, crystal: string, pal: Palette): PartPiece {
  const b = s.back
  const cluster = (x: number, y: number, dir: number) =>
    glow(
      g({}, [
        polygon([[x, y + 4], [x + dir * 6, y - 18], [x + dir * 14, y + 2]], { fill: crystal, ...outlined(pal, { 'stroke-width': 2 }) }),
        polygon([[x + dir * 12, y + 6], [x + dir * 20, y - 10], [x + dir * 26, y + 4]], { fill: crystal, ...outlined(pal, { 'stroke-width': 2 }) }),
        polygon([[x - dir * 6, y + 6], [x - dir * 2, y - 8], [x + dir * 4, y + 4]], { fill: lighten(crystal, 25), ...outlined(pal, { 'stroke-width': 2 }) }),
      ]),
    )
  return { over: cluster(b.x - 22, b.y + 2, -1) + cluster(b.x + 22, b.y + 2, 1) }
}

/* ---------- Pluckrex ---------- */

export function fanCrest(s: Sockets, fill: string, pal: Palette, fired: boolean, size = 1): PartPiece {
  const c = s.crown
  const blades = [-2, -1, 0, 1, 2].map((i) => {
    const a = (-90 + i * 26) * (Math.PI / 180)
    const len = (30 - Math.abs(i) * 5) * size
    const tipX = c.x + Math.cos(a) * len
    const tipY = c.y + 6 + Math.sin(a) * len
    return polygon(
      [
        [c.x + (i - 0.5) * 6 * size, c.y + 8],
        [tipX, tipY],
        [c.x + (i + 0.5) * 6 * size, c.y + 8],
      ],
      { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) },
    )
  })
  const crest = g({}, blades)
  return { back: fired ? glow(crest) + glow(ellipse(c.x, c.y - 4, 26 * size, 20 * size, { fill: fill, opacity: 0.25 })) : crest }
}

/** A dinosaur muzzle: a wide rounded jaw under the eyes with a toothy grin across it (drawn as the mouth). */
export function dinoJaw(s: Sockets, pal: Palette): string {
  const h = s.head
  const jx = h.x + h.r * 0.22
  const jy = h.y + h.r * 0.48
  const w = h.r * 0.66
  const mouthY = jy + 1
  const teeth = [-0.72, -0.36, 0, 0.36, 0.72].map((f) => polygon([[jx + w * f - 4, mouthY - 2], [jx + w * f, mouthY + 8], [jx + w * f + 4, mouthY - 2]], { fill: '#fff' }))
  return (
    ellipse(jx, jy, h.r * 0.8, h.r * 0.44, { fill: pal.paint(pal.body), ...outlined(pal) }) +
    path(`M${jx - w} ${mouthY - 4} Q${jx} ${mouthY + 18} ${jx + w} ${mouthY - 4} Z`, { fill: pal.outline }) +
    g({}, teeth) +
    circle(jx + h.r * 0.52, jy - h.r * 0.22, 2.2, { fill: pal.outline, opacity: 0.7 }) +
    circle(jx + h.r * 0.68, jy - h.r * 0.16, 2.2, { fill: pal.outline, opacity: 0.7 })
  )
}

/** Small plates along the upper back, from the neck toward the tail. */
export function backRidges(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.body
  const ridges = [-100, -124, -148, -170].map((deg, i) => {
    const a = (deg * Math.PI) / 180
    const x = b.x + b.rx * Math.cos(a)
    const y = b.y + b.ry * Math.sin(a)
    const size = 10 - i
    return polygon(
      [
        [x - 7, y + 5],
        [x - 3 + Math.cos(a) * size, y - 4 + Math.sin(a) * size],
        [x + 6, y + 2],
      ],
      { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) },
    )
  })
  return { back: g({}, ridges) }
}

export function thickTail(s: Sockets, fill: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 12} ${t.y - 16} C${t.x - 18} ${t.y - 12} ${t.x - 46} ${t.y + 4} ${t.x - 44} ${t.y + 22} C${t.x - 24} ${t.y + 28} ${t.x - 4} ${t.y + 18} ${t.x + 12} ${t.y + 12} Z`
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 10}px ${t.y}px` }, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + path(`M${t.x - 6} ${t.y - 4} C${t.x - 18} ${t.y} ${t.x - 30} ${t.y + 8} ${t.x - 36} ${t.y + 18}`, { ...st(pal, 2), opacity: 0.4 })) }
}

export function bracers(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.body
  const x = b.x + 42
  const y = b.y + 2
  return { front: g({}, [rect(x - 10, y - 8, 20, 16, 5, { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) }), line(x - 4, y - 6, x - 4, y + 6, st(pal, 1.5)), line(x + 3, y - 6, x + 3, y + 6, st(pal, 1.5))]) }
}

/* ---------- Paladove ---------- */

export function haloRing(s: Sockets, gold: string): PartPiece {
  const c = { x: s.crown.x, y: s.crown.y - 14 }
  return { front: g({ class: 'ws-mon__halo' }, [glow(ellipse(c.x, c.y, 24, 8, { fill: 'none', stroke: lighten(gold, 30), 'stroke-width': 9, opacity: 0.35 })), ellipse(c.x, c.y, 22, 7, { fill: 'none', stroke: gold, 'stroke-width': 4 }), ellipse(c.x - 6, c.y - 2, 8, 2, { fill: '#fff', opacity: 0.6 })]) }
}

export function tinyCrest(s: Sockets, fill: string, pal: Palette): PartPiece {
  const c = s.crown
  const ds = [-1, 0, 1].map((i) => `M${c.x + i * 4} ${c.y + 6} C${c.x + i * 8} ${c.y - 4} ${c.x + i * 12} ${c.y - 10} ${c.x + i * 14} ${c.y - 16}`)
  return { back: g({}, [...ds.map((d) => path(d, st(pal, 6))), ...ds.map((d) => path(d, st(pal, 3, fill)))]) }
}

export function fourWings(s: Sockets, fill: string, gold: string, pal: Palette): PartPiece {
  const b = s.back
  const wing = (dir: number, scale: number, dy: number, delay: number) => {
    const x = b.x + dir * 6
    const y = b.y + dy
    const w = 86 * scale
    const h = 70 * scale
    const d = `M${x} ${y} C${x + dir * w * 0.3} ${y - h * 0.9} ${x + dir * w * 0.8} ${y - h} ${x + dir * w} ${y - h * 0.55} C${x + dir * w * 0.9} ${y - h * 0.3} ${x + dir * w * 0.7} ${y + 2} ${x + dir * w * 0.4} ${y + 10} C${x + dir * w * 0.2} ${y + 14} ${x + dir * 4} ${y + 10} ${x} ${y} Z`
    const feathers = [0.35, 0.55, 0.75].map((t) => `M${x + dir * w * t} ${y + 8 - t * 10} C${x + dir * w * (t + 0.1)} ${y - h * 0.25} ${x + dir * w * (t + 0.2)} ${y - h * 0.45} ${x + dir * w * (t + 0.25)} ${y - h * 0.6}`)
    return lagGroup('ws-mon__wing', { x, y }, delay, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + g({}, feathers.map((f) => path(f, { ...st(pal, 2), opacity: 0.5 }))) + path(`M${x + dir * w * 0.3} ${y + 10} C${x + dir * w * 0.5} ${y + 6} ${x + dir * w * 0.7} ${y + 2} ${x + dir * w * 0.9} ${y - h * 0.3}`, { ...st(pal, 3, gold), opacity: 0.8 }))
  }
  return { back: wing(-1, 1, 0, -0.2) + wing(1, 0.9, 0, 0.1) + wing(-1, 0.65, 22, -0.6) + wing(1, 0.6, 22, -0.3) }
}

export function chestArmor(s: Sockets, gold: string, pal: Palette): PartPiece {
  const b = s.body
  const c = { x: b.x + 8, y: b.y + 6 }
  const plate = `M${c.x - 24} ${c.y - 18} L${c.x + 24} ${c.y - 18} L${c.x + 20} ${c.y + 14} L${c.x} ${c.y + 26} L${c.x - 20} ${c.y + 14} Z`
  return { over: g({}, [path(plate, { fill: '#fff', ...outlined(pal, { stroke: gold, 'stroke-width': 3.5 }) }), path(`M${c.x} ${c.y - 10} C${c.x - 10} ${c.y - 2} ${c.x - 6} ${c.y + 10} ${c.x} ${c.y + 14} C${c.x + 6} ${c.y + 10} ${c.x + 10} ${c.y - 2} ${c.x} ${c.y - 10} Z`, { fill: gold, opacity: 0.9 }), line(c.x, c.y - 8, c.x, c.y + 12, { ...st(pal, 1.5, '#fff'), opacity: 0.8 })]) }
}

export function featherShield(s: Sockets, gold: string, pal: Palette): PartPiece {
  const c = { x: s.body.x - s.body.rx - 6, y: s.body.y + 8 }
  return { front: g({}, [circle(c.x, c.y, 20, { fill: '#fff', ...outlined(pal, { stroke: gold, 'stroke-width': 4 }) }), circle(c.x, c.y, 13, { fill: 'none', stroke: gold, 'stroke-width': 1.5, opacity: 0.7 }), path(`M${c.x} ${c.y + 10} C${c.x - 8} ${c.y + 2} ${c.x - 6} ${c.y - 8} ${c.x + 2} ${c.y - 11} C${c.x + 6} ${c.y - 2} ${c.x + 4} ${c.y + 4} ${c.x} ${c.y + 10} Z`, { fill: gold }), line(c.x, c.y + 8, c.x + 1, c.y - 8, { ...st(pal, 1.2, '#fff') })]) }
}

/* ---------- Starhowl ---------- */

export function auroraMane(s: Sockets, teal: string, rose: string, pal: Palette): PartPiece {
  const h = s.head
  const strands = [0, 1, 2, 3, 4].map((i) => {
    const x0 = h.x - h.r * 0.5 - i * 6
    const y0 = h.y - h.r * 0.6 + i * 12
    return `M${x0} ${y0} C${x0 - 26} ${y0 + 4 + i * 2} ${x0 - 44} ${y0 + 22} ${x0 - 54 + i * 4} ${y0 + 44 + i * 4}`
  })
  return {
    back: lagGroup('ws-mon__mane', { x: h.x - h.r * 0.5, y: h.y }, -0.5, g({}, [...strands.map((d) => path(d, st(pal, 16))), ...strands.map((d) => path(d, st(pal, 11, teal))), ...strands.map((d) => path(d, { ...st(pal, 5, rose), opacity: 0.85 })), ...strands.map((d) => path(d, { ...st(pal, 1.5, '#fff'), opacity: 0.35 }))])),
  }
}

export function constellations(s: Sockets, pal: Palette): PartPiece {
  const b = s.body
  const pts: [number, number][] = [
    [b.x - 30, b.y - 14],
    [b.x - 12, b.y - 24],
    [b.x + 6, b.y - 12],
    [b.x + 24, b.y - 2],
    [b.x - 20, b.y + 12],
    [b.x + 10, b.y + 18],
  ]
  const brow: [number, number][] = [
    [s.eyeL.x - 2, s.eyeL.y - 16],
    [s.head.x, s.head.y - s.head.r * 0.55],
    [s.eyeR.x + 2, s.eyeR.y - 16],
  ]
  const star = ([x, y]: [number, number], r: number) => circle(x, y, r, { fill: '#fff', opacity: 0.9 })
  return {
    over: g({}, [polyline(pts.slice(0, 4), { ...st(pal, 1, '#fff'), opacity: 0.35 }), ...pts.map((p, i) => star(p, 1.6 + (i % 3) * 0.5)), polyline(brow, { ...st(pal, 1, '#fff'), opacity: 0.5 }), ...brow.map((p) => star(p, 1.8))]),
  }
}

export function starTail(s: Sockets, fill: string, star: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 10} ${t.y + 2} C${t.x - 18} ${t.y - 10} ${t.x - 48} ${t.y - 4} ${t.x - 46} ${t.y - 38}`
  return {
    back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 8}px ${t.y}px` }, [path(d, st(pal, 26)), path(d, st(pal, 20, pal.paint(fill))), glow(path(`M${t.x - 46} ${t.y - 50} l3 8 l8 2 l-7 5 l2 8 l-6 -5 l-6 5 l2 -8 l-7 -5 l8 -2 Z`, { fill: star, ...outlined(pal, { 'stroke-width': 1.5 }) }))]),
  }
}

/* ---------- Petalphant ---------- */

export function petalEars(s: Sockets, fill: string, pal: Palette): PartPiece {
  const ear = (p: Pt, dir: number) => {
    const d = `M${p.x} ${p.y + 10} C${p.x + dir * 10} ${p.y - 30} ${p.x + dir * 56} ${p.y - 26} ${p.x + dir * 50} ${p.y + 14} C${p.x + dir * 44} ${p.y + 40} ${p.x + dir * 10} ${p.y + 34} ${p.x} ${p.y + 10} Z`
    const vein = `M${p.x + dir * 8} ${p.y + 12} C${p.x + dir * 22} ${p.y} ${p.x + dir * 34} ${p.y + 2} ${p.x + dir * 42} ${p.y + 10}`
    return lagGroup('ws-mon__ear', { x: p.x, y: p.y + 10 }, dir * 0.25, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + path(vein, { ...st(pal, 2, lighten(fill, 30)), opacity: 0.8 }))
  }
  return { back: ear(S(s.earL, 6, 4), -1) + ear(S(s.earR, -6, 4), 1) }
}

const S = (p: Pt, dx: number, dy: number): Pt => ({ x: p.x + dx, y: p.y + dy })

export function trunk(s: Sockets, fill: string, bud: string, open: boolean, pal: Palette): PartPiece {
  const h = s.head
  const x0 = h.x + h.r * 0.75
  const y0 = h.y + h.r * 0.3
  const d = `M${x0} ${y0} C${x0 + 18} ${y0 + 10} ${x0 + 20} ${y0 + 40} ${x0 + 6} ${y0 + 52} C${x0 - 2} ${y0 + 60} ${x0 - 4} ${y0 + 62} ${x0 + 2} ${y0 + 66}`
  const tip = { x: x0 + 2, y: y0 + 66 }
  const flower = open
    ? g({}, [...[0, 1, 2, 3, 4].map((i) => ellipse(tip.x + Math.cos((i * 2 * Math.PI) / 5) * 8, tip.y + Math.sin((i * 2 * Math.PI) / 5) * 8, 7, 5, { fill: bud, ...outlined(pal, { 'stroke-width': 1.5 }), transform: `rotate(${(i * 360) / 5} ${tip.x + Math.cos((i * 2 * Math.PI) / 5) * 8} ${tip.y + Math.sin((i * 2 * Math.PI) / 5) * 8})` })), circle(tip.x, tip.y, 5, { fill: '#F7D36B', ...outlined(pal, { 'stroke-width': 1.5 }) })])
    : path(`M${tip.x} ${tip.y - 12} C${tip.x + 9} ${tip.y - 6} ${tip.x + 8} ${tip.y + 6} ${tip.x} ${tip.y + 10} C${tip.x - 8} ${tip.y + 6} ${tip.x - 9} ${tip.y - 6} ${tip.x} ${tip.y - 12} Z`, { fill: bud, ...outlined(pal, { 'stroke-width': 2 }) }) + line(tip.x, tip.y - 10, tip.x, tip.y + 8, { ...st(pal, 1.2, lighten(bud, 35)) })
  return { front: g({ class: 'ws-mon__tail', style: `transform-origin:${x0}px ${y0}px` }, [path(d, st(pal, 18)), path(d, st(pal, 12, pal.paint(fill))), path(d, { ...st(pal, 3, pal.shade), opacity: 0.4, 'stroke-dasharray': '2 5' }), flower]) }
}

export function leafTail(s: Sockets, leaf: string, pal: Palette): PartPiece {
  const t = s.tail
  const leafAt = (x: number, y: number, rot: number) => path(`M${x} ${y} c-10 -4 -14 -14 -8 -22 c10 2 14 12 8 22 Z`, { fill: leaf, ...outlined(pal, { 'stroke-width': 2 }), transform: `rotate(${rot} ${x} ${y})` })
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 8}px ${t.y}px` }, [line(t.x + 8, t.y + 4, t.x - 16, t.y + 18, st(pal, 6)), line(t.x + 8, t.y + 4, t.x - 16, t.y + 18, st(pal, 3, pal.body)), leafAt(t.x - 16, t.y + 18, -30), leafAt(t.x - 18, t.y + 22, 30), leafAt(t.x - 22, t.y + 16, -80)]) }
}

/* ---------- Scrollopus ---------- */

export function spectacles(s: Sockets, rim: string, _pal: Palette): PartPiece {
  const r = s.eyeR_ * 1.9
  return { front: g({}, [circle(s.eyeL.x, s.eyeL.y, r, { fill: 'none', stroke: rim, 'stroke-width': 3 }), circle(s.eyeR.x, s.eyeR.y, r, { fill: 'none', stroke: rim, 'stroke-width': 3 }), line(s.eyeL.x + r, s.eyeL.y, s.eyeR.x - r, s.eyeR.y, { stroke: rim, 'stroke-width': 3 }), circle(s.eyeL.x - r * 0.4, s.eyeL.y - r * 0.4, r * 0.25, { fill: '#fff', opacity: 0.5 }), circle(s.eyeR.x - r * 0.4, s.eyeR.y - r * 0.4, r * 0.25, { fill: '#fff', opacity: 0.5 }), line(s.eyeL.x - r, s.eyeL.y, s.eyeL.x - r - 14, s.eyeL.y - 6, { stroke: rim, 'stroke-width': 2.5 }), line(s.eyeR.x + r, s.eyeR.y, s.eyeR.x + r + 14, s.eyeR.y - 6, { stroke: rim, 'stroke-width': 2.5 })]) }
}

export function scholarCap(s: Sockets, cap: string, tassel: string, pal: Palette): PartPiece {
  const c = s.crown
  return {
    over: g({}, [
      rect(c.x - 22, c.y - 6, 44, 14, 5, { fill: cap, ...outlined(pal) }),
      polygon(
        [
          [c.x - 34, c.y - 8],
          [c.x, c.y - 22],
          [c.x + 34, c.y - 8],
          [c.x, c.y + 2],
        ],
        { fill: lighten(cap, 12), ...outlined(pal) },
      ),
      g({ class: 'ws-mon__tail', style: `transform-origin:${c.x + 10}px ${c.y - 14}px` }, [path(`M${c.x + 10} ${c.y - 14} C${c.x + 22} ${c.y - 12} ${c.x + 30} ${c.y - 2} ${c.x + 32} ${c.y + 12}`, { ...st(pal, 2, tassel) }), path(`M${c.x + 26} ${c.y + 10} l12 0 l2 14 l-16 0 Z`, { fill: tassel, ...outlined(pal, { 'stroke-width': 1.5 }) })]),
    ]),
  }
}

export function tentacleItems(s: Sockets, pal: Palette): PartPiece {
  const b = s.body
  const y0 = b.y + b.ry - 14
  const tip = (i: number) => ({ x: b.x - 52 + i * 15 + (i % 2 === 0 ? -1 : 1) * 4, y: y0 + 58 })
  const scroll = (p: Pt) => g({}, [rect(p.x - 12, p.y - 8, 24, 14, 3, { fill: '#F3E6C4', ...outlined(pal, { 'stroke-width': 2 }) }), circle(p.x - 12, p.y - 1, 5, { fill: '#E7D5A8', ...outlined(pal, { 'stroke-width': 2 }) }), circle(p.x + 12, p.y - 1, 5, { fill: '#E7D5A8', ...outlined(pal, { 'stroke-width': 2 }) }), line(p.x - 6, p.y - 3, p.x + 6, p.y - 3, { ...st(pal, 1.2), opacity: 0.6 }), line(p.x - 6, p.y + 1, p.x + 4, p.y + 1, { ...st(pal, 1.2), opacity: 0.6 })])
  const quill = (p: Pt) => g({}, [path(`M${p.x - 10} ${p.y + 10} L${p.x + 8} ${p.y - 16}`, st(pal, 3)), path(`M${p.x - 2} ${p.y - 4} c4 -10 10 -14 14 -14 c-2 8 -6 12 -14 14 Z`, { fill: '#F5F8FC', ...outlined(pal, { 'stroke-width': 2 }) })])
  const book = (p: Pt) => g({}, [rect(p.x - 12, p.y - 9, 24, 18, 2, { fill: '#B85B4E', ...outlined(pal, { 'stroke-width': 2 }) }), rect(p.x - 9, p.y - 6, 18, 12, 1, { fill: '#F3E6C4' }), line(p.x, p.y - 9, p.x, p.y + 9, st(pal, 1.5))])
  return { front: scroll(tip(1)) + quill(tip(4)) + book(tip(6)) }
}

export function inkFreckles(s: Sockets, ink: string): PartPiece {
  const pts: [number, number][] = [
    [s.cheekL.x - 6, s.cheekL.y - 4],
    [s.cheekL.x + 4, s.cheekL.y + 6],
    [s.cheekR.x + 6, s.cheekR.y - 2],
    [s.cheekR.x - 4, s.cheekR.y + 7],
    [s.body.x - 34, s.body.y + 24],
    [s.body.x + 38, s.body.y + 18],
  ]
  return { over: g({}, pts.map(([x, y], i) => circle(x, y, 1.6 + (i % 2), { fill: ink, opacity: 0.75 }))) }
}

/* ---------- Gloomgrin ---------- */

export function runeLines(s: Sockets, color: string): PartPiece {
  const b = s.body
  const ds = [`M${b.x - 26} ${b.y - 14} l8 6 l-6 8 l10 4`, `M${b.x + 14} ${b.y - 20} l6 8 l-8 6 l6 10`, `M${s.head.x - 16} ${s.head.y + 10} l6 4 l-4 6`, `M${b.x - 4} ${b.y + 14} l10 2 l-4 10`]
  return { over: glow(g({}, ds.map((d) => path(d, { fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: 0.8 })))) }
}

export function stubbyHorns(s: Sockets, fill: string, pal: Palette): PartPiece {
  const horn = (p: Pt, dir: number) => polygon([[p.x - 7, p.y + 8], [p.x + dir * 3, p.y - 12], [p.x + 7, p.y + 6]], { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) })
  return { over: horn(S(s.earL, 2, 0), -0.6) + horn(S(s.earR, -2, 0), 0.6) }
}

export function batWings(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.back
  const wing = (dir: number) => {
    const x = b.x + dir * 8
    const y = b.y + 2
    const d = `M${x} ${y} C${x + dir * 10} ${y - 30} ${x + dir * 44} ${y - 40} ${x + dir * 54} ${y - 22} L${x + dir * 44} ${y - 12} L${x + dir * 36} ${y - 2} L${x + dir * 22} ${y + 4} Z`
    return lagGroup('ws-mon__wing', { x, y }, dir * 0.2, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + path(`M${x + dir * 4} ${y - 4} L${x + dir * 44} ${y - 12} M${x + dir * 4} ${y - 4} L${x + dir * 36} ${y - 2}`, { ...st(pal, 2), opacity: 0.5 }))
  }
  return { back: wing(-1) + wing(1) }
}

export function impTail(s: Sockets, fill: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 8} ${t.y} C${t.x - 16} ${t.y + 4} ${t.x - 30} ${t.y - 18} ${t.x - 18} ${t.y - 30} C${t.x - 10} ${t.y - 38} ${t.x} ${t.y - 30} ${t.x - 6} ${t.y - 24}`
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 6}px ${t.y}px` }, [path(d, st(pal, 9)), path(d, st(pal, 5, pal.paint(fill))), polygon([[t.x - 12, t.y - 26], [t.x - 4, t.y - 34], [t.x - 2, t.y - 22]], { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2 }) })]) }
}

export function squareGrin(s: Sockets, pal: Palette): string {
  const m = s.mouth
  const w = s.eyeR_ * 3
  return path(`M${m.x - w} ${m.y - 2} Q${m.x} ${m.y + w * 0.9} ${m.x + w} ${m.y - 2} Z`, { fill: pal.outline }) + rect(m.x - w * 0.8, m.y, w * 1.6, w * 0.38, 1, { fill: '#fff' }) + g({}, [-0.4, 0, 0.4].map((f) => line(m.x + w * f, m.y, m.x + w * f, m.y + w * 0.38, { stroke: pal.outline, 'stroke-width': 1.5 })))
}

/* ---------- Rammerjack ---------- */

export function spiralHorns(s: Sockets, fill: string, rope: string, pal: Palette): PartPiece {
  const horn = (p: Pt, dir: number) => {
    const d = `M${p.x} ${p.y + 6} C${p.x - 2} ${p.y - 14} ${p.x - 30} ${p.y - 22} ${p.x - 36} ${p.y - 4} C${p.x - 40} ${p.y + 10} ${p.x - 24} ${p.y + 18} ${p.x - 16} ${p.y + 8} C${p.x - 10} ${p.y} ${p.x - 18} ${p.y - 6} ${p.x - 22} ${p.y - 2}`
    const bands = [0.2, 0.45].map((t) => {
      const x = p.x - 36 * t
      const y = p.y - 10 - 6 * t
      return line(x - 4, y - 5, x + 4, y + 5, { stroke: rope, 'stroke-width': 3 })
    })
    return g({ transform: dir < 0 ? '' : `translate(${2 * p.x} 0) scale(-1 1)` }, [path(d, st(pal, 15)), path(d, st(pal, 10, pal.paint(fill))), path(d, { ...st(pal, 2, lighten(fill, 30)), opacity: 0.5 }), ...bands])
  }
  return { back: horn(S(s.earL, 4, -2), -1) + horn(S(s.earR, -4, -2), 1) }
}

export function beard(s: Sockets, fill: string, pal: Palette): PartPiece {
  const c = s.chin
  return { front: path(`M${c.x - 14} ${c.y - 6} C${c.x - 12} ${c.y + 10} ${c.x - 8} ${c.y + 18} ${c.x - 6} ${c.y + 26} L${c.x} ${c.y + 18} L${c.x + 6} ${c.y + 28} L${c.x + 10} ${c.y + 16} L${c.x + 16} ${c.y + 22} C${c.x + 16} ${c.y + 8} ${c.x + 14} ${c.y - 2} ${c.x + 12} ${c.y - 6} Z`, { fill: pal.paint(fill), ...outlined(pal, { 'stroke-width': 2.5 }) }) }
}

export function scarf(s: Sockets, red: string, pal: Palette): PartPiece {
  const h = s.head
  const y = h.y + h.r - 2
  const band = rect(h.x - h.r * 0.9, y - 6, h.r * 1.8, 14, 6, { fill: red, ...outlined(pal, { 'stroke-width': 2.5 }) })
  const tail = `M${h.x - h.r * 0.6} ${y + 4} C${h.x - h.r * 0.9} ${y + 20} ${h.x - h.r * 1.3} ${y + 24} ${h.x - h.r * 1.4} ${y + 40}`
  return {
    front: band + g({}, [line(h.x - h.r * 0.6, y - 4, h.x - h.r * 0.5, y + 6, { stroke: darken(red, 20), 'stroke-width': 1.5 }), line(h.x - h.r * 0.2, y - 4, h.x - h.r * 0.1, y + 6, { stroke: darken(red, 20), 'stroke-width': 1.5 }), line(h.x + h.r * 0.2, y - 4, h.x + h.r * 0.3, y + 6, { stroke: darken(red, 20), 'stroke-width': 1.5 })]),
    back: lagGroup('ws-mon__mane', { x: h.x - h.r * 0.6, y: y + 4 }, -0.7, path(tail, st(pal, 15)) + path(tail, st(pal, 10, red)) + polygon([[h.x - h.r * 1.5, y + 38], [h.x - h.r * 1.3, y + 38], [h.x - h.r * 1.45, y + 48]], { fill: red, ...outlined(pal, { 'stroke-width': 2 }) })),
  }
}

export function hooves(xs: number[], color: string, pal: Palette): PartPiece {
  return { over: g({}, xs.map((x) => rect(x - 10, 218, 20, 12, 5, { fill: color, ...outlined(pal, { 'stroke-width': 2 }) }))) }
}

export function brows(s: Sockets, pal: Palette): PartPiece {
  return { front: g({}, [line(s.eyeL.x - 12, s.eyeL.y - 14, s.eyeL.x + 8, s.eyeL.y - 18, st(pal, 5)), line(s.eyeR.x - 8, s.eyeR.y - 18, s.eyeR.x + 12, s.eyeR.y - 14, st(pal, 5))]) }
}

/* ---------- Frostlance ---------- */

export function iceTusk(s: Sockets, ice: string, pal: Palette): PartPiece {
  const h = s.head
  const x0 = h.x + h.r * 0.75
  const y0 = h.y + 2
  const len = 70
  const tusk = polygon(
    [
      [x0, y0 - 6],
      [x0 + len, y0 - 10],
      [x0, y0 + 6],
    ],
    { fill: ice, ...outlined(pal, { 'stroke-width': 2.5 }) },
  )
  const spirals = [0.15, 0.32, 0.5, 0.68, 0.84].map((t) => line(x0 + len * t, y0 - 6 + 5 * (1 - t), x0 + len * (t + 0.08), y0 + 6 - 5 * (1 - t) - 2, { stroke: pal.outline, 'stroke-width': 1.3, opacity: 0.55 }))
  return { front: g({}, [tusk, ...spirals, line(x0 + 4, y0 - 3, x0 + len * 0.6, y0 - 6, { stroke: '#fff', 'stroke-width': 1.5, opacity: 0.7 })]) }
}

export function frostFins(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.body
  const dorsal = `M${b.x - 10} ${b.y - b.ry + 4} C${b.x - 4} ${b.y - b.ry - 24} ${b.x + 22} ${b.y - b.ry - 20} ${b.x + 26} ${b.y - b.ry + 2} Z`
  const side = `M${b.x + 10} ${b.y + 12} C${b.x + 6} ${b.y + 34} ${b.x - 20} ${b.y + 40} ${b.x - 24} ${b.y + 30} C${b.x - 14} ${b.y + 24} ${b.x - 4} ${b.y + 16} ${b.x + 10} ${b.y + 12} Z`
  const fluke = `M${b.x - b.rx + 8} ${b.y} C${b.x - b.rx - 10} ${b.y - 20} ${b.x - b.rx - 26} ${b.y - 24} ${b.x - b.rx - 30} ${b.y - 12} C${b.x - b.rx - 20} ${b.y - 4} ${b.x - b.rx - 20} ${b.y + 4} ${b.x - b.rx - 30} ${b.y + 12} C${b.x - b.rx - 26} ${b.y + 24} ${b.x - b.rx - 10} ${b.y + 20} ${b.x - b.rx + 8} ${b.y} Z`
  const frost = { stroke: '#fff', 'stroke-width': 2, 'stroke-dasharray': '3 4', opacity: 0.7, fill: 'none' }
  return {
    back: lagGroup('ws-mon__fin', { x: b.x - b.rx + 8, y: b.y }, -0.3, path(fluke, { fill: pal.paint(fill), ...outlined(pal) }) + path(fluke, frost)) + lagGroup('ws-mon__fin', { x: b.x, y: b.y - b.ry + 4 }, 0.2, path(dorsal, { fill: pal.paint(fill), ...outlined(pal) }) + path(dorsal, frost)),
    front: lagGroup('ws-mon__fin', { x: b.x + 10, y: b.y + 12 }, -0.6, path(side, { fill: pal.paint(fill), ...outlined(pal) }) + path(side, frost)),
  }
}

export function tealBack(s: Sockets, color: string): PartPiece {
  const b = s.body
  const d = `M${b.x - b.rx + 14} ${b.y - 6} C${b.x - b.rx * 0.5} ${b.y - b.ry - 2} ${b.x + b.rx * 0.6} ${b.y - b.ry - 2} ${b.x + b.rx - 8} ${b.y - 6} C${b.x + b.rx * 0.5} ${b.y - 10} ${b.x - b.rx * 0.5} ${b.y - 10} ${b.x - b.rx + 14} ${b.y - 6} Z`
  const flakes: [number, number][] = [
    [b.x - 30, b.y - 18],
    [b.x - 6, b.y - 24],
    [b.x + 18, b.y - 20],
    [b.x + 36, b.y - 12],
  ]
  return { over: g({}, [path(d, { fill: color, opacity: 0.9 }), ...flakes.map(([x, y]) => path(`M${x - 3} ${y} h6 M${x} ${y - 3} v6 M${x - 2} ${y - 2} l4 4 M${x + 2} ${y - 2} l-4 4`, { stroke: '#fff', 'stroke-width': 1.2, opacity: 0.85 }))]) }
}

export { limb }
