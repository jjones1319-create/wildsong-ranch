import type { BodyPlan } from '../../data/types.ts'
import type { Palette } from './palettes.ts'
import { circle, ellipse, g, path, rect, type Attrs } from './svg.ts'

/**
 * GAME_DESIGN §22: nine paper-doll body plans. Every plan draws its silhouette on a 256×256 canvas
 * (ground line at y = 232, facing right) and reports its sockets: the points where the head, ears,
 * crown, back, tail, chin and front parts attach. Breed looks and sub-breed accent parts snap to those.
 * Big shapes are painted through `pal.paint()` (a top-left-lit gradient), get a rim highlight and,
 * when the look asks for one, a subtle texture overlay.
 */

export interface Pt {
  x: number
  y: number
}

export interface Sockets {
  head: Pt & { r: number }
  eyeL: Pt
  eyeR: Pt
  eyeR_: number
  mouth: Pt
  crown: Pt
  earL: Pt
  earR: Pt
  back: Pt
  tail: Pt
  chin: Pt
  front: Pt
  cheekL: Pt
  cheekR: Pt
  body: Pt & { rx: number; ry: number }
}

export interface PlanKnobs {
  bodyRx?: number
  bodyRy?: number
  headR?: number
  /** Quadrupeds: a short muzzle bump. */
  snout?: boolean
  /** Quadrupeds: a longer muzzle (goats, wolves). */
  snoutLong?: boolean
  /** Quadrupeds: cloud-puff body (Nimbusheep). */
  cloud?: boolean
  /** Quadrupeds: the head sits on a raised neck (grown Hearthwing). */
  neck?: boolean
  /** Floaters: a paper-lantern rounded box instead of an egg (Wishlume). */
  lantern?: boolean
  /** Floaters: a tattered shroud (Ashwraith). */
  shroud?: boolean
  /** Floaters: draw no body at all; the look supplies it (Mirrorkin). */
  hollow?: boolean
  /** Floaters: small size (Zipwisp). */
  small?: boolean
  /** Floaters: a horizontal swimmer with a fluke (Frostlance). */
  horizontal?: boolean
  /** Constructs: no separate head; the body is the whole creature (Lootlid). */
  noHead?: boolean
  /** Constructs: a rounded head (Gearhoot). */
  roundHead?: boolean
  /** Insects: fewer, slimmer segments (Velvesper). */
  slim?: boolean
  /** Serpents: lifted off the ground (Aurelwyrm floats). */
  lifted?: boolean
  /** Shelled: upright crab stance (Reefclaw). */
  crab?: boolean
  /** Shelled: a fixed shell colour from the brief instead of the body colour. */
  shellColor?: string
  /** Shelled: skin in the body colour (the belly colour is the default skin). */
  skinFromBody?: boolean
  /** Bipeds: a hulking, hunched giant with pillar arms (Grumblestone). */
  hulk?: boolean
  /** Bipeds: a squat crouch with hands on the ground (Gloomgrin). */
  squat?: boolean
  /** Bipeds: a big-headed little dinosaur (Pluckrex). */
  dino?: boolean
  /** Bipeds: the taller grown dinosaur. */
  grownDino?: boolean
  /** Avians: a round fluffy chick (young Paladove). */
  chick?: boolean
  /** Avians: a stout, armoured dove (grown Paladove). */
  stout?: boolean
  /** Blobs: eight curling tentacles instead of feet (Scrollopus). */
  tentacles?: boolean
}

export interface PlanDraw {
  /** Behind the body: back legs, far wing, tentacles. */
  back: string
  /** The body, belly, shading, near limbs and the head base. */
  body: string
  sockets: Sockets
  floats: boolean
}

export const OUTLINE_WIDTH = 3.5

export function outlined(pal: Palette, extra: Attrs = {}): Attrs {
  return { stroke: pal.outline, 'stroke-width': OUTLINE_WIDTH, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', ...extra }
}

/** A stubby leg: a rounded column with a rounded foot. */
export function leg(x: number, top: number, bottom: number, w: number, fill: string, pal: Palette): string {
  return rect(x - w / 2, top, w, bottom - top, w / 2.2, { fill: pal.paint(fill), ...outlined(pal) })
}

/** The soft shading layer: a darker crescent on the lower part of a round shape. */
export function shading(cx: number, cy: number, rx: number, ry: number, pal: Palette): string {
  return ellipse(cx, cy + ry * 0.45, rx * 0.72, ry * 0.42, { fill: pal.shade, opacity: 0.3 })
}

/** The rim highlight: a soft light arc along the top-left edge of a round shape. */
export function rimLight(cx: number, cy: number, rx: number, ry: number): string {
  const ix = rx * 0.84
  const iy = ry * 0.84
  const a1 = (200 * Math.PI) / 180
  const a2 = (292 * Math.PI) / 180
  const x1 = cx + ix * Math.cos(a1)
  const y1 = cy + iy * Math.sin(a1)
  const x2 = cx + ix * Math.cos(a2)
  const y2 = cy + iy * Math.sin(a2)
  return path(`M${x1.toFixed(1)} ${y1.toFixed(1)} A${ix.toFixed(1)} ${iy.toFixed(1)} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`, { fill: 'none', stroke: '#fff', 'stroke-width': 4, 'stroke-linecap': 'round', opacity: 0.26 })
}

/** The texture overlay for one shape (scales, fur, stone, feathers), when the look has one. */
export function textured(shape: (attrs: Attrs) => string, pal: Palette): string {
  return pal.texture ? shape({ fill: pal.texture, opacity: 0.24 }) : ''
}

/** A soft contact shadow on the ground line. */
export function groundShadow(pal: Palette, cx = 128, rx = 44): string {
  return ellipse(cx, 230, rx, 9, { fill: `url(#${pal.id}-s)` })
}

/** A thick limb or neck: outline stroke under a painted stroke. */
export function limb(x1: number, y1: number, x2: number, y2: number, w: number, fill: string, pal: Palette): string {
  const d = `M${x1} ${y1} L${x2} ${y2}`
  return path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': w + 7, 'stroke-linecap': 'round' }) + path(d, { fill: 'none', stroke: pal.paint(fill), 'stroke-width': w, 'stroke-linecap': 'round' })
}

function sockets(partial: Omit<Sockets, 'cheekL' | 'cheekR' | 'eyeR_'> & Partial<Pick<Sockets, 'cheekL' | 'cheekR' | 'eyeR_'>>): Sockets {
  const h = partial.head
  return {
    eyeR_: 7,
    cheekL: { x: h.x - h.r * 0.5, y: h.y + h.r * 0.25 },
    cheekR: { x: h.x + h.r * 0.5, y: h.y + h.r * 0.25 },
    ...partial,
  }
}

function roundBody(pal: Palette, body: { x: number; y: number; rx: number; ry: number }, bellyScale = 0.6): string {
  const shape = (a: Attrs) => ellipse(body.x, body.y, body.rx, body.ry, a)
  return shape({ fill: pal.paint(pal.body), ...outlined(pal) }) + textured(shape, pal) + ellipse(body.x, body.y + body.ry * 0.35, body.rx * bellyScale, body.ry * 0.5, { fill: pal.paint(pal.belly) }) + shading(body.x, body.y, body.rx, body.ry, pal) + rimLight(body.x, body.y, body.rx, body.ry)
}

function roundHead(pal: Palette, head: { x: number; y: number; r: number }): string {
  const shape = (a: Attrs) => circle(head.x, head.y, head.r, a)
  return shape({ fill: pal.paint(pal.body), ...outlined(pal) }) + textured(shape, pal) + rimLight(head.x, head.y, head.r, head.r)
}

function quadruped(pal: Palette, k: PlanKnobs): PlanDraw {
  const rx = k.bodyRx ?? 58
  const ry = k.bodyRy ?? 40
  const body = { x: k.neck ? 120 : 124, y: k.neck ? 176 : 172, rx, ry }
  const head = k.neck ? { x: 184, y: 84, r: k.headR ?? 30 } : { x: 160, y: 116, r: k.headR ?? 38 }
  const legTop = body.y + ry - 18
  const back = g({}, [leg(body.x - 28, legTop, 230, 18, pal.shade, pal), leg(body.x - 10, legTop, 230, 18, pal.shade, pal)])
  const parts: string[] = []
  if (k.cloud) {
    const puffs = [
      [78, 176, 26],
      [100, 158, 30],
      [128, 150, 34],
      [156, 162, 28],
      [120, 190, 30],
      [88, 196, 24],
      [152, 194, 26],
    ] as const
    parts.push(g({}, puffs.map(([x, y, r]) => circle(x, y, r, { fill: pal.paint(pal.body), ...outlined(pal) }))))
    parts.push(g({}, puffs.map(([x, y, r]) => circle(x, y, r - 2.5, { fill: pal.paint(pal.body) }))))
    parts.push(rimLight(128, 150, 34, 34))
  } else {
    parts.push(roundBody(pal, body))
  }
  parts.push(leg(body.x + 24, legTop, 230, 18, pal.body, pal), leg(body.x + 44, legTop, 230, 18, pal.body, pal))
  if (k.neck) {
    parts.push(limb(body.x + 38, body.y - 26, head.x - 4, head.y + 14, 26, pal.body, pal))
    parts.push(path(`M${body.x + 44} ${body.y - 10} L${head.x + 2} ${head.y + 18}`, { fill: 'none', stroke: pal.paint(pal.belly), 'stroke-width': 10, 'stroke-linecap': 'round', opacity: 0.9 }))
  }
  parts.push(roundHead(pal, head))
  if (k.snout || k.snoutLong) {
    const long = Boolean(k.snoutLong)
    parts.push(ellipse(head.x + head.r * (long ? 0.72 : 0.55), head.y + head.r * (long ? 0.4 : 0.35), head.r * (long ? 0.56 : 0.42), head.r * (long ? 0.36 : 0.3), { fill: pal.paint(pal.belly), ...outlined(pal) }))
  }
  return {
    back,
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 12, y: head.y - 6 },
      eyeR: { x: head.x + 12, y: head.y - 6 },
      mouth: { x: head.x + 6, y: head.y + 16 },
      crown: { x: head.x, y: head.y - head.r },
      earL: { x: head.x - head.r * 0.6, y: head.y - head.r * 0.75 },
      earR: { x: head.x + head.r * 0.6, y: head.y - head.r * 0.75 },
      back: { x: body.x - 14, y: body.y - ry + 4 },
      tail: { x: body.x - rx + 6, y: body.y - 8 },
      chin: { x: head.x + 8, y: head.y + head.r - 4 },
      front: k.neck ? { x: body.x + rx + 2, y: body.y - 8 } : { x: head.x + head.r + 6, y: body.y - 6 },
      body,
    }),
  }
}

function blob(pal: Palette, k: PlanKnobs): PlanDraw {
  const rx = k.bodyRx ?? 74
  const ry = k.bodyRy ?? 58
  const body = k.tentacles ? { x: 128, y: 148, rx: k.bodyRx ?? 60, ry: k.bodyRy ?? 52 } : { x: 128, y: 166, rx, ry }
  const back: string[] = []
  const parts: string[] = []
  if (k.tentacles) {
    const arms: string[] = []
    for (let i = 0; i < 8; i++) {
      const x0 = body.x - 52 + i * 15
      const dir = i % 2 === 0 ? -1 : 1
      const y0 = body.y + body.ry - 14
      const d = `M${x0} ${y0} C${x0 + dir * 4} ${y0 + 26} ${x0 + dir * 24} ${y0 + 30} ${x0 + dir * 18} ${y0 + 54} C${x0 + dir * 14} ${y0 + 68} ${x0 - dir * 2} ${y0 + 66} ${x0 + dir * 4} ${y0 + 58}`
      arms.push(
        g({ class: 'ws-mon__tentacle', style: `transform-origin:${x0}px ${y0}px;animation-delay:${(-0.37 * i).toFixed(2)}s` }, [
          path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 17, 'stroke-linecap': 'round' }),
          path(d, { fill: 'none', stroke: pal.paint(pal.body), 'stroke-width': 11, 'stroke-linecap': 'round' }),
          path(d, { fill: 'none', stroke: pal.belly, 'stroke-width': 4, 'stroke-linecap': 'round', opacity: 0.55, 'stroke-dasharray': '3 6' }),
        ]),
      )
    }
    back.push(g({}, arms))
    parts.push(roundBody(pal, body, 0.55))
  } else {
    parts.push(roundBody(pal, body, 0.62))
    parts.push(ellipse(100, 226, 20, 8, { fill: pal.paint(pal.body), ...outlined(pal) }), ellipse(156, 226, 20, 8, { fill: pal.paint(pal.body), ...outlined(pal) }))
  }
  const head = k.tentacles ? { x: 128, y: 134, r: 50 } : { x: 128, y: 140, r: 60 }
  return {
    back: back.join(''),
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 22, y: head.y - 6 },
      eyeR: { x: head.x + 22, y: head.y - 6 },
      eyeR_: 9,
      mouth: { x: 128, y: head.y + 28 },
      crown: { x: 128, y: body.y - body.ry },
      earL: { x: body.x - body.rx * 0.6, y: body.y - body.ry * 0.75 },
      earR: { x: body.x + body.rx * 0.6, y: body.y - body.ry * 0.75 },
      back: { x: 128, y: body.y - body.ry + 2 },
      tail: { x: body.x - body.rx + 6, y: body.y + 12 },
      chin: { x: 128, y: body.y + body.ry * 0.55 },
      front: { x: body.x + body.rx + 8, y: body.y + 14 },
      cheekL: { x: head.x - 34, y: head.y + 12 },
      cheekR: { x: head.x + 34, y: head.y + 12 },
      body,
    }),
  }
}

function biped(pal: Palette, k: PlanKnobs): PlanDraw {
  let body = { x: 128, y: 172, rx: k.bodyRx ?? 36, ry: k.bodyRy ?? 44 }
  let head = { x: 128, y: 104, r: k.headR ?? 34 }
  const parts: string[] = []
  const back: string[] = []
  if (k.hulk) {
    body = { x: 128, y: 170, rx: 58, ry: 46 }
    head = { x: 128, y: 108, r: 28 }
    parts.push(leg(104, 204, 230, 28, pal.body, pal), leg(152, 204, 230, 28, pal.body, pal))
    parts.push(roundHead(pal, head))
    parts.push(roundBody(pal, body, 0.5))
    parts.push(limb(82, 142, 66, 212, 26, pal.body, pal), limb(174, 142, 190, 212, 26, pal.body, pal))
    return {
      back: '',
      body: g({}, parts),
      floats: false,
      sockets: sockets({
        head,
        eyeL: { x: 116, y: 100 },
        eyeR: { x: 140, y: 100 },
        eyeR_: 5,
        mouth: { x: 128, y: 118 },
        crown: { x: 128, y: 80 },
        earL: { x: 104, y: 88 },
        earR: { x: 152, y: 88 },
        back: { x: 128, y: 128 },
        tail: { x: 74, y: 196 },
        chin: { x: 128, y: 128 },
        front: { x: 196, y: 160 },
        cheekL: { x: 108, y: 112 },
        cheekR: { x: 148, y: 112 },
        body,
      }),
    }
  }
  if (k.squat) {
    body = { x: 128, y: 182, rx: 40, ry: 34 }
    head = { x: 128, y: 128, r: 30 }
    parts.push(leg(112, 208, 230, 18, pal.body, pal), leg(144, 208, 230, 18, pal.body, pal))
    parts.push(roundBody(pal, body, 0.6))
    parts.push(limb(100, 168, 84, 218, 12, pal.body, pal), limb(156, 168, 172, 218, 12, pal.body, pal))
    parts.push(roundHead(pal, head))
    return {
      back: '',
      body: g({}, parts),
      floats: false,
      sockets: sockets({
        head,
        eyeL: { x: 116, y: 122 },
        eyeR: { x: 140, y: 122 },
        mouth: { x: 128, y: 142 },
        crown: { x: 128, y: 98 },
        earL: { x: 106, y: 106 },
        earR: { x: 150, y: 106 },
        back: { x: 92, y: 160 },
        tail: { x: 90, y: 196 },
        chin: { x: 128, y: 158 },
        front: { x: 180, y: 176 },
        body,
      }),
    }
  }
  if (k.dino || k.grownDino) {
    const grown = Boolean(k.grownDino)
    body = grown ? { x: 126, y: 162, rx: 38, ry: 50 } : { x: 124, y: 174, rx: 34, ry: 38 }
    head = grown ? { x: 138, y: 88, r: 32 } : { x: 134, y: 100, r: 36 }
    parts.push(leg(body.x - 16, body.y + body.ry - 8, 230, grown ? 22 : 20, pal.body, pal), leg(body.x + 16, body.y + body.ry - 8, 230, grown ? 22 : 20, pal.body, pal))
    parts.push(roundBody(pal, body, 0.62))
    parts.push(limb(body.x + 28, body.y - 10, body.x + (grown ? 50 : 44), body.y + (grown ? 14 : 2), grown ? 13 : 11, pal.body, pal))
    parts.push(roundHead(pal, head))
    return {
      back: '',
      body: g({}, parts),
      floats: false,
      sockets: sockets({
        head,
        eyeL: { x: head.x - 14, y: head.y - 6 },
        eyeR: { x: head.x + 12, y: head.y - 6 },
        eyeR_: 8,
        mouth: { x: head.x + 8, y: head.y + 16 },
        crown: { x: head.x, y: head.y - head.r },
        earL: { x: head.x - head.r * 0.7, y: head.y - head.r * 0.6 },
        earR: { x: head.x + head.r * 0.7, y: head.y - head.r * 0.6 },
        back: { x: body.x - body.rx + 2, y: body.y - 20 },
        tail: { x: body.x - body.rx + 8, y: body.y + 14 },
        chin: { x: head.x + 6, y: head.y + head.r - 2 },
        front: { x: body.x + body.rx + 24, y: body.y + 4 },
        body,
      }),
    }
  }
  parts.push(leg(114, 206, 230, 18, pal.body, pal), leg(142, 206, 230, 18, pal.body, pal))
  parts.push(roundBody(pal, body, 0.62))
  parts.push(limb(102, 158, 84, 186, 11, pal.body, pal), limb(154, 158, 172, 186, 11, pal.body, pal))
  parts.push(roundHead(pal, head))
  return {
    back: back.join(''),
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 12, y: head.y - 4 },
      eyeR: { x: head.x + 12, y: head.y - 4 },
      mouth: { x: head.x, y: head.y + 16 },
      crown: { x: head.x, y: head.y - head.r },
      earL: { x: head.x - head.r * 0.7, y: head.y - head.r * 0.65 },
      earR: { x: head.x + head.r * 0.7, y: head.y - head.r * 0.65 },
      back: { x: body.x - body.rx + 2, y: body.y - 20 },
      tail: { x: body.x - body.rx + 4, y: body.y + 22 },
      chin: { x: head.x, y: head.y + head.r },
      front: { x: body.x + body.rx + 10, y: body.y - 10 },
      body,
    }),
  }
}

export const SERPENT_PATH = 'M52 214 C70 150 120 150 140 190 C160 230 200 220 196 170 C192 130 160 120 168 100'
export const SERPENT_PATH_LIFTED = 'M48 186 C66 122 116 122 136 162 C156 202 198 192 194 142 C190 102 158 92 166 72'

function serpent(pal: Palette, k: PlanKnobs): PlanDraw {
  const d = k.lifted ? SERPENT_PATH_LIFTED : SERPENT_PATH
  const dy = k.lifted ? -28 : 0
  const headR = k.headR ?? 30
  const head = { x: 170, y: 92 + dy, r: headR }
  const parts = [
    path(d, { fill: 'none', stroke: pal.outline, 'stroke-width': 36, 'stroke-linecap': 'round' }),
    path(d, { fill: 'none', stroke: pal.paint(pal.body), 'stroke-width': 29, 'stroke-linecap': 'round' }),
    pal.texture ? path(d, { fill: 'none', stroke: pal.texture, 'stroke-width': 29, 'stroke-linecap': 'round', opacity: 0.24 }) : '',
    path(d, { fill: 'none', stroke: pal.paint(pal.belly), 'stroke-width': 11, 'stroke-linecap': 'round', opacity: 0.85 }),
    roundHead(pal, head),
    ellipse(head.x + 10, head.y + 12, headR * 0.5, headR * 0.3, { fill: pal.paint(pal.belly) }),
  ]
  return {
    back: '',
    body: g({}, parts),
    floats: Boolean(k.lifted),
    sockets: sockets({
      head,
      eyeL: { x: head.x - 10, y: head.y - 6 },
      eyeR: { x: head.x + 12, y: head.y - 6 },
      mouth: { x: head.x + 10, y: head.y + 14 },
      crown: { x: head.x, y: head.y - headR },
      earL: { x: head.x - headR * 0.7, y: head.y - headR * 0.6 },
      earR: { x: head.x + headR * 0.7, y: head.y - headR * 0.6 },
      back: { x: 112, y: 152 + dy },
      tail: { x: 52, y: 214 + dy },
      chin: { x: head.x + 8, y: head.y + headR - 2 },
      front: { x: head.x + headR + 6, y: head.y + 6 },
      body: { x: 128, y: 170 + dy, rx: 76, ry: 60 },
    }),
  }
}

function avian(pal: Palette, k: PlanKnobs): PlanDraw {
  const legLine = (x1: number, x2: number, top: number, w: number) =>
    path(`M${x1} ${top} L${x2} 230`, { stroke: pal.outline, 'stroke-width': w + 4, 'stroke-linecap': 'round' }) +
    path(`M${x1} ${top} L${x2} 230`, { stroke: pal.accent, 'stroke-width': w, 'stroke-linecap': 'round' }) +
    path(`M${x2 - 10} 230 L${x2 + 10} 230`, { stroke: pal.accent, 'stroke-width': w, 'stroke-linecap': 'round' })
  if (k.chick) {
    const body = { x: 128, y: 172, rx: 44, ry: 40 }
    const head = { x: 128, y: 128, r: 30 }
    const parts = [legLine(116, 114, 206, 5), legLine(140, 142, 206, 5), roundBody(pal, body, 0.6), roundHead(pal, head)]
    return {
      back: '',
      body: g({}, parts),
      floats: false,
      sockets: sockets({
        head,
        eyeL: { x: 116, y: 122 },
        eyeR: { x: 140, y: 122 },
        eyeR_: 6,
        mouth: { x: 128, y: 140 },
        crown: { x: 128, y: 98 },
        earL: { x: 106, y: 106 },
        earR: { x: 150, y: 106 },
        back: { x: 90, y: 150 },
        tail: { x: 86, y: 186 },
        chin: { x: 128, y: 158 },
        front: { x: 178, y: 160 },
        body,
      }),
    }
  }
  if (k.stout) {
    const body = { x: 124, y: 160, rx: 44, ry: 40 }
    const head = { x: 162, y: 96, r: 26 }
    const parts = [legLine(112, 110, 196, 7), legLine(136, 140, 196, 7), limb(150, 136, 158, 108, 20, pal.body, pal), roundBody(pal, body, 0.6), roundHead(pal, head)]
    return {
      back: '',
      body: g({}, parts),
      floats: false,
      sockets: sockets({
        head,
        eyeL: { x: head.x - 8, y: head.y - 5 },
        eyeR: { x: head.x + 8, y: head.y - 5 },
        eyeR_: 6,
        mouth: { x: head.x + 22, y: head.y + 4 },
        crown: { x: head.x, y: head.y - head.r },
        earL: { x: head.x - 16, y: head.y - 18 },
        earR: { x: head.x + 16, y: head.y - 18 },
        back: { x: 96, y: 136 },
        tail: { x: 80, y: 170 },
        chin: { x: head.x + 2, y: head.y + head.r },
        front: { x: 196, y: 150 },
        body,
      }),
    }
  }
  const body = { x: 124, y: 160, rx: 36, ry: 30 }
  const head = { x: 166, y: 84, r: 24 }
  const parts = [
    legLine(116, 114, 186, 5),
    legLine(134, 140, 186, 5),
    limb(144, 150, 160, 98, 19, pal.body, pal),
    roundBody(pal, body, 0.6),
    ellipse(110, 158, 28, 18, { fill: pal.shade, opacity: 0.5, ...outlined(pal) }),
    roundHead(pal, head),
  ]
  return {
    back: '',
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 8, y: head.y - 5 },
      eyeR: { x: head.x + 8, y: head.y - 5 },
      eyeR_: 5,
      mouth: { x: head.x + 22, y: head.y + 4 },
      crown: { x: head.x, y: head.y - head.r },
      earL: { x: head.x - 16, y: head.y - 18 },
      earR: { x: head.x + 16, y: head.y - 18 },
      back: { x: 104, y: 136 },
      tail: { x: 86, y: 166 },
      chin: { x: head.x + 2, y: head.y + head.r },
      front: { x: 200, y: 140 },
      body,
    }),
  }
}

function floater(pal: Palette, k: PlanKnobs): PlanDraw {
  if (k.horizontal) {
    const body = { x: 118, y: 142, rx: 66, ry: 30 }
    const head = { x: 162, y: 138, r: 28 }
    const parts = [groundShadow(pal, 124, 48), roundBody(pal, body, 0.7)]
    return {
      back: '',
      body: g({}, parts),
      floats: true,
      sockets: sockets({
        head,
        eyeL: { x: 150, y: 130 },
        eyeR: { x: 172, y: 132 },
        eyeR_: 6,
        mouth: { x: 174, y: 152 },
        crown: { x: 160, y: 112 },
        earL: { x: 140, y: 114 },
        earR: { x: 178, y: 114 },
        back: { x: 100, y: 114 },
        tail: { x: 52, y: 142 },
        chin: { x: 170, y: 164 },
        front: { x: 184, y: 140 },
        cheekL: { x: 144, y: 146 },
        cheekR: { x: 180, y: 146 },
        body,
      }),
    }
  }
  const rx = k.bodyRx ?? (k.small ? 34 : 46)
  const ry = k.bodyRy ?? (k.small ? 34 : 54)
  const body = { x: 128, y: k.small ? 140 : 130, rx, ry }
  const parts: string[] = [groundShadow(pal, 128, 36)]
  if (k.lantern) {
    const shape = (a: Attrs) => rect(body.x - rx, body.y - ry, rx * 2, ry * 2, 26, a)
    parts.push(shape({ fill: pal.paint(pal.body), ...outlined(pal) }), textured(shape, pal))
    parts.push(rect(body.x - rx + 10, body.y - ry + 10, rx * 2 - 20, ry * 2 - 20, 18, { fill: pal.paint(pal.belly), opacity: 0.6 }))
    parts.push(rimLight(body.x, body.y, rx, ry))
  } else if (k.shroud) {
    const d = `M${body.x - rx} ${body.y - 10} C${body.x - rx} ${body.y - ry - 20} ${body.x + rx} ${body.y - ry - 20} ${body.x + rx} ${body.y - 10} L${body.x + rx - 4} ${body.y + ry} L${body.x + rx * 0.55} ${body.y + ry - 22} L${body.x + rx * 0.2} ${body.y + ry + 6} L${body.x - rx * 0.2} ${body.y + ry - 18} L${body.x - rx * 0.6} ${body.y + ry + 2} L${body.x - rx + 4} ${body.y + ry - 24} Z`
    const shape = (a: Attrs) => path(d, a)
    parts.push(shape({ fill: pal.paint(pal.body), ...outlined(pal) }), textured(shape, pal))
    parts.push(shading(body.x, body.y, rx, ry, pal), rimLight(body.x, body.y - 6, rx, ry))
  } else if (!k.hollow) {
    parts.push(roundBody(pal, body, 0.6))
  }
  const head = { x: body.x, y: body.y - ry * 0.2, r: Math.min(rx, ry) }
  return {
    back: '',
    body: g({}, parts),
    floats: true,
    sockets: sockets({
      head,
      eyeL: { x: body.x - rx * 0.36, y: head.y },
      eyeR: { x: body.x + rx * 0.36, y: head.y },
      eyeR_: k.small ? 6 : 8,
      mouth: { x: body.x, y: head.y + ry * 0.4 },
      crown: { x: body.x, y: body.y - ry },
      earL: { x: body.x - rx * 0.85, y: body.y - ry * 0.6 },
      earR: { x: body.x + rx * 0.85, y: body.y - ry * 0.6 },
      back: { x: body.x - rx, y: body.y },
      tail: { x: body.x, y: body.y + ry },
      chin: { x: body.x, y: body.y + ry * 0.7 },
      front: { x: body.x + rx + 4, y: body.y + 10 },
      body,
    }),
  }
}

function shelled(pal: Palette, k: PlanKnobs): PlanDraw {
  const body = { x: 128, y: 166, rx: 66, ry: 56 }
  const head = { x: k.crab ? 150 : 196, y: k.crab ? 118 : 160, r: 26 }
  const skin = k.skinFromBody ? pal.body : pal.belly
  const shell = k.shellColor ?? pal.body
  const parts: string[] = []
  parts.push(leg(80, 194, 230, 16, skin, pal), leg(106, 194, 230, 16, skin, pal), leg(150, 194, 230, 16, skin, pal), leg(176, 194, 230, 16, skin, pal))
  parts.push(ellipse(128, 196, 58, 16, { fill: pal.paint(skin), ...outlined(pal) }))
  if (!k.crab) parts.push(circle(head.x, head.y, head.r, { fill: pal.paint(skin), ...outlined(pal) }), rimLight(head.x, head.y, head.r, head.r))
  const dome = (a: Attrs) => path(`M62 192 A66 62 0 0 1 194 192 Z`, a)
  parts.push(dome({ fill: pal.paint(shell), ...outlined(pal) }), textured(dome, pal))
  parts.push(path(`M80 190 A48 44 0 0 1 176 190`, { fill: 'none', stroke: pal.shade, 'stroke-width': 6, opacity: 0.5 }))
  parts.push(path(`M74 160 A56 52 0 0 1 112 134`, { fill: 'none', stroke: '#fff', 'stroke-width': 5, 'stroke-linecap': 'round', opacity: 0.25 }))
  if (k.crab) parts.push(ellipse(head.x, head.y + 8, 34, 22, { fill: pal.paint(skin), ...outlined(pal) }))
  return {
    back: '',
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 8, y: head.y - 6 },
      eyeR: { x: head.x + 8, y: head.y - 6 },
      eyeR_: 6,
      mouth: { x: head.x + 2, y: head.y + 12 },
      crown: { x: head.x, y: head.y - head.r },
      earL: { x: head.x - 16, y: head.y - 20 },
      earR: { x: head.x + 16, y: head.y - 20 },
      back: { x: 128, y: 132 },
      tail: { x: 58, y: 190 },
      chin: { x: head.x + 2, y: head.y + head.r },
      front: { x: 222, y: 170 },
      body,
    }),
  }
}

function insect(pal: Palette, k: PlanKnobs): PlanDraw {
  const segs: (readonly [number, number, number])[] = k.slim
    ? [
        [88, 192, 18],
        [112, 186, 21],
        [138, 180, 24],
      ]
    : [
        [76, 194, 22],
        [100, 190, 25],
        [126, 186, 28],
        [152, 182, 30],
      ]
  const head = { x: k.slim ? 168 : 182, y: k.slim ? 164 : 172, r: k.slim ? 26 : 30 }
  const parts: string[] = []
  for (const [x, , r] of segs) parts.push(leg(x, 212, 230, 8, pal.accent, pal), leg(x + r * 0.5, 212, 230, 8, pal.accent, pal))
  for (const [x, y, r] of segs) {
    const shape = (a: Attrs) => circle(x, y, r, a)
    parts.push(shape({ fill: pal.paint(pal.body), ...outlined(pal) }), textured(shape, pal))
    parts.push(ellipse(x, y + r * 0.45, r * 0.6, r * 0.35, { fill: pal.paint(pal.belly) }))
    parts.push(rimLight(x, y, r, r))
  }
  parts.push(roundHead(pal, head))
  return {
    back: '',
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 10, y: head.y - 6 },
      eyeR: { x: head.x + 10, y: head.y - 6 },
      mouth: { x: head.x + 2, y: head.y + 14 },
      crown: { x: head.x, y: head.y - head.r },
      earL: { x: head.x - 14, y: head.y - 22 },
      earR: { x: head.x + 14, y: head.y - 22 },
      back: { x: segs[Math.floor(segs.length / 2)]![0], y: 156 },
      tail: { x: segs[0]![0] - segs[0]![2], y: segs[0]![1] },
      chin: { x: head.x + 2, y: head.y + head.r },
      front: { x: head.x + head.r + 4, y: head.y + 4 },
      body: { x: 128, y: 184, rx: 80, ry: 32 },
    }),
  }
}

function construct(pal: Palette, k: PlanKnobs): PlanDraw {
  const body = { x: 128, y: 168, rx: 44, ry: 44 }
  const head = k.noHead ? { x: 128, y: 150, r: 44 } : { x: 128, y: 96, r: 30 }
  const parts: string[] = [leg(110, 208, 230, 18, pal.shade, pal), leg(146, 208, 230, 18, pal.shade, pal)]
  const box = (a: Attrs) => rect(body.x - body.rx, body.y - body.ry, body.rx * 2, body.ry * 2, 20, a)
  parts.push(box({ fill: pal.paint(pal.body), ...outlined(pal) }), textured(box, pal))
  parts.push(rect(body.x - body.rx + 10, body.y - 6, body.rx * 2 - 20, body.ry - 6, 12, { fill: pal.paint(pal.belly), opacity: 0.9 }))
  parts.push(rimLight(body.x, body.y, body.rx, body.ry))
  for (const [x, y] of [
    [body.x - body.rx + 10, body.y - body.ry + 10],
    [body.x + body.rx - 10, body.y - body.ry + 10],
    [body.x - body.rx + 10, body.y + body.ry - 10],
    [body.x + body.rx - 10, body.y + body.ry - 10],
  ] as const) {
    parts.push(circle(x, y, 3, { fill: pal.outline }))
  }
  if (!k.noHead) {
    parts.push(k.roundHead ? roundHead(pal, head) : rect(head.x - 28, head.y - 30, 56, 60, 16, { fill: pal.paint(pal.body), ...outlined(pal) }) + rimLight(head.x, head.y, 28, 30))
  }
  return {
    back: '',
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 12, y: head.y - 4 },
      eyeR: { x: head.x + 12, y: head.y - 4 },
      eyeR_: 8,
      mouth: { x: head.x, y: head.y + 16 },
      crown: { x: head.x, y: head.y - head.r },
      earL: { x: head.x - 24, y: head.y - 26 },
      earR: { x: head.x + 24, y: head.y - 26 },
      back: { x: body.x - body.rx, y: body.y - 16 },
      tail: { x: body.x - body.rx + 4, y: body.y + 28 },
      chin: { x: head.x, y: head.y + head.r },
      front: { x: body.x + body.rx + 8, y: body.y - 8 },
      body,
    }),
  }
}

const PLANS: Record<BodyPlan, (pal: Palette, k: PlanKnobs) => PlanDraw> = {
  blob,
  quadruped,
  biped,
  serpent,
  avian,
  floater,
  shelled,
  insect,
  construct,
}

export function drawPlan(plan: BodyPlan, pal: Palette, knobs: PlanKnobs = {}): PlanDraw {
  return PLANS[plan](pal, knobs)
}
