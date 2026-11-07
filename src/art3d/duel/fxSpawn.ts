import { Color, type Vector3 } from 'three'
import { ART } from '../../data/tuning.ts'
import { CELL, type AttackFxRecipe, type FxQuality } from './fxRecipe.ts'
import { FACE, FADE, MOVE, noise, type Particle, type ParticlePool } from './fxParticles.ts'

/**
 * docs/BATTLE_3D.md §7: the impacts. A burst of the element's particles plus its extra layer, the 3-D form of the
 * classic battle's hit recipe (src/fx/recipes.ts): Fire bursts and smokes, Water splashes a ring, Ice breaks and mists,
 * Lightning forks and flickers, Wind spirals round, Earth cracks the floor and raises dust, Nature whirls leaves, Light blooms,
 * Dark gathers then smokes, Sound rings out, a plain blow rings and kicks up dust.
 */

const TAU = Math.PI * 2
const C = new Color()

/** What every spawner needs: the pool, the quality, and a seed for the repeatable spread. */
export interface FxCtx {
  pool: ParticlePool
  q: FxQuality
  seed: number
}

export function part(c: FxCtx, cell: number, glow: boolean, t0: number, life: number): Particle {
  const p = c.pool.spawn()
  p.cell = cell
  p.glow = glow
  p.t0 = t0
  p.life = Math.max(0.03, life)
  return p
}

export function from(p: Particle, v: Vector3, dx = 0, dy = 0, dz = 0): Particle {
  p.x = v.x + dx
  p.y = v.y + dy
  p.z = v.z + dz
  return p
}

/** Colours from → to over its life (0xRRGGBB, sRGB; stored linear), and its alpha. */
export function tint(p: Particle, a: number, b: number, alpha = 1): Particle {
  C.setHex(a)
  p.r0 = C.r
  p.g0 = C.g
  p.b0 = C.b
  C.setHex(b)
  p.r1 = C.r
  p.g1 = C.g
  p.b1 = C.b
  p.a = alpha
  return p
}

export function grow(p: Particle, s0: number, s1: number): Particle {
  p.s0 = s0
  p.s1 = s1
  return p
}

/** Particles a base count stands for at this quality. */
export const many = (c: FxCtx, base: number) => Math.max(1, Math.round((base * c.q.particlePct) / 100))

/** A ring: flat on the floor, facing the camera, or standing across `n`. */
export function ring(c: FxCtx, at: Vector3, hex: number, glow: boolean, s0: number, s1: number, t0: number, life: number, face: number = FACE.ground, n?: Vector3): Particle {
  const p = grow(tint(from(part(c, CELL.ring, glow, t0, life), at, 0, face === FACE.ground ? 0.02 : 0), hex, hex, 0.9), s0, s1)
  p.face = face
  p.fade = FADE.hold
  if (n) {
    p.nx = n.x
    p.ny = n.y
    p.nz = n.z
  }
  return p
}

/** A soft glow that blooms and fades. */
export function pop(c: FxCtx, at: Vector3, hex: number, size: number, t0: number, life: number, alpha = 0.9): Particle {
  return grow(tint(from(part(c, CELL.dot, true, t0, life), at), hex, hex, alpha), size * 0.6, size)
}

/** Puffs of smoke, dust or mist (solid), rising or drifting (`spread` m/s outward). */
export function puffs(c: FxCtx, at: Vector3, n: number, hex: number, to: number, alpha: number, s0: number, s1: number, t0: number, life: number, rise: number, spread: number, seed: number): void {
  for (let i = 0; i < n; i++) {
    const a = noise(seed + i) * TAU
    const p = grow(tint(from(part(c, CELL.puff, false, t0 + i * 0.02, life * (0.8 + 0.4 * noise(seed + 9 + i))), at), hex, to, alpha), s0, s1)
    p.vx = Math.cos(a) * spread
    p.vz = Math.sin(a) * spread
    p.vy = rise
    p.rot = a
    p.spin = (noise(seed + 17 + i) - 0.5) * 2
  }
}

/** The element's burst: its particles thrown out (or drawn in, for Dark), pushed on through by the blow. */
export function burst(c: FxCtx, r: AttackFxRecipe, at: Vector3, dir: Vector3, t0: number, scale: number, count: number): void {
  const k = r.look
  const ss = Math.sqrt(scale)
  for (let i = 0; i < count; i++) {
    const s = c.seed + i * 7
    const th = noise(s) * TAU
    const u = noise(s + 1) * 2 - 1
    const w = Math.sqrt(1 - u * u)
    let x = w * Math.cos(th) + dir.x * 0.7
    // Wind streams out nearly level (streaks of air, not a starburst)
    let y = (Math.abs(u) * 0.8 + 0.25) * (k.flow ? 0.3 : 1)
    let z = w * Math.sin(th) + dir.z * 0.7
    const len = Math.hypot(x, y, z) || 1
    const speed = k.speed * (0.55 + 0.6 * noise(s + 2)) * ss
    x /= len
    y /= len
    z /= len
    const life = k.life * (0.7 + 0.5 * noise(s + 3)) * c.q.life
    const p = part(c, k.cell, k.glow, t0, life)
    if (k.inward) {
      const reach = 0.55 * scale
      from(p, at, x * reach, y * reach, z * reach)
      p.vx = (-x * reach) / life
      p.vy = (-y * reach) / life
      p.vz = (-z * reach) / life
    } else {
      from(p, at)
      p.vx = x * speed
      p.vy = y * speed
      p.vz = z * speed
      p.g = k.gravity
    }
    p.move = MOVE.free
    p.face = k.stretch ? FACE.stretch : FACE.camera
    p.stretch = k.stretch ? 2.2 : 1
    p.rot = k.spin === 0 && !k.stretch ? 0 : noise(s + 4) * TAU
    p.spin = k.spin * (noise(s + 5) > 0.5 ? 1 : -1)
    grow(p, k.sizeM * ss, k.sizeM * ss * (k.glow ? 0.35 : 0.6))
    p.fade = k.glow ? FADE.pop : FADE.hold
    tint(p, k.glow ? r.ramp[0]! : r.ramp[1]!, r.ramp[2]!, 1)
  }
}

/**
 * Wind: ribbons of air spiralling round the target's body from low to high, widening and rising as they go (half of
 * each turn behind it, so the gust wraps it), and a faint ring where it touches down.
 */
function gustSpiral(c: FxCtx, r: AttackFxRecipe, feet: Vector3, t0: number, S: number): void {
  const G = ART.duel.fx.gust
  const s = c.seed + 140
  for (let i = 0, n = many(c, G.ribbons); i < n; i++) {
    const a = (i / n) * TAU * 1.5 + noise(s + i) * 0.4
    const rad = G.radiusM * S * (0.8 + 0.4 * noise(s + 10 + i))
    const p = grow(tint(part(c, CELL.gust, false, t0 + i * 0.03, 0.5 * c.q.life * (0.8 + 0.4 * noise(s + 20 + i))), r.ramp[1]!, r.ramp[3]!, 0.9), 0.15 * S, 0.11 * S)
    p.move = MOVE.orbit
    p.tx = feet.x
    p.ty = feet.y + 0.12
    p.tz = feet.z
    p.x = Math.cos(a) * rad
    p.z = Math.sin(a) * rad
    p.y = (i / Math.max(1, n - 1)) * 0.75 * S
    p.swirl = G.turnRadPerSec * (i % 3 === 2 ? 1.2 : 1)
    p.widen = G.widenPerSec
    p.vy = G.riseMps
    p.face = FACE.stretch
    p.stretch = 2.8
    p.fade = FADE.hold
  }
  ring(c, feet, r.ramp[2]!, false, 0.25 * S, 1.1 * S, t0, 0.35 * c.q.life).a = 0.55
}

/** The element's extra layer, with the burst. */
export function extra(c: FxCtx, r: AttackFxRecipe, at: Vector3, feet: Vector3, dir: Vector3, t0: number, S: number): void {
  const L = c.q.life
  const s = c.seed + 101
  switch (r.look.extra) {
    case 'flames':
      for (let i = 0; i < many(c, 4); i++) {
        const p = grow(tint(from(part(c, CELL.flame, false, t0 + i * 0.03, 0.45 * L), at, (noise(s + i) - 0.5) * 0.35 * S, -0.08, (noise(s + 20 + i) - 0.5) * 0.35 * S), r.ramp[1]!, r.ramp[2]!), 0.16 * S, 0.4 * S)
        p.vy = 0.9
        p.fade = FADE.hold
      }
      puffs(c, at, many(c, 3), r.smoke, r.smoke, 0.5, 0.12 * S, 0.42 * S, t0 + 0.1, 0.8 * L, 0.5, 0.25, s + 40)
      pop(c, at, r.glow, 0.5 * S, t0, 0.16 * L)
      break
    case 'ring':
      ring(c, feet, r.ramp[1]!, false, 0.2 * S, 1.25 * S, t0, 0.45 * L)
      ring(c, at, r.ramp[1]!, false, 0.1 * S, 0.6 * S, t0, 0.24 * L, FACE.camera)
      pop(c, at, r.glow, 0.45 * S, t0, 0.14 * L)
      break
    case 'mist':
      puffs(c, at, many(c, 4), r.smoke, r.core, 0.5, 0.15 * S, 0.45 * S, t0 + 0.04, 0.85 * L, 0.1, 0.35, s)
      pop(c, at, r.core, 0.5 * S, t0, 0.14 * L)
      break
    case 'bolts':
      for (let i = 0; i < many(c, 5); i++) {
        const a = noise(s + i) * TAU
        const p = grow(tint(from(part(c, CELL.bolt, false, t0 + (i % 3) * 0.035, 0.14 * L), at), r.ramp[1]!, r.ramp[2]!), 0.3 * S, 0.36 * S)
        p.vx = Math.cos(a) * 0.4
        p.vy = Math.sin(a) * 0.4
        p.vz = dir.z * 0.2
        p.face = FACE.stretch
        p.stretch = 2.6
        p.fade = FADE.hold
        from(p, at, Math.cos(a) * 0.25 * S, Math.sin(a) * 0.25 * S, 0)
      }
      pop(c, at, r.core, 0.85 * S, t0, 0.12 * L)
      break
    case 'spiral':
      gustSpiral(c, r, feet, t0, S)
      break
    case 'crack': {
      const p = grow(tint(from(part(c, CELL.crack, false, t0, 0.9 * L), feet, 0, 0.015, 0), r.ramp[3]!, r.ramp[3]!, 0.9), 0.45 * S, 0.55 * S)
      p.face = FACE.ground
      p.fade = FADE.hold
      p.nx = dir.x
      p.nz = dir.z
      p.stretch = 1.6
      puffs(c, feet, many(c, 6), r.smoke, r.smoke, 0.7, 0.1 * S, 0.4 * S, t0, 0.7 * L, 0.25, 0.9, s + 60)
      ring(c, feet, r.ramp[1]!, false, 0.2 * S, 1.0 * S, t0, 0.4 * L)
      break
    }
    case 'whirl':
      for (let i = 0, n = many(c, 7); i < n; i++) {
        const a = (i / n) * TAU
        const p = grow(tint(from(part(c, CELL.leaf, false, t0, 0.85 * L), at, Math.cos(a) * 0.3 * S, 0, Math.sin(a) * 0.3 * S), r.ramp[1]!, r.ramp[2]!), 0.17 * S, 0.14 * S)
        p.vx = -Math.sin(a) * 1.8 + Math.cos(a) * 0.4
        p.vz = Math.cos(a) * 1.8 + Math.sin(a) * 0.4
        p.vy = 0.8
        p.g = 1.2
        p.spin = 8
      }
      pop(c, at, r.glow, 0.4 * S, t0, 0.18 * L)
      break
    case 'glow':
      pop(c, at, r.glow, 1.0 * S, t0, 0.3 * L)
      ring(c, at, r.ramp[2]!, false, 0.15 * S, 0.85 * S, t0, 0.3 * L, FACE.camera)
      break
    case 'smoke': {
      const p = grow(tint(from(part(c, CELL.orb, false, t0, 0.4 * L), at), r.ramp[1]!, r.ramp[2]!), 0.42 * S, 0.12 * S)
      p.fade = FADE.hold
      puffs(c, at, many(c, 4), r.smoke, r.ramp[3]!, 0.75, 0.15 * S, 0.5 * S, t0 + 0.12, 0.75 * L, 0.4, 0.3, s)
      break
    }
    case 'rings':
      for (let i = 0; i < 3; i++) ring(c, at, r.ramp[2]!, false, 0.12 * S, 0.8 * S, t0 + i * 0.08, 0.42 * L, FACE.camera)
      break
    default:
      ring(c, at, r.ramp[1]!, false, 0.08 * S, 0.65 * S, t0, 0.22 * L, FACE.camera)
      puffs(c, feet, many(c, 4), r.smoke, r.smoke, 0.7, 0.1 * S, 0.35 * S, t0, 0.5 * L, 0.2, 0.7, s)
      pop(c, at, r.core, 0.4 * S, t0, 0.12 * L)
  }
}
