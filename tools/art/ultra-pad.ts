/**
 * Art 2.1: pad a baked atlas before it ships (ART_2_DETAIL §9.2), for every Ultra look. Used by tools/art/ultra.ts.
 *
 * Texels no bake wrote (between the UV islands, between the tuft locks of the strip) and the transparent texels of the
 * fur-card tiles (alpha < ½) take the colour and ORM of the nearest texels that hold data, ring by ring outward, so
 * texture filtering and mipmaps at an island's edge or a card's alpha edge never pull in black (dark specks on the
 * cards when the renderer runs without MSAA), a zero AO, or a zero roughness (glints). Alpha is kept as baked. The
 * normal map's empty texels are flat already; its unwritten gaps are padded the same way, the card tiles left flat.
 *
 * PNGs are decoded and encoded with ffmpeg (the ffmpeg-static devDependency): no new dependency.
 */
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

export interface Raw { w: number; h: number; data: Uint8Array }

const MAX_BUFFER = 256 * 1024 * 1024

export function readPng(ffmpeg: string, path: string): Raw {
  const png = readFileSync(path)
  const w = png.readUInt32BE(16)     // IHDR: width and height, big-endian
  const h = png.readUInt32BE(20)
  const raw = execFileSync(ffmpeg, ['-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'], { maxBuffer: MAX_BUFFER })
  if (raw.length !== w * h * 4) throw new Error(`${path}: decoded ${raw.length} bytes, expected ${w * h * 4}`)
  return { w, h, data: new Uint8Array(raw.buffer, raw.byteOffset, raw.length) }
}

export function writePng(ffmpeg: string, path: string, img: Raw, alpha: boolean): void {
  execFileSync(ffmpeg, ['-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${img.w}x${img.h}`, '-i', '-',
    '-frames:v', '1', '-pix_fmt', alpha ? 'rgba' : 'rgb24', path], { input: Buffer.from(img.data.buffer, img.data.byteOffset, img.data.byteLength), maxBuffer: MAX_BUFFER })
}

/** 1 where a bake wrote (any colour, or a non-zero AO or roughness), 0 where nothing did. */
export function writtenMask(base: Raw, orm: Raw): Uint8Array {
  const n = base.w * base.h
  const m = new Uint8Array(n)
  const b = base.data
  const o = orm.data
  for (let i = 0; i < n; i++) {
    const k = i * 4
    const empty = b[k]! <= 1 && b[k + 1]! <= 1 && b[k + 2]! <= 1 && o[k]! <= 1 && o[k + 1]! <= 1
    m[i] = empty ? 0 : 1
  }
  return m
}

/** Texels to keep as baked: written, and (in the card tiles) at least half opaque. */
export function solidMask(base: Raw, written: Uint8Array): Uint8Array {
  const m = new Uint8Array(written.length)
  for (let i = 0; i < m.length; i++) m[i] = written[i]! && base.data[i * 4 + 3]! >= 128 ? 1 : 0
  return m
}

/** The atlas layout (bake.py): the bottom `strip` share of the rows is cut into `cells` tiles across. */
export interface Layout { strip: number; cells: number }
export const DEFAULT_LAYOUT: Layout = { strip: 0.125, cells: 8 }

/** A region id per texel: 0 for the islands above the strip, 1 + the cell for each strip tile. Fills never cross. */
export function regions(w: number, h: number, layout: Layout): Uint8Array {
  const r = new Uint8Array(w * h)
  const top = h - Math.round(h * layout.strip)      // rows top-down: the strip is at the bottom
  const cw = w / layout.cells
  for (let y = top; y < h; y++) for (let x = 0; x < w; x++) r[y * w + x] = 1 + Math.min(layout.cells - 1, Math.floor(x / cw))
  return r
}

/**
 * Fill every texel where `keep` is 0 with the mean of its already-filled 8-neighbours in the same region, in
 * breadth-first rings from the kept texels (each texel is visited once). Only RGB changes; texels no ring reaches
 * keep their value.
 */
export function dilate(img: Raw, keep: Uint8Array, region: Uint8Array): number {
  const { w, h, data } = img
  const done = keep.slice()
  let frontier: number[] = []
  for (let i = 0; i < done.length; i++) {
    if (done[i]) continue
    const x = i % w
    const y = (i - x) / w
    if (hasDone(done, region, x, y, w, h)) frontier.push(i)
  }
  let filled = 0
  const queued = new Uint8Array(done.length)
  for (const i of frontier) queued[i] = 1
  while (frontier.length) {
    const next: number[] = []
    const vals: [number, number, number, number][] = []
    for (const i of frontier) {
      const x = i % w
      const y = (i - x) / w
      let r = 0
      let g = 0
      let b = 0
      let c = 0
      for (let dy = -1; dy <= 1; dy++) {
        const yy = y + dy
        if (yy < 0 || yy >= h) continue
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx
          if ((dx === 0 && dy === 0) || xx < 0 || xx >= w) continue
          const j = yy * w + xx
          if (!done[j] || region[j] !== region[i]) continue
          r += data[j * 4]!
          g += data[j * 4 + 1]!
          b += data[j * 4 + 2]!
          c++
        }
      }
      vals.push([i, r / c, g / c, b / c])
    }
    for (const [i, r, g, b] of vals) {
      data[i * 4] = Math.round(r)
      data[i * 4 + 1] = Math.round(g)
      data[i * 4 + 2] = Math.round(b)
      done[i] = 1
      filled++
    }
    for (const [i] of vals) {
      const x = i % w
      const y = (i - x) / w
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx
          const yy = y + dy
          if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue
          const j = yy * w + xx
          if (!done[j] && !queued[j] && region[j] === region[i]) {
            queued[j] = 1
            next.push(j)
          }
        }
      }
    }
    frontier = next
  }
  return filled
}

function hasDone(done: Uint8Array, region: Uint8Array, x: number, y: number, w: number, h: number): boolean {
  const own = region[y * w + x]
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      const xx = x + dx
      const yy = y + dy
      if ((dx || dy) && xx >= 0 && yy >= 0 && xx < w && yy < h && done[yy * w + xx] && region[yy * w + xx] === own) return true
    }
  }
  return false
}

export interface PadReport { colour: number; orm: number; normal: number; variants: number }

/**
 * Pad the atlas in `src` (atlas_base.png, atlas_normal.png, atlas_orm.png and each variant's atlas_<name>.png) into
 * `dst` under the same names. Returns how many texels each map filled.
 */
export function padAtlas(ffmpeg: string, src: string, dst: string, variants: string[], layout: Layout = DEFAULT_LAYOUT): PadReport {
  const p = (dir: string, name: string) => `${dir}/atlas_${name}.png`
  const base = readPng(ffmpeg, p(src, 'base'))
  const orm = readPng(ffmpeg, p(src, 'orm'))
  const normal = readPng(ffmpeg, p(src, 'normal'))
  const written = writtenMask(base, orm)
  const solid = solidMask(base, written)
  const region = regions(base.w, base.h, layout)
  const rep: PadReport = { colour: dilate(base, solid, region), orm: dilate(orm, solid, region), normal: dilate(normal, written, region), variants: 0 }
  writePng(ffmpeg, p(dst, 'base'), base, true)
  writePng(ffmpeg, p(dst, 'orm'), orm, false)
  writePng(ffmpeg, p(dst, 'normal'), normal, false)
  for (const v of variants) {
    const img = readPng(ffmpeg, p(src, v))
    rep.variants += dilate(img, solid, region)
    writePng(ffmpeg, p(dst, v), img, true)
  }
  return rep
}
