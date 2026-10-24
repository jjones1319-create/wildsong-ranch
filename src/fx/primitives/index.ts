import type { FxContext } from '../context.ts'
import { beam } from './beam.ts'
import { burst } from './burst.ts'
import { cone } from './cone.ts'
import { debris } from './debris.ts'
import { glow } from './glow.ts'
import { haze } from './haze.ts'
import { impact } from './impact.ts'
import { lightning } from './lightning.ts'
import { mist } from './mist.ts'
import { projectile } from './projectile.ts'
import { ring } from './ring.ts'
import { flash, hitstop, impactFrame, shake } from './screen.ts'
import { sheet } from './sheet.ts'
import { splash } from './splash.ts'
import { trail } from './trail.ts'
import type { EffectHandle, PrimitiveName, PrimitiveParamsMap } from './types.ts'

type Factory<K extends PrimitiveName> = (ctx: FxContext, params: PrimitiveParamsMap[K]) => EffectHandle

/** The 18 primitives by name (VISUAL_V1_EFFECTS §4). */
export const PRIMITIVES: { [K in PrimitiveName]: Factory<K> } = {
  burst,
  cone,
  trail,
  projectile,
  beam,
  ring,
  impact,
  splash,
  sheet,
  lightning,
  haze,
  glow,
  debris,
  mist,
  flash,
  shake,
  hitstop,
  impactFrame,
}
