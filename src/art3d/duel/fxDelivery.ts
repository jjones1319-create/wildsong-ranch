import type { Vector3 } from 'three'
import { ART } from '../../data/tuning.ts'
import { styleOf } from '../../fx/elements.ts'
import { CELL, type AttackFxRecipe } from './fxRecipe.ts'
import { FACE, FADE, MOVE, noise, type Particle } from './fxParticles.ts'
import { from, grow, many, part, pop, ring, tint, type FxCtx } from './fxSpawn.ts'

/**
 * docs/BATTLE_3D.md §7: how an attack gets there. The wind-up gathers a glow at the attacker; a ranged technique flies
 * its element's projectile (orb, drop, lance, bolt, blade, boulder, leaves or a note) to arrive on the landing; a sweep
 * rolls a wave across the floor; Wither and drain send wisps back; Sharp slashes; knockback rings out.
 */

const F = ART.duel.fx
const TAU = Math.PI * 2

/** The wind-up: a glow building at the attacker's front, a ring closing in on it, and motes drawn in for big moves. */
export function charge(c: FxCtx, r: AttackFxRecipe, front: number, t0: number, until: number, S: number, motes: number): void {
  const life = Math.max(0.06, until - t0)
  const p = grow(tint(part(c, CELL.dot, true, t0, life), r.glow, r.core, 0.6), F.chargeM * Math.sqrt(S) * 0.35, F.chargeM * Math.sqrt(S))
  p.move = MOVE.anchor
  p.anchor = front
  p.fade = FADE.swell
  // a ring of the element's colour closing in: reads as gathering power even in bright sun
  const g = grow(tint(part(c, CELL.ring, false, t0, life), r.ramp[1]!, r.ramp[2]!, 0.85), F.chargeM * Math.sqrt(S) * 1.6, F.chargeM * Math.sqrt(S) * 0.25)
  g.move = MOVE.anchor
  g.anchor = front
  g.fade = FADE.swell
  for (let i = 0; i < motes; i++) {
    const s = c.seed + 300 + i * 5
    const th = noise(s) * TAU
    const u = noise(s + 1) * 1.6 - 0.6
    const d = (0.5 + 0.4 * noise(s + 2)) * S
    const m = grow(tint(part(c, r.look.trail, r.look.trailGlow, t0 + life * 0.3 * noise(s + 3), life * (0.7 + 0.3 * noise(s + 4))), r.ramp[0]!, r.core), 0.08 * Math.sqrt(S), 0.04)
    m.move = MOVE.gather
    m.anchor = front
    m.x = Math.cos(th) * d
    m.y = u * d * 0.6
    m.z = Math.sin(th) * d
    m.swirl = 5
    m.fade = FADE.swell
  }
}

function flier(c: FxCtx, cell: number, glow: boolean, side: number, seq: number, src: number, dst: number, t0: number, travel: number, arc: number): Particle {
  const p = part(c, cell, glow, t0, travel + F.overshootSec)
  p.move = MOVE.path
  p.from = src
  p.anchor = dst
  p.travel = travel
  p.arc = arc
  p.owner = side
  p.seq = seq
  p.fade = FADE.hold
  return p
}

/** One projectile (seq k of a multi-hit), from the attacker's front anchor to the target's chest anchor. */
export function projectile(c: FxCtx, r: AttackFxRecipe, side: number, seq: number, src: number, dst: number, t0: number, travel: number, S: number): Particle {
  const sz = F.projectileM * Math.sqrt(S)
  const arc = (0.1 + 0.12 * noise(c.seed + seq)) * (seq % 2 ? -1 : 1)
  const halo = (hex: number, size: number, alpha: number) => grow(tint(flier(c, CELL.dot, true, side, seq, src, dst, t0, travel, arc), hex, hex, alpha), size, size * 1.1)
  let core: Particle
  switch (r.projectile) {
    case 'drop':
      core = grow(tint(flier(c, CELL.drop, false, side, seq, src, dst, t0, travel, arc), r.ramp[1]!, r.ramp[1]!, 0.95), sz * 1.1, sz * 1.2)
      core.face = FACE.stretch
      core.stretch = 1.7
      halo(r.glow, sz * 2.2, 0.45)
      break
    case 'lance':
    case 'bolt':
      core = grow(tint(flier(c, r.projectile === 'bolt' ? CELL.bolt : CELL.shard, false, side, seq, src, dst, t0, travel, arc * 0.5), r.ramp[1]!, r.ramp[1]!), sz * 1.5, sz * 1.6)
      core.face = FACE.stretch
      core.stretch = 2.5
      halo(r.glow, sz * 2.5, 0.6)
      break
    case 'blade':
      core = grow(tint(flier(c, CELL.crescent, false, side, seq, src, dst, t0, travel, arc), r.ramp[0]!, r.ramp[1]!, 0.9), sz * 2.2, sz * 2.4)
      core.spin = 16
      grow(tint(flier(c, CELL.swirl, false, side, seq, src, dst, t0, travel, arc), r.ramp[1]!, r.ramp[2]!, 0.6), sz * 2, sz * 2.6).spin = -12
      break
    case 'boulder':
      core = grow(tint(flier(c, CELL.rock, false, side, seq, src, dst, t0, travel, arc + 0.15), r.ramp[1]!, r.ramp[2]!), sz * 1.9, sz * 1.9)
      core.spin = 7
      break
    case 'leaf':
      core = grow(tint(flier(c, CELL.leaf, false, side, seq, src, dst, t0, travel, arc), r.ramp[1]!, r.ramp[2]!), sz * 1.3, sz * 1.3)
      core.spin = 10
      for (let j = 1; j <= 2; j++) grow(tint(flier(c, CELL.leaf, false, side, seq, src, dst, t0 + j * 0.03, travel, arc + (j === 1 ? 0.22 : -0.18)), r.ramp[1]!, r.ramp[2]!), sz, sz).spin = j === 1 ? -9 : 12
      break
    case 'note':
      core = grow(tint(flier(c, CELL.note, false, side, seq, src, dst, t0, travel, arc), r.ramp[1]!, r.ramp[2]!), sz * 1.6, sz * 1.6)
      grow(tint(flier(c, CELL.ring, false, side, seq, src, dst, t0, travel, arc), r.ramp[2]!, r.ramp[2]!, 0.7), sz * 2, sz * 2.4)
      break
    default:
      if (r.motif === 'smoke') {
        core = grow(tint(flier(c, CELL.puff, false, side, seq, src, dst, t0, travel, arc), r.smoke, r.ramp[3]!, 0.9), sz * 2, sz * 2.2)
        core.spin = 2
        halo(r.glow, sz * 1.3, 0.9)
      } else {
        core = grow(tint(flier(c, CELL.orb, false, side, seq, src, dst, t0, travel, arc), r.ramp[1]!, r.ramp[1]!), sz * 1.2, sz * 1.3)
        halo(r.glow, sz * 2.6, 0.6)
      }
  }
  return core
}

/** One trail particle where a projectile (or a lunging attacker) is now. */
export function trail(c: FxCtx, r: AttackFxRecipe, at: Vector3, vx: number, vy: number, vz: number, t0: number, S: number, i: number): void {
  const k = r.look
  const s = c.seed + 500 + i * 3
  const big = k.trail === CELL.puff || k.trail === CELL.flame || k.trail === CELL.ring
  const p = grow(tint(from(part(c, k.trail, k.trailGlow, t0, 0.38 * c.q.life), at, (noise(s) - 0.5) * 0.1, (noise(s + 1) - 0.5) * 0.1, (noise(s + 2) - 0.5) * 0.1), k.trailGlow ? r.ramp[0]! : r.ramp[1]!, r.ramp[2]!, 0.9), 0.1 * Math.sqrt(S) * (big ? 1.6 : 1), 0.04 * (big ? 3 : 1))
  p.vx = -vx * 0.08 + (noise(s + 3) - 0.5) * 0.4
  p.vy = -vy * 0.08 + (noise(s + 4) - 0.5) * 0.4
  p.vz = -vz * 0.08 + (noise(s + 5) - 0.5) * 0.4
  p.g = k.trailGravity
  p.fade = FADE.hold
  p.rot = noise(s + 6) * TAU
  p.spin = k.spin
  if (k.trail === CELL.streak || k.trail === CELL.drop) {
    p.face = FACE.stretch
    p.stretch = 2.4
  }
}

/** A sweep: a ring rolls out across the floor from the attacker and its front of element particles arrives on the landing. */
export function wave(c: FxCtx, r: AttackFxRecipe, feet: Vector3, dir: Vector3, dist: number, t0: number, travel: number, S: number, count: number): void {
  const reach = dist + 0.4
  // a faint full ring, and the front itself: crescents on the floor, side by side across the arc toward the target
  const g = ring(c, feet, r.ramp[2]!, false, 0.2, reach / 0.78, t0, travel + 0.14)
  g.linear = true
  g.a = 0.4
  const spread = (F.waveFrontDeg * Math.PI) / 180
  const base = Math.atan2(dir.z, dir.x)
  const speed = reach / Math.max(0.05, travel)
  const arcs = Math.max(5, Math.round(count * 0.6))
  for (let i = 0; i < arcs; i++) {
    const a = base + spread * ((i + 0.5) / arcs - 0.5) * 2
    const p = grow(tint(from(part(c, CELL.crescent, false, t0, travel + 0.12), feet, Math.cos(a) * 0.25, 0.03, Math.sin(a) * 0.25), r.ramp[1]!, r.ramp[2]!, 0.9), 0.12 * S, ((reach * spread) / arcs) * 1.5)
    p.vx = Math.cos(a) * speed
    p.vz = Math.sin(a) * speed
    p.face = FACE.ground
    p.nx = Math.sin(a)
    p.nz = -Math.cos(a)
    p.linear = true
    p.fade = FADE.hold
  }
  // the element's own bits, thrown up as the front passes
  const k = r.look
  const size = k.sizeM * Math.sqrt(S)
  for (let i = 0; i < count; i++) {
    const f = 0.25 + 0.75 * noise(c.seed + 60 + i)
    const a = base + spread * (noise(c.seed + 80 + i) * 2 - 1)
    const p = grow(tint(from(part(c, k.cell, k.glow, t0 + travel * f, k.life * c.q.life), feet, Math.cos(a) * reach * f, 0.08, Math.sin(a) * reach * f), r.ramp[1]!, r.ramp[2]!), size, size * 0.7)
    p.vx = Math.cos(a) * 0.8
    p.vz = Math.sin(a) * 0.8
    p.vy = 1.4 + noise(c.seed + 100 + i)
    p.g = k.gravity
    p.spin = k.spin
    p.face = k.stretch ? FACE.stretch : FACE.camera
    p.stretch = k.stretch ? 2 : 1
  }
}

/** Wither and drain: wisps fly back from the target to the attacker. */
export function wisps(c: FxCtx, r: AttackFxRecipe, at: Vector3, dst: number, t0: number, S: number): void {
  for (let i = 0, n = many(c, F.wisps); i < n; i++) {
    const s = c.seed + 700 + i * 3
    const travel = F.wispSec * (0.8 + 0.4 * noise(s))
    const p = grow(tint(from(part(c, CELL.drop, false, t0 + i * 0.04, travel), at, (noise(s + 1) - 0.5) * 0.3, (noise(s + 2) - 0.5) * 0.3, 0), r.ramp[1]!, r.ramp[2]!, 0.95), 0.12 * Math.sqrt(S), 0.08)
    p.move = MOVE.path
    p.anchor = dst
    p.travel = travel
    p.arc = (0.2 + 0.3 * noise(s + 3)) * (i % 2 ? -1 : 1)
    p.face = FACE.stretch
    p.stretch = 1.8
    p.fade = FADE.hold
  }
}

/** Special and Signature: a brief bloom of light over the impact (not in Lite or Reduce motion). */
export function flash(c: FxCtx, at: Vector3, hex: number, S: number, t0: number): void {
  if (!c.q.flash) return
  const p = pop(c, at, hex, F.flashM * Math.sqrt(S), t0, F.flashSec, 0.7)
  p.s0 = F.flashM * Math.sqrt(S) * 0.5
}

/** Sharp: a slash arc across the target (or past it, faint, on a miss). */
export function slash(c: FxCtx, r: AttackFxRecipe, at: Vector3, S: number, t0: number, alpha = 1): void {
  const rot = -0.7 + 0.5 * noise(c.seed + 900)
  const a = grow(tint(from(part(c, CELL.crescent, false, t0, 0.22 * c.q.life), at), r.ramp[0]!, r.ramp[1]!, alpha), 0.5 * F.slashM * S, F.slashM * S)
  a.rot = rot
  a.fade = FADE.hold
  const b = grow(tint(from(part(c, CELL.crescent, true, t0 + 0.02, 0.24 * c.q.life), at), r.glow, r.glow, 0.5 * alpha), 0.6 * F.slashM * S, 1.25 * F.slashM * S)
  b.rot = rot + 0.15
}

/** Knockback: a shockwave ring standing across the blow, and one on the floor. */
export function shockwave(c: FxCtx, r: AttackFxRecipe, at: Vector3, feet: Vector3, dir: Vector3, S: number, t0: number): void {
  ring(c, at, r.ramp[1]!, false, 0.15 * S, F.shockwaveM * S, t0, 0.32 * c.q.life, FACE.across, dir).fade = FADE.pop
  ring(c, feet, r.smoke, false, 0.2 * S, 1.3 * S, t0, 0.4 * c.q.life)
}

/** A heal: sparkles rise round the healer (the classic battle's heal colours: Light sparkles, a Nature glow). */
export function healSparkles(c: FxCtx, feet: Vector3, t0: number, scale: number): void {
  const light = styleOf('Light')
  const nature = styleOf('Nature')
  for (let i = 0, n = many(c, Math.round(14 * scale)); i < n; i++) {
    const a = (i / n) * TAU
    const p = grow(tint(from(part(c, CELL.star, false, t0 + i * 0.03, 0.9 * c.q.life), feet, Math.cos(a) * 0.35, 0.1, Math.sin(a) * 0.35), light.ramp[1]!, nature.ramp[1]!), 0.13, 0.08)
    p.vy = 0.9 + 0.5 * noise(c.seed + i)
    p.spin = 3
  }
  ring(c, feet, nature.ramp[1]!, false, 0.2, 0.8 * scale, t0, 0.5 * c.q.life)
}

/** A melee miss: a swish of air beside the target and a few bits drifting off (no impact). */
export function whiff(c: FxCtx, r: AttackFxRecipe, at: Vector3, S: number, t0: number): void {
  const p = grow(tint(from(part(c, CELL.crescent, r.look.glow, t0, 0.22 * c.q.life), at), r.ramp[0]!, r.ramp[1]!, 0.55), 0.35 * S, 0.7 * S)
  p.rot = 0.4
  p.fade = FADE.hold
}

/** Knocked into the fence: dust and grit at the feet. */
export function dustKick(c: FxCtx, feet: Vector3, t0: number): void {
  const earth = styleOf('Earth')
  ring(c, feet, earth.smoke, false, 0.2, 1.1, t0, 0.45 * c.q.life)
  for (let i = 0, n = many(c, 8); i < n; i++) {
    const a = noise(c.seed + i) * TAU
    const p = grow(tint(from(part(c, i % 2 ? CELL.rock : CELL.puff, false, t0, 0.6 * c.q.life), feet, 0, 0.1, 0), earth.ramp[1]!, earth.smoke, 0.8), i % 2 ? 0.06 : 0.14, i % 2 ? 0.05 : 0.35)
    p.vx = Math.cos(a) * 1.2
    p.vz = Math.sin(a) * 1.2
    p.vy = i % 2 ? 2 : 0.3
    p.g = i % 2 ? 8 : 0
    p.spin = 5
  }
}
