import { outlined, type Pt, type Sockets } from './bodyPlans.ts'
import type { Palette } from './palettes.ts'
import { circle, ellipse, g, lighten, line, path, poly, polygon, polyline, rect } from './svg.ts'

/**
 * Shared parametric parts (GAME_DESIGN §22): ears, tails, crests and the like, drawn at a socket.
 * The 20 breed looks use them for their own features, and the ACCENTS table uses them for the one
 * part a sub breed adds to the main body (§14.3, CONTENT §2.2 "accent").
 */

export interface PartPiece {
  /** Drawn behind the body. */
  back?: string
  /** Drawn over the body, under the face. */
  over?: string
  /** Drawn in front of everything. */
  front?: string
}

const S = (p: Pt, dx: number, dy: number): Pt => ({ x: p.x + dx, y: p.y + dy })

/** Secondary motion: a part that lags a little behind the body (ears, wings, manes, fins). */
export function lagGroup(cls: 'ws-mon__ear' | 'ws-mon__wing' | 'ws-mon__mane' | 'ws-mon__fin', origin: Pt, delay: number, inner: string): string {
  return g({ class: cls, style: `transform-origin:${origin.x}px ${origin.y}px;animation-delay:${delay}s` }, inner)
}

/* ---------- ears, crowns ---------- */

export function finEars(s: Sockets, fill: string, inner: string, pal: Palette): PartPiece {
  const ear = (p: Pt, dir: number) => {
    const d = `M${p.x} ${p.y + 6} C${p.x + dir * 6} ${p.y - 22} ${p.x + dir * 34} ${p.y - 18} ${p.x + dir * 30} ${p.y + 8} C${p.x + dir * 28} ${p.y + 22} ${p.x + dir * 8} ${p.y + 20} ${p.x} ${p.y + 6} Z`
    const i = `M${p.x + dir * 6} ${p.y + 6} C${p.x + dir * 9} ${p.y - 10} ${p.x + dir * 26} ${p.y - 8} ${p.x + dir * 22} ${p.y + 8} Z`
    return lagGroup('ws-mon__ear', { x: p.x, y: p.y + 6 }, dir * 0.2, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + path(i, { fill: inner, opacity: 0.8 }))
  }
  return { back: ear(S(s.earL, 2, 0), -1) + ear(S(s.earR, -2, 0), 1) }
}

export function pointedEars(s: Sockets, fill: string, inner: string, pal: Palette): PartPiece {
  const ear = (p: Pt, dir: number) =>
    lagGroup(
      'ws-mon__ear',
      { x: p.x, y: p.y + 8 },
      dir * 0.3,
      polygon(
        [
          [p.x - 10, p.y + 10],
          [p.x + dir * 6, p.y - 24],
          [p.x + 12, p.y + 8],
        ],
        { fill: pal.paint(fill), ...outlined(pal) },
      ) +
        polygon(
          [
            [p.x - 4, p.y + 6],
            [p.x + dir * 4, p.y - 12],
            [p.x + 7, p.y + 5],
          ],
          { fill: inner, opacity: 0.85 },
        ),
    )
  return { back: ear(s.earL, -0.4) + ear(s.earR, 0.4) }
}

export function emberTufts(s: Sockets, fill: string, pal: Palette): PartPiece {
  const tuft = (p: Pt, dir: number) =>
    lagGroup(
      'ws-mon__ear',
      { x: p.x, y: p.y + 2 },
      dir * 0.25,
      polygon(
        [
          [p.x - 8, p.y + 2],
          [p.x + dir * 4, p.y - 30],
          [p.x + 9, p.y + 2],
        ],
        { fill: pal.paint(fill), ...outlined(pal) },
      ) + circle(p.x + dir * 4, p.y - 24, 3, { fill: lighten(fill, 45) }),
    )
  return { back: tuft(S(s.earL, 0, -8), -0.5) + tuft(S(s.earR, 0, -8), 0.5) }
}

export function featherCrest(s: Sockets, fill: string, pal: Palette): PartPiece {
  const c = s.crown
  const feathers = [-2, -1, 0, 1, 2].map((i) => {
    const dx = i * 11
    return path(`M${c.x + dx * 0.4} ${c.y + 6} C${c.x + dx * 0.6} ${c.y - 6} ${c.x + dx * 1.3} ${c.y - 18} ${c.x + dx * 1.8} ${c.y - 26 + Math.abs(i) * 5}`, { fill: 'none', stroke: fill, 'stroke-width': 7, 'stroke-linecap': 'round' })
  })
  return { back: g({}, [...feathers.map((f) => f.replace(`stroke="${fill}"`, `stroke="${pal.outline}"`).replace('stroke-width="7"', 'stroke-width="11"')), ...feathers]) }
}

export function crestPlumes(s: Sockets, fill: string, pal: Palette): PartPiece {
  const c = s.crown
  const plume = (dy: number, len: number) => `M${c.x} ${c.y + 4 + dy} C${c.x - 14} ${c.y - 6 + dy} ${c.x - len * 0.6} ${c.y - 2 + dy} ${c.x - len} ${c.y + 10 + dy}`
  const ds = [plume(0, 44), plume(6, 36), plume(12, 26)]
  return { back: g({}, [...ds.map((d) => path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 9, 'stroke-linecap': 'round' })), ...ds.map((d) => path(d, { fill: 'none', stroke: fill, 'stroke-width': 5, 'stroke-linecap': 'round' }))]) }
}

export function antennaNubs(s: Sockets, fill: string, pal: Palette): PartPiece {
  const nub = (p: Pt, dir: number) => line(p.x, p.y + 6, p.x + dir * 8, p.y - 14, { stroke: pal.outline, 'stroke-width': 5, 'stroke-linecap': 'round' }) + circle(p.x + dir * 8, p.y - 14, 5, { fill: pal.paint(fill), ...outlined(pal) })
  return { back: nub(S(s.crown, -10, 2), -1) + nub(S(s.crown, 10, 2), 1) }
}

export function featheryAntennae(s: Sockets, fill: string, pal: Palette): PartPiece {
  const one = (p: Pt, dir: number) => {
    const stem = `M${p.x} ${p.y + 4} C${p.x + dir * 6} ${p.y - 14} ${p.x + dir * 18} ${p.y - 24} ${p.x + dir * 30} ${p.y - 34}`
    const barbs = [0.3, 0.5, 0.7, 0.9].map((t) => {
      const x = p.x + dir * 30 * t
      const y = p.y + 4 - 38 * t
      return line(x, y, x + dir * 6, y - 8, { stroke: fill, 'stroke-width': 3, 'stroke-linecap': 'round' }) + line(x, y, x - dir * 2, y - 9, { stroke: fill, 'stroke-width': 3, 'stroke-linecap': 'round' })
    })
    return path(stem, { fill: 'none', stroke: pal.outline, 'stroke-width': 6, 'stroke-linecap': 'round' }) + path(stem, { fill: 'none', stroke: fill, 'stroke-width': 3, 'stroke-linecap': 'round' }) + barbs.join('')
  }
  return { back: one(S(s.crown, -8, 4), -1) + one(S(s.crown, 8, 4), 1) }
}

export function curledHorns(s: Sockets, fill: string, pal: Palette): PartPiece {
  const horn = (p: Pt, dir: number) => {
    const d = `M${p.x} ${p.y + 6} C${p.x + dir * 4} ${p.y - 10} ${p.x + dir * 26} ${p.y - 12} ${p.x + dir * 24} ${p.y + 4} C${p.x + dir * 22} ${p.y + 14} ${p.x + dir * 10} ${p.y + 12} ${p.x + dir * 12} ${p.y + 4}`
    return path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 12, 'stroke-linecap': 'round' }) + path(d, { fill: 'none', stroke: fill, 'stroke-width': 7, 'stroke-linecap': 'round' })
  }
  return { back: horn(s.earL, -1) + horn(s.earR, 1) }
}

export function antlers(s: Sockets, fill: string, pal: Palette): PartPiece {
  const one = (p: Pt, dir: number) => {
    const d = `M${p.x} ${p.y + 6} L${p.x + dir * 6} ${p.y - 14} L${p.x + dir * 16} ${p.y - 26} M${p.x + dir * 6} ${p.y - 14} L${p.x - dir * 4} ${p.y - 28}`
    return path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }) + path(d, { fill: 'none', stroke: fill, 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
  }
  return { back: one(S(s.crown, -10, 6), -1) + one(S(s.crown, 10, 6), 1) }
}

/* ---------- tails ---------- */

export function tadpoleTail(s: Sockets, fill: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 10} ${t.y - 6} C${t.x - 10} ${t.y - 30} ${t.x - 40} ${t.y - 10} ${t.x - 26} ${t.y + 12} C${t.x - 16} ${t.y + 26} ${t.x} ${t.y + 14} ${t.x + 10} ${t.y + 6} Z`
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 8}px ${t.y}px` }, path(d, { fill: pal.paint(fill), ...outlined(pal) })) }
}

export function curledTail(s: Sockets, fill: string, tip: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 12} ${t.y + 10} C${t.x - 20} ${t.y + 20} ${t.x - 56} ${t.y - 10} ${t.x - 36} ${t.y - 44} C${t.x - 22} ${t.y - 66} ${t.x + 12} ${t.y - 56} ${t.x + 8} ${t.y - 34} C${t.x + 6} ${t.y - 22} ${t.x - 10} ${t.y - 20} ${t.x - 14} ${t.y - 30}`
  return {
    back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 10}px ${t.y + 8}px` }, [
      path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 30, 'stroke-linecap': 'round' }),
      path(d, { fill: 'none', stroke: pal.paint(fill), 'stroke-width': 23, 'stroke-linecap': 'round' }),
      circle(t.x - 14, t.y - 30, 9, { fill: tip }),
    ]),
  }
}

export function tasselTail(s: Sockets, fill: string, pal: Palette): PartPiece {
  const t = s.tail
  const stem = `M${t.x} ${t.y} C${t.x - 2} ${t.y + 12} ${t.x + 4} ${t.y + 18} ${t.x + 2} ${t.y + 28}`
  const tassel = poly(
    [
      [t.x - 8, t.y + 28],
      [t.x + 12, t.y + 28],
      [t.x + 14, t.y + 50],
      [t.x - 10, t.y + 50],
    ],
    true,
  )
  return {
    front: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x}px ${t.y}px` }, [
      path(stem, { fill: 'none', stroke: pal.outline, 'stroke-width': 4, 'stroke-linecap': 'round' }),
      path(tassel, { fill: pal.paint(fill), ...outlined(pal) }),
      line(t.x - 4, t.y + 36, t.x - 4, t.y + 48, { stroke: pal.outline, 'stroke-width': 2 }),
      line(t.x + 2, t.y + 36, t.x + 2, t.y + 48, { stroke: pal.outline, 'stroke-width': 2 }),
      line(t.x + 8, t.y + 36, t.x + 8, t.y + 48, { stroke: pal.outline, 'stroke-width': 2 }),
    ]),
  }
}

export function emberTail(s: Sockets, fill: string, tip: string, pal: Palette): PartPiece {
  const t = s.tail
  const d = `M${t.x + 10} ${t.y + 4} C${t.x - 16} ${t.y + 4} ${t.x - 34} ${t.y - 20} ${t.x - 26} ${t.y - 44}`
  return {
    back: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x + 8}px ${t.y + 4}px` }, [
      path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 18, 'stroke-linecap': 'round' }),
      path(d, { fill: 'none', stroke: fill, 'stroke-width': 12, 'stroke-linecap': 'round' }),
      circle(t.x - 26, t.y - 44, 8, { fill: tip, ...outlined(pal) }),
    ]),
  }
}

export function zigzagTail(s: Sockets, fill: string, pal: Palette): PartPiece {
  const t = s.tail
  const pts: [number, number][] = [
    [t.x, t.y],
    [t.x - 12, t.y + 14],
    [t.x + 4, t.y + 24],
    [t.x - 10, t.y + 38],
    [t.x + 2, t.y + 48],
  ]
  return {
    front: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x}px ${t.y}px` }, [polyline(pts, { stroke: pal.outline, 'stroke-width': 10, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }), polyline(pts, { stroke: fill, 'stroke-width': 5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' })]),
  }
}

export function trailingWisps(s: Sockets, fill: string, pal: Palette): PartPiece {
  const t = s.tail
  const wisp = (dx: number, len: number) => `M${t.x + dx} ${t.y - 4} C${t.x + dx - 10} ${t.y + len * 0.4} ${t.x + dx + 12} ${t.y + len * 0.7} ${t.x + dx - 2} ${t.y + len}`
  const ds = [wisp(-18, 36), wisp(0, 46), wisp(18, 32)]
  return {
    front: g({ class: 'ws-mon__tail', style: `transform-origin:${t.x}px ${t.y}px` }, [
      ...ds.map((d) => path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 9, 'stroke-linecap': 'round', opacity: 0.5 })),
      ...ds.map((d) => path(d, { fill: 'none', stroke: fill, 'stroke-width': 6, 'stroke-linecap': 'round', opacity: 0.85 })),
    ]),
  }
}

export function ribbonFins(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.back
  const ribbon = (ox: number, oy: number, len: number) => `M${b.x + ox} ${b.y + oy} C${b.x + ox - 10} ${b.y + oy - 30} ${b.x + ox - len * 0.5} ${b.y + oy - 10} ${b.x + ox - len} ${b.y + oy - 40} C${b.x + ox - len * 0.7} ${b.y + oy - 46} ${b.x + ox - 24} ${b.y + oy - 24} ${b.x + ox - 6} ${b.y + oy + 6} Z`
  const ds = [ribbon(0, 0, 60), ribbon(30, 6, 48), ribbon(-28, 10, 40)]
  return { back: g({ class: 'ws-mon__tail', style: `transform-origin:${b.x}px ${b.y}px` }, ds.map((d) => path(d, { fill: pal.paint(fill), ...outlined(pal) }))) }
}

/* ---------- backs ---------- */

export function stonePlates(s: Sockets, fill: string, moss: string, pal: Palette): PartPiece {
  const b = s.back
  const plate = (x: number, y: number, w: number, h: number) => rect(x, y, w, h, 7, { fill: pal.paint(fill), ...outlined(pal) })
  return {
    over: g({}, [plate(b.x - 24, b.y - 10, 30, 20), plate(b.x + 10, b.y - 14, 34, 22), plate(b.x - 6, b.y + 10, 26, 16), circle(b.x + 2, b.y - 12, 6, { fill: moss }), circle(b.x + 30, b.y - 18, 5, { fill: moss }), circle(b.x - 18, b.y + 8, 4, { fill: moss })]),
  }
}

export function crenellatedRim(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.back
  const teeth = [-30, -10, 10, 30].map((dx) => rect(b.x + dx - 7, b.y - 14, 14, 16, 2, { fill: pal.paint(fill), ...outlined(pal) }))
  return { over: g({}, [rect(b.x - 40, b.y - 2, 80, 10, 3, { fill: pal.paint(fill), ...outlined(pal) }), ...teeth]) }
}

export function backQuills(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.back
  const quills = [0, 1, 2, 3, 4].map((i) => {
    const x = b.x - 6 + i * 9
    const y = b.y + 6 - Math.abs(i - 2) * 3
    return polygon(
      [
        [x - 6, y + 8],
        [x - 10 + i * 2, y - 26],
        [x + 6, y + 8],
      ],
      { fill: pal.paint(fill), ...outlined(pal) },
    )
  })
  return { back: g({}, quills) }
}

export function cloudTufts(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.back
  return { over: g({}, [circle(b.x - 18, b.y + 2, 13, { fill: pal.paint(fill), ...outlined(pal) }), circle(b.x, b.y - 8, 16, { fill: pal.paint(fill), ...outlined(pal) }), circle(b.x + 20, b.y + 2, 13, { fill: pal.paint(fill), ...outlined(pal) }), circle(b.x, b.y - 8, 13, { fill: pal.paint(fill) }), circle(b.x - 18, b.y + 2, 10, { fill: pal.paint(fill) }), circle(b.x + 20, b.y + 2, 10, { fill: pal.paint(fill) })]) }
}

export function ribbonCloak(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.body
  const d = `M${b.x - b.rx * 0.5} ${b.y - b.ry * 0.7} C${b.x - b.rx * 1.3} ${b.y - b.ry * 0.2} ${b.x - b.rx * 1.2} ${b.y + b.ry * 0.9} ${b.x - b.rx * 0.9} ${b.y + b.ry * 1.05} L${b.x - b.rx * 0.5} ${b.y + b.ry * 0.8} L${b.x - b.rx * 0.2} ${b.y + b.ry * 1.1} L${b.x + b.rx * 0.2} ${b.y + b.ry * 0.85} L${b.x + b.rx * 0.6} ${b.y + b.ry * 1.05} C${b.x + b.rx * 1.2} ${b.y + b.ry * 0.9} ${b.x + b.rx * 1.3} ${b.y - b.ry * 0.2} ${b.x + b.rx * 0.5} ${b.y - b.ry * 0.7} Z`
  return { back: lagGroup('ws-mon__mane', { x: b.x, y: b.y - b.ry * 0.7 }, -0.4, path(d, { fill: pal.paint(fill), ...outlined(pal) }) + circle(b.x, b.y - b.ry * 0.68, 7, { fill: lighten(fill, 30), ...outlined(pal) })) }
}

export function gearWings(s: Sockets, fill: string, pal: Palette): PartPiece {
  const b = s.body
  const gear = (cx: number, cy: number, r: number) => {
    const teeth: [number, number][] = []
    for (let i = 0; i < 16; i++) {
      const a = (i * Math.PI) / 8
      const rr = i % 2 === 0 ? r : r * 0.78
      teeth.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr])
    }
    return g({ class: 'ws-mon__gear', style: `animation-duration:${(r / 4).toFixed(1)}s` }, polygon(teeth, { fill: pal.paint(fill), ...outlined(pal) }) + circle(cx, cy, r * 0.3, { fill: pal.outline }))
  }
  return { back: g({}, [gear(b.x - b.rx - 4, b.y - 6, 26), gear(b.x - b.rx - 22, b.y + 20, 17), gear(b.x + b.rx + 4, b.y - 6, 26), gear(b.x + b.rx + 22, b.y + 20, 17)]) }
}

/* ---------- fronts, chins ---------- */

export function throatSac(s: Sockets, fill: string, pal: Palette): PartPiece {
  const c = s.chin
  return { front: g({ class: 'ws-mon__body' }, circle(c.x, c.y + 10, 22, { fill: pal.paint(fill), ...outlined(pal) }) + ellipse(c.x - 6, c.y + 4, 7, 4, { fill: lighten(fill, 35), opacity: 0.8 })) }
}

export function coralClaw(s: Sockets, fill: string, pal: Palette): PartPiece {
  const f = s.front
  const arm = `M${f.x - 24} ${f.y + 10} L${f.x} ${f.y}`
  const claw = `M${f.x - 4} ${f.y + 12} C${f.x + 20} ${f.y + 30} ${f.x + 50} ${f.y + 10} ${f.x + 34} ${f.y - 16} C${f.x + 26} ${f.y - 30} ${f.x + 6} ${f.y - 24} ${f.x + 2} ${f.y - 10} Z`
  const branches = [`M${f.x + 30} ${f.y - 16} l10 -14 M${f.x + 34} ${f.y - 20} l12 -4`, `M${f.x + 36} ${f.y + 4} l14 6 M${f.x + 40} ${f.y + 10} l6 10`]
  return {
    front: g({}, [path(arm, { fill: 'none', stroke: pal.outline, 'stroke-width': 14, 'stroke-linecap': 'round' }), path(arm, { fill: 'none', stroke: fill, 'stroke-width': 8, 'stroke-linecap': 'round' }), ...branches.map((d) => path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 9, 'stroke-linecap': 'round' })), ...branches.map((d) => path(d, { fill: 'none', stroke: fill, 'stroke-width': 5, 'stroke-linecap': 'round' })), path(claw, { fill: pal.paint(fill), ...outlined(pal) }), path(`M${f.x + 8} ${f.y - 2} L${f.x + 30} ${f.y + 2}`, { stroke: pal.outline, 'stroke-width': 3, 'stroke-linecap': 'round' })]),
  }
}

export function goldLid(s: Sockets, fill: string, pal: Palette): PartPiece {
  const c = s.crown
  return { over: g({}, [rect(c.x - 26, c.y - 18, 52, 20, 6, { fill: pal.shade, ...outlined(pal) }), rect(c.x - 28, c.y - 4, 56, 8, 3, { fill: pal.paint(fill), ...outlined(pal) }), rect(c.x - 6, c.y - 22, 12, 10, 2, { fill: pal.paint(fill), ...outlined(pal) })]) }
}

/* ---------- faces ---------- */

export type EyeStyle = 'round' | 'beady' | 'painted' | 'ember' | 'lidded' | 'dot'
export type MouthStyle = 'smile' | 'grin' | 'flat' | 'frown' | 'open' | 'wobble' | 'beak' | 'chew' | 'fangs' | 'none' | 'worried'

export interface FaceOptions {
  eyes?: EyeStyle
  mouth?: MouthStyle
  /** Scale for the eye radius from the plan's default. */
  eyeScale?: number
  /** Extra outline around the whites (owls, mirrors). */
  rim?: string
}

export type EyeMood = 'open' | 'happy' | 'droopy' | 'closed' | 'angry' | 'sad' | 'narrow'

/** The moving part of an eye follows two CSS variables (`--ws-look-x/y`) so the eyes can glance toward a tap. */
const pupil = (inner: string) => g({ class: 'ws-mon__pupil' }, inner)

function eyeWhites(p: Pt, r: number, pal: Palette, style: EyeStyle, rim?: string): string {
  if (style === 'ember') return circle(p.x, p.y, r * 1.4, { fill: pal.eye, opacity: 0.22 }) + pupil(circle(p.x, p.y, r * 1.05, { fill: pal.eye, opacity: 0.4 }) + circle(p.x, p.y, r * 0.7, { fill: pal.eye }) + circle(p.x - r * 0.2, p.y - r * 0.25, r * 0.22, { fill: '#fff', opacity: 0.9 }))
  if (style === 'dot') return pupil(circle(p.x, p.y, r * 0.6, { fill: pal.eye }) + circle(p.x - r * 0.2, p.y - r * 0.2, r * 0.18, { fill: '#fff' }))
  if (style === 'painted') return pupil(ellipse(p.x, p.y, r * 1.1, r * 0.8, { fill: pal.eye }) + circle(p.x + r * 0.3, p.y - r * 0.2, r * 0.25, { fill: '#fff' }))
  const whites = ellipse(p.x, p.y, r * 1.25, r * 1.35, { fill: '#fff', stroke: rim ?? pal.outline, 'stroke-width': rim ? 3 : 2.5 })
  const pupilR = style === 'beady' ? r * 0.55 : r * 0.78
  return whites + pupil(circle(p.x + r * 0.15, p.y + r * 0.15, pupilR, { fill: pal.eye }) + circle(p.x + r * 0.42, p.y - r * 0.3, r * 0.3, { fill: '#fff' }))
}

function eyeMoodOverlay(p: Pt, r: number, pal: Palette, mood: EyeMood, skin: string): string {
  const R = r * 1.4
  switch (mood) {
    case 'open':
      return ''
    case 'happy':
      return ellipse(p.x, p.y, R + 1, R + 1, { fill: skin }) + path(`M${p.x - R} ${p.y + 2} Q${p.x} ${p.y - R * 1.3} ${p.x + R} ${p.y + 2}`, { fill: 'none', stroke: pal.outline, 'stroke-width': 3.5, 'stroke-linecap': 'round' })
    case 'droopy':
      return path(`M${p.x - R - 2} ${p.y - R - 2} L${p.x + R + 2} ${p.y - R - 2} L${p.x + R + 2} ${p.y - r * 0.1} Q${p.x} ${p.y + r * 0.4} ${p.x - R - 2} ${p.y - r * 0.1} Z`, { fill: skin }) + path(`M${p.x - R} ${p.y - r * 0.1} Q${p.x} ${p.y + r * 0.4} ${p.x + R} ${p.y - r * 0.1}`, { fill: 'none', stroke: pal.outline, 'stroke-width': 3, 'stroke-linecap': 'round' })
    case 'narrow':
      return path(`M${p.x - R - 2} ${p.y - R - 2} L${p.x + R + 2} ${p.y - R - 2} L${p.x + R + 2} ${p.y - r * 0.4} L${p.x - R - 2} ${p.y - r * 0.1} Z`, { fill: skin }) + line(p.x - R, p.y - r * 0.1, p.x + R, p.y - r * 0.4, { stroke: pal.outline, 'stroke-width': 3, 'stroke-linecap': 'round' })
    case 'closed':
      return ellipse(p.x, p.y, R + 1, R + 1, { fill: skin }) + path(`M${p.x - R} ${p.y - 2} Q${p.x} ${p.y + R} ${p.x + R} ${p.y - 2}`, { fill: 'none', stroke: pal.outline, 'stroke-width': 3.5, 'stroke-linecap': 'round' })
    case 'angry':
      return line(p.x - R, p.y - R * 1.1, p.x + R, p.y - R * 0.6, { stroke: pal.outline, 'stroke-width': 4, 'stroke-linecap': 'round' })
    case 'sad':
      return line(p.x - R, p.y - R * 0.6, p.x + R, p.y - R * 1.1, { stroke: pal.outline, 'stroke-width': 4, 'stroke-linecap': 'round' })
  }
}

/** Blink lids: skin-coloured covers that the CSS animation flashes on for a few frames. Hidden by default. */
function blinkLids(l: Pt, r: Pt, radius: number, pal: Palette, skin: string): string {
  const R = radius * 1.45
  return g({ class: 'ws-mon__lids', opacity: 0 }, [ellipse(l.x, l.y, R, R, { fill: skin }), ellipse(r.x, r.y, R, R, { fill: skin }), line(l.x - R * 0.7, l.y, l.x + R * 0.7, l.y, { stroke: pal.outline, 'stroke-width': 3, 'stroke-linecap': 'round' }), line(r.x - R * 0.7, r.y, r.x + R * 0.7, r.y, { stroke: pal.outline, 'stroke-width': 3, 'stroke-linecap': 'round' })])
}

export function drawEyes(s: Sockets, pal: Palette, mood: EyeMood, opts: FaceOptions, skin: string): string {
  const style = opts.eyes ?? 'round'
  const r = s.eyeR_ * (opts.eyeScale ?? 1)
  const mirrored = (p: Pt, side: 1 | -1) => eyeWhites(p, r, pal, style, opts.rim) + eyeMoodOverlay(p, r, pal, side === -1 && (mood === 'angry' || mood === 'sad') ? (mood === 'angry' ? 'sad' : 'angry') : mood, skin)
  const lids = style === 'ember' || mood === 'closed' || mood === 'happy' ? '' : blinkLids(s.eyeL, s.eyeR, r, pal, skin)
  return g({ class: 'ws-mon__eyes' }, mirrored(s.eyeL, -1) + mirrored(s.eyeR, 1) + lids)
}

export function drawMouth(s: Sockets, pal: Palette, style: MouthStyle, skin: string): string {
  const m = s.mouth
  const w = s.eyeR_ * 2.2
  const stroke = { fill: 'none', stroke: pal.outline, 'stroke-width': 3.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }
  switch (style) {
    case 'none':
      return ''
    case 'smile':
      return path(`M${m.x - w} ${m.y} Q${m.x} ${m.y + w * 0.9} ${m.x + w} ${m.y}`, stroke)
    case 'grin':
      return path(`M${m.x - w * 1.3} ${m.y - 2} Q${m.x} ${m.y + w * 1.4} ${m.x + w * 1.3} ${m.y - 2} Z`, { fill: pal.outline }) + rect(m.x - w * 0.9, m.y, w * 1.8, w * 0.4, 2, { fill: '#fff' })
    case 'flat':
      return line(m.x - w * 0.8, m.y + 2, m.x + w * 0.8, m.y + 2, stroke)
    case 'frown':
      return path(`M${m.x - w} ${m.y + 6} Q${m.x} ${m.y - w * 0.6} ${m.x + w} ${m.y + 6}`, stroke)
    case 'worried':
      return path(`M${m.x - w} ${m.y + 4} Q${m.x - w * 0.5} ${m.y - 4} ${m.x} ${m.y + 4} Q${m.x + w * 0.5} ${m.y + 12} ${m.x + w} ${m.y + 4}`, stroke)
    case 'open':
      return ellipse(m.x, m.y + 4, w * 0.7, w * 0.8, { fill: pal.outline }) + ellipse(m.x, m.y + 8, w * 0.45, w * 0.35, { fill: '#e86a7c' })
    case 'wobble':
      return path(`M${m.x - w} ${m.y + 4} l${w * 0.5} -5 l${w * 0.5} 5 l${w * 0.5} -5 l${w * 0.5} 5`, stroke)
    case 'beak':
      return polygon(
        [
          [m.x - 4, m.y - 8],
          [m.x + 30, m.y - 1],
          [m.x - 4, m.y + 6],
        ],
        { fill: pal.accent, ...outlined(pal) },
      ) + line(m.x - 2, m.y - 1, m.x + 24, m.y - 1, { stroke: pal.outline, 'stroke-width': 2 })
    case 'chew':
      return ellipse(m.x, m.y + 2, w * 0.8, w * 0.45, { fill: pal.outline }) + g({ class: 'ws-mon__chew' }, ellipse(m.x, m.y + 2, w * 0.55, w * 0.25, { fill: skin }))
    case 'fangs':
      return path(`M${m.x - w} ${m.y} Q${m.x} ${m.y + w * 0.7} ${m.x + w} ${m.y}`, stroke) + polygon([[m.x - w * 0.6, m.y + 1], [m.x - w * 0.35, m.y + 10], [m.x - w * 0.1, m.y + 2]], { fill: '#fff', stroke: pal.outline, 'stroke-width': 1.5 }) + polygon([[m.x + w * 0.1, m.y + 2], [m.x + w * 0.35, m.y + 10], [m.x + w * 0.6, m.y + 1]], { fill: '#fff', stroke: pal.outline, 'stroke-width': 1.5 })
  }
}

export function cheeks(s: Sockets, color: string, r = 6): string {
  return ellipse(s.cheekL.x, s.cheekL.y, r * 1.3, r, { fill: color, opacity: 0.55 }) + ellipse(s.cheekR.x, s.cheekR.y, r * 1.3, r, { fill: color, opacity: 0.55 })
}

/* ---------- overlays (§6.6 expression cues) ---------- */

export function sweatDrop(s: Sockets, pal: Palette): string {
  const p = { x: s.head.x + s.head.r * 0.8, y: s.head.y - s.head.r * 0.7 }
  return g({ class: 'ws-mon__sweat' }, path(`M${p.x} ${p.y - 10} C${p.x + 8} ${p.y} ${p.x + 8} ${p.y + 8} ${p.x} ${p.y + 8} C${p.x - 8} ${p.y + 8} ${p.x - 8} ${p.y} ${p.x} ${p.y - 10} Z`, { fill: '#9fd8ff', stroke: pal.outline, 'stroke-width': 2 }))
}

export function sparkles(s: Sockets): string {
  const star = (cx: number, cy: number, r: number) => path(`M${cx} ${cy - r} Q${cx} ${cy} ${cx + r} ${cy} Q${cx} ${cy} ${cx} ${cy + r} Q${cx} ${cy} ${cx - r} ${cy} Q${cx} ${cy} ${cx} ${cy - r} Z`, { fill: '#ffe680', stroke: '#f2b544', 'stroke-width': 1.2 })
  const h = s.head
  return g({ class: 'ws-mon__sparkle' }, [star(h.x - h.r - 8, h.y - h.r * 0.5, 9), star(h.x + h.r + 6, h.y - h.r, 7), star(h.x + h.r * 0.2, h.y - h.r - 14, 6)])
}

export function sickTint(s: Sockets): string {
  const b = s.body
  return ellipse(b.x, b.y, b.rx * 1.05, b.ry * 1.05, { fill: '#7faf5a', opacity: 0.22 }) + ellipse(s.head.x, s.head.y, s.head.r * 1.05, s.head.r * 1.05, { fill: '#7faf5a', opacity: 0.22 })
}

export function rainbow(s: Sockets): string {
  const c = s.crown
  const arcs = ['#F28F8F', '#F7D36B', '#8FD1A8', '#8FB8F2'].map((col, i) => path(`M${c.x - 40 + i * 4} ${c.y - 6} A${40 - i * 4} ${40 - i * 4} 0 0 1 ${c.x + 40 - i * 4} ${c.y - 6}`, { fill: 'none', stroke: col, 'stroke-width': 4 }))
  return g({ class: 'ws-mon__sparkle' }, arcs)
}
