import { Group, PerspectiveCamera, Scene, Vector3 } from 'three'
import type { Mesh, Object3D } from 'three'
import { applyFilm, buildBursts, buildStudio, dirFrom, showPart, standIn, type Assets, type Bursts, type Studio } from './content.ts'
import type { PerfView } from './view.ts'

/**
 * Art 2.1 Performance check: the scenes. A scene owns its three.js Scene, camera, the monsters and the effects; the view
 * draws it. Coordinates are the glTF's (Y up, the monster faces +Z).
 */

export type SceneKind = 'shot' | 'battle' | 'card' | 'dash'

export interface ShotView { target: [number, number, number]; az: number; el: number; size: number }

/** The review views of tools/blender/spikes/detail_spike.py (Blender metres: x, y, z → three x, z, −y). */
export const VIEWS: Record<string, ShotView> = {
  head_34: { target: [0.0, -0.42, 0.76], az: 26, el: 12, size: 0.98 },
  head_front: { target: [0.0, -0.42, 0.76], az: 0, el: 4, size: 0.98 },
  head_side: { target: [0.0, -0.42, 0.76], az: 90, el: 4, size: 0.98 },
  paw_34: { target: [0.15, -0.26, 0.1], az: 30, el: 16, size: 0.42 },
}

export interface PerfScene {
  kind: SceneKind
  scene: Scene
  camera: PerspectiveCamera
  studio: Studio
  monsters: Object3D[]
  bursts: Bursts | null
  /** Advance the scene's motion to time t (seconds). */
  update(t: number): void
  /** Distance from the camera to the focus (for depth of field in the cinematic scenes). */
  focus: number
}

function aimShot(camera: PerspectiveCamera, v: ShotView): number {
  const [bx, by, bz] = v.target
  const target = new Vector3(bx, bz, -by)
  const dist = v.size * 2.4
  camera.position.copy(target).add(dirFrom(v.az, v.el).multiplyScalar(dist))
  camera.fov = (2 * Math.atan(v.size / 2 / dist) * 180) / Math.PI
  camera.lookAt(target)
  camera.updateProjectionMatrix()
  return dist
}

function cardsOnLayerOne(root: Object3D): void {
  root.traverse((o) => {
    if ((o as Mesh).isMesh && o.userData.kind === 'card') o.layers.set(1)
  })
}

/** Build a scene for the view. `cinematic` swaps the head onto its 2048² cinematic texture set (Monster Card, cutscenes). */
export function buildScene(kind: SceneKind, assets: Assets, view: PerfView, aspect: number, opts: { shot?: ShotView; part?: 'head' | 'paw'; cinematic?: boolean } = {}): PerfScene {
  const scene = new Scene()
  const camera = new PerspectiveCamera(30, aspect, 0.05, 60)
  camera.layers.enable(1)
  const monsters: Object3D[] = []
  let bursts: Bursts | null = null
  let focus = 3
  let update: (t: number) => void = () => {}
  const cinematic = opts.cinematic === true
  if (kind === 'shot') {
    const m = assets.scene.clone(true)
    applyFilm(m, assets, cinematic)
    showPart(m, opts.part ?? 'head')
    cardsOnLayerOne(m)
    scene.add(m)
    monsters.push(m)
    focus = aimShot(camera, opts.shot ?? VIEWS.head_34!)
  } else {
    const n = kind === 'battle' ? 2 : kind === 'card' ? 1 : 4
    for (let i = 0; i < n; i++) {
      const g = new Group()
      const m = standIn(assets)
      applyFilm(m, assets, cinematic || kind === 'card')
      cardsOnLayerOne(m)
      g.add(m)
      scene.add(g)
      monsters.push(g)
    }
    if (kind === 'battle') {
      monsters[0]!.position.set(-0.9, 0, 0)
      monsters[0]!.rotation.y = Math.PI / 2 - 0.45
      monsters[1]!.position.set(0.9, 0, 0)
      monsters[1]!.rotation.y = -Math.PI / 2 + 0.45
      camera.fov = 22
      camera.position.set(0, 1.25, 6.4)
      camera.lookAt(0, 0.55, 0)
      bursts = buildBursts(scene, [new Vector3(-0.9, 0, 0), new Vector3(0.9, 0, 0)])
      update = (t) => {
        // idle bob and sway (no rig in the stand-in), a lunge every few seconds
        monsters.forEach((m, i) => {
          const ph = t * 2.2 + i * 1.7
          m.position.y = Math.abs(Math.sin(ph)) * 0.035
          const lunge = Math.max(0, Math.sin(t * 0.9 + i * Math.PI)) ** 6
          m.position.x = (i === 0 ? -0.9 : 0.9) * (1 - 0.35 * lunge)
        })
        bursts?.update(t, camera)
      }
    } else if (kind === 'card') {
      camera.fov = 26
      camera.position.set(0.55, 0.95, 2.1)
      camera.lookAt(0, 0.62, 0.15)
      focus = camera.position.distanceTo(new Vector3(0, 0.75, 0.38))
      update = (t) => {
        monsters[0]!.rotation.y = Math.sin(t * 0.35) * 0.6
        monsters[0]!.position.y = Math.abs(Math.sin(t * 1.6)) * 0.02
      }
    } else {
      // Meadow Dash: four runners across the meadow
      monsters.forEach((m, i) => {
        m.position.set(-2.4 + i * 1.6, 0, -i * 0.6)
        m.rotation.y = Math.PI / 2
      })
      camera.fov = 30
      camera.position.set(0, 1.6, 7.5)
      camera.lookAt(0, 0.5, -0.8)
      update = (t) => {
        monsters.forEach((m, i) => {
          const ph = t * 7 + i
          m.position.y = Math.abs(Math.sin(ph)) * 0.12
          m.rotation.z = Math.sin(ph) * 0.05
        })
      }
    }
    camera.updateProjectionMatrix()
  }
  camera.aspect = aspect
  camera.updateProjectionMatrix()
  const reach = kind === 'shot' ? 1.2 : kind === 'dash' ? 5 : 3
  const studio = buildStudio(scene, view.environment, new Vector3(0, 0.5, 0), reach)
  return { kind, scene, camera, studio, monsters, bursts, update, focus }
}

/** Count what a scene draws: triangles (incl. instancing), fur cards and draw calls are reported by the renderer. */
export function countTriangles(root: Object3D): number {
  let n = 0
  root.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh || !m.visible || m.userData.isHelper) return
    const g = m.geometry
    n += (g.index ? g.index.count : g.attributes.position!.count) / 3
  })
  return Math.round(n)
}

export function countCards(root: Object3D): number {
  let n = 0
  root.traverse((o) => {
    const m = o as Mesh
    if (!m.isMesh || m.userData.kind !== 'card') return
    n += m.geometry.attributes.position!.count / 6
  })
  return Math.round(n)
}
