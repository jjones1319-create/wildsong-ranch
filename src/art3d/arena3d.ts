import { lookFor } from '../art/models.ts'
import { stageOf, type Monster } from '../core/monster.ts'
import { ART, BATTLE } from '../data/tuning.ts'
import type { FxEvent } from '../fx/bus.ts'
import { battleClipFor, IDLE_SIGNALS, locomotionRate, type ClipChoice, type FighterSignals } from './battleClips.ts'
import type { StageCamera } from './arenaCamera.ts'
import type { ActorSpec, StageHandle } from './Stage3D.ts'
import type { ClipName, FaceName } from './types.ts'

/**
 * The battle seam until P11 (ART_2_PLAN §3.3, §5): turns the arena's two fighters (positions, flags and the
 * effects-bus events) into actors on the shared stage, choosing the nearest ★ clip every frame. A fighter whose
 * breed has no model is simply left out (it stays Classic SVG in the arena's DOM).
 */

export interface ArenaFighterLike {
  monster: Monster
  /** Arena units. */
  x: number
  expression?: string
  busy?: boolean
  dawdling?: boolean
  stunned?: boolean
  lunge?: boolean
  hit?: boolean
  ko?: boolean
  win?: boolean
}

const SIDES = ['a', 'b'] as const
/** The engine's dash speed in arena units per second (walk base × the dash multiplier). */
export const DASH_SPEED = (BATTLE.walk.base / 100) * BATTLE.ticksPerSecond * BATTLE.dash.speedMul

interface SideState {
  prevX: number | null
  vx: number
  prevLunge: boolean
  prevHit: boolean
  pending: Partial<Pick<FighterSignals, 'hit' | 'hitHeavy' | 'lunge' | 'shove' | 'dash' | 'ranged'>>
  /** A one-shot that is still playing (ko and other hold clips stay until the flags change). */
  oneShot: ClipName | null
  oneShotKind: ClipChoice['kind'] | null
}

const FACE_NAMES = new Set<string>(['neutral', 'happy', 'tired', 'stressed', 'sad', 'angry', 'sleepy', 'sick', 'strain', 'dizzy', 'surprised'])

function faceOf(expression: string | undefined): FaceName {
  return expression && FACE_NAMES.has(expression) ? (expression as FaceName) : 'neutral'
}

export class Arena3DLayer {
  private readonly h: StageHandle
  private readonly sides: [SideState, SideState]

  constructor(handle: StageHandle) {
    this.h = handle
    const fresh = (): SideState => ({ prevX: null, vx: 0, prevLunge: false, prevHit: false, pending: {}, oneShot: null, oneShotKind: null })
    this.sides = [fresh(), fresh()]
  }

  get handle(): StageHandle {
    return this.h
  }

  setCamera(c: StageCamera): void {
    this.h.setCamera(c)
  }

  /** Bus events give the hits their weight, and the shoves and dashes their edges. */
  onEvent(ev: FxEvent): void {
    const target = this.sides[ev.side]!
    const other = this.sides[ev.side === 0 ? 1 : 0]!
    switch (ev.kind) {
      case 'hit':
      case 'crit':
        if (ev.crit || ev.strength >= 0.75) target.pending.hitHeavy = true
        else target.pending.hit = true
        break
      case 'fire':
        if (ev.ranged) target.pending.ranged = true
        else target.pending.lunge = true
        break
      case 'push':
        other.pending.shove = true
        target.pending.hit = true
        break
      case 'dash':
        target.pending.dash = true
        break
      default:
        break
    }
  }

  /** Every frame: positions and flags in, actors and clips out. */
  update(fighters: readonly [ArenaFighterLike, ArenaFighterLike], dtMs: number): void {
    const specs: ActorSpec[] = []
    for (let i = 0; i < 2; i++) {
      const f = fighters[i]!
      const side = this.sides[i]!
      const look = lookFor(f.monster.mainBreed, f.monster.variantId, stageOf(f.monster))
      if (!look) {
        side.prevX = null
        continue
      }
      const otherX = fighters[i === 0 ? 1 : 0]!.x
      const facing: 1 | -1 = otherX > f.x ? 1 : otherX < f.x ? -1 : i === 0 ? 1 : -1
      if (side.prevX !== null && dtMs > 0) {
        const v = ((f.x - side.prevX) * 1000) / dtMs
        side.vx += (v - side.vx) / ART.arena.velocitySmoothFrames
      }
      side.prevX = f.x
      const lungeEdge = !!f.lunge && !side.prevLunge
      side.prevLunge = !!f.lunge
      const hitEdge = !!f.hit && !side.prevHit
      side.prevHit = !!f.hit
      const sig: FighterSignals = {
        ...IDLE_SIGNALS,
        ko: !!f.ko,
        win: !!f.win,
        hitHeavy: !!side.pending.hitHeavy,
        hit: hitEdge || !!side.pending.hit,
        stunned: !!f.stunned,
        busy: !!f.busy,
        lunge: lungeEdge || !!side.pending.lunge,
        ranged: !!side.pending.ranged,
        shove: !!side.pending.shove,
        dash: !!side.pending.dash,
        dawdling: !!f.dawdling,
        vx: side.vx,
        facing,
        lowHp: f.expression === 'tired',
        expression: faceOf(f.expression),
      }
      side.pending = {}
      const choice = battleClipFor(sig, DASH_SPEED)
      const id = SIDES[i]!
      specs.push({
        id,
        look: look.look,
        variant: look.variant,
        stage: stageOf(f.monster),
        face: choice.face ?? faceOf(f.expression),
        x: f.x,
        yawDeg: facing * ART.arena.facingYawDeg,
        sick: f.monster.status.sickWeeks > 0 ? 1 : 0,
        flash: hitEdge ? 0.85 : 0,
      })
      this.applyClip(side, id, choice)
    }
    this.h.setActors(specs)
  }

  private applyClip(side: SideState, id: string, choice: ClipChoice): void {
    const actor = this.h.actor(id)
    if (!actor) return
    const meta = actor.asset.meta.clips[choice.clip]
    const oneShot = meta?.loop === false
    if (side.oneShot && side.oneShot !== choice.clip) {
      // a one-shot is still playing; only a hit (or a knockout) cuts it short
      const cuts = choice.kind === 'hit' || choice.clip === 'ko'
      if (!cuts) return
    }
    if (side.oneShot === choice.clip && actor.clipName === choice.clip) return
    const fade = ART.arena.fadeMs[choice.kind]
    let rate = 1
    if (choice.speedDriven && meta) rate = locomotionRate(Math.abs(side.vx), meta.rootSpeed * actor.unitsPerMetre)
    const ok = this.h.play(id, choice.clip, {
      fade,
      rate,
      restart: oneShot,
      onFinish: oneShot && !meta?.hold ? () => {
        if (side.oneShot === choice.clip) {
          side.oneShot = null
          side.oneShotKind = null
        }
      } : undefined,
    })
    if (!ok) return
    side.oneShot = oneShot ? choice.clip : null
    side.oneShotKind = oneShot ? choice.kind : null
    if (!oneShot && choice.speedDriven) actor.setRate(rate)
  }

  frame(time: number): void {
    this.h.frame(time)
  }

  setTimeScale(k: number): void {
    this.h.setTimeScale(k)
  }

  setPaused(on: boolean): void {
    this.h.setPaused(on)
  }

  setHitstop(on: boolean): void {
    this.h.setHitstop(on)
  }

  release(): void {
    this.h.release()
  }
}
