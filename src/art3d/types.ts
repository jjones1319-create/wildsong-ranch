/**
 * Art 2.0 runtime types (ART_2_PLAN §3.2, §5): the clip contract, the faces, and the sidecar JSON a look ships
 * with (written by tools/blender/monsters/build.py next to its .glb).
 */

/** The ★ clips every look has from P1 (the rest of §5 arrives with each plan's batch). */
export const STAR_CLIPS = [
  'idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop', 'celebrate',
  'walk', 'run', 'sit_down', 'sit', 'dizzy',
  'battle_idle', 'step_fwd', 'step_back', 'dash', 'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win',
] as const
export type ClipName = (typeof STAR_CLIPS)[number]

export const FACES = ['neutral', 'happy', 'tired', 'stressed', 'sad', 'angry', 'sleepy', 'sick', 'strain', 'dizzy', 'surprised'] as const
export type FaceName = (typeof FACES)[number]

export const SOCKETS = ['socket_head', 'socket_crown', 'socket_back', 'socket_mouth', 'socket_paw_L', 'socket_paw_R', 'socket_tail'] as const

export interface ClipMetaJson {
  loop: boolean
  hold: boolean
  seconds: number
  /** Metres per second the clip means to travel (0 for clips that stay put). */
  rootSpeed: number
  markers: { name: string; t: number }[]
  faces: { t: number; face: string }[]
}

export type Rect = readonly [number, number, number, number]

export interface FaceLayout {
  sheet: number
  cells: { white: Record<string, Rect>; lid: Record<string, Rect>; mouth: Record<string, Rect>; small: Record<string, Rect> }
  expressions: Record<string, { white: string; lid: string; mouth: string; pupil: boolean; pupilScale: number }>
  layers: string[]
  eyeColor: string
}

export interface LookSidecar {
  look: string
  plan: string
  version: number
  heightUnits: number
  /** Metres from the ground to the top of the rest pose. */
  restHeight: number
  bounds: { min: number[]; max: number[] }
  bones: { root: string; head: string; hips: string }
  sockets: Record<string, string>
  springs: { kind: string; chain: string[] }[]
  face: FaceLayout
  variants: Record<string, { texture: string; eyeColor: string }>
  palette: Record<string, string>
  clips: Record<string, ClipMetaJson>
  /** Written by tools/art/optimize.ts. */
  budget?: { bytes: number; triangles: number; vertices: number; joints: number; textures: { name: string; mime: string; width: number; height: number; bytes: number }[]; animationBytes: number }
}
