import { BufferGeometry, CanvasTexture, Float32BufferAttribute, Matrix4, SRGBColorSpace, Vector3 } from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

/**
 * docs/BATTLE_3D.md §8: the crowd's body parts, built in code (low-poly, smooth-shaded, our own storybook townsfolk).
 * One geometry per part; the crowd draws each as one InstancedMesh with a colour per person. Vertex colours multiply
 * that colour: white takes it as is (shirts, skin, hats), darker values make trousers, boots, hat bands and the eyes.
 * Sizes are a base adult in metres; each person scales them. Frames: +y up, +z forward (toward the ring), +x the
 * person's left. A body's origin is its hip on the seat (sitting) or its feet (standing).
 */

/** Where the parts join on a base adult (metres, in the body's frame unless noted). */
export const BODY = {
  /** The torso, hip to the top of the shoulders' slope. */
  torsoH: 0.5,
  /** Standing: the hip's height above the feet. */
  hipStand: 0.44,
  headR: 0.115,
  /** The head's centre above the hip. */
  headY: 0.6,
  shoulderX: 0.128,
  shoulderY: 0.41,
  /** The arm's length to the tip of the hand (an arm hangs down its own −y). */
  armL: 0.37,
  /** Where a held pennant or foam hand starts, down the arm. */
  handY: -0.33,
} as const

type V3 = [number, number, number]

const LEGS = 0.3 // trousers: the shirt's colour, darker (linear multiply)
const BOOTS = 0.07
const EYES = 0.03
const STICK = 0.12

function geometry(pos: number[], col: number[], idx: number[], m?: Matrix4): BufferGeometry {
  const g = new BufferGeometry()
  g.setAttribute('position', new Float32BufferAttribute(pos, 3))
  g.setAttribute('color', new Float32BufferAttribute(col, 3))
  g.setIndex(idx)
  if (m) g.applyMatrix4(m)
  g.computeVertexNormals()
  return g
}

/**
 * A surface of revolution round +y: rings of (radius, y) with a colour each, then optional poles (a point at the
 * bottom or top: [y, colour]). `depth` squashes it front to back.
 */
function lathe(rings: [number, number, number][], segs: number, o: { bottom?: [number, number]; top?: [number, number]; depth?: number; m?: Matrix4 } = {}): BufferGeometry {
  const pos: number[] = []
  const col: number[] = []
  const idx: number[] = []
  const d = o.depth ?? 1
  for (const [r, y, c] of rings) {
    for (let s = 0; s < segs; s++) {
      const a = (s / segs) * Math.PI * 2
      pos.push(Math.sin(a) * r, y, Math.cos(a) * r * d)
      col.push(c, c, c)
    }
  }
  for (let k = 0; k < rings.length - 1; k++) {
    for (let s = 0; s < segs; s++) {
      const a = k * segs + s
      const b = k * segs + ((s + 1) % segs)
      idx.push(a, b, b + segs, a, b + segs, a + segs)
    }
  }
  const pole = ([y, c]: [number, number], ring: number, up: boolean) => {
    const v = pos.length / 3
    pos.push(0, y, 0)
    col.push(c, c, c)
    for (let s = 0; s < segs; s++) {
      const a = ring * segs + s
      const b = ring * segs + ((s + 1) % segs)
      if (up) idx.push(a, b, v)
      else idx.push(b, a, v)
    }
  }
  if (o.top) pole(o.top, rings.length - 1, true)
  if (o.bottom) pole(o.bottom, 0, false)
  return geometry(pos, col, idx, o.m)
}

/** A bent tube through points (its section turned to its path; `phase` turns the section), with an optional end cap. */
function tube(pts: V3[], radii: number[], cols: number[], sides: number, cap: boolean, phase = 0.5): BufferGeometry {
  const pos: number[] = []
  const col: number[] = []
  const idx: number[] = []
  const P = pts.map((p) => new Vector3(...p))
  const side = new Vector3(1, 0, 0)
  for (let i = 0; i < P.length; i++) {
    const t = P[Math.min(P.length - 1, i + 1)]!.clone().sub(P[Math.max(0, i - 1)]!).normalize()
    const u = side.clone().sub(t.clone().multiplyScalar(side.dot(t))).normalize()
    const w = t.clone().cross(u)
    for (let s = 0; s < sides; s++) {
      const a = ((s + phase) / sides) * Math.PI * 2
      const q = P[i]!.clone().addScaledVector(u, Math.cos(a) * radii[i]!).addScaledVector(w, Math.sin(a) * radii[i]!)
      pos.push(q.x, q.y, q.z)
      col.push(cols[i]!, cols[i]!, cols[i]!)
    }
  }
  for (let k = 0; k < P.length - 1; k++) {
    for (let s = 0; s < sides; s++) {
      const a = k * sides + s
      const b = k * sides + ((s + 1) % sides)
      idx.push(a, b, b + sides, a, b + sides, a + sides)
    }
  }
  if (cap) {
    const e = (P.length - 1) * sides
    for (let s = 1; s < sides - 1; s++) idx.push(e, e + s, e + s + 1)
  }
  return geometry(pos, col, idx)
}

/** An axis-aligned box (12 triangles). */
function box(c: V3, size: V3, colour = 1): BufferGeometry {
  const [x, y, z] = c
  const [hx, hy, hz] = size.map((v) => v / 2) as V3
  const pos: number[] = []
  const idx: number[] = []
  // each face its own four corners, so the edges stay crisp
  const faces: [V3, V3, V3][] = [[[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[-1, 0, 0], [0, 0, 1], [0, 1, 0]], [[0, 1, 0], [0, 0, 1], [1, 0, 0]], [[0, -1, 0], [1, 0, 0], [0, 0, 1]], [[0, 0, 1], [1, 0, 0], [0, 1, 0]], [[0, 0, -1], [0, 1, 0], [1, 0, 0]]]
  for (const [n, u, v] of faces) {
    const b = pos.length / 3
    for (const [su, sv] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      pos.push(x + (n[0] + u[0] * su! + v[0] * sv!) * hx, y + (n[1] + u[1] * su! + v[1] * sv!) * hy, z + (n[2] + u[2] * su! + v[2] * sv!) * hz)
    }
    idx.push(b, b + 1, b + 2, b, b + 2, b + 3)
  }
  return geometry(pos, new Array(pos.length).fill(colour), idx)
}

/** Flat polygons (a fan from the first point), one colour: eyes, the flag, the scarf's tail. */
function flat(pts: V3[], colour: number): BufferGeometry {
  const idx: number[] = []
  for (let i = 1; i < pts.length - 1; i++) idx.push(0, i, i + 1)
  return geometry(pts.flat(), new Array(pts.length * 3).fill(colour), idx)
}

function merge(parts: BufferGeometry[]): BufferGeometry {
  const g = mergeGeometries(parts, false)!
  for (const p of parts) p.dispose()
  return g
}

const torso = (lift: number) =>
  lathe([[0.165, lift, 0.8], [0.176, lift + 0.17, 1], [0.126, lift + 0.42, 1]], 7, { top: [lift + BODY.torsoH, 1], depth: 0.82 })

/** Two legs, hip → knee → ankle → toe: three-sided (a flat to the front and on top of the thigh) to keep the crowd light. */
function legs(points: (x: number) => V3[], radii: number[]): BufferGeometry[] {
  return [-1, 1].map((sx) => tube(points(sx * 0.078), radii, [LEGS, LEGS, BOOTS, BOOTS], 3, false, 0.25))
}

/** Every part's geometry (built once and shared by every crowd). */
export function buildPartGeometries() {
  const R = BODY.headR
  const eye = (sx: number) => {
    const d = new Vector3(sx * 0.36, 0.12, 0.92).normalize()
    const c = d.clone().multiplyScalar(R * 1.01)
    const u = new Vector3(0, 1, 0).cross(d).normalize()
    const v = d.clone().cross(u).normalize()
    const p = (a: number, b: number): V3 => c.clone().addScaledVector(u, a).addScaledVector(v, b).toArray() as V3
    return flat([p(0, -0.016), p(0.012, 0.008), p(-0.012, 0.008)], EYES)
  }
  const tilt = new Matrix4().makeRotationX(-0.32)
  return {
    bodySit: merge([torso(0), ...legs((x) => [[x, 0.065, -0.02], [x * 1.05, 0.07, 0.27], [x * 1.05, -0.24, 0.29], [x * 1.05, -0.27, 0.39]], [0.07, 0.064, 0.05, 0.045])]),
    bodyStand: merge([torso(BODY.hipStand - 0.02), ...legs((x) => [[x, BODY.hipStand, 0], [x, 0.23, 0.025], [x, 0.07, 0], [x, 0.045, 0.1]], [0.07, 0.062, 0.05, 0.045])]),
    head: merge([lathe([[R * 0.64, -R * 0.77, 1], [R, 0, 1], [R * 0.64, R * 0.77, 1]], 8, { bottom: [-R, 1], top: [R, 1] }), eye(-1), eye(1)]),
    arm: lathe([[0.042, -0.29, 1], [0.05, 0, 1]], 3, { bottom: [-BODY.armL, 1] }),
    hair: lathe([[R * 1.07, R * 0.12, 1], [R * 0.82, R * 0.72, 1]], 8, { top: [R * 1.08, 1], m: tilt }),
    hat: merge([
      lathe([[R * 0.98, R * 0.45, 0.45], [R * 0.9, R * 1.12, 1]], 8, { top: [R * 1.24, 1] }),
      lathe([[R * 1.85, R * 0.38, 0.85], [R * 0.95, R * 0.47, 0.85]], 8),
    ]),
    scarf: merge([lathe([[0.108, 0.43, 1], [0.08, 0.52, 1]], 8, { depth: 0.85 }), flat([[0.06, 0.28, 0.11], [0.11, 0.28, 0.1], [0.09, 0.45, 0.075], [0.03, 0.46, 0.085]], 1)]),
    pennant: merge([tube([[0, -0.28, 0], [0, -0.8, 0]], [0.013, 0.011], [STICK, STICK], 3, false), flat([[0, -0.79, 0], [0.3, -0.7, 0], [0, -0.6, 0]], 1)]),
    foam: merge([box([0, -0.42, 0.01], [0.16, 0.17, 0.06]), box([0.025, -0.56, 0.01], [0.05, 0.13, 0.05])]),
  }
}

export type PartName = keyof ReturnType<typeof buildPartGeometries>

/** Triangles in a geometry. */
export function triangles(g: BufferGeometry): number {
  return (g.index ? g.index.count : g.getAttribute('position').count) / 3
}

const toSrgb = (c: number) => (c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055)

/**
 * The people's light, painted into a small matcap (the shading by the surface's direction as the camera sees it): a
 * warm sun from above and to the left, a cool sky from above, a warm bounce from the ground. Unlit like the arena (its
 * light is baked), so it sits with it from any angle, costs no lights, and looks the same on WebGL and WebGPU.
 */
export function crowdMatcap(light: { sun: number; sky: number; bounce: number; floor: number }, px = 64): CanvasTexture {
  const c = document.createElement('canvas')
  c.width = c.height = px
  const g = c.getContext('2d')!
  const img = g.createImageData(px, px)
  const L = new Vector3(-0.38, 0.78, 0.5).normalize()
  const rgb: number[] = []
  let peak = 0
  for (let j = 0; j < px; j++) {
    for (let i = 0; i < px; i++) {
      let x = ((i + 0.5) / px) * 2 - 1
      let y = 1 - ((j + 0.5) / px) * 2
      const r = Math.hypot(x, y)
      if (r > 0.999) {
        x /= r / 0.999
        y /= r / 0.999
      }
      const z = Math.sqrt(Math.max(0, 1 - x * x - y * y))
      const sun = Math.max(0, x * L.x + y * L.y + z * L.z) * light.sun
      const sky = (0.5 + 0.5 * y) * light.sky
      const bounce = (0.5 - 0.5 * y) * light.bounce
      const v = [sun * 1.0 + sky * 0.8 + bounce * 1.0 + light.floor, sun * 0.94 + sky * 0.87 + bounce * 0.85 + light.floor, sun * 0.84 + sky * 1.0 + bounce * 0.65 + light.floor]
      peak = Math.max(peak, ...v)
      rgb.push(...v)
    }
  }
  for (let k = 0; k < px * px; k++) {
    for (let ch = 0; ch < 3; ch++) img.data[k * 4 + ch] = Math.round(255 * toSrgb(rgb[k * 3 + ch]! / peak))
    img.data[k * 4 + 3] = 255
  }
  g.putImageData(img, 0, 0)
  const t = new CanvasTexture(c)
  t.colorSpace = SRGBColorSpace
  return t
}
