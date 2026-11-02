// The Guild arena's crowd (src/art3d/duel/crowd.ts) on its own, for review stills: the arena as the game draws it
// (unlit, baked light, Neutral tone mapping), grey 1 m capsules at the spawns, and the crowd simulated for `t` seconds
// (deterministic 30 Hz steps) with an optional cheer. Query: view, fame, t, cheer, cheerAt, lite=1, reduce=1, w, h, dpr.
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'
import { createCrowd } from '../../src/art3d/duel/crowd.ts'
import type { CheerKind } from '../../src/art3d/duel/crowdPlan.ts'

const q = new URLSearchParams(location.search)
const num = (k: string, d: number) => (q.has(k) ? Number(q.get(k)) : d)
const W = num('w', 900)
const H = num('h', 1200)
const BASE = '/wildsong-ranch/models/arenas/guild/'

/** Cameras inside the fence (glTF frame: the long stand toward −z, gate A at −x, the open front toward +z). */
const VIEWS: Record<string, { eye: number[]; target: number[]; fov: number }> = {
  stands: { eye: [0, 1.6, 3.5], target: [0, 1.0, -9.5], fov: 50 },
  front: { eye: [2.2, 1.35, -4.4], target: [3.6, 0.85, -8.6], fov: 38 },
  near: { eye: [-4.4, 1.45, -3.6], target: [-6.6, 0.95, -6.6], fov: 46 },
  gateA: { eye: [-1.5, 1.5, 0.6], target: [-8.5, 0.9, -0.8], fov: 54 },
  nearB: { eye: [-1.5, 1.6, -2.5], target: [6, 0.9, 5.2], fov: 52 },
  open: { eye: [0, 1.6, -3.5], target: [0, 0.8, 8], fov: 52 },
  top: { eye: [-12, 10, -4], target: [0, 0.8, 0], fov: 38 },
}

async function main(): Promise<void> {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
  renderer.setPixelRatio(num('dpr', 1))
  renderer.setSize(W, H)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.NeutralToneMapping
  renderer.setClearColor(0xbfd6e8)
  document.body.appendChild(renderer.domElement)
  const ktx2 = new KTX2Loader().setTranscoderPath('/wildsong-ranch/basis/')
  ktx2.detectSupport(renderer)
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).setKTX2Loader(ktx2)
  const meta = await (await fetch(BASE + 'guild.json')).json()
  const lite = q.get('lite') === '1'
  const gltf = await loader.loadAsync(BASE + meta.files[lite ? 'lite' : 'full'])
  const scene = new THREE.Scene()
  scene.add(gltf.scene)
  gltf.scene.traverse((o) => {
    const m = o as THREE.Mesh
    if (m.isMesh && m.name === 'shadow_catcher') m.visible = false
  })
  const key = new THREE.DirectionalLight(0xfff0d6, 3.0)
  key.position.set(...(meta.sun.direction as [number, number, number])).multiplyScalar(20)
  scene.add(key, new THREE.HemisphereLight(0xcfe3f5, 0x9c8a6a, 1.5))
  const grey = new THREE.MeshStandardMaterial({ color: 0xbcbcc2, roughness: 0.6 })
  for (const x of [-2.4, 2.4]) {
    const c = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.4, 8, 24), grey)
    c.position.set(x, 0.5, 0)
    scene.add(c)
  }
  const crowd = await createCrowd(scene, meta, { fame: num('fame', 60), lite, reduceMotion: q.get('reduce') === '1', seed: 7 })
  const v = VIEWS[q.get('view') ?? 'stands'] ?? VIEWS.stands!
  const camera = new THREE.PerspectiveCamera(v.fov, W / H, 0.05, 2000)
  camera.position.set(v.eye[0]!, v.eye[1]!, v.eye[2]!)
  camera.lookAt(new THREE.Vector3(v.target[0], v.target[1], v.target[2]))
  // simulate: 30 Hz steps to t, the action wandering a little round the middle
  const T = num('t', 6)
  const cheer = q.get('cheer') as CheerKind | null
  const cheerAt = num('cheerAt', Math.max(0, T - 1.2))
  const focus = (now: number) => ({ x: 2 * Math.sin(now * 0.4), z: 0.8 * Math.sin(now * 0.25) })
  let fired = false
  for (let s = 0; s <= Math.round(T * 30); s++) {
    const now = s / 30
    if (cheer && !fired && now >= cheerAt) {
      crowd?.cheer(cheer)
      fired = true
    }
    crowd?.update(1 / 30, now, focus(now))
  }
  // the crowd's CPU per frame: 300 updates
  const t0 = performance.now()
  for (let i = 0; i < 300; i++) crowd?.update(1 / 60, T + i / 600, focus(T))
  const cpuMs = (performance.now() - t0) / 300
  crowd?.update(1 / 30, T, focus(T))
  renderer.render(scene, camera)
  ;(window as unknown as { __crowd: unknown }).__crowd = {
    ready: true,
    shot() {
      renderer.info.autoReset = false
      renderer.info.reset()
      renderer.render(scene, camera)
      const info = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, cpuMs, crowd: crowd?.stats() ?? null }
      renderer.info.autoReset = true
      return { png: renderer.domElement.toDataURL('image/png'), ...info }
    },
  }
}

main().catch((e) => {
  console.error(e)
  ;(window as unknown as { __crowd: unknown }).__crowd = { ready: true, error: String(e), shot: () => ({ png: 'data:,' }) }
})
