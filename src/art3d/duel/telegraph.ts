import { CanvasTexture, Mesh, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace, type Scene, type Texture, type Vector3 } from 'three'
import { ART, BATTLE } from '../../data/tuning.ts'

/**
 * docs/BATTLE_3D.md §7: the wind-up telegraphs on the floor, quiet so the attack's own effects lead (the owner, Nov 3:
 * "the big lanes compete with the effects"). A straight-line technique paints an outlined lane with faint chevrons
 * toward the defender; a sweep an outlined ring round it. Each fades in over the start of the wind-up and out from
 * the release (the projectile or lunge on its way) to the landing. One mesh per side and shape, made once (no
 * allocation while the battle runs); two textures drawn in code.
 */

const T = ART.duel.telegraph

/** The telegraph's strength (0…peak) at `now`: in over inPct of the wind-up, held, out from the release to the landing. */
export function telegraphAlpha(now: number, born: number, release: number, land: number): number {
  if (now < born || now >= land) return 0
  const w = Math.max(0.05, land - born)
  const fadeIn = Math.min(1, (now - born) / Math.max(1e-3, (w * T.inPct) / 100))
  const from = Math.min(land - 1e-3, Math.max(release, born + (w * T.holdPct) / 100))
  const out = now <= from ? 1 : (land - now) / (land - from)
  return T.opacity * Math.max(0, Math.min(fadeIn, out))
}

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  return [c, c.getContext('2d')!]
}

function texture(c: HTMLCanvasElement): CanvasTexture {
  const t = new CanvasTexture(c)
  t.colorSpace = SRGBColorSpace
  return t
}

/** The lane: two edge lines, a faint fill and three chevrons pointing at the far end (the canvas top), soft at both ends. */
function laneTexture(): CanvasTexture {
  const [c, g] = canvas(64, 256)
  const fill = T.fillPct / 100
  g.fillStyle = `rgba(255,255,255,${fill})`
  g.fillRect(8, 0, 48, 256)
  g.fillStyle = 'white'
  g.fillRect(1, 0, 7, 256)
  g.fillRect(56, 0, 7, 256)
  g.strokeStyle = `rgba(255,255,255,${Math.min(1, fill * 2.2)})`
  g.lineWidth = 6
  g.lineCap = 'round'
  g.lineJoin = 'round'
  for (const y of [72, 136, 200]) {
    g.beginPath()
    g.moveTo(18, y + 12)
    g.lineTo(32, y)
    g.lineTo(46, y + 12)
    g.stroke()
  }
  // soft ends: in from the attacker (the bottom), out just past the defender (the top)
  const mask = g.createLinearGradient(0, 256, 0, 0)
  mask.addColorStop(0, 'rgba(0,0,0,0)')
  mask.addColorStop(0.18, 'rgba(0,0,0,1)')
  mask.addColorStop(0.88, 'rgba(0,0,0,1)')
  mask.addColorStop(1, 'rgba(0,0,0,0)')
  g.globalCompositeOperation = 'destination-in'
  g.fillStyle = mask
  g.fillRect(0, 0, 64, 256)
  return texture(c)
}

/** The sweep: an outlined ring with a soft fill inside it and a faint inner ring (a wide area, not a line). */
function ringTexture(): CanvasTexture {
  const [c, g] = canvas(128, 128)
  const fill = T.fillPct / 100
  const grad = g.createRadialGradient(64, 64, 22, 64, 64, 60)
  grad.addColorStop(0, 'rgba(255,255,255,0)')
  grad.addColorStop(0.7, `rgba(255,255,255,${fill})`)
  grad.addColorStop(1, `rgba(255,255,255,${fill})`)
  g.fillStyle = grad
  g.beginPath()
  g.arc(64, 64, 60, 0, Math.PI * 2)
  g.fill()
  g.strokeStyle = 'white'
  g.lineWidth = 4
  g.beginPath()
  g.arc(64, 64, 59, 0, Math.PI * 2)
  g.stroke()
  g.strokeStyle = `rgba(255,255,255,${Math.min(1, fill * 2.2)})`
  g.lineWidth = 3
  g.beginPath()
  g.arc(64, 64, 42, 0, Math.PI * 2)
  g.stroke()
  return texture(c)
}

interface Live {
  mesh: Mesh | null
  born: number
  release: number
  land: number
}

export class Telegraphs {
  private readonly geo = new PlaneGeometry(1, 1).rotateX(-Math.PI / 2)
  private readonly maps: [Texture, Texture]
  /** Per side: [lane, ring]. */
  private readonly meshes: [Mesh, Mesh][]
  private readonly live: [Live, Live] = [{ mesh: null, born: 0, release: 0, land: 0 }, { mesh: null, born: 0, release: 0, land: 0 }]

  constructor(scene: Scene) {
    this.maps = [laneTexture(), ringTexture()]
    const make = (map: Texture): Mesh => {
      const m = new Mesh(this.geo, new MeshBasicMaterial({ map, transparent: true, opacity: 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }))
      m.visible = false
      // under the effects (3, 4), over the floor
      m.renderOrder = 2
      scene.add(m)
      return m
    }
    this.meshes = [0, 1].map((): [Mesh, Mesh] => [make(this.maps[0]), make(this.maps[1])])
  }

  /** `side` fired a technique now from `a` at `b` (the engine's spots), landing windupSec later, released travelSec before. */
  show(side: number, path: 'line' | 'sweep', int: boolean, a: Vector3, b: Vector3, now: number, windupSec: number, travelSec: number): void {
    const l = this.live[side]!
    if (l.mesh) l.mesh.visible = false
    const mesh = this.meshes[side]![path === 'line' ? 0 : 1]
    ;(mesh.material as MeshBasicMaterial).color.set(int ? T.int : T.pow)
    if (path === 'line') {
      const dx = b.x - a.x
      const dz = b.z - a.z
      const len = Math.max(0.2, Math.hypot(dx, dz))
      mesh.scale.set(((BATTLE.duel.pathHalfWidth * 2) / 100) * (T.widthPct / 100), 1, len + 0.6)
      mesh.rotation.set(0, Math.atan2(-dx, -dz), 0)
      mesh.position.set((a.x + b.x) / 2 + (dx / len) * 0.3, 0.02, (a.z + b.z) / 2 + (dz / len) * 0.3)
    } else {
      mesh.scale.set(T.sweepM * 2, 1, T.sweepM * 2)
      mesh.rotation.set(0, 0, 0)
      mesh.position.set(b.x, 0.02, b.z)
    }
    l.mesh = mesh
    l.born = now
    l.land = now + Math.max(0.05, windupSec)
    l.release = l.land - Math.min(windupSec, travelSec)
    this.update(now)
  }

  update(now: number): void {
    for (const l of this.live) {
      if (!l.mesh) continue
      const a = telegraphAlpha(now, l.born, l.release, l.land)
      ;(l.mesh.material as MeshBasicMaterial).opacity = a
      l.mesh.visible = a > 0.003
      if (now >= l.land) l.mesh = null
    }
  }

  dispose(): void {
    for (const pair of this.meshes) {
      for (const m of pair) {
        m.removeFromParent()
        ;(m.material as MeshBasicMaterial).dispose()
      }
    }
    this.geo.dispose()
    for (const t of this.maps) t.dispose()
  }
}
