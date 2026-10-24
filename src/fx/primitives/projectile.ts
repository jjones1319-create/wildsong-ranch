import { Container, Sprite } from 'pixi.js'
import { FX } from '../../data/tuning.ts'
import { FRAME } from '../atlas.ts'
import type { FxContext } from '../context.ts'
import { styleOf, type ProjectileShape } from '../elements.ts'
import { arcPoint, scaled, spawnParticle, strengthOf, timed } from './helpers.ts'
import type { EffectHandle, ProjectileParams } from './types.ts'

const CELL_PX = 64

function frameFor(shape: ProjectileShape): number {
  switch (shape) {
    case 'lance':
    case 'shard':
      return FRAME.shard
    case 'blade':
      return FRAME.streak
    case 'boulder':
      return FRAME.rock
    case 'feather':
      return FRAME.petal
    case 'note':
      return FRAME.note
    case 'drop':
      return FRAME.droplet
    case 'leaf':
      return FRAME.leaf
    case 'bolt':
      return FRAME.spark
    default:
      return FRAME.softDot
  }
}

/** #4 projectile: a shaped sprite that flies (straight or lobbed) with a trail and resolves on arrival. */
export function projectile(ctx: FxContext, p: ProjectileParams): EffectHandle {
  const style = styleOf(p.element)
  const str = strengthOf(p.strength)
  const shape = p.shape ?? style.projectile
  const size = scaled(p.size ?? FX.projectile.size, str)
  const dist = Math.hypot(p.to.x - p.x, p.to.y - p.y)
  const duration = p.durationMs ?? Math.max(FX.projectile.minMs, (dist / FX.projectile.speedUnitsPerSec) * 1000)
  const arc = p.arc ?? (shape === 'boulder' || shape === 'leaf' || shape === 'feather' || shape === 'note' ? FX.projectile.arcHeight : shape === 'drop' ? FX.projectile.arcHeight * 0.5 : 0)
  const tumble = shape === 'boulder' || shape === 'leaf' || shape === 'feather' || shape === 'shard'
  const long = shape === 'lance' || shape === 'blade' || shape === 'drop'

  const node = new Container()
  const body = new Sprite(ctx.atlas.frames[frameFor(shape)]!)
  body.anchor.set(0.5)
  body.tint = style.ramp[1]!
  body.blendMode = style.additive ? 'add' : 'normal'
  const core = new Sprite(ctx.atlas.frames[FRAME.softDot]!)
  core.anchor.set(0.5)
  core.tint = style.core
  core.blendMode = 'add'
  core.alpha = 0.9
  const halo = new Sprite(ctx.atlas.frames[FRAME.softDot]!)
  halo.anchor.set(0.5)
  halo.tint = style.glow
  halo.blendMode = 'add'
  halo.alpha = style.additive ? 0.55 : 0.3
  node.addChild(halo, body, core)
  const s = size / (CELL_PX * 0.7)
  body.scale.set(long ? s * 2.1 : s, long ? s * 0.8 : s)
  core.scale.set(s * 0.55)
  halo.scale.set(s * 1.9)
  if (shape === 'boulder' || shape === 'leaf' || shape === 'feather' || shape === 'blade') core.visible = false
  ctx.shapes.addChild(node)

  let acc = 0
  let lastX = p.x
  let lastY = p.y
  return timed(
    duration,
    (prog, dt) => {
      const q = arcPoint(p.x, p.y, p.to.x, p.to.y, arc, prog)
      node.position.set(q.x, q.y)
      const heading = Math.atan2(q.y - lastY, q.x - lastX) || Math.atan2(p.to.y - p.y, p.to.x - p.x)
      body.rotation = tumble ? body.rotation + dt * 0.012 : long ? heading + (shape === 'drop' ? Math.PI / 2 : 0) : heading
      if (shape === 'bolt') body.rotation += dt * 0.03
      lastX = q.x
      lastY = q.y
      acc += (FX.trail.ratePerSec * 0.6 * dt) / 1000
      let n = Math.floor(acc)
      acc -= n
      n = ctx.allowance(n)
      for (let i = 0; i < n; i++) {
        spawnParticle(ctx, { element: p.element, x: q.x + ctx.rng.range(-6, 6), y: q.y + ctx.rng.range(-6, 6), vx: ctx.rng.range(-30, 30), vy: ctx.rng.range(-40, 20), gravity: style.gravity * 120, drag: 0.8, lifeMs: FX.trail.lifeMs * 1.2, size0: size * 0.45, size1: size * 0.1, fadeIn: 0, fadeFrom: 0.3 }, style)
      }
    },
    () => {
      node.destroy({ children: true })
      const arrive = p.onArrive ?? 'spark'
      if (arrive === 'impact') ctx.fire({ name: 'impact', params: { element: p.element, x: p.to.x, y: p.to.y, strength: str } })
      else if (arrive === 'splash' || (arrive === 'spark' && style.splashOnLand)) ctx.fire({ name: 'splash', params: { element: p.element, x: p.to.x, y: p.to.y, strength: str * 0.7 } })
      else if (arrive === 'spark') ctx.fire({ name: 'burst', params: { element: p.element, x: p.to.x, y: p.to.y, count: 8, speed: 160, lifeMs: 380, size: size * 0.4, strength: str * 0.6 } })
    },
  )
}
