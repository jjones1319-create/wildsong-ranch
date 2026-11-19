/**
 * The ground of a land (docs/WORLD_3D.md §4): a faithful port of Gloamvault's `Land.cs` height path, so Wildsong's
 * tools can build the town, the land around it and the ranch on the same ground Gloamvault's game stood on.
 *
 * Every sample is a pure function of (x, z) in game space (metres; x east, z south; origin the north-west corner):
 *   heightAt = baseHeight (naturalHeight under the town's plateau) → the buildings' plots → the water's beds and banks
 *   naturalHeight = the areas' soft discs → the hills → the fbm noise → the edges' rise
 *
 * Doubles throughout (Unity used float32): heights differ from Gloamvault's by ~1e-5 m. Order-sensitive steps keep
 * Unity's order (plots in building order; each water body sees the height the one before it left). The input data is
 * never mutated: `levelFrom: "ground"` water is resolved on a copy.
 */
import type { LandArea, LandBuilding, LandData, LandPlace, LandRoad, LandWater, XZ } from './data.ts'
import { clamp, clamp01, fbm, lerp, noise, seedHashOf, smooth } from './noise.ts'

/** Land.cs constants. */
export const PLATEAU_MARGIN = 10
export const PLATEAU_BLEND = 15
export const PLOT_EDGE = 3
export const BANK = 5
export const MAX_BANK = 12

/** Palette slots of the Vale kit (build_kit_vale.py): field stone 0, packed earth 1, sand 10, grass 12. */
export const SLOT = { stone: 0, earth: 1, sand: 10, grass: 12, grassAlt: 6, water: 15 } as const

/** A building's flat plot: the base height at its centre, held across a square of `half` and blended over PLOT_EDGE. */
export interface Plot { x: number; z: number; half: number; height: number }

export interface Land {
  readonly data: LandData
  /** The water with `levelFrom: "ground"` resolved (levels absolute, levelFrom ""). */
  readonly water: readonly LandWater[]
  /** The walled town's plateau box (the first `streets` place ± PLATEAU_MARGIN) and its level, or null. */
  readonly town: { x0: number; x1: number; z0: number; z1: number; height: number } | null
  readonly plots: readonly Plot[]
  heightAt(x: number, z: number): number
  baseHeight(x: number, z: number): number
  naturalHeight(x: number, z: number): number
  edgeRise(x: number, z: number): number
  bankRun(x: number, z: number): number
  /** Distance outside a water body's edge (≤ 0 inside; NaN when far) and `inner` (0 at the middle, 1 at the edge). */
  waterEdge(w: LandWater, x: number, z: number): { e: number; inner: number }
  /** The water surface's height at a point, or NaN. */
  waterLevelAt(x: number, z: number): number
  /** Metres to the nearest water's edge (0 inside), or 1000. */
  waterDistance(x: number, z: number): number
  /** The current at a point (m/s, game space [x, z]). */
  waterFlowAt(x: number, z: number): XZ
  /** The surface normal [x, y, z] from central differences over 0.5 m. */
  normalAt(x: number, z: number): [number, number, number]
  areaAt(x: number, z: number): LandArea | null
  placeAt(x: number, z: number): LandPlace | null
  inStreets(x: number, z: number): boolean
  /** The narrowest road covering the point (a door path over the street it leaves), or null. */
  roadAt(x: number, z: number): LandRoad | null
  /**
   * Land.GroundSlotAt: the palette slot of the ground at a point. With `underlay` (the terrain mesh under the road
   * ribbons and the market slab), no road and no market paint. `slope01` ≤ 0 reads the land's own slope.
   */
  groundSlot(x: number, z: number, underlay?: boolean, slope01?: number): number
  roadSlot(r: LandRoad, x: number, z: number): number
  /** 1 footpath · 2 field track · 3 cart road · 4 flagstones · 5 boards (Land.RoadKind). */
  roadKind(r: LandRoad, x: number, z: number): number
  /** The land's value noise in −1..1 (seeded). */
  noise(x: number, z: number, scale: number, salt?: number): number
}

/** Land.Inside: a place with a size holds its rectangle, else its radius. */
export function inside(p: LandPlace, x: number, z: number): boolean {
  if (p.size[0] > 0 && p.size[1] > 0) return Math.abs(x - p.at[0]) <= p.size[0] / 2 && Math.abs(z - p.at[1]) <= p.size[1] / 2
  return p.radius > 0 && (x - p.at[0]) ** 2 + (z - p.at[1]) ** 2 <= p.radius * p.radius
}

/** Land.Names: inside, or within the wider name radius. */
export function names(p: LandPlace, x: number, z: number): boolean {
  if (inside(p, x, z)) return true
  return p.nameRadius > 0 && (x - p.at[0]) ** 2 + (z - p.at[1]) ** 2 <= p.nameRadius * p.nameRadius
}

/** Land.PolylineNearest: the distance to a polyline and the nearest segment's index. */
export function polylineNearest(pts: readonly XZ[], x: number, z: number): { d: number; segment: number } {
  let best = Number.MAX_VALUE
  let segment = 0
  for (let i = 0; i + 1 < pts.length; i++) {
    const [ax, az] = pts[i]!
    const [bx, bz] = pts[i + 1]!
    const vx = bx - ax
    const vz = bz - az
    const len2 = vx * vx + vz * vz
    const t = len2 < 1e-6 ? 0 : clamp01(((x - ax) * vx + (z - az) * vz) / len2)
    const px = ax + vx * t - x
    const pz = az + vz * t - z
    const d = Math.sqrt(px * px + pz * pz)
    if (d < best) { best = d; segment = i }
  }
  return { d: best, segment }
}

/** Land.PolylineDistance. */
export const polylineDistance = (pts: readonly XZ[], x: number, z: number): number => polylineNearest(pts, x, z).d

/** Land.FootprintHalf(piece): the old table for a building without a footprint (every Vale building has one). */
const FOOTPRINT_HALF: Record<string, number> = {
  vale_house_small: 3.6, vale_house_small_m: 3.6, vale_house_small_b: 3.6, vale_house_long: 5.1, vale_barn: 4.6, vale_smithy: 3.6,
  vale_well: 1.6, vale_shrine: 1.2, vale_stall: 2.2, vale_bank: 6.0, vale_store: 3.6, vale_inn: 5.1, vale_chapel: 5.6, vale_hall: 6.6,
  vale_house_tall: 3.1, vale_house_tall_m: 3.1, vale_house_tall_b: 3.1, vale_shophouse: 4.0, vale_shophouse_m: 4.0, vale_guardhouse: 2.6,
  vale_workshop: 4.1, vale_workshop_slate: 4.1, vale_keep: 6.5, vale_church: 10.5, vale_guildhall: 6.6, vale_library: 5.1,
  vale_stables: 5.1, vale_watermill: 5.6, vale_tannery: 5.1, vale_tent: 2.4, vale_tent_large: 3.6, vale_toll_ruin: 4.6,
  vale_drowned_chapel: 6.4, vale_cave_mouth: 5, vale_keep_gate: 8.4, vale_wall_stone: 2.25, vale_wall_tower_stone: 2.2,
  vale_gate_tower: 2.5, vale_shop_arms: 3.6, vale_shop_bows: 3.6, vale_shop_runes: 3.6, vale_shop_larder: 3.6, vale_shop_apothecary: 3.6,
}

/** Land.FootprintHalf(building): half the longest side of its footprint. */
export function footprintHalf(b: LandBuilding): number {
  const [fw, fd] = b.footprint
  return fw > 0 || fd > 0 ? Math.max(fw, fd) / 2 : (FOOTPRINT_HALF[b.piece] ?? 1.5)
}

export function createLand(data: LandData): Land {
  const seedHash = seedHashOf(data.seed)
  const n = (x: number, z: number, scale: number, salt = 0) => noise(seedHash, x, z, scale, salt)
  const [landWidth, landDepth] = data.size
  const edges = data.terrain.edges
  const fords = data.terrain.fords
  const shoreBank = data.terrain.shore.bank
  const streets = data.places.filter(p => p.kind === 'streets')
  // A copy: ResolveLevels writes the levels back, and the caller's data stays as loaded.
  const water: LandWater[] = data.water.map(w => ({ ...w, centre: [...w.centre] as XZ, radii: [...w.radii] as XZ, points: w.points.map(p => [p[0], p[1]] as XZ) }))

  function edgeRise(x: number, z: number): number {
    let y = 0
    for (let k = 0; k < edges.length; k++) {
      const e = edges[k]!
      if (e.width <= 0 || e.height === 0) continue
      let d: number
      let along: number
      switch (e.side) {
        case 'north': d = z; along = x; break
        case 'south': d = landDepth - z; along = x; break
        case 'west': d = x; along = z; break
        case 'east': d = landWidth - x; along = z; break
        default: continue
      }
      if (d >= e.width * (1 + Math.abs(e.ragged))) continue
      const w = e.width * (1 + e.ragged * n(along, 1000 + k * 300, 55, 70 + k))
      if (d >= w) continue
      y += e.height * Math.pow(clamp01(1 - d / w), Math.max(0.5, e.power))
    }
    return y
  }

  function naturalHeight(x: number, z: number): number {
    let sum = 0
    let wsum = 0
    for (const a of data.areas) {
      const d = Math.sqrt((x - a.centre[0]) ** 2 + (z - a.centre[1]) ** 2)
      const t = Math.max(0, 1 - d / a.radius)
      const outside = Math.max(0, d - a.radius) / 40
      const w = t * t + 0.02 / (1 + outside * outside)
      sum += w * a.height
      wsum += w
    }
    let y = wsum > 1e-6 ? sum / wsum : 0
    for (const h of data.hills) {
      const d2 = ((x - h.centre[0]) ** 2 + (z - h.centre[1]) ** 2) / (h.radius * h.radius)
      if (d2 >= 1) continue
      if (h.flat > 0) {
        const d = Math.sqrt(d2)
        const k = d <= h.flat ? 1 : 1 - smooth((d - h.flat) / (1 - h.flat))
        y += h.height * k
      } else {
        const k = 1 - d2
        y += h.height * k * k
      }
    }
    if (data.noise.amplitude > 0) y += data.noise.amplitude * fbm(seedHash, x, z, data.noise.scale, data.noise.octaves)
    y += edgeRise(x, z)
    return y
  }

  // W13: the town plateau — the first 'streets' rectangle plus a margin, at the natural height of its middle.
  let town: Land['town'] = null
  const t0 = streets[0]
  if (t0 && t0.size[0] > 0 && t0.size[1] > 0) {
    town = {
      x0: t0.at[0] - t0.size[0] / 2 - PLATEAU_MARGIN, x1: t0.at[0] + t0.size[0] / 2 + PLATEAU_MARGIN,
      z0: t0.at[1] - t0.size[1] / 2 - PLATEAU_MARGIN, z1: t0.at[1] + t0.size[1] / 2 + PLATEAU_MARGIN,
      height: naturalHeight(t0.at[0], t0.at[1]),
    }
  }

  function baseHeight(x: number, z: number): number {
    const y = naturalHeight(x, z)
    if (!town) return y
    const dx = Math.max(town.x0 - x, 0, x - town.x1)
    const dz = Math.max(town.z0 - z, 0, z - town.z1)
    const d = Math.sqrt(dx * dx + dz * dz)
    if (d >= PLATEAU_BLEND) return y
    return lerp(town.height, y, smooth(d / PLATEAU_BLEND))
  }

  const plots: Plot[] = data.buildings.map(b => ({ x: b.at[0], z: b.at[1], half: footprintHalf(b), height: baseHeight(b.at[0], b.at[1]) }))

  // Land.ResolveLevels: a body with levelFrom "ground" takes the lowest natural ground round its rim or along its course.
  for (const w of water) {
    if (w.levelFrom !== 'ground') continue
    let low = Number.MAX_VALUE
    if (w.kind === 'pond') {
      low = naturalHeight(w.centre[0], w.centre[1])
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4
        low = Math.min(low, naturalHeight(w.centre[0] + Math.cos(a) * w.radii[0], w.centre[1] + Math.sin(a) * w.radii[1]))
      }
    } else {
      for (let i = 0; i + 1 < w.points.length; i++) {
        const [px, pz] = w.points[i]!
        const [qx, qz] = w.points[i + 1]!
        const len = Math.sqrt((qx - px) ** 2 + (qz - pz) ** 2)
        const steps = Math.max(1, Math.ceil(len / 4))
        for (let s = 0; s <= steps; s++) low = Math.min(low, naturalHeight(lerp(px, qx, s / steps), lerp(pz, qz, s / steps)))
      }
    }
    if (low < Number.MAX_VALUE) w.level = low + w.level
    w.levelFrom = ''
  }

  // Each water body's box (pond: centre ± radii; brook: its points' bounds ± half its width).
  const waterBox = water.map(w => {
    if (w.kind === 'pond') return [w.centre[0] - w.radii[0], w.centre[1] - w.radii[1], w.centre[0] + w.radii[0], w.centre[1] + w.radii[1]] as const
    if (!w.points.length) return [1e9, 1e9, -1e9, -1e9] as const
    let x0 = Infinity, z0 = Infinity, x1 = -Infinity, z1 = -Infinity
    for (const [px, pz] of w.points) { x0 = Math.min(x0, px); z0 = Math.min(z0, pz); x1 = Math.max(x1, px); z1 = Math.max(z1, pz) }
    const h = w.width / 2
    return [x0 - h, z0 - h, x1 + h, z1 + h] as const
  })
  const boxDistance = (k: number, x: number, z: number): number => {
    const b = waterBox[k]!
    const dx = Math.max(b[0] - x, 0, x - b[2])
    const dz = Math.max(b[1] - z, 0, z - b[3])
    return Math.sqrt(dx * dx + dz * dz)
  }

  // Land.WaterEdge, with `inner` in a scratch slot (the map samples it a million times).
  let inner = 1
  function edgeOf(w: LandWater, x: number, z: number): number {
    inner = 1
    if (w.kind === 'pond') {
      const [rx, rz] = w.radii
      if (rx <= 0 || rz <= 0) return NaN
      const r = Math.min(rx, rz)
      const lim = 1 + (MAX_BANK + 1) / r
      if (Math.abs(x - w.centre[0]) > rx * lim || Math.abs(z - w.centre[1]) > rz * lim) return NaN
      const ex = (x - w.centre[0]) / rx
      const ez = (z - w.centre[1]) / rz
      const e = Math.sqrt(ex * ex + ez * ez)
      inner = Math.min(1, e)
      const d = (e - 1) * r
      return d > MAX_BANK + 1 ? NaN : d
    }
    if (w.points.length < 2 || w.width <= 0) return NaN
    const dist = polylineDistance(w.points, x, z)
    const hw = w.width / 2
    inner = Math.min(1, dist / hw)
    const dd = dist - hw
    return dd > MAX_BANK + 1 ? NaN : dd
  }

  const bankRun = (x: number, z: number): number => Math.min(BANK, shoreBank) * (0.55 + 0.45 * (0.5 + 0.5 * n(x, z, 21, 61)))

  function heightAt(x: number, z: number): number {
    let y = baseHeight(x, z)
    for (const p of plots) {
      const d = Math.max(Math.abs(x - p.x), Math.abs(z - p.z)) - p.half
      if (d >= PLOT_EDGE) continue
      y = lerp(y, p.height, d <= 0 ? 1 : 1 - smooth(d / PLOT_EDGE))
    }
    for (let k = 0; k < water.length; k++) {
      const w = water[k]!
      if (w.kind !== 'pond' && boxDistance(k, x, z) > MAX_BANK + 1) continue
      const e = edgeOf(w, x, z)
      if (Number.isNaN(e)) continue
      if (e <= 0) {
        let bed = w.level - w.depth * Math.max(0, 1 - inner * inner)
        for (const f of fords) {
          const d = Math.sqrt((x - f.at[0]) ** 2 + (z - f.at[1]) ** 2)
          if (d < f.radius) bed = lerp(bed, Math.max(bed, w.level - f.depth), 1 - smooth(d / f.radius))
        }
        y = Math.min(y, bed)
      } else if (e < MAX_BANK) {
        const drop = y - w.level
        if (drop <= 0) { if (e < BANK) y = Math.min(y, w.level); continue }
        const run = clamp(drop * 2.6, bankRun(x, z), MAX_BANK)
        if (e >= run) continue
        const margin = 0.7
        const low = Math.min(y, w.level + 0.05)
        y = e <= margin ? low : lerp(low, y, smooth((e - margin) / (run - margin)))
      }
    }
    return y
  }

  function waterLevelAt(x: number, z: number): number {
    let best = NaN
    for (let k = 0; k < water.length; k++) {
      if (boxDistance(k, x, z) > 0.02) continue
      const w = water[k]!
      const e = edgeOf(w, x, z)
      if (!Number.isNaN(e) && e <= 0.01 && (Number.isNaN(best) || w.level > best)) best = w.level
    }
    return best
  }

  function waterDistance(x: number, z: number): number {
    let best = 1000
    for (let k = 0; k < water.length; k++) {
      const w = water[k]!
      let e: number
      if (w.kind === 'pond') {
        const [rx, rz] = w.radii
        if (rx <= 0 || rz <= 0) continue
        const ex = (x - w.centre[0]) / rx
        const ez = (z - w.centre[1]) / rz
        const r = Math.min(rx, rz)
        if ((Math.max(Math.abs(ex), Math.abs(ez)) - 1) * r >= best) continue
        e = (Math.sqrt(ex * ex + ez * ez) - 1) * r
      } else {
        if (w.points.length < 2) continue
        if (boxDistance(k, x, z) >= best) continue
        e = polylineDistance(w.points, x, z) - w.width / 2
      }
      best = Math.min(best, Math.max(0, e))
    }
    return best
  }

  function waterFlowAt(x: number, z: number): XZ {
    let best: XZ = [0, 0]
    let bestD = Number.MAX_VALUE
    for (const w of water) {
      if (w.kind !== 'brook' || w.flow === 0 || w.points.length < 2) continue
      const { d, segment } = polylineNearest(w.points, x, z)
      const half = w.width / 2
      if (d > half + 1.5 || d >= bestD) continue
      const [ax, az] = w.points[segment]!
      const [bx, bz] = w.points[segment + 1]!
      const dx = bx - ax
      const dz = bz - az
      const len2 = dx * dx + dz * dz
      if (len2 < 1e-6) continue
      const len = Math.sqrt(len2)
      const edge = clamp01(d / Math.max(0.5, half))
      const speed = w.flow * (1 - 0.55 * edge * edge)
      best = [(dx / len) * speed, (dz / len) * speed]
      bestD = d
    }
    if (bestD === Number.MAX_VALUE) return [0, 0]
    for (const w of water) {
      if (w.kind !== 'pond') continue
      const e = edgeOf(w, x, z)
      if (!Number.isNaN(e) && e < 0) return [best[0] * 0.33, best[1] * 0.33]
    }
    return best
  }

  function normalAt(x: number, z: number): [number, number, number] {
    const h = 0.5
    const dx = heightAt(x + h, z) - heightAt(x - h, z)
    const dz = heightAt(x, z + h) - heightAt(x, z - h)
    const nx = -dx / (2 * h)
    const nz = -dz / (2 * h)
    const len = Math.sqrt(nx * nx + 1 + nz * nz)
    return [nx / len, 1 / len, nz / len]
  }

  function areaAt(x: number, z: number): LandArea | null {
    let best: LandArea | null = null
    let bestW = 0
    let nearest: LandArea | null = null
    let nearestD = Number.MAX_VALUE
    for (const a of data.areas) {
      const d = Math.sqrt((x - a.centre[0]) ** 2 + (z - a.centre[1]) ** 2)
      const w = Math.max(0, 1 - d / a.radius)
      if (w > bestW) { bestW = w; best = a }
      if (d - a.radius < nearestD) { nearestD = d - a.radius; nearest = a }
    }
    return best ?? nearest
  }

  function placeAt(x: number, z: number): LandPlace | null {
    let best: LandPlace | null = null
    let bestSize = Number.MAX_VALUE
    for (const p of data.places) {
      if (!names(p, x, z)) continue
      const r = Math.max(p.radius, p.nameRadius)
      const size = p.size[0] > 0 && p.size[1] > 0 ? p.size[0] * p.size[1] : Math.PI * r * r
      if (size < bestSize) { bestSize = size; best = p }
    }
    return best
  }

  const inStreets = (x: number, z: number): boolean => streets.some(p => inside(p, x, z))
  const greens = data.places.filter(p => p.kind === 'green')

  function roadAt(x: number, z: number): LandRoad | null {
    let best: LandRoad | null = null
    for (const r of data.roads) {
      if (r.points.length < 2) continue
      if (polylineDistance(r.points, x, z) > r.width / 2) continue
      if (!best || r.width < best.width) best = r
    }
    return best
  }

  /** Land.Grass: grass with patches of the darker green (the kit's leaf slot), by a slow noise. */
  const grass = (x: number, z: number): number => (n(x, z, 16, 20) + 0.5 * n(x, z, 5, 22) > 0.42 ? SLOT.grassAlt : SLOT.grass)

  function groundSlot(x: number, z: number, underlay = false, slope01 = 0): number {
    if (slope01 <= 0) slope01 = (1 - clamp01(normalAt(x, z)[1])) * 2.5
    const road = underlay ? null : roadAt(x, z)
    let streetsHere = false
    for (const p of data.places) {
      if (!inside(p, x, z)) continue
      if (p.kind === 'town' && !underlay) return SLOT.stone
      if (p.kind === 'arena') return SLOT.sand
      if (p.kind === 'streets') streetsHere = true
    }
    if (streetsHere) {
      if (road) return roadSlot(road, x, z)
      for (const g of greens) if (inside(g, x, z)) return grass(x, z)
      return n(x, z, 3.5, 41) > 0.3 ? SLOT.stone : SLOT.earth
    }
    if (road) return roadSlot(road, x, z)
    const wd = waterDistance(x, z)
    if (wd <= 0) return SLOT.earth
    if (wd < 1.2) return SLOT.sand
    if (slope01 > 0.62) return SLOT.stone
    for (const p of data.places) {
      if (!inside(p, x, z)) continue
      if (p.kind === 'mine') return n(x, z, 4, 31) > -0.1 ? SLOT.stone : SLOT.earth
      if (p.kind === 'camp') return n(x, z, 5, 33) > 0.25 ? grass(x, z) : SLOT.earth
      if (p.kind === 'ruin' || p.kind === 'lair' || p.kind === 'gate') return n(x, z, 4, 35) > 0.1 ? SLOT.stone : SLOT.earth
    }
    switch (areaAt(x, z)?.ground) {
      case 'earth': return SLOT.earth
      case 'sand': return SLOT.sand
      case 'rock': return slope01 > 0.3 ? SLOT.stone : grass(x, z)
      case 'marsh': return n(x, z, 7, 21) > 0.1 ? SLOT.grassAlt : SLOT.grass
      default: return grass(x, z)
    }
  }
  const roadSlot = (r: LandRoad, x: number, z: number): number =>
    r.surface === 'earth' ? SLOT.earth : r.surface === 'stone' ? SLOT.stone : inStreets(x, z) ? SLOT.stone : SLOT.earth
  function roadKind(r: LandRoad, x: number, z: number): number {
    if (r.surface === 'boards') return 5
    if (roadSlot(r, x, z) === SLOT.stone) return 4
    if (r.id.startsWith('path-')) return 1
    return r.width <= data.terrain.roads.trackMaxWidth ? 2 : 3
  }

  return {
    data, water, town, plots,
    heightAt, baseHeight, naturalHeight, edgeRise, bankRun,
    waterEdge: (w, x, z) => { const e = edgeOf(w, x, z); return { e, inner } },
    waterLevelAt, waterDistance, waterFlowAt, normalAt, areaAt, placeAt, inStreets, roadAt, groundSlot, roadSlot, roadKind,
    noise: n,
  }
}
