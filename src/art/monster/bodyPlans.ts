import type { BodyPlan } from '../../data/types.ts'
import type { Palette } from './palettes.ts'
import { circle, ellipse, g, path, rect, type Attrs } from './svg.ts'

/**
 * GAME_DESIGN §22: nine paper-doll body plans. Every plan draws its silhouette on a 256×256 canvas
 * (ground line at y = 232, facing right) and reports its sockets: the points where the head, ears,
 * crown, back, tail, chin and front parts attach. Breed looks and sub-breed accent parts snap to those.
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
  /** Quadrupeds: cloud-puff body (Nimbusheep). */
  cloud?: boolean
  /** Floaters: a paper-lantern rounded box instead of an egg (Wishlume). */
  lantern?: boolean
  /** Floaters: a tattered shroud (Ashwraith). */
  shroud?: boolean
  /** Floaters: draw no body at all; the look supplies it (Mirrorkin). */
  hollow?: boolean
  /** Floaters: small size (Zipwisp). */
  small?: boolean
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
}

export interface PlanDraw {
  /** Behind the body: back legs, far wing. */
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
  return rect(x - w / 2, top, w, bottom - top, w / 2.2, { fill, ...outlined(pal) })
}

/** The soft shading layer: a darker crescent on the lower part of a round shape. */
export function shading(cx: number, cy: number, rx: number, ry: number, pal: Palette): string {
  return ellipse(cx, cy + ry * 0.45, rx * 0.72, ry * 0.42, { fill: pal.shade, opacity: 0.35 })
}

export function groundShadow(cx = 128, rx = 44): string {
  return ellipse(cx, 230, rx, 7, { fill: '#000', opacity: 0.18 })
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

function quadruped(pal: Palette, k: PlanKnobs): PlanDraw {
  const rx = k.bodyRx ?? 58
  const ry = k.bodyRy ?? 40
  const headR = k.headR ?? 38
  const body = { x: 124, y: 172, rx, ry }
  const head = { x: 160, y: 116, r: headR }
  const legTop = body.y + ry - 18
  const back = g({}, [leg(96, legTop, 230, 18, pal.shade, pal), leg(114, legTop, 230, 18, pal.shade, pal)])
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
    parts.push(g({}, puffs.map(([x, y, r]) => circle(x, y, r, { fill: pal.body, ...outlined(pal) }))))
    parts.push(g({}, puffs.map(([x, y, r]) => circle(x, y, r - 2.5, { fill: pal.body }))))
  } else {
    parts.push(ellipse(body.x, body.y, rx, ry, { fill: pal.body, ...outlined(pal) }))
    parts.push(ellipse(body.x, body.y + 14, rx * 0.6, ry * 0.5, { fill: pal.belly }))
    parts.push(shading(body.x, body.y, rx, ry, pal))
  }
  parts.push(leg(148, legTop, 230, 18, pal.body, pal), leg(168, legTop, 230, 18, pal.body, pal))
  parts.push(circle(head.x, head.y, head.r, { fill: pal.body, ...outlined(pal) }))
  if (k.snout) parts.push(ellipse(head.x + headR * 0.55, head.y + headR * 0.35, headR * 0.42, headR * 0.3, { fill: pal.belly, ...outlined(pal) }))
  return {
    back,
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 12, y: head.y - 6 },
      eyeR: { x: head.x + 12, y: head.y - 6 },
      mouth: { x: head.x + 6, y: head.y + 16 },
      crown: { x: head.x, y: head.y - headR },
      earL: { x: head.x - headR * 0.6, y: head.y - headR * 0.75 },
      earR: { x: head.x + headR * 0.6, y: head.y - headR * 0.75 },
      back: { x: 110, y: body.y - ry + 4 },
      tail: { x: body.x - rx + 6, y: body.y - 8 },
      chin: { x: head.x + 8, y: head.y + headR - 4 },
      front: { x: head.x + headR + 6, y: body.y - 6 },
      body,
    }),
  }
}

function blob(pal: Palette, k: PlanKnobs): PlanDraw {
  const rx = k.bodyRx ?? 74
  const ry = k.bodyRy ?? 58
  const body = { x: 128, y: 166, rx, ry }
  const parts = [
    ellipse(body.x, body.y, rx, ry, { fill: pal.body, ...outlined(pal) }),
    ellipse(body.x, body.y + 22, rx * 0.62, ry * 0.42, { fill: pal.belly }),
    shading(body.x, body.y, rx, ry, pal),
    ellipse(100, 226, 20, 8, { fill: pal.body, ...outlined(pal) }),
    ellipse(156, 226, 20, 8, { fill: pal.body, ...outlined(pal) }),
  ]
  return {
    back: '',
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head: { x: 128, y: 140, r: 60 },
      eyeL: { x: 104, y: 128 },
      eyeR: { x: 152, y: 128 },
      eyeR_: 9,
      mouth: { x: 128, y: 164 },
      crown: { x: 128, y: body.y - ry },
      earL: { x: 84, y: 118 },
      earR: { x: 172, y: 118 },
      back: { x: 128, y: 110 },
      tail: { x: 56, y: 178 },
      chin: { x: 128, y: 196 },
      front: { x: 196, y: 180 },
      cheekL: { x: 94, y: 150 },
      cheekR: { x: 162, y: 150 },
      body,
    }),
  }
}

function biped(pal: Palette, k: PlanKnobs): PlanDraw {
  const rx = k.bodyRx ?? 36
  const ry = k.bodyRy ?? 44
  const headR = k.headR ?? 34
  const body = { x: 128, y: 172, rx, ry }
  const head = { x: 128, y: 104, r: headR }
  const arm = (x1: number, y1: number, x2: number, y2: number) => path(`M${x1} ${y1} L${x2} ${y2}`, { stroke: pal.outline, 'stroke-width': 18, 'stroke-linecap': 'round' }) + path(`M${x1} ${y1} L${x2} ${y2}`, { stroke: pal.body, 'stroke-width': 11, 'stroke-linecap': 'round' })
  const parts = [
    leg(114, 206, 230, 18, pal.body, pal),
    leg(142, 206, 230, 18, pal.body, pal),
    ellipse(body.x, body.y, rx, ry, { fill: pal.body, ...outlined(pal) }),
    ellipse(body.x, body.y + 10, rx * 0.62, ry * 0.6, { fill: pal.belly }),
    shading(body.x, body.y, rx, ry, pal),
    arm(102, 158, 84, 186),
    arm(154, 158, 172, 186),
    circle(head.x, head.y, headR, { fill: pal.body, ...outlined(pal) }),
  ]
  return {
    back: '',
    body: g({}, parts),
    floats: false,
    sockets: sockets({
      head,
      eyeL: { x: head.x - 12, y: head.y - 4 },
      eyeR: { x: head.x + 12, y: head.y - 4 },
      mouth: { x: head.x, y: head.y + 16 },
      crown: { x: head.x, y: head.y - headR },
      earL: { x: head.x - headR * 0.7, y: head.y - headR * 0.65 },
      earR: { x: head.x + headR * 0.7, y: head.y - headR * 0.65 },
      back: { x: body.x - rx + 2, y: body.y - 20 },
      tail: { x: body.x - rx + 4, y: body.y + 22 },
      chin: { x: head.x, y: head.y + headR },
      front: { x: body.x + rx + 10, y: body.y - 10 },
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
    path(d, { fill: 'none', stroke: pal.body, 'stroke-width': 29, 'stroke-linecap': 'round' }),
    path(d, { fill: 'none', stroke: pal.belly, 'stroke-width': 11, 'stroke-linecap': 'round', opacity: 0.85 }),
    circle(head.x, head.y, headR, { fill: pal.body, ...outlined(pal) }),
    ellipse(head.x + 10, head.y + 12, headR * 0.5, headR * 0.3, { fill: pal.belly }),
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

function avian(pal: Palette, _k: PlanKnobs): PlanDraw {
  const body = { x: 124, y: 160, rx: 36, ry: 30 }
  const head = { x: 166, y: 84, r: 24 }
  const legLine = (x1: number, x2: number) =>
    path(`M${x1} 186 L${x2} 230`, { stroke: pal.outline, 'stroke-width': 9, 'stroke-linecap': 'round' }) +
    path(`M${x1} 186 L${x2} 230`, { stroke: pal.accent, 'stroke-width': 5, 'stroke-linecap': 'round' }) +
    path(`M${x2 - 10} 230 L${x2 + 10} 230`, { stroke: pal.accent, 'stroke-width': 5, 'stroke-linecap': 'round' })
  const neck = path(`M144 150 L160 98`, { stroke: pal.outline, 'stroke-width': 26, 'stroke-linecap': 'round' }) + path(`M144 150 L160 98`, { stroke: pal.body, 'stroke-width': 19, 'stroke-linecap': 'round' })
  const parts = [
    legLine(116, 114),
    legLine(134, 140),
    neck,
    ellipse(body.x, body.y, body.rx, body.ry, { fill: pal.body, ...outlined(pal) }),
    ellipse(body.x + 4, body.y + 10, body.rx * 0.6, body.ry * 0.5, { fill: pal.belly }),
    ellipse(110, 158, 28, 18, { fill: pal.shade, opacity: 0.5, ...outlined(pal) }),
    circle(head.x, head.y, head.r, { fill: pal.body, ...outlined(pal) }),
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
  const rx = k.bodyRx ?? (k.small ? 34 : 46)
  const ry = k.bodyRy ?? (k.small ? 34 : 54)
  const body = { x: 128, y: k.small ? 140 : 130, rx, ry }
  const parts: string[] = [groundShadow(128, 36)]
  if (k.lantern) {
    parts.push(rect(body.x - rx, body.y - ry, rx * 2, ry * 2, 26, { fill: pal.body, ...outlined(pal) }))
    parts.push(rect(body.x - rx + 10, body.y - ry + 10, rx * 2 - 20, ry * 2 - 20, 18, { fill: pal.belly, opacity: 0.6 }))
  } else if (k.shroud) {
    const d = `M${body.x - rx} ${body.y - 10} C${body.x - rx} ${body.y - ry - 20} ${body.x + rx} ${body.y - ry - 20} ${body.x + rx} ${body.y - 10} L${body.x + rx - 4} ${body.y + ry} L${body.x + rx * 0.55} ${body.y + ry - 22} L${body.x + rx * 0.2} ${body.y + ry + 6} L${body.x - rx * 0.2} ${body.y + ry - 18} L${body.x - rx * 0.6} ${body.y + ry + 2} L${body.x - rx + 4} ${body.y + ry - 24} Z`
    parts.push(path(d, { fill: pal.body, ...outlined(pal) }))
    parts.push(shading(body.x, body.y, rx, ry, pal))
  } else if (!k.hollow) {
    parts.push(ellipse(body.x, body.y, rx, ry, { fill: pal.body, ...outlined(pal) }))
    parts.push(ellipse(body.x, body.y + ry * 0.35, rx * 0.6, ry * 0.4, { fill: pal.belly }))
    parts.push(shading(body.x, body.y, rx, ry, pal))
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
  parts.push(ellipse(128, 196, 58, 16, { fill: skin, ...outlined(pal) }))
  if (!k.crab) parts.push(circle(head.x, head.y, head.r, { fill: skin, ...outlined(pal) }))
  parts.push(path(`M62 192 A66 62 0 0 1 194 192 Z`, { fill: shell, ...outlined(pal) }))
  parts.push(path(`M80 190 A48 44 0 0 1 176 190`, { fill: 'none', stroke: pal.shade, 'stroke-width': 6, opacity: 0.5 }))
  if (k.crab) parts.push(ellipse(head.x, head.y + 8, 34, 22, { fill: skin, ...outlined(pal) }))
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
    parts.push(circle(x, y, r, { fill: pal.body, ...outlined(pal) }))
    parts.push(ellipse(x, y + r * 0.45, r * 0.6, r * 0.35, { fill: pal.belly }))
  }
  parts.push(circle(head.x, head.y, head.r, { fill: pal.body, ...outlined(pal) }))
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
  parts.push(rect(body.x - body.rx, body.y - body.ry, body.rx * 2, body.ry * 2, 20, { fill: pal.body, ...outlined(pal) }))
  parts.push(rect(body.x - body.rx + 10, body.y - 6, body.rx * 2 - 20, body.ry - 6, 12, { fill: pal.belly, opacity: 0.9 }))
  for (const [x, y] of [
    [body.x - body.rx + 10, body.y - body.ry + 10],
    [body.x + body.rx - 10, body.y - body.ry + 10],
    [body.x - body.rx + 10, body.y + body.ry - 10],
    [body.x + body.rx - 10, body.y + body.ry - 10],
  ] as const) {
    parts.push(circle(x, y, 3, { fill: pal.outline }))
  }
  if (!k.noHead) {
    parts.push(k.roundHead ? circle(head.x, head.y, head.r, { fill: pal.body, ...outlined(pal) }) : rect(head.x - 28, head.y - 30, 56, 60, 16, { fill: pal.body, ...outlined(pal) }))
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
