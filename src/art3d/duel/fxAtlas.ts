import { CanvasTexture, SRGBColorSpace } from 'three'
import { DRAW } from './fxShapes.ts'

/**
 * docs/BATTLE_3D.md §7: the attack effects' one texture, drawn in code once at load: 16 white shapes in a 4 × 4 grid
 * of 64 px cells (fxShapes.ts), tinted per particle by its vertex colour.
 */

const N = 64
const COLS = 4
let atlas: CanvasTexture | null = null

/** The atlas (made once and shared). */
export function fxAtlas(): CanvasTexture {
  if (atlas) return atlas
  const c = document.createElement('canvas')
  c.width = c.height = N * COLS
  const g = c.getContext('2d')!
  for (const key of Object.keys(DRAW)) {
    const cell = Number(key)
    g.save()
    g.translate((cell % COLS) * N, Math.floor(cell / COLS) * N)
    g.beginPath()
    g.rect(1, 1, N - 2, N - 2)
    g.clip()
    DRAW[cell]!(g)
    g.restore()
  }
  atlas = new CanvasTexture(c)
  atlas.colorSpace = SRGBColorSpace
  return atlas
}

/** A cell's texture rectangle (u0, v0 at the bottom-left; the canvas is flipped on upload). */
export function cellUv(cell: number, out: Float32Array): Float32Array {
  const col = cell % COLS
  const row = Math.floor(cell / COLS)
  out[0] = col / COLS
  out[1] = 1 - (row + 1) / COLS
  out[2] = (col + 1) / COLS
  out[3] = 1 - row / COLS
  return out
}

/** Drop the shared atlas (when the duel closes). */
export function disposeFxAtlas(): void {
  atlas?.dispose()
  atlas = null
}
