import { CELL } from './fxRecipe.ts'

/**
 * docs/BATTLE_3D.md §7: the effect shapes, drawn in code (64 px cells, white, tinted per particle). Like the monsters'
 * cel look, the solid shapes are **inked**: a grey rim that the tint turns into a darker shade of the particle's own
 * colour, so a flame, drop or leaf reads against the bright arena floor in any light. Long shapes point along +x.
 */

type G = CanvasRenderingContext2D
/** The rim: a mid grey, so a tinted rim is the particle's colour, darker. */
const RIM = 'rgb(118,118,118)'
const FACET = 'rgb(222,222,222)'

function soft(g: G, x: number, y: number, r: number, stops: [number, number][]): void {
  const grad = g.createRadialGradient(x, y, 0, x, y, r)
  for (const [at, a] of stops) grad.addColorStop(at, `rgba(255,255,255,${a})`)
  g.fillStyle = grad
  g.beginPath()
  g.arc(x, y, r, 0, Math.PI * 2)
  g.fill()
}

function path(g: G, pts: readonly number[]): void {
  g.beginPath()
  g.moveTo(pts[0]!, pts[1]!)
  for (let i = 2; i < pts.length; i += 2) g.lineTo(pts[i]!, pts[i + 1]!)
  g.closePath()
}

/** A shape filled white with an ink rim (`trace` builds the path). */
function inked(g: G, trace: () => void, rim = 5, fill = 'white'): void {
  g.lineJoin = 'round'
  g.lineCap = 'round'
  trace()
  g.strokeStyle = RIM
  g.lineWidth = rim
  g.stroke()
  trace()
  g.fillStyle = fill
  g.fill()
}

/** A line drawn as an inked stroke: rim underneath, white on top. */
function inkLine(g: G, pts: readonly number[], width: number): void {
  g.lineJoin = 'round'
  g.lineCap = 'round'
  for (const [w, c] of [[width + 4, RIM], [width, 'white']] as const) {
    g.strokeStyle = c
    g.lineWidth = w
    g.beginPath()
    g.moveTo(pts[0]!, pts[1]!)
    for (let i = 2; i < pts.length; i += 2) g.lineTo(pts[i]!, pts[i + 1]!)
    g.stroke()
  }
}

/**
 * A tapered ribbon from x0 to x1 along a shallow arc (its middle `bow` px above y), widest (`half` px) toward its
 * head (+x), sharp at both ends: a stroke of moving air.
 */
function ribbon(g: G, x0: number, x1: number, y: number, bow: number, half: number): void {
  const n = 14
  const at = (u: number) => [x0 + (x1 - x0) * u, y - bow * Math.sin(Math.PI * u)] as const
  const w = (u: number) => half * Math.sin(Math.PI * Math.pow(u, 1.4))
  g.beginPath()
  for (let i = 0; i <= n; i++) {
    const [x, yy] = at(i / n)
    g[i ? 'lineTo' : 'moveTo'](x, yy - w(i / n))
  }
  for (let i = n; i >= 0; i--) {
    const [x, yy] = at(i / n)
    g.lineTo(x, yy + w(i / n))
  }
  g.closePath()
}

const circle = (g: G, x: number, y: number, r: number) => () => {
  g.beginPath()
  g.arc(x, y, r, 0, Math.PI * 2)
}

/** Each cell's drawing, in its own 64 × 64 space. */
export const DRAW: Record<number, (g: G) => void> = {
  [CELL.dot]: (g) => soft(g, 32, 32, 30, [[0, 1], [0.25, 0.8], [1, 0]]),
  [CELL.puff]: (g) => {
    const lobes = [[32, 36, 17], [20, 32, 12], [44, 31, 13], [30, 23, 12], [40, 41, 11]] as const
    g.fillStyle = RIM
    for (const [x, y, r] of lobes) circle(g, x + 1, y + 2, r + 2)(), g.fill()
    g.fillStyle = FACET
    for (const [x, y, r] of lobes) circle(g, x, y + 1, r)(), g.fill()
    g.fillStyle = 'white'
    for (const [x, y, r] of lobes) circle(g, x - 2, y - 2, r * 0.75)(), g.fill()
  },
  [CELL.ring]: (g) => {
    g.lineWidth = 9
    g.strokeStyle = RIM
    circle(g, 32, 32, 25)()
    g.stroke()
    g.lineWidth = 5
    g.strokeStyle = 'white'
    circle(g, 32, 32, 25)()
    g.stroke()
  },
  [CELL.crescent]: (g) =>
    inked(g, () => {
      g.beginPath()
      g.arc(32, 42, 27, Math.PI * 1.06, Math.PI * 1.94)
      g.arc(32, 53, 26, Math.PI * 1.86, Math.PI * 1.14, true)
      g.closePath()
    }, 4),
  [CELL.shard]: (g) => {
    inked(g, () => path(g, [4, 32, 36, 21, 60, 32, 36, 43]))
    g.fillStyle = FACET
    path(g, [8, 32, 36, 32, 58, 32, 36, 41])
    g.fill()
  },
  [CELL.leaf]: (g) => {
    inked(g, () => {
      g.beginPath()
      g.moveTo(5, 32)
      g.quadraticCurveTo(30, 8, 59, 32)
      g.quadraticCurveTo(30, 56, 5, 32)
    })
    g.strokeStyle = RIM
    g.lineWidth = 2.5
    g.beginPath()
    g.moveTo(10, 32)
    g.lineTo(52, 32)
    g.stroke()
  },
  [CELL.drop]: (g) => {
    inked(g, () => {
      g.beginPath()
      g.moveTo(6, 32)
      g.lineTo(40, 18)
      g.arc(42, 32, 14, -Math.PI / 2, Math.PI / 2)
      g.lineTo(6, 32)
    })
    circle(g, 46, 27, 4)()
    g.fillStyle = 'white'
    g.fill()
  },
  [CELL.star]: (g) => inked(g, () => path(g, [32, 3, 38, 26, 61, 32, 38, 38, 32, 61, 26, 38, 3, 32, 26, 26]), 4),
  [CELL.streak]: (g) => inked(g, () => path(g, [3, 32, 30, 25, 61, 32, 30, 39]), 4),
  [CELL.crack]: (g) => {
    for (const p of [[4, 33, 16, 29, 26, 35, 38, 30, 48, 34, 60, 31], [26, 35, 30, 46, 27, 56], [38, 30, 42, 19, 47, 10], [16, 29, 13, 20]]) {
      g.strokeStyle = 'white'
      g.lineWidth = 4
      g.lineJoin = 'round'
      g.beginPath()
      g.moveTo(p[0]!, p[1]!)
      for (let i = 2; i < p.length; i += 2) g.lineTo(p[i]!, p[i + 1]!)
      g.stroke()
    }
  },
  [CELL.note]: (g) =>
    inked(g, () => {
      g.beginPath()
      g.ellipse(23, 46, 11, 8, -0.4, 0, Math.PI * 2)
      g.rect(30, 12, 6, 34)
      g.moveTo(30, 12)
      g.lineTo(52, 22)
      g.lineTo(50, 31)
      g.lineTo(36, 23)
    }, 4),
  // a gust: two tapered ribbons of air sweeping along +x in a long, shallow arc (no curl, so it never reads as a letter)
  [CELL.gust]: (g) => {
    inked(g, () => ribbon(g, 3, 61, 40, 10, 5), 3.5)
    inked(g, () => ribbon(g, 14, 54, 26, 6, 2.6), 3)
  },
  [CELL.bolt]: (g) => inkLine(g, [3, 33, 15, 22, 24, 38, 35, 24, 44, 40, 53, 27, 61, 32], 5),
  [CELL.rock]: (g) => {
    inked(g, () => path(g, [14, 22, 30, 9, 50, 15, 57, 36, 44, 55, 19, 52, 7, 37]))
    g.fillStyle = FACET
    path(g, [44, 34, 57, 36, 44, 55, 19, 52, 30, 40])
    g.fill()
  },
  [CELL.orb]: (g) => {
    inked(g, circle(g, 32, 32, 25))
    g.fillStyle = FACET
    g.beginPath()
    g.arc(32, 32, 23, 0.2, Math.PI * 0.95)
    g.fill()
    circle(g, 24, 23, 7)()
    g.fillStyle = 'white'
    g.fill()
  },
  [CELL.flame]: (g) => {
    inked(g, () => {
      g.beginPath()
      g.moveTo(32, 3)
      g.bezierCurveTo(41, 21, 54, 33, 49, 47)
      g.bezierCurveTo(45, 61, 19, 61, 15, 47)
      g.bezierCurveTo(11, 33, 25, 23, 32, 3)
    }, 4, FACET)
    g.fillStyle = 'white'
    g.beginPath()
    g.moveTo(32, 26)
    g.bezierCurveTo(38, 36, 42, 42, 39, 49)
    g.bezierCurveTo(36, 56, 28, 56, 25, 49)
    g.bezierCurveTo(22, 42, 28, 36, 32, 26)
    g.fill()
  },
}
