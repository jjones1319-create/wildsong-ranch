import { AdditiveBlending, BufferAttribute, BufferGeometry, DoubleSide, DynamicDrawUsage, Mesh, MeshBasicMaterial, NormalBlending, type Texture } from 'three'
import { cellUv } from './fxAtlas.ts'

/** The per-vertex attributes and their floats per quad. */
const ATTRS = [['position', 12], ['uv', 8], ['color', 16]] as const

/**
 * docs/BATTLE_3D.md §7: one draw for many effect quads. A fixed pool of quads whose corners, texture cells and colours
 * (with alpha) are written on the CPU each frame into preallocated arrays; only the used part is uploaded, and the
 * mesh hides itself when empty (no draw at all). The attack effects use two: glowing (added light) and solid.
 * Plain MeshBasicMaterial with vertex colours, so the WebGL and WebGPU renderers draw it the same.
 */
export class QuadBatch {
  readonly mesh: Mesh
  readonly max: number
  private readonly pos: Float32Array
  private readonly uv: Float32Array
  private readonly col: Float32Array
  private readonly geo = new BufferGeometry()
  private readonly cell = new Float32Array(4)
  private n = 0
  private drawn = 0

  constructor(max: number, map: Texture, glowing: boolean) {
    this.max = max
    this.pos = new Float32Array(max * 12)
    this.uv = new Float32Array(max * 8)
    this.col = new Float32Array(max * 16)
    const idx = new Uint16Array(max * 6)
    for (let i = 0; i < max; i++) {
      const v = i * 4
      idx[i * 6] = v
      idx[i * 6 + 1] = v + 1
      idx[i * 6 + 2] = v + 2
      idx[i * 6 + 3] = v
      idx[i * 6 + 4] = v + 2
      idx[i * 6 + 5] = v + 3
    }
    this.geo.setIndex(new BufferAttribute(idx, 1))
    this.geo.setAttribute('position', new BufferAttribute(this.pos, 3).setUsage(DynamicDrawUsage))
    this.geo.setAttribute('uv', new BufferAttribute(this.uv, 2).setUsage(DynamicDrawUsage))
    this.geo.setAttribute('color', new BufferAttribute(this.col, 4).setUsage(DynamicDrawUsage))
    this.geo.setDrawRange(0, 0)
    const mat = new MeshBasicMaterial({ map, vertexColors: true, transparent: true, depthWrite: false, side: DoubleSide, blending: glowing ? AdditiveBlending : NormalBlending })
    this.mesh = new Mesh(this.geo, mat)
    this.mesh.frustumCulled = false
    this.mesh.visible = false
    // solid smoke and dust under the glow
    this.mesh.renderOrder = glowing ? 4 : 3
  }

  begin(): void {
    this.n = 0
  }

  /** A quad centred at (x, y, z) spanning ±a and ±b (world half-axes), from the atlas cell, in linear r, g, b and alpha. */
  quad(x: number, y: number, z: number, ax: number, ay: number, az: number, bx: number, by: number, bz: number, cell: number, r: number, g: number, b: number, a: number): void {
    if (this.n >= this.max || a <= 0.003) return
    const i = this.n++
    const p = this.pos
    let o = i * 12
    p[o++] = x - ax - bx; p[o++] = y - ay - by; p[o++] = z - az - bz
    p[o++] = x + ax - bx; p[o++] = y + ay - by; p[o++] = z + az - bz
    p[o++] = x + ax + bx; p[o++] = y + ay + by; p[o++] = z + az + bz
    p[o++] = x - ax + bx; p[o++] = y - ay + by; p[o] = z - az + bz
    const c = cellUv(cell, this.cell)
    const u = this.uv
    o = i * 8
    u[o++] = c[0]!; u[o++] = c[1]!
    u[o++] = c[2]!; u[o++] = c[1]!
    u[o++] = c[2]!; u[o++] = c[3]!
    u[o++] = c[0]!; u[o] = c[3]!
    const k = this.col
    o = i * 16
    for (let v = 0; v < 4; v++) {
      k[o++] = r
      k[o++] = g
      k[o++] = b
      k[o++] = a
    }
  }

  /** Upload what was written this frame (nothing when it stayed empty). */
  end(): void {
    const n = this.n
    this.mesh.visible = n > 0
    if (n === 0 && this.drawn === 0) return
    this.drawn = n
    this.geo.setDrawRange(0, n * 6)
    for (let j = 0; j < ATTRS.length; j++) {
      const [name, size] = ATTRS[j]!
      const attr = this.geo.getAttribute(name) as BufferAttribute
      attr.clearUpdateRanges()
      attr.addUpdateRange(0, Math.max(1, n) * size)
      attr.needsUpdate = true
    }
  }

  get count(): number {
    return this.n
  }

  dispose(): void {
    this.geo.dispose()
    ;(this.mesh.material as MeshBasicMaterial).dispose()
  }
}
