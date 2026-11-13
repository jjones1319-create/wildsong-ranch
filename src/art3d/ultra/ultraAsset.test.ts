import { describe, expect, it } from 'vitest'
import { BufferAttribute, BufferGeometry, Group, Mesh, MeshStandardMaterial, Texture } from 'three'
import type { MeshPhysicalMaterial } from 'three'
import { makeUltraModel, type UltraAsset, type UltraMeta } from './ultraAsset.ts'

/** A one-triangle mesh with its own material maps. */
function tri(name: string, maps: { map?: Texture; orm?: Texture; normal?: Texture }): Mesh {
  const g = new BufferGeometry()
  g.setAttribute('position', new BufferAttribute(new Float32Array([0, 0, 0, 0.1, 0, 0, 0, 0.5, 0]), 3))
  g.setAttribute('uv', new BufferAttribute(new Float32Array([0, 0, 1, 0, 0, 1]), 2))
  const m = new MeshStandardMaterial({ map: maps.map ?? null, roughnessMap: maps.orm ?? null, aoMap: maps.orm ?? null, normalMap: maps.normal ?? null })
  const mesh = new Mesh(g, m)
  mesh.name = name
  return mesh
}

const shared = { base: new Texture(), orm: new Texture(), normal: new Texture() }
const ownBase = new Texture()
const ownOrm = new Texture()
const plainBase = new Texture()

/** A model with a body, eyes and two variants: `stone-x` with its own ORM (VARIANT_ORM), `plain-x` without. */
function asset(meta: UltraMeta): UltraAsset {
  const scene = new Group()
  scene.add(tri('lo_body', { map: shared.base, orm: shared.orm, normal: shared.normal }))
  scene.add(tri('lo_eyes', { map: shared.base, orm: shared.orm, normal: shared.normal }))
  scene.add(tri('lo_cards', { map: shared.base, orm: shared.orm, normal: shared.normal }))
  scene.add(tri('__variant_stone-x', { map: ownBase, orm: ownOrm }))
  scene.add(tri('__variant_plain-x', { map: plainBase, orm: shared.orm }))
  return { look: 'puddlepup', breed: 'puddlepup', scene, clips: [], meta, kind: 'ultra' } as unknown as UltraAsset
}

function film(model: Group, name: string): MeshPhysicalMaterial {
  let found: MeshPhysicalMaterial | null = null
  model.traverse((o) => {
    if ((o as Mesh).isMesh && o.name === name) found = (o as Mesh).material as MeshPhysicalMaterial
  })
  if (!found) throw new Error(`no ${name}`)
  return found
}

const META: UltraMeta = {
  meshes: { lo_body: 'body', lo_eyes: 'eye' },
  glow: { strength: 1.0, tint: null },
  variants: { 'stone-x': { orm: true, glow: { strength: 2.0, tint: '#ffd040' } }, 'plain-x': {} },
}

function shown(model: Group, name: string): boolean {
  let v = false
  model.traverse((o) => {
    if ((o as Mesh).isMesh && o.name === name) v = o.visible
  })
  return v
}

describe('a variant without fur cards (VARIANT_CARDS_OFF)', () => {
  const meta: UltraMeta = { meshes: { lo_body: 'body', lo_eyes: 'eye', lo_cards: 'card' }, variants: { 'stone-x': { cards: false }, 'plain-x': {} } }

  it('hides the cards only on that variant, and it stands as tall as the others', () => {
    const stone = makeUltraModel(asset(meta), 'stone-x', 1)
    expect(shown(stone.model as unknown as Group, 'lo_cards')).toBe(false)
    expect(shown(stone.model as unknown as Group, 'lo_body')).toBe(true)
    for (const v of ['plain-x', null]) {
      const other = makeUltraModel(asset(meta), v, 1)
      expect(shown(other.model as unknown as Group, 'lo_cards')).toBe(true)
      expect(other.scale).toBe(stone.scale)
    }
  })
})

describe("a variant's own ORM (VARIANT_ORM)", () => {
  it('swaps in its roughness, clearcoat and glow mask on every part but the eyes, with its own glow', () => {
    const { model } = makeUltraModel(asset(META), 'stone-x', 1)
    const body = film(model as unknown as Group, 'lo_body')
    expect(body.map).toBe(ownBase)
    expect(body.roughnessMap).toBe(ownOrm)
    expect(body.aoMap).toBe(ownOrm)
    expect(body.userData.glow.strength).toBe(2.0)
    expect(body.userData.glow.tint).not.toBeNull()
    const eyes = film(model as unknown as Group, 'lo_eyes')
    expect(eyes.map).toBe(shared.base)
    expect(eyes.roughnessMap).toBe(shared.orm)
  })

  it('keeps the shared ORM and the breed glow for a variant without one, and for the usual look', () => {
    for (const v of ['plain-x', null]) {
      const { model } = makeUltraModel(asset(META), v, 1)
      const body = film(model as unknown as Group, 'lo_body')
      expect(body.roughnessMap).toBe(shared.orm)
      expect(body.userData.glow.strength).toBe(1.0)
    }
  })

  it("the eyes keep the shared ORM, so they glow by the breed's entry, never the variant's", () => {
    // the breed glows: the eyes take its glow (1.0), not the variant's (2.0)
    const eyes = film(makeUltraModel(asset(META), 'stone-x', 1).model as unknown as Group, 'lo_eyes')
    expect(eyes.userData.glow.strength).toBe(1.0)
    // a breed without a glow of its own (Stormcrown Nimbusheep): the variant glows, its eyes don't
    const { glow: _breed, ...noBreedGlow } = META
    const eyes2 = film(makeUltraModel(asset(noBreedGlow), 'stone-x', 1).model as unknown as Group, 'lo_eyes')
    expect(eyes2.userData.glow).toBeUndefined()
    const body2 = film(makeUltraModel(asset(noBreedGlow), 'stone-x', 1).model as unknown as Group, 'lo_body')
    expect(body2.userData.glow.strength).toBe(2.0)
  })

  it('a variant whose own ORM has no glow (glow: null) does not glow, even on a breed that does', () => {
    const meta: UltraMeta = { ...META, variants: { 'stone-x': { orm: true, glow: null }, 'plain-x': {} } }
    const body = film(makeUltraModel(asset(meta), 'stone-x', 1).model as unknown as Group, 'lo_body')
    expect(body.roughnessMap).toBe(ownOrm)
    expect(body.userData.glow).toBeUndefined()
  })

  it('a sidecar without the orm flag never swaps, whatever the holder carries', () => {
    const meta: UltraMeta = { ...META, variants: { 'stone-x': {}, 'plain-x': {} } }
    const body = film(makeUltraModel(asset(meta), 'stone-x', 1).model as unknown as Group, 'lo_body')
    expect(body.map).toBe(ownBase)
    expect(body.roughnessMap).toBe(shared.orm)
  })
})
