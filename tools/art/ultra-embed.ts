/**
 * Art 2.1 Ultra: put the textures and film-ready materials into the .glb, so the battle runtime can show a look with
 * GLTFLoader alone (ART_2_DETAIL §3.4). Used by tools/art/ultra.ts.
 *
 * Each mesh kind that is present (lo_body and lo_eyes always; lo_fins, lo_cards, lo_tuft and lo_props when the recipe
 * builds them) gets a MeshPhysical-compatible material:
 *   colour (sRGB; the fur-card tiles carry alpha) · tangent normal (scale = ART.ultra.film.normalScale) ·
 *   ORM as occlusion (R) and metallicRoughness (G roughness; B is the clearcoat mask, so metallicFactor = 0) ·
 *   KHR_materials_clearcoat, KHR_materials_sheen (the texel's own colour: the colour map × sheenGain × strength, the
 *   game film's rule), KHR_materials_specular (eyes) ·
 *   fins: double-sided with a faint self-glow from their own colour · cards: alphaMode MASK ·
 *   props (horns, a rope, a scarf): the body's material with no sheen and the membranes' clearcoat.
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

function texture(doc: Document, dir: string, file: string, format: Format, cache: Map<string, Texture>): Texture {
  const hit = cache.get(file)
  if (hit) return hit
  const name = file.replace(/\.(ktx2|webp)$/, '')
  const t = doc.createTexture(name).setImage(readFileSync(join(dir, file))).setMimeType(format === 'ktx2' ? 'image/ktx2' : 'image/webp').setURI(file)
  cache.set(file, t)
  return t
}

export type Kind = 'body' | 'eye' | 'fin' | 'card' | 'lock' | 'prop'
/** Mesh name → kind (tools/blender/lib/ultra.py MESH_KINDS); only lo_body and lo_eyes are always there. */
export const KIND_BY_MESH: Record<string, Kind> = { lo_body: 'body', lo_eyes: 'eye', lo_fins: 'fin', lo_cards: 'card', lo_tuft: 'lock', lo_props: 'prop' }
/** A mesh's kind: KIND_BY_MESH, and 'prop' for a variant's own props (lo_props_<short>, shown only with that variant). */
export function kindOfMesh(name: string): Kind | undefined {
  return KIND_BY_MESH[name] ?? (name.startsWith('lo_props_') ? 'prop' : undefined)
}

/** The film numbers the materials read (ART.ultra.film). A missing one (a mid-edit of tuning.ts) fails the ship in words
 * instead of writing NaN factors into the .glb. */
const FILM_KEYS = ['normalScale', 'furRoughness', 'furCoat', 'furCoatRoughness', 'furSheen', 'cardSheen', 'sheenGain', 'sheenRoughness',
  'finCoat', 'finGlow', 'eyeCoat', 'eyeSpecular', 'cardAlphaTest'] as const

function checkFilm(): void {
  const film = F as unknown as Record<string, unknown>
  const bad = FILM_KEYS.filter((k) => typeof film[k] !== 'number' || !Number.isFinite(film[k]))
  if (bad.length) throw new Error(`src/data/tuning.ts ART.ultra.film is missing ${bad.join(', ')} (or they aren't numbers): the materials can't be written`)
}

/** Film-ready materials with embedded textures on every lo_* mesh, plus the variant holders. Returns the material count. */
export function embedTextures(doc: Document, dir: string, body: Record<string, { ktx2: string; webp: string }>,
  variants: Record<string, { ktx2: string; webp: string }>, format: Format): number {
  checkFilm()
  ;(format === 'ktx2' ? doc.createExtension(KHRTextureBasisu) : doc.createExtension(EXTTextureWebP)).setRequired(true)
  const clearcoat = doc.createExtension(KHRMaterialsClearcoat)
  const sheen = doc.createExtension(KHRMaterialsSheen)
  const specular = doc.createExtension(KHRMaterialsSpecular)
  const cache = new Map<string, Texture>()
  const tex = (f: { ktx2: string; webp: string }) => texture(doc, dir, format === 'ktx2' ? f.ktx2 : f.webp, format, cache)
  const base = tex(body.base!)
  const normal = tex(body.normal!)
  const orm = tex(body.orm!)
  const made = new Map<string, Material>()

  function film(kind: Kind, map: Texture, name: string): Material {
    const m = doc.createMaterial(name).setBaseColorTexture(map).setBaseColorFactor([1, 1, 1, 1])
      .setNormalTexture(normal).setNormalScale(F.normalScale)
      .setOcclusionTexture(orm).setOcclusionStrength(1)
      .setMetallicRoughnessTexture(orm).setMetallicFactor(0).setRoughnessFactor(F.furRoughness)
    const coat = kind === 'fin' || kind === 'prop' ? F.finCoat : kind === 'eye' ? F.eyeCoat : kind === 'card' ? 0 : F.furCoat
    if (coat > 0) m.setExtension('KHR_materials_clearcoat', clearcoat.createClearcoat().setClearcoatFactor(coat).setClearcoatRoughnessFactor(kind === 'eye' ? 0.05 : F.furCoatRoughness))
    const sh = kind === 'fin' || kind === 'eye' || kind === 'prop' ? 0 : kind === 'card' ? F.cardSheen : F.furSheen
    // the sheen takes each texel's own colour, as in the game (a fixed teal one cast every dark coat olive in a raw viewer)
    const g = sh * F.sheenGain
    if (sh > 0) m.setExtension('KHR_materials_sheen', sheen.createSheen().setSheenColorTexture(map).setSheenColorFactor([g, g, g]).setSheenRoughnessFactor(F.sheenRoughness))
    if (kind === 'eye') m.setExtension('KHR_materials_specular', specular.createSpecular().setSpecularFactor(F.eyeSpecular))
    if (kind === 'fin') m.setDoubleSided(true).setEmissiveTexture(map).setEmissiveFactor([F.finGlow, F.finGlow, F.finGlow])
    if (kind === 'card') m.setAlphaMode('MASK').setAlphaCutoff(F.cardAlphaTest)
    return m
  }

  for (const node of doc.getRoot().listNodes()) {
    const mesh = node.getMesh()
    const kind = kindOfMesh(node.getName())
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

/**
 * Blender exports the cards' and tuft's colours as custom attributes: make them COLOR_0 (base) and COLOR_1, COLOR_2, …
 * (the variants in VARIANTS order: _COLOR_VARIANT, _COLOR_VARIANT2, …). Returns how many primitives had colours.
 */
export function promoteColours(doc: Document): number {
  let n = 0
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const p of mesh.listPrimitives()) {
      const base = p.getAttribute('_COLOR_BASE')
      if (!base) continue
      p.setAttribute('COLOR_0', base).setAttribute('_COLOR_BASE', null)
      for (let i = 1; ; i++) {
        const name = i === 1 ? '_COLOR_VARIANT' : `_COLOR_VARIANT${i}`
        const variant = p.getAttribute(name)
        if (!variant) break
        p.setAttribute(`COLOR_${i}`, variant).setAttribute(name, null)
      }
      n++
    }
  }
  return n
}
