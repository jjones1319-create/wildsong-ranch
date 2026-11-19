/**
 * The land's data (docs/WORLD_3D.md §4): the shape of Gloamvault's content file `content/world/land/vale.json`, as
 * snapshotted in tools/world/gloamvault/land/vale.json, for the fields Wildsong's tools read. Game space: metres,
 * x east, z south, origin the land's north-west corner; a yaw θ (degrees) turns a front (south at 0) to (sin θ, cos θ).
 *
 * `loadLand` fills the defaults Unity's loader gives a missing field (`tools/unity/env.ts` writeWorld and the field
 * initialisers in `LandData.cs`), so the height port reads exactly what Gloamvault's game read.
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export type XZ = [number, number]

export interface LandArea { id: string; name?: string; centre: XZ; radius: number; height: number; ground?: string; levels?: [number, number] }
export interface LandHill { centre: XZ; radius: number; height: number; flat: number }
export interface LandWater {
  id: string
  kind: string
  level: number
  depth: number
  centre: XZ
  radii: XZ
  width: number
  flow: number
  points: XZ[]
  /** "ground": the level is read off the land once (an offset in `level`); "" once resolved. */
  levelFrom: string
}
export interface LandEdge { side: string; height: number; width: number; power: number; ragged: number }
export interface LandFord { at: XZ; radius: number; depth: number }
export interface LandPlace { id: string; name?: string; at: XZ; kind: string; size: XZ; radius: number; nameRadius: number }
export interface LandBuilding { id: string; piece: string; at: XZ; yaw: number; label?: string; footprint: XZ; paint?: [number, number, number] }
export interface LandProp { piece: string; at: XZ; yaw: number; scale: number; cloth: number; lift: number }
export interface LandStation { id: string; kind: string; piece: string; at: XZ; yaw: number; label?: string }
export interface LandRoad { id: string; width: number; points: XZ[]; surface: string }
export interface LandShore { sand: number; wet: number; bank: number }
export interface LandRoadLook { trackMaxWidth: number; boardsLift: number }
export interface LandTerrain { edges: LandEdge[]; fords: LandFord[]; shore: LandShore; roads: LandRoadLook }
export interface TownLook { walls: string[]; timbers: string[]; trims: string[] }

export interface LandData {
  id: string
  name: string
  size: XZ
  seed: number
  noise: { amplitude: number; scale: number; octaves: number }
  areas: LandArea[]
  hills: LandHill[]
  water: LandWater[]
  roads: LandRoad[]
  buildings: LandBuilding[]
  props: LandProp[]
  stations: LandStation[]
  places: LandPlace[]
  terrain: LandTerrain
  townLook: TownLook
  /** Everything else in the file, untouched (look, woods, scatter, npcs…), for later phases. */
  raw: Record<string, unknown>
}

const HERE = dirname(fileURLToPath(import.meta.url))
/** The snapshot of Gloamvault's land (tools/world/gloamvault/land/vale.json). */
export const VALE_PATH = join(HERE, '..', 'gloamvault', 'land', 'vale.json')

type Json = Record<string, unknown>
const arr = <T>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : [])
const num = (v: unknown, d = 0): number => (typeof v === 'number' && Number.isFinite(v) ? v : d)
const str = (v: unknown, d = ''): string => (typeof v === 'string' ? v : d)
const xz = (v: unknown): XZ => (Array.isArray(v) && v.length >= 2 ? [num(v[0]), num(v[1])] : [0, 0])

/** The land with Unity's defaults filled in. A fresh object every call: nothing is shared or mutated. */
export function parseLand(j: Json): LandData {
  const terrain = (j.terrain ?? {}) as Json
  const shore = (terrain.shore ?? {}) as Json
  const roadLook = (terrain.roads ?? {}) as Json
  const noiseJ = (j.noise ?? {}) as Json
  const town = (j.townLook ?? {}) as Json
  return {
    id: str(j.id),
    name: str(j.name),
    size: xz(j.size),
    seed: num(j.seed),
    noise: { amplitude: num(noiseJ.amplitude), scale: num(noiseJ.scale, 1), octaves: num(noiseJ.octaves, 1) },
    areas: arr<Json>(j.areas).map(a => ({ id: str(a.id), name: str(a.name), centre: xz(a.centre), radius: num(a.radius), height: num(a.height), ground: str(a.ground) })),
    hills: arr<Json>(j.hills).map(h => ({ centre: xz(h.centre), radius: num(h.radius), height: num(h.height), flat: num(h.flat) })),
    water: arr<Json>(j.water).map(w => ({
      id: str(w.id), kind: str(w.kind), level: num(w.level), depth: num(w.depth), centre: xz(w.centre), radii: xz(w.radii),
      width: num(w.width), flow: num(w.flow), points: arr<unknown>(w.points).map(xz), levelFrom: str(w.levelFrom),
    })),
    roads: arr<Json>(j.roads).map(r => ({ id: str(r.id), width: num(r.width), points: arr<unknown>(r.points).map(xz), surface: str(r.surface) })),
    buildings: arr<Json>(j.buildings).map(b => ({
      id: str(b.id), piece: str(b.piece), at: xz(b.at), yaw: num(b.yaw), label: typeof b.label === 'string' ? b.label : undefined,
      footprint: xz(b.footprint), paint: Array.isArray(b.paint) && b.paint.length === 3 ? [num(b.paint[0]), num(b.paint[1]), num(b.paint[2])] : undefined,
    })),
    // Unity: a prop's scale ≤ 0 reads as 1, cloth −1 is none, lift 0 (WorldBuilder.cs, env.ts).
    props: arr<Json>(j.props).map(p => ({ piece: str(p.piece), at: xz(p.at), yaw: num(p.yaw), scale: num(p.scale) > 0 ? num(p.scale) : 1, cloth: num(p.cloth, -1), lift: num(p.lift) })),
    stations: arr<Json>(j.stations).map(s => ({ id: str(s.id), kind: str(s.kind), piece: str(s.piece), at: xz(s.at), yaw: num(s.yaw), label: typeof s.label === 'string' ? s.label : undefined })),
    places: arr<Json>(j.places).map(p => ({ id: str(p.id), name: str(p.name), at: xz(p.at), kind: str(p.kind), size: xz(p.size), radius: num(p.radius), nameRadius: num(p.nameRadius) })),
    terrain: {
      // LandData.cs: an edge's power defaults to 2; the shore's bank to 5; a track is at most 3.2 m wide.
      edges: arr<Json>(terrain.edges).map(e => ({ side: str(e.side), height: num(e.height), width: num(e.width), power: num(e.power, 2), ragged: num(e.ragged) })),
      fords: arr<Json>(terrain.fords).map(f => ({ at: xz(f.at), radius: num(f.radius), depth: num(f.depth) })),
      shore: { sand: num(shore.sand, 2), wet: num(shore.wet, 2.8), bank: num(shore.bank, 5) },
      roads: { trackMaxWidth: num(roadLook.trackMaxWidth, 3.2), boardsLift: num(roadLook.boardsLift, 0.24) },
    },
    townLook: { walls: arr<string>(town.walls), timbers: arr<string>(town.timbers), trims: arr<string>(town.trims) },
    raw: j,
  }
}

/** Reads a land file (the Vale snapshot by default). */
export function loadLand(path = VALE_PATH): LandData {
  return parseLand(JSON.parse(readFileSync(path, 'utf8')) as Json)
}
