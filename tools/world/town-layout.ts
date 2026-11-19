/**
 * The 3D world (docs/WORLD_3D.md §3), W0: the town laid out for Blender from the Gloamvault snapshot — every building,
 * prop and station near the walls with its height from the land port, its paint and cloth resolved; the ground under
 * it as a heightfield and palette slots; the road ribbons and the market slab as Unity built them (TerrainChunk.cs
 * BuildRoads / BuildSlabs); and the review cameras that match Gloamvault's own town screenshots.
 *
 * Game space: metres, x east, z south, y up; a yaw θ (degrees) turns a front (south) to (sin θ, cos θ). In Blender a
 * placement is location (x, −z, y), rotation_euler.z = radians(yaw), no mirroring (Gloamvault's kit_lib.game_matrix).
 *
 * Used by tools/blender/world/town.ts (stage `layout`); writes tools/blender/out/world/town/{layout.json, ground.f32,
 * ground.u8}.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { XZ } from './land/data.ts'
import type { Land } from './land/land.ts'

/** The town's wall line (the `streets` place) and the margin of land laid out around it. */
export const TOWN_BOX = { x0: 400, x1: 560, z0: 528, z1: 722 } as const
export const MARGIN = 60
/** The heightfield's spacing (metres). */
export const GROUND_STEP = 1

/** Unity lifts these stations 0.1 m onto the workshops' floors (WorldBuilder.cs). */
const WORKSHOP_FLOOR = new Set(['vale_workbench', 'vale_fletching_bench', 'vale_alchemy_table', 'vale_range', 'vale_tanning_rack', 'vale_spinning_wheel'])

export interface Placement {
  kind: 'building' | 'prop' | 'station'
  id?: string
  label?: string
  piece: string
  x: number
  y: number
  z: number
  yaw: number
  scale: number
  /** Buildings: the [plaster, timber, trim] colours replacing slots 13, 2 and 3-trim (null keeps the palette's). */
  paint?: [string | null, string | null, string | null]
  /** Props: the palette slot the cloth (slot 7) is drawn in, or −1. */
  cloth?: number
}

/** A quad of a road ribbon or the market slab: four corners [x, y, z] (left0, right0, left1, right1) and its kind. */
export interface Quad { c: [number, number, number][]; kind: number }

export interface Camera { name: string; from: [number, number, number]; to: [number, number, number]; fovY: number; ortho?: number; gvShot?: string }

export interface TownLayout {
  about: string
  box: { x0: number; x1: number; z0: number; z1: number }
  palette: string[]
  sky: string
  /** The direction the sunlight travels, game space (Unity's Euler(pitch, yaw) un-mirrored in x). */
  sunDir: [number, number, number]
  placements: Placement[]
  ground: { x0: number; z0: number; nx: number; nz: number; step: number; heights: string; slots: string }
  roads: { id: string; quads: Quad[] }[]
  slab: Quad[]
  cameras: Camera[]
  counts: Record<string, number>
}

type Manifest = { palette: string[]; pieces: Record<string, unknown> }

const round = (v: number, k = 1000) => Math.round(v * k) / k

/**
 * Gloamvault's shot camera (Shots.cs, FollowCamera.cs): the hero at `at` facing `face`; the camera looks at a point
 * 0.05 + 2.916 m over the hero's feet (0.62 × 1.8 m + 1.8 m), from 12 m behind and 2.4 m above it; 40° vertical.
 */
function shotCamera(land: Land, name: string, at: XZ, face: XZ, gvShot: string): Camera {
  const ground = land.heightAt(at[0], at[1])
  const to: [number, number, number] = [at[0], ground + 0.05 + 0.62 * 1.8 + 1.8, at[1]]
  const fx = face[0] - at[0], fz = face[1] - at[1]
  const fl = Math.hypot(fx, fz)
  const from: [number, number, number] = [at[0] - (fx / fl) * 12, to[1] + 2.4, at[1] - (fz / fl) * 12]
  return { name, from: from.map(v => round(v)) as Camera['from'], to: to.map(v => round(v)) as Camera['to'], fovY: 40, gvShot }
}

export function buildTownLayout(land: Land, manifest: Manifest, outDir: string): TownLayout {
  const box = { x0: TOWN_BOX.x0 - MARGIN, x1: TOWN_BOX.x1 + MARGIN, z0: TOWN_BOX.z0 - MARGIN, z1: TOWN_BOX.z1 + MARGIN }
  const inBox = ([x, z]: XZ) => x >= box.x0 && x <= box.x1 && z >= box.z0 && z <= box.z1
  const known = (piece: string) => {
    if (!(piece in manifest.pieces)) throw new Error(`${piece} is not in the kit manifest`)
    return piece
  }
  const look = land.data.townLook
  const pick = (list: string[], i: number) => (i >= 0 && i < list.length ? list[i]! : null)

  const placements: Placement[] = []
  for (const b of land.data.buildings) {
    if (!inBox(b.at)) continue
    placements.push({
      kind: 'building', id: b.id, ...(b.label ? { label: b.label } : {}), piece: known(b.piece),
      x: b.at[0], y: round(land.heightAt(b.at[0], b.at[1])), z: b.at[1], yaw: b.yaw, scale: 1,
      ...(b.paint ? { paint: [pick(look.walls, b.paint[0]), pick(look.timbers, b.paint[1]), pick(look.trims, b.paint[2])] as Placement['paint'] } : {}),
    })
  }
  for (const p of land.data.props) {
    if (!inBox(p.at)) continue
    placements.push({
      kind: 'prop', piece: known(p.piece), x: p.at[0], y: round(land.heightAt(p.at[0], p.at[1]) + Math.max(0, p.lift)), z: p.at[1],
      yaw: p.yaw, scale: p.scale, ...(p.cloth >= 0 ? { cloth: p.cloth } : {}),
    })
  }
  for (const s of land.data.stations) {
    // A station with no piece is a spot inside another building (the church's shrine, a workshop's rack): Unity skips it.
    if (!s.piece || !inBox(s.at)) continue
    placements.push({
      kind: 'station', id: s.id, ...(s.label ? { label: s.label } : {}), piece: known(s.piece), x: s.at[0],
      y: round(land.heightAt(s.at[0], s.at[1]) + (WORKSHOP_FLOOR.has(s.piece) ? 0.1 : 0)), z: s.at[1], yaw: s.yaw, scale: 1,
    })
  }

  // The ground: heights and underlay slots at every grid point.
  const nx = Math.round((box.x1 - box.x0) / GROUND_STEP) + 1
  const nz = Math.round((box.z1 - box.z0) / GROUND_STEP) + 1
  const heights = new Float32Array(nx * nz)
  const slots = new Uint8Array(nx * nz)
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const x = box.x0 + i * GROUND_STEP, z = box.z0 + j * GROUND_STEP
    heights[j * nx + i] = land.heightAt(x, z)
    slots[j * nx + i] = land.groundSlot(x, z, true)
  }

  // The road ribbons (TerrainChunk.BuildRoads): offsets mitred at the bends, a quad every ≤ 2 m, 6 cm over the ground
  // (a boardwalk `boardsLift` over the ground and the water); kept when the quad's middle lies in the box.
  const roads: TownLayout['roads'] = []
  for (const r of land.data.roads) {
    const pts = r.points
    if (pts.length < 2 || r.width <= 0) continue
    const boards = r.surface === 'boards'
    const lift = boards ? land.data.terrain.roads.boardsLift : 0.06
    const half = r.width / 2
    const off: XZ[] = pts.map((_, i) => {
      const norm = (a: XZ, b: XZ): XZ => { const dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz) || 1; return [-dz / l, dx / l] }
      const nPrev: XZ = i > 0 ? norm(pts[i - 1]!, pts[i]!) : [0, 0]
      const nNext: XZ = i + 1 < pts.length ? norm(pts[i]!, pts[i + 1]!) : [0, 0]
      let m: XZ = [nPrev[0] + nNext[0], nPrev[1] + nNext[1]]
      if (m[0] * m[0] + m[1] * m[1] < 1e-6) m = nPrev[0] || nPrev[1] ? nPrev : nNext
      const ml = Math.hypot(m[0], m[1]) || 1
      m = [m[0] / ml, m[1] / ml]
      const basis = nNext[0] || nNext[1] ? nNext : nPrev
      const scale = half / Math.max(0.4, m[0] * basis[0] + m[1] * basis[1])
      return [m[0] * scale, m[1] * scale]
    })
    const vtx = (x: number, z: number): [number, number, number] => {
      const g = land.heightAt(x, z)
      const w = boards ? land.waterLevelAt(x, z) : NaN
      return [round(x), round((Number.isNaN(w) ? g : Math.max(g, w)) + lift), round(z)]
    }
    const quads: Quad[] = []
    for (let i = 0; i + 1 < pts.length; i++) {
      const a = pts[i]!, e = pts[i + 1]!
      const len = Math.hypot(e[0] - a[0], e[1] - a[1])
      if (len < 1e-3) continue
      const pieces = Math.max(1, Math.ceil(len / 2))
      for (let k = 0; k < pieces; k++) {
        const t0 = k / pieces, t1 = (k + 1) / pieces
        const c0: XZ = [a[0] + (e[0] - a[0]) * t0, a[1] + (e[1] - a[1]) * t0]
        const c1: XZ = [a[0] + (e[0] - a[0]) * t1, a[1] + (e[1] - a[1]) * t1]
        const mid: XZ = [(c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2]
        if (!inBox(mid)) continue
        const o0: XZ = [off[i]![0] + (off[i + 1]![0] - off[i]![0]) * t0, off[i]![1] + (off[i + 1]![1] - off[i]![1]) * t0]
        const o1: XZ = [off[i]![0] + (off[i + 1]![0] - off[i]![0]) * t1, off[i]![1] + (off[i + 1]![1] - off[i]![1]) * t1]
        quads.push({
          kind: land.roadKind(r, mid[0], mid[1]),
          c: [vtx(c0[0] + o0[0], c0[1] + o0[1]), vtx(c0[0] - o0[0], c0[1] - o0[1]), vtx(c1[0] + o1[0], c1[1] + o1[1]), vtx(c1[0] - o1[0], c1[1] - o1[1])],
        })
      }
    }
    if (quads.length) roads.push({ id: r.id, quads })
  }

  // The market slab (TerrainChunk.BuildSlabs): every 'town' place as 2 m cells, 5 cm over the ground, flagstones.
  const slab: Quad[] = []
  for (const p of land.data.places) {
    if (p.kind !== 'town' || p.size[0] <= 0 || p.size[1] <= 0) continue
    const px0 = p.at[0] - p.size[0] / 2, px1 = p.at[0] + p.size[0] / 2, pz0 = p.at[1] - p.size[1] / 2, pz1 = p.at[1] + p.size[1] / 2
    const v = (x: number, z: number): [number, number, number] => [round(x), round(land.heightAt(x, z) + 0.05), round(z)]
    for (let z = pz0; z < pz1; z += 2) for (let x = px0; x < px1; x += 2) {
      const qx1 = Math.min(x + 2, px1), qz1 = Math.min(z + 2, pz1)
      slab.push({ kind: 4, c: [v(x, z), v(qx1, z), v(x, qz1), v(qx1, qz1)] })
    }
  }

  // Gloamvault's town shots (Shots.cs 608-615, 707-711), plus a look down on the whole town and one over it.
  const cameras: Camera[] = [
    shotCamera(land, 'town-square', [481, 650], [481, 590], 'town-square.png'),
    shotCamera(land, 'town-gate', [484, 506], [480, 560], 'town-gate.png'),
    shotCamera(land, 'town-shops', [482, 609], [462, 607], 'town-shops.png'),
    { name: 'overview', from: [600, 95, 800], to: [480, 4, 620], fovY: 40 },
    { name: 'top', from: [480, 300, 625], to: [480, 0, 625.001], fovY: 40, ortho: 236 },
  ]

  const raw = land.data.raw as { look?: { sky?: string; sunPitch?: number; sunYaw?: number } }
  const pitch = ((raw.look?.sunPitch ?? 52) * Math.PI) / 180
  const yaw = ((raw.look?.sunYaw ?? 215) * Math.PI) / 180
  const sunDir: [number, number, number] = [round(-Math.sin(yaw) * Math.cos(pitch), 1e4), round(-Math.sin(pitch), 1e4), round(Math.cos(yaw) * Math.cos(pitch), 1e4)]

  const counts: Record<string, number> = { buildings: 0, props: 0, stations: 0 }
  for (const p of placements) counts[`${p.kind}s`]!++
  counts.pieces = new Set(placements.map(p => p.piece)).size
  counts.roadQuads = roads.reduce((n, r) => n + r.quads.length, 0)
  counts.slabQuads = slab.length

  mkdirSync(outDir, { recursive: true })
  writeFileSync(join(outDir, 'ground.f32'), Buffer.from(heights.buffer))
  writeFileSync(join(outDir, 'ground.u8'), Buffer.from(slots.buffer))
  const layout: TownLayout = {
    about: 'Ashbrook (Gloamvault Open World @ 588c001) laid out for the W0 Blender check: docs/WORLD_3D.md, tools/world/town-layout.ts',
    box, palette: manifest.palette, sky: raw.look?.sky ?? '#cfe0ee', sunDir, placements,
    ground: { x0: box.x0, z0: box.z0, nx, nz, step: GROUND_STEP, heights: 'ground.f32', slots: 'ground.u8' },
    roads, slab, cameras, counts,
  }
  writeFileSync(join(outDir, 'layout.json'), JSON.stringify(layout))
  return layout
}

/** The kit manifest from the snapshot. */
export function readKitManifest(path: string): Manifest {
  return JSON.parse(readFileSync(path, 'utf8')) as Manifest
}
