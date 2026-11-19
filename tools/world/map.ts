/**
 * The 3D world (docs/WORLD_3D.md §4), W0: a top-down map of the land from the height port, to check it against
 * Gloamvault's own map (unity/shots/town-map-whole.png) and to plan the town, the road north and the ranch on.
 *
 *   npm run world:map      → art-review/world/map.png       the whole Vale, 1 px a metre
 *                          → art-review/world/map-north.png  the town and the ranch site, 2 px a metre
 *
 * Drawn: hill shading and a height tint, the woods, the water (where waterLevelAt holds), the roads by kind, the
 * buildings' footprints turned by their yaw, the town's wall line, and the proposed ranch site (WORLD_3D §5).
 */
import { mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { writePng, type Raw } from '../art/ultra-pad.ts'
import { loadLand, type XZ } from './land/data.ts'
import { createLand, type Land } from './land/land.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const OUT = join(ROOT, 'art-review', 'world')
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')

/** The ranch site proposed in WORLD_3D §5: the flattest stretch of the brook, up the road from the north gate. */
export const RANCH_SITE = { x0: 390, x1: 640, z0: 250, z1: 500 } as const
/** The town's wall line (the 'streets' place). */
const WALLS = { x0: 400, x1: 560, z0: 528, z1: 722 } as const

type RGB = [number, number, number]
const hex = (h: string): RGB => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
const mix = (a: RGB, b: RGB, t: number): RGB => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]

const GRASS = hex('#6f9a44')
const HIGH = hex('#9a9078')
const LOW = hex('#4f7a3a')
const WOOD = hex('#3f6a34')
const WATER_SHALLOW = hex('#3f7f86')
const WATER_DEEP = hex('#1f4a5a')
const ROAD: Record<number, RGB> = { 1: hex('#8a7552'), 2: hex('#7d6646'), 3: hex('#6b5538'), 4: hex('#9a958a'), 5: hex('#9c7a4e') }
const ROOF = hex('#8c4a3a')
const WALL_LINE = hex('#2b2a30')
const RANCH = hex('#ffd34a')

interface View { name: string; x0: number; z0: number; w: number; h: number; scale: number }

function render(land: Land, v: View): Raw {
  const W = Math.round(v.w * v.scale)
  const Hh = Math.round(v.h * v.scale)
  const img = new Uint8Array(W * Hh * 4)
  const px = (i: number, j: number): [number, number] => [v.x0 + (i + 0.5) / v.scale, v.z0 + (j + 0.5) / v.scale]

  // Heights at pixel centres, one row of margin each side for the normals.
  const G = new Float64Array((W + 2) * (Hh + 2))
  for (let j = -1; j <= Hh; j++) for (let i = -1; i <= W; i++) {
    const [x, z] = px(i, j)
    G[(j + 1) * (W + 2) + (i + 1)] = land.heightAt(x, z)
  }
  const g = (i: number, j: number) => G[(j + 1) * (W + 2) + (i + 1)]!
  // Light from the north-west, a little high: game (x east, y up, z south).
  const L = [-1, 1.6, -1]
  const Ln = Math.hypot(L[0]!, L[1]!, L[2]!)
  const woods = ((land.data.raw.woods ?? []) as { centre: XZ; radius: number }[])

  const set = (i: number, j: number, c: RGB) => {
    if (i < 0 || j < 0 || i >= W || j >= Hh) return
    const k = (j * W + i) * 4
    img[k] = Math.round(c[0]); img[k + 1] = Math.round(c[1]); img[k + 2] = Math.round(c[2]); img[k + 3] = 255
  }

  for (let j = 0; j < Hh; j++) for (let i = 0; i < W; i++) {
    const [x, z] = px(i, j)
    const y = g(i, j)
    const step = 2 / v.scale
    const nx = -(g(i + 1, j) - g(i - 1, j)) / step
    const nz = -(g(i, j + 1) - g(i, j - 1)) / step
    const nl = Math.hypot(nx, 1, nz)
    const lit = Math.max(0, (nx * L[0]! + L[1]! + nz * L[2]!) / (nl * Ln))
    let c = y < 3 ? mix(LOW, GRASS, Math.max(0, y) / 3) : mix(GRASS, HIGH, Math.min(1, (y - 3) / 18))
    if (woods.some(wd => (x - wd.centre[0]) ** 2 + (z - wd.centre[1]) ** 2 <= wd.radius * wd.radius)) c = mix(c, WOOD, 0.55)
    c = c.map(ch => ch * (0.55 + 0.6 * lit)) as RGB
    const level = land.waterLevelAt(x, z)
    if (!Number.isNaN(level)) c = mix(WATER_SHALLOW, WATER_DEEP, Math.min(1, Math.max(0, (level - y) / 1.6)))
    set(i, j, c)
  }

  // Roads: every pixel within half a road's width of its centreline, coloured by kind.
  for (const r of land.data.roads) {
    for (let s = 0; s + 1 < r.points.length; s++) {
      const [ax, az] = r.points[s]!
      const [bx, bz] = r.points[s + 1]!
      const hw = r.width / 2
      const i0 = Math.floor((Math.min(ax, bx) - hw - v.x0) * v.scale), i1 = Math.ceil((Math.max(ax, bx) + hw - v.x0) * v.scale)
      const j0 = Math.floor((Math.min(az, bz) - hw - v.z0) * v.scale), j1 = Math.ceil((Math.max(az, bz) + hw - v.z0) * v.scale)
      const vx = bx - ax, vz = bz - az, len2 = vx * vx + vz * vz
      for (let j = Math.max(0, j0); j <= Math.min(Hh - 1, j1); j++) for (let i = Math.max(0, i0); i <= Math.min(W - 1, i1); i++) {
        const [x, z] = px(i, j)
        const t = len2 < 1e-6 ? 0 : Math.max(0, Math.min(1, ((x - ax) * vx + (z - az) * vz) / len2))
        if (Math.hypot(ax + vx * t - x, az + vz * t - z) <= hw) set(i, j, ROAD[land.roadKind(r, x, z)] ?? ROAD[3]!)
      }
    }
  }

  // Buildings: the footprint turned by the yaw (local +x → (cos a, −sin a), local +z → (sin a, cos a)).
  for (const b of land.data.buildings) {
    const a = (b.yaw * Math.PI) / 180
    const [fw, fd] = b.footprint
    const hx = fw / 2, hz = fd / 2
    const rr = Math.hypot(hx, hz)
    for (let j = Math.floor((b.at[1] - rr - v.z0) * v.scale); j <= Math.ceil((b.at[1] + rr - v.z0) * v.scale); j++) {
      for (let i = Math.floor((b.at[0] - rr - v.x0) * v.scale); i <= Math.ceil((b.at[0] + rr - v.x0) * v.scale); i++) {
        const [x, z] = px(i, j)
        const dx = x - b.at[0], dz = z - b.at[1]
        const lx = dx * Math.cos(a) - dz * Math.sin(a)
        const lz = dx * Math.sin(a) + dz * Math.cos(a)
        if (Math.abs(lx) <= hx && Math.abs(lz) <= hz) set(i, j, lz > hz - 0.8 ? mix(ROOF, [255, 255, 255], 0.35) : ROOF)
      }
    }
  }

  const rect = (r: { x0: number; x1: number; z0: number; z1: number }, c: RGB, thick: number) => {
    const I0 = Math.round((r.x0 - v.x0) * v.scale), I1 = Math.round((r.x1 - v.x0) * v.scale)
    const J0 = Math.round((r.z0 - v.z0) * v.scale), J1 = Math.round((r.z1 - v.z0) * v.scale)
    for (let t = 0; t < thick; t++) {
      for (let i = I0; i <= I1; i++) { set(i, J0 + t, c); set(i, J1 - t, c) }
      for (let j = J0; j <= J1; j++) { set(I0 + t, j, c); set(I1 - t, j, c) }
    }
  }
  rect(WALLS, WALL_LINE, Math.max(1, Math.round(v.scale)))
  rect(RANCH_SITE, RANCH, Math.max(2, Math.round(2 * v.scale)))
  return { w: W, h: Hh, data: img }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  mkdirSync(OUT, { recursive: true })
  const land = createLand(loadLand())
  const t0 = Date.now()
  const views: View[] = [
    { name: 'map', x0: 0, z0: 0, w: 960, h: 960, scale: 1 },
    { name: 'map-north', x0: 360, z0: 230, w: 320, h: 530, scale: 2 },
  ]
  for (const v of views) {
    const path = join(OUT, `${v.name}.png`)
    writePng(FFMPEG, path, render(land, v), false)
    console.log(`${path} (${Math.round(v.w * v.scale)}×${Math.round(v.h * v.scale)})`)
  }
  console.log(`done in ${((Date.now() - t0) / 1000).toFixed(1)} s`)
}
