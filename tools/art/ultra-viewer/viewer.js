// Art 2.1 review viewer (docs/ART_2_DETAIL.md §9, P1.1): Ultra monsters from public/models/monsters-ultra/ drawn with
// the Performance check's film renderer (src/art3d/perf/: the same materials, studio light and Ultra effects), posed by
// their own clips. tools/art/ultra-review.ts calls window.__ultra.shot({...}) and tools/art/lineup.ts calls
// window.__ultra.lineup({...}); both save the PNGs. Plain JS (served by Vite as is), so the game's and the tools' type
// checks never see it. Framing comes from the caller (the sidecar's height and centre), never a fixed 1 m monster.
import { AnimationMixer, Box3, Group, PerspectiveCamera, Scene, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { buildStudio, dirFrom, filmMaterial, SITE } from '../../../src/art3d/perf/content.ts'
import { createWebGLView } from '../../../src/art3d/perf/view.ts'
// the game's own part rules (src/art3d/ultra/ultraAsset.ts dresses a look with these), so the sheets match the phone:
// the material kind per mesh (props are 'prop', not 'body'), which parts show, the glow channel, soft fins
import { glowOf, partKind, partVisible, softFinsOf } from '../../../src/art3d/ultra/parts.ts'
import { ART } from '../../../src/data/tuning.ts'

const host = document.getElementById('host')
// mesh name → the film material kind (lo_props, the glossy rigid parts, use the body's)
const KINDS = [['lo_cards', 'card'], ['lo_fins', 'fin'], ['lo_eyes', 'eye'], ['lo_tuft', 'lock'], ['lo_props', 'body'], ['lo_body', 'body']]

function kindOf(name) {
  for (const [p, k] of KINDS) if (name.startsWith(p)) return k
  return 'body'
}

/** 'town-crier-tumblefox' → 'town-crier' (tools/blender/lib/ultra.py variant_short); none for the base. */
function shortOf(vid, look) {
  if (!vid) return null
  return look && vid.endsWith(`-${look}`) ? vid.slice(0, -look.length - 1) : vid
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

function newCanvas(w, h) {
  const canvas = document.createElement('canvas')
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`
  host.append(canvas)
  return canvas
}

/** The .glb as the runtime gets it: textures embedded (KTX2; WebP in <look>.webp.glb and <look>.lite.glb). */
async function loadLook(view, look, o) {
  const base = `${SITE}models/monsters-ultra/`
  const ktx = new KTX2Loader().setTranscoderPath(`${SITE}basis/`).detectSupport(view.renderer)
  const file = o.lite ? `${look}.lite.glb` : `${look}${o.format === 'webp' ? '.webp' : ''}.glb`
  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).setKTX2Loader(ktx).loadAsync(`${base}${file}`)
  // the sidecar: the game reads its meshes, variants, glow and fins too
  let meta = null
  try {
    const r = await fetch(`${base}${look}.json`)
    if (r.ok) meta = await r.json()
  } catch {
    meta = null
  }
  return { gltf, ktx, meta }
}

/**
 * Film materials on every mesh (o.raw: the glb's own), the variant's map and colour set, the variant holders hidden: the
 * same rules as the game's ultraAsset.ts (partKind, partVisible, glowOf, softFinsOf; each mesh's own maps, the eyes
 * keep theirs under a variant), so a review sheet shows what the phone shows.
 */
function dress(gltf, o, meta = null) {
  let variantMap = null
  let variantColour = 'color_1'
  gltf.scene.traverse((m) => {
    if (m.isMesh && m.name === `__variant_${o.variant}`) variantMap = m.material.map
  })
  if (o.colorAttribute) variantColour = o.colorAttribute.toLowerCase()
  let triangles = 0
  let cards = 0
  const glow = glowOf(meta, ART.ultra.film.glow.maxStrength)
  const softFins = softFinsOf(meta)
  gltf.scene.traverse((m) => {
    if (!m.isMesh) return
    // the holders, and the props other variants wear (lo_props_<short>: shown only with their own variant)
    const hidden = meta
      ? !partVisible(m.name, o.variant ?? null, meta.variants)
      : m.name.startsWith('__variant_') || (m.name.startsWith('lo_props_') && m.name !== `lo_props_${shortOf(o.variant, o.look)}`)
    if (hidden) {
      m.visible = false
      return
    }
    const kind = (meta ? partKind(m.name, meta.meshes) : null) ?? kindOf(m.name)
    m.userData.kind = kind
    const g = m.geometry
    if (variantMap && (kind === 'card' || kind === 'lock') && g.getAttribute(variantColour)) g.setAttribute('color', g.getAttribute(variantColour))
    const mat = m.material
    // o.raw: the glb's own materials as loaded; otherwise the game's film material (the card edge fade, the luminance
    // caps, the glow), built from this mesh's own maps
    if (!o.raw && mat?.map) {
      const base = variantMap && kind !== 'eye' ? variantMap : mat.map
      m.material = filmMaterial(kind, { base, normal: mat.normalMap ?? null, orm: mat.roughnessMap ?? mat.aoMap ?? null }, { glow })
    } else if (o.raw && variantMap) mat.map = variantMap
    m.castShadow = kind !== 'card'
    m.receiveShadow = kind !== 'fin' || softFins
    m.frustumCulled = false
    if (kind === 'card') m.layers.set(1)
    triangles += (g.index ? g.index.count : g.attributes.position.count) / 3
    if (kind === 'card') cards += g.attributes.position.count / 6
  })
  return { root: gltf.scene, triangles, cards }
}

async function finish(view, scene, camera) {
  await view.init(scene, camera)
  for (let i = 0; i < 6; i++) {
    view.render()
    await new Promise((r) => requestAnimationFrame(r))
  }
  return view.readPixels()
}

async function shot(o) {
  const size = o.size ?? 900
  host.replaceChildren()
  const view = createWebGLView({ canvas: newCanvas(size, size), width: size, height: size, dpr: o.dpr ?? 1, cinematic: false, focus: 2.4 })
  const { gltf, ktx, meta } = await loadLook(view, o.look ?? 'puddlepup', o)
  const { root, triangles, cards } = dress(gltf, o, meta)
  const scene = new Scene()
  scene.add(root)
  const camera = new PerspectiveCamera(30, 1, 0.05, 60)
  camera.layers.enable(1)
  aim(camera, o.target ?? [0, 0.02, 0.5], o.az ?? 35, o.el ?? 14, o.frame ?? 1.75)
  const st = o.studio ?? { focus: [0, 0.5, 0], reach: 1.6 }
  buildStudio(scene, view.environment, new Vector3(...st.focus), st.reach)
  if (o.clip) {
    const clip = gltf.animations.find((a) => a.name === o.clip)
    if (!clip) throw new Error(`no clip ${o.clip}; have ${gltf.animations.map((a) => a.name).join(',')}`)
    const mixer = new AnimationMixer(root)
    mixer.clipAction(clip).play()
    mixer.setTime(Math.min(clip.duration - 1e-3, (o.t ?? 0.5) * clip.duration))
  }
  const png = await finish(view, scene, camera)
  view.dispose()
  ktx.dispose()
  return { png, triangles: Math.round(triangles), cards: Math.round(cards), clips: gltf.animations.map((a) => `${a.name}:${a.duration.toFixed(3)}`) }
}

/** The visible meshes' box (the hidden variant holders sit under the floor), in world space at the current pose. */
function visibleBox(obj) {
  obj.updateMatrixWorld(true)
  const box = new Box3()
  obj.traverse((m) => {
    if (m.isMesh && m.visible) box.expandByObject(m, true)
  })
  return box
}

/**
 * Several looks side by side at their in-game relative size (each scaled by its `scale`), turned to `az` in place, from
 * a near-orthographic camera: o = { looks: [{ look, scale }], az, el, width, height, gap }. Returns the PNG and each
 * look's label anchor (top centre, in pixels) and its shown height.
 */
async function lineup(o) {
  const W = o.width ?? 2400
  const H = o.height ?? 800
  host.replaceChildren()
  const view = createWebGLView({ canvas: newCanvas(W, H), width: W, height: H, dpr: 1, cinematic: false, focus: 2.4 })
  const scene = new Scene()
  const items = []
  const disposers = []
  for (const it of o.looks) {
    const { gltf, ktx, meta } = await loadLook(view, it.look, {})
    disposers.push(ktx)
    const { root } = dress(gltf, {}, meta)
    const g = new Group()
    g.add(root)
    g.scale.setScalar(it.scale)
    g.rotation.y = (-(o.az ?? 0) * Math.PI) / 180
    scene.add(g)
    items.push({ look: it.look, g, box: visibleBox(g) })
  }
  const gap = o.gap ?? 0.3
  let x = 0
  for (const it of items) {
    it.g.position.x = x - it.box.min.x
    it.g.position.z = -(it.box.min.z + it.box.max.z) / 2
    x += it.box.max.x - it.box.min.x + gap
  }
  const total = x - gap
  for (const it of items) it.g.position.x -= total / 2
  const maxH = Math.max(...items.map((it) => it.box.max.y))
  const fov = 14
  const t = Math.tan((fov * Math.PI) / 360)
  const camera = new PerspectiveCamera(fov, W / H, 0.05, 400)
  camera.layers.enable(1)
  const dist = Math.max((maxH * 1.3) / (2 * t), (total * 1.08) / (2 * t * (W / H)))
  const target = new Vector3(0, maxH * 0.5, 0)
  camera.position.copy(target).add(dirFrom(0, o.el ?? 8).multiplyScalar(dist))
  camera.lookAt(target)
  camera.updateProjectionMatrix()
  buildStudio(scene, view.environment, target, Math.max(total, maxH) * 0.6)
  const png = await finish(view, scene, camera)
  const labels = items.map((it) => {
    const b = visibleBox(it.g)
    const p = new Vector3((b.min.x + b.max.x) / 2, b.max.y, (b.min.z + b.max.z) / 2).project(camera)
    return { look: it.look, x: ((p.x + 1) / 2) * W, y: ((1 - p.y) / 2) * H, height: b.max.y }
  })
  view.dispose()
  for (const k of disposers) k.dispose()
  return { png, labels }
}

window.__ultra = { ready: true, shot, lineup }
