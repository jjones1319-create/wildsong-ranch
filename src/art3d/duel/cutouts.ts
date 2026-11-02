import { BufferAttribute, BufferGeometry, CanvasTexture, DynamicDrawUsage, Float32BufferAttribute, LinearFilter, Mesh, MeshBasicMaterial, SRGBColorSpace } from 'three'
import { renderMonsterSvg, specForBreed } from '../../art/monster/render.ts'
import { BREED_IDS, type BreedId } from '../../data/types.ts'
import type { Occupant } from './crowdPlan.ts'
import { m3, rotYXZ } from './crowdPose.ts'
import { ART } from '../../data/tuning.ts'

const T = ART.duel.crowd

/**
 * docs/BATTLE_3D.md §8: painted wooden cut-outs of the breeds in the stands, the fans' own home-made boards. Each breed's
 * Classic drawing (src/art/monster) is rasterised once into one atlas with a plywood edge round its silhouette; every
 * board is a front and back quad on a little post, all in one mesh whose corners are moved on the CPU each frame
 * (a few hundred vertices), so they bob and rock with the crowd in a single draw. Later, a breed with a 3D model can
 * stand there instead.
 */

export interface Cutouts {
  mesh: Mesh
  count: number
  triangles: number
  /** GPU bytes of the atlas. */
  bytes: number
  update(now: number, excite: (o: Occupant) => number, reduce: boolean): void
  dispose(): void
}

interface Cell { u0: number; v0: number; u1: number; v1: number; aspect: number }
interface Atlas { texture: CanvasTexture; cells: Map<BreedId, Cell>; white: [number, number]; bytes: number }

const COLS = 8
const WOOD_DARK = '#7a5232'
const WOOD = '#e3c38f'
const BACK = [0.42, 0.3, 0.19]
const POST = [0.5, 0.35, 0.21]

/** A breed's Classic picture without its ground shadow (a board has no floor). */
function breedSvg(b: BreedId): string {
  const svg = renderMonsterSvg(specForBreed(b, { animate: false, particles: false, lite: true, expression: 'happy' }), { size: 256 })
  return svg.replace(/<ellipse cx="128" cy="230"[^>]*fill="url\(#[^"]*-s\)"[^>]*\/>/, '')
}

function loadSvg(svg: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('svg'))
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
  })
}

/** `src` grown by r pixels in every direction and filled with one colour (the board's edge). */
function grown(src: HTMLCanvasElement, r: number, colour: string): HTMLCanvasElement {
  const c = document.createElement('canvas')
  c.width = src.width
  c.height = src.height
  const g = c.getContext('2d')!
  for (let k = 0; k < 16; k++) g.drawImage(src, Math.cos((k / 16) * Math.PI * 2) * r, Math.sin((k / 16) * Math.PI * 2) * r)
  g.drawImage(src, 0, 0)
  g.globalCompositeOperation = 'source-in'
  g.fillStyle = colour
  g.fillRect(0, 0, c.width, c.height)
  return c
}

let atlasPromise: Promise<Atlas | null> | null = null

/** Every breed's board picture in one canvas (built once; null where a canvas can't be read back). */
function atlas(): Promise<Atlas | null> {
  atlasPromise ??= (async () => {
    const cell: number = T.cutout.cellPx
    const rows = Math.ceil(BREED_IDS.length / COLS)
    const canvas = document.createElement('canvas')
    canvas.width = COLS * cell
    canvas.height = rows * cell + 4
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return null
    const imgs = await Promise.all(BREED_IDS.map((b) => loadSvg(breedSvg(b)).catch(() => null)))
    const scratch = document.createElement('canvas')
    scratch.width = scratch.height = cell
    const sg = scratch.getContext('2d')!
    const pad = T.cutout.edgePx + 2
    const cells = new Map<BreedId, Cell>()
    for (let k = 0; k < BREED_IDS.length; k++) {
      const img = imgs[k]
      if (!img) continue
      const x = (k % COLS) * cell
      const y = Math.floor(k / COLS) * cell
      sg.clearRect(0, 0, cell, cell)
      sg.drawImage(img, pad, pad, cell - 2 * pad, cell - 2 * pad)
      ctx.drawImage(grown(scratch, T.cutout.edgePx, WOOD_DARK), x, y)
      ctx.drawImage(grown(scratch, T.cutout.edgePx - 1.5, WOOD), x, y)
      ctx.drawImage(scratch, x, y)
      // the painted part's bounds: the board is cut to them
      let a: Uint8ClampedArray
      try {
        a = ctx.getImageData(x, y, cell, cell).data
      } catch {
        return null
      }
      let x0 = cell, y0 = cell, x1 = -1, y1 = -1
      for (let j = 0; j < cell; j++) for (let i = 0; i < cell; i++) if (a[(j * cell + i) * 4 + 3]! > 127) (x0 = Math.min(x0, i), x1 = Math.max(x1, i), y0 = Math.min(y0, j), y1 = Math.max(y1, j))
      if (x1 < 0) continue
      const W = canvas.width
      const H = canvas.height
      cells.set(BREED_IDS[k]!, { u0: (x + x0) / W, u1: (x + x1 + 1) / W, v0: 1 - (y + y1 + 1) / H, v1: 1 - (y + y0) / H, aspect: (x1 - x0 + 1) / (y1 - y0 + 1) })
    }
    // a plain strip along the bottom for the posts (their colour comes from the vertices)
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, rows * cell, canvas.width, 4)
    const texture = new CanvasTexture(canvas)
    texture.colorSpace = SRGBColorSpace
    texture.generateMipmaps = false
    texture.minFilter = LinearFilter
    const white: [number, number] = [0.5, 1 - (rows * cell + 2) / canvas.height]
    return { texture, cells, white, bytes: canvas.width * canvas.height * 4 }
  })().catch(() => null)
  return atlasPromise!
}

/** One board's 24 corners in its own frame (+z = the painted face), with their UVs and colours. */
function board(cell: Cell, mirror: boolean, white: [number, number]): { pos: number[]; uv: number[]; col: number[] } {
  const C = T.cutout
  // a wide breed gets a lower board, so every board fits about one seat
  const h = Math.min(C.heightM, C.maxWidthM / cell.aspect)
  const w = h * cell.aspect
  const y0 = C.postM
  const t = C.thickM / 2
  const [ua, ub] = mirror ? [cell.u1, cell.u0] : [cell.u0, cell.u1]
  const pos = [-w / 2, y0, t, w / 2, y0, t, w / 2, y0 + h, t, -w / 2, y0 + h, t, w / 2, y0, -t, -w / 2, y0, -t, -w / 2, y0 + h, -t, w / 2, y0 + h, -t]
  const uv = [ua, cell.v0, ub, cell.v0, ub, cell.v1, ua, cell.v1, ub, cell.v0, ua, cell.v0, ua, cell.v1, ub, cell.v1]
  const col = [...Array(4).fill([1, 1, 1]).flat(), ...Array(4).fill(BACK).flat()]
  // the post: four sides of a stick behind the board, from the seat to a third of the way up it
  const px = 0.024, zb = -t - 0.001, zf = -t - 0.045, top = y0 + h * 0.35
  const sides = [[[-px, zb], [px, zb]], [[px, zb], [px, zf]], [[px, zf], [-px, zf]], [[-px, zf], [-px, zb]]]
  for (const [[ax, az], [bx, bz]] of sides as [[number, number], [number, number]][]) {
    pos.push(ax!, 0, az!, bx!, 0, bz!, bx!, top, bz!, ax!, top, az!)
    for (let k = 0; k < 4; k++) uv.push(...white), col.push(...POST)
  }
  return { pos, uv, col }
}

export async function createCutouts(list: readonly Occupant[], seed: number): Promise<Cutouts | null> {
  if (!list.length) return null
  const A = await atlas()
  if (!A) return null
  const boards = list.flatMap((o) => (o.breed && A.cells.has(o.breed) ? [{ o, ...board(A.cells.get(o.breed)!, o.mirror, A.white) }] : []))
  if (!boards.length) return null
  const n = boards.length
  const idx: number[] = []
  for (let b = 0; b < n; b++) for (let q = 0; q < 6; q++) idx.push(...[0, 1, 2, 0, 2, 3].map((k) => b * 24 + q * 4 + k))
  const geo = new BufferGeometry()
  const pos = new Float32Array(n * 72)
  // a BufferAttribute keeps this very array (Float32BufferAttribute would copy it), so the writes below reach the GPU
  const posAttr = new BufferAttribute(pos, 3).setUsage(DynamicDrawUsage)
  geo.setAttribute('position', posAttr)
  geo.setAttribute('uv', new Float32BufferAttribute(boards.flatMap((b) => b.uv), 2))
  geo.setAttribute('color', new Float32BufferAttribute(boards.flatMap((b) => b.col), 3))
  geo.setIndex(idx)
  const mat = new MeshBasicMaterial({ map: A.texture, alphaTest: 0.5, vertexColors: true })
  mat.color.setScalar(T.cutout.shade)
  const mesh = new Mesh(geo, mat)
  mesh.name = 'crowd_cutouts'
  mesh.frustumCulled = false
  const R = m3()
  const DEG = Math.PI / 180
  void seed
  return {
    mesh,
    count: n,
    triangles: n * 12,
    bytes: A.bytes,
    update(now, excite, reduce) {
      const C = T.cutout
      const k = reduce ? T.reducePct / 100 : 1
      for (let b = 0; b < n; b++) {
        const { o, pos: local } = boards[b]!
        const e = excite(o)
        const ph = o.phase
        const hop = reduce ? 0 : C.hopM * e * Math.abs(Math.sin(Math.PI * (T.excite.hopHz * now + ph)))
        const roll = (C.swayDeg * Math.sin(Math.PI * 2 * (o.hz * 0.5 * now + ph)) + C.tiltDeg * e * Math.sin(Math.PI * 2 * (1.6 * now + ph))) * DEG * k
        rotYXZ(R, o.yaw, 0, roll)
        const y = o.y + hop
        for (let v = 0; v < 24; v++) {
          const lx = local[v * 3]!, ly = local[v * 3 + 1]!, lz = local[v * 3 + 2]!
          const out = (b * 24 + v) * 3
          pos[out] = o.x + R[0]! * lx + R[1]! * ly + R[2]! * lz
          pos[out + 1] = y + R[3]! * lx + R[4]! * ly + R[5]! * lz
          pos[out + 2] = o.z + R[6]! * lx + R[7]! * ly + R[8]! * lz
        }
      }
      posAttr.needsUpdate = true
    },
    dispose() {
      geo.dispose()
      mat.dispose()
    },
  }
}
