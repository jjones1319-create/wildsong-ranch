// The Crown Amphitheatre in three.js, as the game will draw it: unlit materials with the baked atlases (KTX2),
// Neutral tone mapping, grey 1 m capsule stand-ins at the spawns lit by a key along the bake's sun, and a shadow
// catcher on the floor. Query: view=battle|shoulder|gate|establish|fly0…fly5, tier=full|lite, w, h, dpr.
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'

const q = new URLSearchParams(location.search)
const view = q.get('view') ?? 'battle'
const tier = q.get('tier') ?? 'full'
const W = Number(q.get('w') ?? 900)
const H = Number(q.get('h') ?? 1200)
const DPR = Number(q.get('dpr') ?? 1)
const BASE = '/wildsong-ranch/models/arenas/crown/'

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
renderer.setPixelRatio(DPR)
renderer.setSize(W, H)
renderer.outputColorSpace = THREE.SRGBColorSpace
renderer.toneMapping = THREE.NeutralToneMapping
renderer.toneMappingExposure = 1
renderer.shadowMap.enabled = true
renderer.shadowMap.type = THREE.PCFShadowMap
renderer.setClearColor(0xbfd6e8)
document.body.appendChild(renderer.domElement)

const ktx2 = new KTX2Loader().setTranscoderPath('/wildsong-ranch/basis/')
ktx2.detectSupport(renderer)
const gltfLoader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).setKTX2Loader(ktx2)
const maxAniso = renderer.capabilities.getMaxAnisotropy()

async function main() {
  const meta = await (await fetch(BASE + 'crown.json')).json()
  const gltf = await gltfLoader.loadAsync(BASE + meta.files[tier])
  const scene = new THREE.Scene()
  scene.add(gltf.scene)
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return
    if (o.material.map && /ring|apron|mid|far|plaza|land/.test(o.material.name)) o.material.map.anisotropy = Math.min(8, maxAniso)
    if (o.name === meta.runtime.shadowCatcher.node) {
      o.material = new THREE.ShadowMaterial({ opacity: 0.32, color: 0x3a2a1c })
      o.receiveShadow = true
    }
  })
  const sun = new THREE.Vector3(...meta.sun.direction).normalize()
  const key = new THREE.DirectionalLight(new THREE.Color(...meta.sun.color), 3.2)
  key.position.copy(sun).multiplyScalar(20)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  Object.assign(key.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 50 })
  key.shadow.radius = 3
  scene.add(key, key.target, new THREE.HemisphereLight(0xcfe3f5, 0x9c8a6a, 1.6))
  const grey = new THREE.MeshStandardMaterial({ color: 0xbcbcc2, roughness: 0.6 })
  for (const s of ['spawn_A', 'spawn_B']) {
    const c = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.4, 8, 24), grey)
    c.position.set(...meta.anchors[s].position)
    c.position.y += 0.5
    c.castShadow = true
    scene.add(c)
  }
  const camNode = view.startsWith('fly') ? meta.flyIn[Number(view.slice(3))] : meta.anchors['cam_' + view]
  const camera = new THREE.PerspectiveCamera(camNode.fovDeg, W / H, 0.1, 2000)
  camera.position.set(...(camNode.eye ?? camNode.position))
  camera.lookAt(new THREE.Vector3(...camNode.target))
  renderer.render(scene, camera)
  window.__arena = {
    ready: true,
    shot() {
      const t0 = performance.now()
      for (let i = 0; i < 5; i++) renderer.render(scene, camera)
      renderer.getContext().finish()
      const ms = (performance.now() - t0) / 5
      renderer.info.autoReset = false
      renderer.info.reset()
      renderer.render(scene, camera)
      const info = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, textures: renderer.info.memory.textures, ms }
      renderer.info.autoReset = true
      return { png: renderer.domElement.toDataURL('image/png'), ...info }
    },
  }
}

main().catch((e) => {
  console.error(e)
  window.__arena = { ready: true, error: String(e), shot: () => ({ png: 'data:,', calls: 0, triangles: 0, textures: 0, ms: 0 }) }
})
