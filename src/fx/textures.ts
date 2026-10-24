import { CanvasSource, Rectangle, Texture } from 'pixi.js'
import { ATLAS_COLS, CELL, FRAME, FRAME_COUNT, type FrameId } from './atlas.ts'

/**
 * The particle atlas: 16 small shapes drawn once with Canvas 2D into one texture (no asset files). Every frame is
 * white so the particle tint gives it its colour. Shapes fill about 70 % of the cell, leaving room for soft edges.
 */
export interface Atlas {
  texture: Texture
  frames: Texture[]
  /** The procedural displacement map for heat haze and water wobble (RG around 128 = no displacement). */
  noise: Texture
  destroy(): void
}

type Ctx = CanvasRenderingContext2D

function makeCanvas(w: number, h: number): HTMLCanvasElement | OffscreenCanvas {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h)
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  return c
}

function softDot(ctx: Ctx, cx: number, cy: number, r: number, hot = 0.25): void {
  const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r)
  g.addColorStop(0, 'rgba(255,255,255,1)')
  g.addColorStop(hot, 'rgba(255,255,255,0.9)')
  g.addColorStop(0.7, 'rgba(255,255,255,0.35)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.fill()
}

function star(ctx: Ctx, cx: number, cy: number, points: number, outer: number, inner: number, rot = -Math.PI / 2): void {
  ctx.beginPath()
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? outer : inner
    const a = rot + (i * Math.PI) / points
    const x = cx + Math.cos(a) * r
    const y = cy + Math.sin(a) * r
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fill()
}

function drawFrame(ctx: Ctx, id: FrameId, ox: number, oy: number): void {
  const c = CELL / 2
  const cx = ox + c
  const cy = oy + c
  ctx.save()
  ctx.fillStyle = '#fff'
  ctx.strokeStyle = '#fff'
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  switch (id) {
    case FRAME.softDot:
      softDot(ctx, cx, cy, 28)
      break
    case FRAME.ember:
      softDot(ctx, cx, cy, 22, 0.45)
      break
    case FRAME.spark:
      star(ctx, cx, cy, 4, 28, 6)
      softDot(ctx, cx, cy, 12, 0.5)
      break
    case FRAME.droplet:
      ctx.beginPath()
      ctx.moveTo(cx, cy - 26)
      ctx.bezierCurveTo(cx + 18, cy - 2, cx + 16, cy + 22, cx, cy + 22)
      ctx.bezierCurveTo(cx - 16, cy + 22, cx - 18, cy - 2, cx, cy - 26)
      ctx.fill()
      ctx.globalAlpha = 0.55
      ctx.fillStyle = '#000'
      ctx.globalCompositeOperation = 'destination-out'
      ctx.beginPath()
      ctx.ellipse(cx + 5, cy + 6, 5, 8, 0, 0, Math.PI * 2)
      ctx.fill()
      break
    case FRAME.shard:
      ctx.beginPath()
      ctx.moveTo(cx - 4, cy - 28)
      ctx.lineTo(cx + 14, cy + 4)
      ctx.lineTo(cx + 2, cy + 28)
      ctx.lineTo(cx - 14, cy - 2)
      ctx.closePath()
      ctx.fill()
      break
    case FRAME.ring:
      ctx.lineWidth = 7
      ctx.beginPath()
      ctx.arc(cx, cy, 22, 0, Math.PI * 2)
      ctx.stroke()
      break
    case FRAME.streak: {
      const g = ctx.createLinearGradient(cx - 30, cy, cx + 30, cy)
      g.addColorStop(0, 'rgba(255,255,255,0)')
      g.addColorStop(0.5, 'rgba(255,255,255,1)')
      g.addColorStop(1, 'rgba(255,255,255,0)')
      ctx.fillStyle = g
      ctx.beginPath()
      ctx.ellipse(cx, cy, 30, 5, 0, 0, Math.PI * 2)
      ctx.fill()
      break
    }
    case FRAME.puff:
      softDot(ctx, cx - 8, cy + 4, 18, 0.3)
      softDot(ctx, cx + 9, cy - 2, 17, 0.3)
      softDot(ctx, cx, cy - 9, 15, 0.3)
      break
    case FRAME.leaf:
      ctx.beginPath()
      ctx.moveTo(cx - 24, cy + 16)
      ctx.quadraticCurveTo(cx - 12, cy - 26, cx + 24, cy - 16)
      ctx.quadraticCurveTo(cx + 12, cy + 26, cx - 24, cy + 16)
      ctx.fill()
      ctx.globalCompositeOperation = 'destination-out'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.moveTo(cx - 20, cy + 13)
      ctx.lineTo(cx + 20, cy - 13)
      ctx.stroke()
      break
    case FRAME.petal:
      ctx.beginPath()
      ctx.moveTo(cx, cy + 24)
      ctx.bezierCurveTo(cx - 28, cy + 6, cx - 18, cy - 26, cx, cy - 20)
      ctx.bezierCurveTo(cx + 18, cy - 26, cx + 28, cy + 6, cx, cy + 24)
      ctx.fill()
      break
    case FRAME.note:
      ctx.lineWidth = 5
      ctx.beginPath()
      ctx.ellipse(cx - 8, cy + 16, 11, 8, -0.4, 0, Math.PI * 2)
      ctx.fill()
      ctx.beginPath()
      ctx.moveTo(cx + 2, cy + 14)
      ctx.lineTo(cx + 2, cy - 24)
      ctx.quadraticCurveTo(cx + 14, cy - 22, cx + 18, cy - 8)
      ctx.stroke()
      break
    case FRAME.star:
      star(ctx, cx, cy, 5, 28, 12)
      break
    case FRAME.rock:
      ctx.beginPath()
      ctx.moveTo(cx - 24, cy + 6)
      ctx.lineTo(cx - 14, cy - 20)
      ctx.lineTo(cx + 10, cy - 24)
      ctx.lineTo(cx + 26, cy - 4)
      ctx.lineTo(cx + 16, cy + 22)
      ctx.lineTo(cx - 10, cy + 24)
      ctx.closePath()
      ctx.fill()
      ctx.globalAlpha = 0.35
      ctx.globalCompositeOperation = 'destination-out'
      ctx.beginPath()
      ctx.moveTo(cx - 4, cy + 24)
      ctx.lineTo(cx + 16, cy + 22)
      ctx.lineTo(cx + 26, cy - 4)
      ctx.lineTo(cx + 6, cy + 2)
      ctx.closePath()
      ctx.fill()
      break
    case FRAME.coin:
      ctx.beginPath()
      ctx.arc(cx, cy, 24, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalCompositeOperation = 'destination-out'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.arc(cx, cy, 16, 0, Math.PI * 2)
      ctx.stroke()
      break
    case FRAME.bubble:
      ctx.lineWidth = 4
      ctx.globalAlpha = 0.9
      ctx.beginPath()
      ctx.arc(cx, cy, 22, 0, Math.PI * 2)
      ctx.stroke()
      ctx.globalAlpha = 0.3
      ctx.beginPath()
      ctx.arc(cx, cy, 20, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = 1
      ctx.beginPath()
      ctx.arc(cx - 8, cy - 8, 5, 0, Math.PI * 2)
      ctx.fill()
      break
    case FRAME.flake:
      ctx.lineWidth = 4
      for (let i = 0; i < 3; i++) {
        const a = (i * Math.PI) / 3
        ctx.beginPath()
        ctx.moveTo(cx - Math.cos(a) * 24, cy - Math.sin(a) * 24)
        ctx.lineTo(cx + Math.cos(a) * 24, cy + Math.sin(a) * 24)
        ctx.stroke()
      }
      softDot(ctx, cx, cy, 10, 0.5)
      break
  }
  ctx.restore()
}

/** Smooth value noise for the displacement map, tiled so it can scroll. */
function drawNoise(ctx: Ctx, size: number): void {
  const img = ctx.createImageData(size, size)
  const grid = 8
  const cells: number[][] = []
  let seed = 7
  const rnd = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
    return seed / 4294967296
  }
  for (let y = 0; y <= grid; y++) {
    const row: number[] = []
    for (let x = 0; x <= grid; x++) row.push(rnd(), rnd())
    cells.push(row)
  }
  const smooth = (t: number) => t * t * (3 - 2 * t)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const gx = (x / size) * grid
      const gy = (y / size) * grid
      const x0 = Math.floor(gx) % grid
      const y0 = Math.floor(gy) % grid
      const fx = smooth(gx - Math.floor(gx))
      const fy = smooth(gy - Math.floor(gy))
      const x1 = (x0 + 1) % grid
      const y1 = (y0 + 1) % grid
      const sample = (c: number) => {
        const a = cells[y0]![x0 * 2 + c]!
        const b = cells[y0]![x1 * 2 + c]!
        const d = cells[y1]![x0 * 2 + c]!
        const e = cells[y1]![x1 * 2 + c]!
        return (a * (1 - fx) + b * fx) * (1 - fy) + (d * (1 - fx) + e * fx) * fy
      }
      const i = (y * size + x) * 4
      img.data[i] = Math.round(sample(0) * 255)
      img.data[i + 1] = Math.round(sample(1) * 255)
      img.data[i + 2] = 128
      img.data[i + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
}

export function buildAtlas(): Atlas {
  const rows = Math.ceil(FRAME_COUNT / ATLAS_COLS)
  const canvas = makeCanvas(ATLAS_COLS * CELL, rows * CELL)
  const ctx = canvas.getContext('2d') as Ctx
  for (let id = 0; id < FRAME_COUNT; id++) drawFrame(ctx, id as FrameId, (id % ATLAS_COLS) * CELL, Math.floor(id / ATLAS_COLS) * CELL)
  const source = new CanvasSource({ resource: canvas as HTMLCanvasElement, scaleMode: 'linear', alphaMode: 'premultiply-alpha-on-upload' })
  const texture = new Texture({ source })
  const frames: Texture[] = []
  for (let id = 0; id < FRAME_COUNT; id++) frames.push(new Texture({ source, frame: new Rectangle((id % ATLAS_COLS) * CELL, Math.floor(id / ATLAS_COLS) * CELL, CELL, CELL) }))

  const noiseSize = 128
  const noiseCanvas = makeCanvas(noiseSize, noiseSize)
  drawNoise(noiseCanvas.getContext('2d') as Ctx, noiseSize)
  const noiseSource = new CanvasSource({ resource: noiseCanvas as HTMLCanvasElement, scaleMode: 'linear', addressMode: 'repeat' })
  const noise = new Texture({ source: noiseSource })

  return {
    texture,
    frames,
    noise,
    destroy() {
      for (const f of frames) f.destroy(false)
      texture.destroy(true)
      noise.destroy(true)
    },
  }
}
