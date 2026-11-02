/**
 * Art 2.1 Ultra: put the textures and film-ready materials into the .glb, so the battle runtime can show a look with
 * GLTFLoader alone (ART_2_DETAIL §3.4). Used by tools/art/ultra.ts.
 *
 * Each mesh kind (named lo_body, lo_eyes, lo_fins, lo_cards, lo_tuft) gets a MeshPhysical-compatible material:
 *   colour (sRGB; the fur-card tiles carry alpha) · tangent normal (scale = ART.ultra.film.normalScale) ·
 *   ORM as occlusion (R) and metallicRoughness (G roughness; B is the clearcoat mask, so metallicFactor = 0) ·
 *   KHR_materials_clearcoat, KHR_materials_sheen (sheen colour × strength), KHR_materials_specular (eyes) ·
 *   fins: double-sided with a faint self-glow from their own colour · cards: alphaMode MASK.
 * The card edge fade (cards show only at the outline) is a shader rule the runtime adds (src/art3d/perf/content.ts).
 * Variants: a hidden one-triangle mesh `__variant_<id>` whose material's base colour is the variant's colour map (the
 * Art 2.0 convention, src/art3d/loader.ts).
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Document, Material, Texture } from '@gltf-transform/core'
import { EXTTextureWebP, KHRMaterialsClearcoat, KHRMaterialsSheen, KHRMaterialsSpecular, KHRTextureBasisu } from '@gltf-transform/extensions'
import { ART } from '../../src/data/tuning.ts'

export type Format = 'ktx2' | 'webp'
export interface TexFiles { base: string; normal?: string; orm?: string }
const F = ART.ultra.film

function srgbToLinear(hex: string): [number, number, number] {
  const c = hex.replace('#', '')
  return [0, 2, 4].map((i) => {
    const v = parseInt(c.slice(i, i + 2), 16) / 255
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }) as [number, number, number]
}

function texture(doc: Document, dir: string, file: string, format: Format, cache: Map<string, Texture>): Texture {
  const hit = cache.get(file)
  if (hit) return hit
  const name = file.replace(/\.(ktx2|webp)$/, '')
  const t = doc.createTexture(name).setImage(readFileSync(join(dir, file))).setMimeType(format === 'ktx2' ? 'image/ktx2' : 'image/webp').setURI(file)
  cache.set(file, t)
  return t
}

const KIND_BY_MESH: Record<string, 'body' | 'eye' | 'fin' | 'card' | 'lock'> = { lo_body: 'body', lo_eyes: 'eye', lo_fins: 'fin', lo_cards: 'card', lo_tuft: 'lock' }

/** Film-ready materials with embedded textures on every lo_* mesh, plus the variant holders. Returns the material count. */
export function embedTextures(doc: Document, dir: string, body: Record<string, { ktx2: string; webp: string }>,
  variants: Record<string, { ktx2: string; webp: string }>, format: Format): number {
  (format === 'ktx2' ? doc.createExtension(KHRTextureBasisu) : doc.createExtension(EXTTextureWebP)).setRequired(true)
  const clearcoat = doc.createExtension(KHRMaterialsClearcoat)
  const sheen = doc.createExtension(KHRMaterialsSheen)
  const specular = doc.createExtension(KHRMaterialsSpecular)
  const cache = new Map<string, Texture>()
  const tex = (f: { ktx2: string; webp: string }) => texture(doc, dir, format === 'ktx2' ? f.ktx2 : f.webp, format, cache)
  const base = tex(body.base!)
  const normal = tex(body.normal!)
  const orm = tex(body.orm!)
  const sheenCol = srgbToLinear(F.sheenColor)
  const made = new Map<string, Material>()

  function film(kind: 'body' | 'eye' | 'fin' | 'card' | 'lock', map: Texture, name: string): Material {
    const m = doc.createMaterial(name).setBaseColorTexture(map).setBaseColorFactor([1, 1, 1, 1])
      .setNormalTexture(normal).setNormalScale(F.normalScale)
      .setOcclusionTexture(orm).setOcclusionStrength(1)
      .setMetallicRoughnessTexture(orm).setMetallicFactor(0).setRoughnessFactor(F.furRoughness)
    const coat = kind === 'fin' ? F.finCoat : kind === 'eye' ? F.eyeCoat : kind === 'card' ? 0 : F.furCoat
    if (coat > 0) m.setExtension('KHR_materials_clearcoat', clearcoat.createClearcoat().setClearcoatFactor(coat).setClearcoatRoughnessFactor(kind === 'eye' ? 0.05 : F.furCoatRoughness))
    const sh = kind === 'fin' || kind === 'eye' ? 0 : kind === 'card' ? F.cardSheen : F.furSheen
    if (sh > 0) m.setExtension('KHR_materials_sheen', sheen.createSheen().setSheenColorFactor(sheenCol.map((c) => c * sh) as [number, number, number]).setSheenRoughnessFactor(F.sheenRoughness))
    if (kind === 'eye') m.setExtension('KHR_materials_specular', specular.createSpecular().setSpecularFactor(F.eyeSpecular))
    if (kind === 'fin') m.setDoubleSided(true).setEmissiveTexture(map).setEmissiveFactor([F.finGlow, F.finGlow, F.finGlow])
    if (kind === 'card') m.setAlphaMode('MASK').setAlphaCutoff(F.cardAlphaTest)
    return m
  }

  for (const node of doc.getRoot().listNodes()) {
    const mesh = node.getMesh()
    const kind = KIND_BY_MESH[node.getName()]
    if (!mesh || !kind) continue
    let m = made.get(kind)
    if (!m) {
      m = film(kind, base, `film_${kind}`)
      made.set(kind, m)
    }
    for (const p of mesh.listPrimitives()) {
      const old = p.getMaterial()
      p.setMaterial(m)
      if (old && old.listParents().filter((x) => x.propertyType !== 'Root').length === 0) old.dispose()
    }
  }
  // variant holders: one tiny triangle far under the floor, hidden by the runtime
  const buffer = doc.getRoot().listBuffers()[0] ?? doc.createBuffer()
  const scene = doc.getRoot().getDefaultScene() ?? doc.getRoot().listScenes()[0]!
  for (const [vid, files] of Object.entries(variants)) {
    const mat = film('body', tex(files), `__variant_${vid}`)
    const pos = doc.createAccessor().setType('VEC3').setBuffer(buffer).setArray(new Float32Array([0, -0.5, 0, 0.001, -0.5, 0, 0, -0.5, -0.001]))
    const uv = doc.createAccessor().setType('VEC2').setBuffer(buffer).setArray(new Float32Array([0, 0, 1, 0, 0, 1]))
    const prim = doc.createPrimitive().setAttribute('POSITION', pos).setAttribute('TEXCOORD_0', uv).setMaterial(mat)
    const mesh = doc.createMesh(`__variant_${vid}`).addPrimitive(prim)
    scene.addChild(doc.createNode(`__variant_${vid}`).setMesh(mesh))
  }
  return made.size + Object.keys(variants).length
}

/** Blender exports the cards' and tuft's colours as custom attributes: make them COLOR_0 (base) and COLOR_1 (variant). */
export function promoteColours(doc: Document): number {
  let n = 0
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const p of mesh.listPrimitives()) {
      const base = p.getAttribute('_COLOR_BASE')
      if (!base) continue
      const variant = p.getAttribute('_COLOR_VARIANT')
      p.setAttribute('COLOR_0', base).setAttribute('_COLOR_BASE', null)
      if (variant) p.setAttribute('COLOR_1', variant).setAttribute('_COLOR_VARIANT', null)
      n++
    }
  }
  return n
}
