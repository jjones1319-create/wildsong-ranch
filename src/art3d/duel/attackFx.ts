import { Vector3, type Camera, type PerspectiveCamera, type Scene } from 'three'
import { ART } from '../../data/tuning.ts'
import type { Technique } from '../../data/types.ts'
import { fxAtlas } from './fxAtlas.ts'
import { QuadBatch } from './fxBatch.ts'
import { charge, dustKick, flash, healSparkles, projectile, shockwave, slash, trail, wave, whiff, wisps } from './fxDelivery.ts'
import { fizzle, whoosh } from './fxMiss.ts'
import { MOVE, ParticlePool, place, type Particle } from './fxParticles.ts'
import { attackFxFor, fxCount, fxQuality, type AttackFxRecipe } from './fxRecipe.ts'
import { burst, extra, pop, ring, type FxCtx } from './fxSpawn.ts'

/**
 * docs/BATTLE_3D.md §7: every attack looks like what it is. Battle events in (fire, hit, miss, sidestep, heal, fence),
 * effects out, timed by the stage clock: the wind-up glows at the attacker, the release flies (or lunges, or rolls a
 * wave), and the impact bursts exactly when the engine lands it; a miss whiffs past with no burst. All of it is two
 * draws (glowing and solid quads) from one fixed pool; Lite and Reduce motion draw fewer particles and never flash.
 */

const F = ART.duel.fx
const AT = ART.duel.attack
/** Anchors: each side's chest, feet, and front (the chest a little toward the opponent, where moves leave from). */
const CHEST = [0, 1] as const
const FEET = [2, 3] as const
const FRONT = [4, 5] as const

interface Flight {
  r: AttackFxRecipe | null
  land: number
  trailFrom: number
  trailTo: number
  emitted: number
  /** The size its projectile and trail are drawn at (the family's, grown from afar). */
  size: number
  cores: Particle[]
  coreIds: number[]
}

export interface AttackFxOptions {
  lite: boolean
  reduceMotion: boolean
  speed: () => number
}

export class AttackFx {
  readonly anchors = Array.from({ length: 6 }, () => new Vector3())
  private readonly pool = new ParticlePool(F.maxQuads)
  private readonly glow: QuadBatch
  private readonly solid: QuadBatch
  private readonly flights: [Flight, Flight] = [this.flight(), this.flight()]
  private readonly ctx: FxCtx
  private readonly o: AttackFxOptions
  private serial = 0
  private readonly dir = new Vector3()
  private readonly at = new Vector3()
  private readonly feet = new Vector3()
  private readonly vel = new Vector3()
  /** The camera's position last frame (impacts sit on its side of the target). */
  private readonly eye = new Vector3()
  /** Last frame's lens: the view's short side is 2 · distance · shortTan. */
  private shortTan = Math.tan((ART.duel.fov * Math.PI) / 360)
  /** The last impact's zoom (for the stats line). */
  private zoom = 1
  /** CPU time of the last frame's update (ms), for the stats line. */
  cpuMs = 0

  constructor(scene: Scene, o: AttackFxOptions) {
    this.o = o
    const map = fxAtlas()
    this.solid = new QuadBatch(F.maxQuads, map, false)
    this.glow = new QuadBatch(F.maxQuads, map, true)
    scene.add(this.solid.mesh, this.glow.mesh)
    this.ctx = { pool: this.pool, q: this.quality(), seed: 0 }
  }

  private flight(): Flight {
    return { r: null, land: 0, trailFrom: 0, trailTo: 0, emitted: 0, size: 1, cores: [], coreIds: [] }
  }

  /**
   * How much an impact of size S (familyPct / 100) at `p` grows so it still reads from afar: never smaller on screen
   * than impactMin.viewPct of the view's short side (1 for big ones and up close, so the cut's close-ups are
   * untouched; at most maxZoom). Its size goes with √S.
   */
  private zoomAt(p: Vector3, S: number): number {
    const Z = F.impactMin
    const short = 2 * this.eye.distanceTo(p) * this.shortTan
    return Math.min(Z.maxZoom, Math.max(1, (short * Z.viewPct) / 100 / (Z.impactM * Math.sqrt(S))))
  }

  private quality() {
    return fxQuality({ lite: this.o.lite, reduceMotion: this.o.reduceMotion, speed: this.o.speed() })
  }

  /** A fresh context for one event: the quality at the current speed, and the event's own repeatable seed. */
  private begin(): FxCtx {
    this.ctx.q = this.quality()
    this.ctx.seed = ++this.serial * 977
    return this.ctx
  }

  /** The horizontal unit direction from one side toward the other. */
  private aim(side: number): Vector3 {
    const a = this.anchors[FEET[side]!]!
    const b = this.anchors[FEET[1 - side]!]!
    return this.dir.set(b.x - a.x, 0, b.z - a.z).normalize()
  }

  /** A technique fired now that lands after windupSec (stage seconds). */
  fire(side: number, tech: Technique, now: number, windupSec: number): void {
    const r = attackFxFor(tech)
    const c = this.begin()
    const S = r.sizePct / 100
    const w = Math.max(0.05, windupSec)
    const land = now + w
    const travel = Math.min(w, r.ranged ? AT.boltTravelSec : AT.lungeSec)
    const release = land - travel
    const foe = 1 - side
    const dir = this.aim(side)
    const big = r.grand || r.sizePct >= F.familyPct.Heavy
    charge(c, r, FRONT[side]!, now, release, S, big ? fxCount(F.chargeMotes, r, c.q) : 0)
    const f = this.flights[side]!
    f.r = r
    f.land = land
    f.cores.length = 0
    f.coreIds.length = 0
    // from afar a projectile grows by the root of the impact's zoom (not the grand moves: they cut to a close-up)
    f.size = S * (r.grand && ART.duel.cine.enabled ? 1 : this.zoomAt(this.anchors[CHEST[foe]!]!, S))
    if (r.path === 'sweep') {
      const dist = this.anchors[FEET[side]!]!.distanceTo(this.anchors[FEET[foe]!]!)
      wave(c, r, this.anchors[FEET[side]!]!, dir, dist, release, travel, S, fxCount(F.burst, r, c.q))
    } else if (r.ranged) {
      for (let k = 0; k < Math.min(r.hits, 4); k++) {
        // it reaches the target leadSec after the landing, so a miss can veer off before it gets there
        const p = projectile(c, r, side, k, FRONT[side]!, CHEST[foe]!, release + k * F.hitGapSec, travel + F.miss.leadSec, r.hits > 1 ? f.size * 0.8 : f.size)
        f.cores.push(p)
        f.coreIds.push(p.id)
      }
    }
    f.trailFrom = release
    f.trailTo = land + (r.ranged ? (Math.min(r.hits, 4) - 1) * F.hitGapSec : 0)
    f.emitted = 0
    if (r.signature) pop(c, this.anchors[CHEST[side]!]!, r.glow, 0.5 * S, release, 0.2 * c.q.life)
  }

  /** Hit k of n lands now (the impact; later hits of a multi-hit follow a beat apart). */
  hit(side: number, tech: Technique, hitNo: number, of: number, crit: boolean, now: number): void {
    const f = this.flights[side]!
    const r = f.r?.tech === tech.id ? f.r : attackFxFor(tech)
    const c = this.begin()
    const foe = 1 - side
    const t0 = now + (hitNo - 1) * F.hitGapSec
    // the projectile ends where it strikes (it was due leadSec later: the burst takes over just short of the target)
    this.pool.forOwner(side, Math.min(hitNo - 1, 3), (p) => (p.life = Math.min(p.life, Math.max(now - p.t0, p.travel - F.miss.leadSec))))
    const dir = this.aim(side)
    const at = this.at.copy(this.anchors[CHEST[foe]!]!).addScaledVector(dir, -0.15)
    at.addScaledVector(this.feet.copy(this.eye).sub(at).setY(0).normalize(), F.impactFrontM)
    const feet = this.feet.copy(this.anchors[FEET[foe]!]!)
    const S = (r.sizePct / 100) * (of > 1 ? 0.75 : 1) * (crit ? 1.2 : 1)
    // from afar every impact grows (the same for every family); its size on screen goes with z · √S
    const z = (this.zoom = this.zoomAt(at, S))
    burst(c, r, at, dir, t0, S * z * z, Math.max(1, Math.round(fxCount(F.burst, r, c.q) * (of > 1 ? 0.6 : 1))))
    // the extra layer grows with the square root of the size: Basics stay readable, grand moves don't swallow the target
    extra(c, r, at, feet, dir, t0, Math.sqrt(S) * z)
    if (r.slash) slash(c, r, at, S * z, t0)
    if (r.shockwave && hitNo === of) shockwave(c, r, at, feet, dir, S * z, t0)
    if (r.drain && hitNo === 1) wisps(c, r, at, CHEST[side]!, t0 + 0.05, S)
    if (r.grand && hitNo === 1) {
      flash(c, at, r.core, S, t0)
      ring(c, feet, r.ramp[2]!, false, 0.3 * S, 1.8 * S, t0, 0.5 * c.q.life)
    }
    if (r.signature && hitNo === of) {
      burst(c, r, at, this.vel.set(0, 1, 0), t0 + 0.08, S * 1.2 * z * z, fxCount(F.burst, r, c.q))
      ring(c, at, r.ramp[1]!, false, 0.2 * S * z, 1.2 * S * z, t0 + 0.08, 0.4 * c.q.life, 0)
    }
  }

  /**
   * Hit k of n misses (no impact). A projectile veers aside just short of the target, slows and dips to the floor,
   * still trailing, and fizzles out there in a small puff; a melee blow swishes past beside it and kicks up dust. Either
   * way a whoosh of air rushes past the target's side.
   */
  miss(side: number, tech: Technique, hitNo: number, now: number): void {
    const f = this.flights[side]!
    const r = f.r?.tech === tech.id ? f.r : attackFxFor(tech)
    const c = this.begin()
    const M = F.miss
    const dir = this.aim(side)
    const sx = -dir.z
    const sz = dir.x
    const seq = Math.min(hitNo - 1, 3)
    const chest = this.anchors[CHEST[1 - side]!]!
    // aside toward the camera, so it comes down in plain sight in front of the target (side-on, a veer away from the
    // camera would only hide it behind the target's body)
    const sign = (this.eye.x - chest.x) * sx + (this.eye.z - chest.z) * sz >= 0 ? 1 : -1
    const S = (r.sizePct / 100) * this.zoomAt(chest, r.sizePct / 100)
    let veered = false
    this.pool.forOwner(side, seq, (p) => {
      if (p.move !== MOVE.path || p.devAt >= 0) return
      p.devX = sx * sign * F.missOffsetM
      p.devZ = sz * sign * F.missOffsetM
      p.devAt = now
      p.veerSec = M.veerSec
      p.slow = M.slowPct / 100
      p.devSec = M.flySec
      p.life = Math.max(p.life, now - p.t0 + M.flySec)
      // where it would be by then, so it can dip to the floor there
      place(p, now + M.flySec, this.anchors, this.at, this.vel)
      p.devY = M.landM - this.at.y
      veered = true
    })
    const core = f.cores[seq]
    if (veered && core && core.alive && core.id === f.coreIds[seq] && core.devAt === now) {
      place(core, now + M.flySec, this.anchors, this.at, this.vel)
      fizzle(c, r, this.at.setY(M.landM), now + M.flySec * 0.92, f.size)
      if (r.path === 'line') f.trailTo = Math.max(f.trailTo, now + M.flySec * 0.85)
    }
    const beside = this.at.copy(chest).add(this.vel.set(sx * sign * 0.45, 0.1, sz * sign * 0.45))
    if (veered || r.path === 'line') whoosh(c, r, beside, dir, now, S)
    if (!veered && r.path === 'line' && !r.ranged) {
      whiff(c, r, beside, S, now)
      fizzle(c, r, beside.set(beside.x + sx * sign * 0.2, M.landM, beside.z + sz * sign * 0.2), now + 0.05, S * 0.8, true)
    }
  }

  /** A sidestep: straight-line projectiles in the air toward this side keep to where it stood, so a dodge shows. */
  sidestep(side: number): void {
    const chest = this.anchors[CHEST[side]!]!
    this.pool.forOwner(1 - side, -1, (p) => {
      if (p.move !== MOVE.path || p.anchor !== CHEST[side]) return
      p.tx = chest.x
      p.ty = chest.y
      p.tz = chest.z
      p.anchor = -1
    })
  }

  /** A technique's heal (or a drain's) shows as sparkles rising round the healer. */
  healed(side: number, why: string, now: number): void {
    if (why !== 'tech' && why !== 'drain') return
    healSparkles(this.begin(), this.anchors[FEET[side]!]!, now + (why === 'drain' ? F.wispSec : 0), why === 'tech' ? 1 : 0.5)
  }

  fenced(side: number, now: number): void {
    dustKick(this.begin(), this.anchors[FEET[side]!]!, now)
  }

  /** Each frame: the anchors from the monsters (lunges included), trails, then the two draws. */
  update(now: number, camera: Camera, root0: Vector3, root1: Vector3, h0: number, h1: number): void {
    const t0 = performance.now()
    this.eye.copy(camera.position)
    const lens = camera as PerspectiveCamera
    if (lens.isPerspectiveCamera) this.shortTan = Math.tan((lens.fov * Math.PI) / 360) * Math.min(1, lens.aspect)
    this.anchors[CHEST[0]].copy(root0).setY(root0.y + h0 * 0.55)
    this.anchors[CHEST[1]].copy(root1).setY(root1.y + h1 * 0.55)
    this.anchors[FEET[0]].copy(root0).setY(root0.y + 0.03)
    this.anchors[FEET[1]].copy(root1).setY(root1.y + 0.03)
    for (let s = 0; s < 2; s++) {
      const d = this.aim(s)
      this.anchors[FRONT[s]!]!.copy(this.anchors[CHEST[s]!]!).addScaledVector(d, 0.3)
    }
    for (let s = 0; s < 2; s++) this.emitTrail(s, now)
    this.glow.begin()
    this.solid.begin()
    this.pool.draw(now, this.anchors, camera, this.glow, this.solid)
    this.glow.end()
    this.solid.end()
    this.cpuMs = performance.now() - t0
  }

  private emitTrail(side: number, now: number): void {
    const f = this.flights[side]!
    const r = f.r
    if (!r || now < f.trailFrom || now > f.trailTo + 0.05) return
    const c = this.ctx
    const rate = (F.trailPerSec * r.sizePct * c.q.particlePct) / 10_000
    const due = Math.floor((Math.min(now, f.trailTo) - f.trailFrom) * rate)
    const S = f.size
    for (; f.emitted < due; f.emitted++) {
      if (r.ranged && r.path === 'line') {
        const i = f.emitted % Math.max(1, f.cores.length)
        const p = f.cores[i]
        if (!p || !p.alive || p.id !== f.coreIds[i] || p.owner !== side || now < p.t0) continue
        place(p, now, this.anchors, this.at, this.vel)
        trail(c, r, this.at, this.vel.x / p.travel, this.vel.y / p.travel, this.vel.z / p.travel, now, S, f.emitted)
      } else if (!r.ranged) {
        const d = this.aim(side)
        trail(c, r, this.anchors[CHEST[side]!]!, d.x * 4, 0, d.z * 4, now, S, f.emitted)
      }
    }
  }

  /** Quads drawn last frame (glowing + solid), the draws they took, and the last impact's zoom. */
  stats(): { quads: number; draws: number; ms: number; zoom: number } {
    return { quads: this.glow.count + this.solid.count, draws: (this.glow.count ? 1 : 0) + (this.solid.count ? 1 : 0), ms: this.cpuMs, zoom: +this.zoom.toFixed(2) }
  }

  dispose(): void {
    this.pool.clear()
    this.glow.mesh.removeFromParent()
    this.solid.mesh.removeFromParent()
    this.glow.dispose()
    this.solid.dispose()
  }
}
