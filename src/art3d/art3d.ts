/**
 * The lazy entry of the 3D monster runtime (ART_2_PLAN §3.2). Everything that imports three lives behind this
 * module; the UI loads it with `import('../art3d/art3d.ts')` the first time a screen shows a model.
 */
export { Stage3D, qualityFor } from './Stage3D.ts'
export type { ActorSpec, MountOptions, PortraitRequest, QualityTier, StageHandle, StageStats } from './Stage3D.ts'
export type { Actor, PlayOptions } from './actor.ts'
export { Arena3DLayer, DASH_SPEED } from './arena3d.ts'
export type { ArenaFighterLike } from './arena3d.ts'
export { portraitCamera } from './arenaCamera.ts'
export type { StageCamera } from './arenaCamera.ts'
export { battleClipFor, IDLE_SIGNALS, locomotionRate, ranchActionFor, ranchIdleFor } from './battleClips.ts'
export type { FighterSignals } from './battleClips.ts'
export { seededRandom } from './faceCells.ts'
export { FACES, STAR_CLIPS } from './types.ts'
export type { ClipName, FaceName } from './types.ts'
