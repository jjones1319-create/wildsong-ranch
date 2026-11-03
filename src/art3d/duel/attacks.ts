import { AdditiveBlending, Color, Mesh, MeshBasicMaterial, SphereGeometry, Vector3, type Scene } from 'three'
import { ART } from '../../data/tuning.ts'

/**
 * docs/BATTLE_3D.md §7: attacks that visibly reach. The owner (Nov 2): "the attacks do not seem to land". The rules
 * were fine (a simple player lands 60% and wins most fights); the picture wasn't: strikes played in place across a 2–3 m
 * gap and ranged moves had nothing travelling. So a melee attack lunges across the gap and back, and a ranged one sends
 * a glowing bolt that arrives on the engine's landing tick. Picture only: the engine's positions never change.
 */

const A = ART.duel.attack

export interface Lunge {
  /** Seconds (the stage's clock): the lunge starts, reaches the target on the landing, holds, then returns. */
  start: number
  impact: number
  end: number
}

const ease = (k: number) => k * k * (3 - 2 * k)

/** How far along the gap the attacker is (0 at home, 1 at contact). */
export function lungeReach(now: number, l: Lunge): number {
  if (now <= l.start || now >= l.end) return 0
  if (now < l.impact) return ease((now - l.start) / Math.max(1e-3, l.impact - l.start))
  const hold = l.impact + A.lungeHoldSec
  if (now < hold) return 1
  return 1 - ease((now - hold) / Math.max(1e-3, l.end - hold))
}

/** The lunge for a melee technique fired now that lands after `windupSec` (it leans in over the last part of it). */
export function lungeFor(now: number, windupSec: number): Lunge {
  const lean = Math.min(windupSec, A.lungeSec)
  return { start: now + windupSec - lean, impact: now + windupSec, end: now + windupSec + A.lungeHoldSec + A.lungeBackSec }
}

interface Bolt {
  mesh: Mesh
  from: () => Vector3
  to: () => Vector3
  t0: number
  t1: number
}

/** Glowing bolts for ranged techniques, from the caster to the target, arriving on the landing. */
export class Bolts {
  private live: Bolt[] = []
  private readonly geo = new SphereGeometry(A.boltSizeM, 12, 8)
  private readonly scene: Scene
  constructor(scene: Scene) {
    this.scene = scene
  }

  launch(from: () => Vector3, to: () => Vector3, now: number, windupSec: number, int: boolean): void {
    const travel = Math.min(windupSec, A.boltTravelSec)
    const mat = new MeshBasicMaterial({ color: new Color(int ? A.intColor : A.powColor), transparent: true, opacity: 0, blending: AdditiveBlending, depthWrite: false })
    const mesh = new Mesh(this.geo, mat)
    this.scene.add(mesh)
    this.live.push({ mesh, from, to, t0: now + windupSec - travel, t1: now + windupSec })
  }

  update(now: number): void {
    this.live = this.live.filter((b) => {
      const mat = b.mesh.material as MeshBasicMaterial
      if (now >= b.t1 + A.boltFadeSec) {
        this.scene.remove(b.mesh)
        mat.dispose()
        return false
      }
      if (now < b.t0) return true
      const k = Math.min(1, (now - b.t0) / Math.max(1e-3, b.t1 - b.t0))
      b.mesh.position.copy(b.from()).lerp(b.to(), k)
      // a little arc, and a swell as it arrives
      b.mesh.position.y += Math.sin(k * Math.PI) * A.boltArcM
      b.mesh.scale.setScalar(0.8 + 0.4 * k)
      mat.opacity = now <= b.t1 ? 0.9 : 0.9 * (1 - (now - b.t1) / A.boltFadeSec)
      return true
    })
  }

  dispose(): void {
    for (const b of this.live) {
      this.scene.remove(b.mesh)
      ;(b.mesh.material as MeshBasicMaterial).dispose()
    }
    this.live = []
    this.geo.dispose()
  }
}
