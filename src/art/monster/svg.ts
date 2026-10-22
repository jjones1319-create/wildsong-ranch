/**
 * Tiny SVG string builder and colour helpers for the procedural monster art (GAME_DESIGN §22).
 * Everything here is pure string work, so the renderer runs in Node tests, in a worker and in the page.
 */

export type Attrs = Record<string, string | number | boolean | null | undefined>

function fmt(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1).replace(/\.0$/, '')
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')
}

export function el(tag: string, attrs: Attrs = {}, children: string | string[] = ''): string {
  let a = ''
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue
    a += ` ${k}="${escapeAttr(typeof v === 'number' ? fmt(v) : v === true ? k : v)}"`
  }
  const inner = Array.isArray(children) ? children.join('') : children
  return inner ? `<${tag}${a}>${inner}</${tag}>` : `<${tag}${a}/>`
}

export const g = (attrs: Attrs, children: string | string[]) => el('g', attrs, children)
export const circle = (cx: number, cy: number, r: number, attrs: Attrs = {}) => el('circle', { cx, cy, r, ...attrs })
export const ellipse = (cx: number, cy: number, rx: number, ry: number, attrs: Attrs = {}) => el('ellipse', { cx, cy, rx, ry, ...attrs })
export const rect = (x: number, y: number, width: number, height: number, rx: number, attrs: Attrs = {}) => el('rect', { x, y, width, height, rx, ...attrs })
export const path = (d: string, attrs: Attrs = {}) => el('path', { d, ...attrs })
export const line = (x1: number, y1: number, x2: number, y2: number, attrs: Attrs = {}) => el('line', { x1, y1, x2, y2, ...attrs })
export const polygon = (points: readonly (readonly [number, number])[], attrs: Attrs = {}) => el('polygon', { points: points.map(([x, y]) => `${fmt(x)},${fmt(y)}`).join(' '), ...attrs })
export const polyline = (points: readonly (readonly [number, number])[], attrs: Attrs = {}) => el('polyline', { points: points.map(([x, y]) => `${fmt(x)},${fmt(y)}`).join(' '), fill: 'none', ...attrs })

/** A path `d` from a list of points, optionally closed. */
export function poly(points: readonly (readonly [number, number])[], close = true): string {
  return points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${fmt(x)} ${fmt(y)}`).join(' ') + (close ? ' Z' : '')
}

/* ---------- colours ---------- */

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = Number.parseInt(full, 16)
  if (!Number.isFinite(n) || full.length !== 6) return [128, 128, 128]
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function rgbToHex(r: number, g: number, b: number): string {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')
  return `#${c(r)}${c(g)}${c(b)}`
}

/** Mixes `pct`% of `b` into `a`. */
export function mix(a: string, b: string, pct: number): string {
  const [ar, ag, ab] = hexToRgb(a)
  const [br, bg, bb] = hexToRgb(b)
  const t = Math.max(0, Math.min(100, pct)) / 100
  return rgbToHex(ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t)
}

export const darken = (hex: string, pct: number) => mix(hex, '#000000', pct)
export const lighten = (hex: string, pct: number) => mix(hex, '#ffffff', pct)

/** Perceived brightness 0–255, to pick a readable outline. */
export function luma(hex: string): number {
  const [r, g, b] = hexToRgb(hex)
  return 0.299 * r + 0.587 * g + 0.114 * b
}
