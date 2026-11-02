// Art 2.1 review viewer (docs/ART_2_DETAIL.md §9, P1.1): one Ultra monster from public/models/monsters-ultra/ drawn with
// the Performance check's film renderer (src/art3d/perf/: the same materials, studio light and Ultra effects), posed by
// its own clips. tools/art/ultra-review.ts calls window.__ultra.shot({...}) and saves the PNGs. Plain JS (served by Vite
// as is), so the game's and the tools' type checks never see it.
import { AnimationMixer, PerspectiveCamera, Scene, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { buildStudio, dirFrom, filmMaterial, SITE } from '../../../src/art3d/perf/content.ts'
import { createWebGLView } from '../../../src/art3d/perf/view.ts'

const host = document.getElementById('host')
const KINDS = [['lo_cards', 'card'], ['lo_fins', 'fin'], ['lo_eyes', 'eye'], ['lo_tuft', 'lock'], ['lo_body', 'body']]

function kindOf(name) {
  for (const [p, k] of KINDS) if (name.startsWith(p)) return k
  return 'body'
}

function aim(camera, target, az, el, size) {
  const [bx, by, bz] = target
  const t = new Vector3(bx, bz, -by)
  const dist = size * 2.4
  camera.position.copy(t).add(dirFrom(az, el).multiplyScalar(dist))
  camera.fov = (2 * Math.atan(size / 2 / dist) * 180) / Math.PI
  camera.lookAt(t)
  camera.updateProjectionMatrix()
}

async function shot(o) {
  const size = o.size ?? 900
  host.replaceChildren()
  const canvas = document.createElement('canvas')
  canvas.style.width = canvas.style.height = `${size}px`
  host.append(canvas)
  const view = createWebGLView({ canvas, width: size, height: size, dpr: o.dpr ?? 1, cinematic: false, focus: 2.4 })
  const look = o.look ?? 'puddlepup'
  const base = `${SITE}models/monsters-ultra/`
  // the .glb as the runtime gets it: textures embedded (KTX2, or WebP in <look>.webp.glb), film materials assigned
  const ktx = new KTX2Loader().setTranscoderPath(`${SITE}basis/`).detectSupport(view.renderer)
  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).setKTX2Loader(ktx)
    .loadAsync(`${base}${look}${o.format === 'webp' ? '.webp' : ''}.glb`)
  let variantMap = null
  gltf.scene.traverse((m) => {
    if (m.isMesh && m.name === `__variant_${o.variant}`) variantMap = m.material.map
  })
  let set = null
  const root = gltf.scene
  let triangles = 0
  let cards = 0
  root.traverse((m) => {
    if (!m.isMesh) return
    if (m.name.startsWith('__variant_')) {
      m.visible = false
      return
    }
    const kind = kindOf(m.name)
    m.userData.kind = kind
    const g = m.geometry
    if (variantMap && (kind === 'card' || kind === 'lock') && g.getAttribute('color_1')) g.setAttribute('color', g.getAttribute('color_1'))
    const mat = m.material
    set ??= { base: mat.map, normal: mat.normalMap, orm: mat.aoMap, bytes: 0 }
    // o.raw: the glb's own materials as loaded; otherwise the Performance check's film material (with the card edge fade)
    if (!o.raw) m.material = filmMaterial(kind, { ...set, base: variantMap ?? set.base })
    else if (variantMap) mat.map = variantMap
    m.castShadow = kind !== 'card'
    m.receiveShadow = kind !== 'fin'
    m.frustumCulled = false
    if (kind === 'card') m.layers.set(1)
    triangles += (g.index ? g.index.count : g.attributes.position.count) / 3
    if (kind === 'card') cards += g.attributes.position.count / 6
  })
  const scene = new Scene()
  scene.add(root)
  const camera = new PerspectiveCamera(30, 1, 0.05, 60)
  camera.layers.enable(1)
  aim(camera, o.target ?? [0, 0.02, 0.5], o.az ?? 35, o.el ?? 14, o.frame ?? 1.75)
  buildStudio(scene, view.environment, new Vector3(0, 0.5, 0), 1.6)
  let mixer = null
  if (o.clip) {
    const clip = gltf.animations.find((a) => a.name === o.clip)
    if (!clip) throw new Error(`no clip ${o.clip}; have ${gltf.animations.map((a) => a.name).join(',')}`)
    mixer = new AnimationMixer(root)
    const action = mixer.clipAction(clip)
    action.play()
    mixer.setTime(Math.min(clip.duration - 1e-3, (o.t ?? 0.5) * clip.duration))
  }
  await view.init(scene, camera)
  for (let i = 0; i < 6; i++) {
    view.render()
    await new Promise((r) => requestAnimationFrame(r))
  }
  const png = view.readPixels()
  view.dispose()
  ktx.dispose()
  return { png, triangles: Math.round(triangles), cards: Math.round(cards), clips: gltf.animations.map((a) => `${a.name}:${a.duration.toFixed(3)}`) }
}

window.__ultra = { ready: true, shot }
