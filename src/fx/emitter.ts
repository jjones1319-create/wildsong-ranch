import { Particle, ParticleContainer } from 'pixi.js'
import { CELL } from './atlas.ts'
import { RAMPS } from './elements.ts'
import { Pool } from './pool.ts'
import { ParticleSim, rampColor, type SpawnSpec } from './sim.ts'
import type { Atlas } from './textures.ts'

/**
 * The Pixi side of the particles: two ParticleContainers (normal and additive) over the atlas, each mirroring a
 * ParticleSim with a pooled array of Particle objects. Spawning takes from the pool; a dying particle goes back.
 * Nothing is allocated per frame once the pool is warm.
 */
class Bank {
  readonly container: ParticleContainer<Particle>
  readonly sim: ParticleSim
  readonly pool: Pool<Particle>
  constructor(atlas: Atlas, capacity: number, additive: boolean) {
    this.container = new ParticleContainer<Particle>({ texture: atlas.texture, dynamicProperties: { position: true, scale: true, rotation: true, color: true, uvs: true } })
    this.container.blendMode = additive ? 'add' : 'normal'
    this.sim = new ParticleSim(capacity)
    this.pool = new Pool(() => new Particle({ texture: atlas.frames[0]!, anchorX: 0.5, anchorY: 0.5 }), capacity)
  }

  spawn(spec: SpawnSpec, atlas: Atlas): boolean {
    const p = this.pool.take()
    if (!p) return false
    const i = this.sim.spawn(spec)
    if (i < 0) {
      this.pool.give(p)
      return false
    }
    p.texture = atlas.frames[spec.frame] ?? atlas.frames[0]!
    this.container.particleChildren.push(p)
    this.touched = true
    return true
  }

  private touched = false

  update(dtMs: number): void {
    const kids = this.container.particleChildren
    const removed = this.sim.update(
      dtMs,
      (from, to) => {
        kids[to] = kids[from]!
      },
      (last) => {
        const p = kids[last]!
        kids.length = last
        this.pool.give(p)
      },
    )
    if (removed > 0) this.touched = true
    const sim = this.sim
    for (let i = 0; i < sim.count; i++) {
      const p = kids[i]!
      p.x = sim.x[i]!
      p.y = sim.y[i]!
      const s = sim.sizeAt(i) / (CELL * 0.7)
      p.scaleX = s
      p.scaleY = s
      p.rotation = sim.rotation[i]!
      p.alpha = sim.alphaAt(i)
      p.tint = rampColor(RAMPS[sim.ramp[i]!] ?? RAMPS[0]!, sim.progress(i))
    }
    if (this.touched) {
      this.container.update()
      this.touched = false
    }
  }

  clear(): void {
    const kids = this.container.particleChildren
    for (const p of kids) this.pool.give(p)
    kids.length = 0
    this.sim.clear()
    this.container.update()
  }

  destroy(): void {
    this.container.destroy({ children: true })
  }
}

export class ParticleLayer {
  readonly normal: Bank
  readonly additive: Bank
  private readonly atlas: Atlas
  constructor(atlas: Atlas, capacity: number) {
    this.atlas = atlas
    this.normal = new Bank(atlas, capacity, false)
    this.additive = new Bank(atlas, capacity, true)
  }

  /** Live particles across both banks (the cap in quality.ts counts these). */
  get live(): number {
    return this.normal.sim.count + this.additive.sim.count
  }

  spawn(spec: SpawnSpec): boolean {
    return (spec.additive ? this.additive : this.normal).spawn(spec, this.atlas)
  }

  update(dtMs: number): void {
    this.normal.update(dtMs)
    this.additive.update(dtMs)
  }

  warm(): void {
    this.normal.pool.warm()
    this.additive.pool.warm()
  }

  clear(): void {
    this.normal.clear()
    this.additive.clear()
  }

  destroy(): void {
    this.normal.destroy()
    this.additive.destroy()
  }
}
