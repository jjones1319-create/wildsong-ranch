import { createHash } from 'node:crypto'
import { existsSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { DUEL_FALLBACK_OK, DUEL_REQUIRED_CLIPS, resolveClipName } from '../art3d/ultra/clips.ts'
import { cardEdgeFadeOf, glowOf, normalScaleOf, partKind, partVisible, softFinsOf, variantOfPart } from '../art3d/ultra/parts.ts'
import { ART } from '../data/tuning.ts'
import { BREED_IDS } from '../data/types.ts'
import { SECRETS } from '../data/secrets.ts'
import { hasGrownForm } from './monster/render.ts'
import { buildTagOf, isUltraId, looksFromQuery, ULTRA_IDS, ULTRA_LOOKS, ultraHeightPct, ultraIdFor, ultraVariant, versionedUrl } from './ultraLooks.ts'

/**
 * Art 2.1 Ultra registry (src/art/ultraLooks.ts): every breed listed has shipped, with what Battle 3D and the 3D Gallery
 * need, inside the budgets (ART_2_DETAIL §5.1): ≤ 100k triangles and ≤ 8 MB; the Lite copy ≤ 12k triangles, ≤ 1.5 MB.
 */

const PUBLIC = 'public'
const MB = 1024 * 1024

interface Sidecar {
  glow?: unknown
  cards?: unknown
  normal?: unknown
  fins?: unknown
  heightUnits?: number
  build?: unknown
  clips?: Record<string, unknown>
  variants?: Record<string, { holder?: string; meshes?: string[] }>
  lite?: { file?: string; build?: string }
}

interface GlbJson {
  nodes?: { name?: string; mesh?: number }[]
  meshes?: { name?: string; primitives: { indices?: number; mode?: number; attributes: Record<string, number> }[] }[]
  accessors?: { count: number }[]
  animations?: { name?: string }[]
}

/** The JSON chunk of a .glb (the scene graph, accessors and animations; the buffers stay compressed). */
function glbJson(path: string): GlbJson {
  const b = readFileSync(path)
  expect(b.readUInt32LE(0), `${path} is a glb`).toBe(0x46546c67)
  const len = b.readUInt32LE(12)
  expect(b.readUInt32LE(16)).toBe(0x4e4f534a)
  return JSON.parse(b.subarray(20, 20 + len).toString('utf8')) as GlbJson
}

/** Triangles drawn by every mesh of a glb (the hidden variant holders included, as the pipeline's budget counts them). */
function triangles(j: GlbJson): number {
  let n = 0
  for (const m of j.meshes ?? []) {
    for (const p of m.primitives) {
      if ((p.mode ?? 4) !== 4) continue
      const acc = p.indices !== undefined ? j.accessors![p.indices]! : j.accessors![p.attributes.POSITION!]!
      n += acc.count / 3
    }
  }
  return Math.round(n)
}

const names = (j: GlbJson) => new Set([...(j.nodes ?? []).map((n) => n.name ?? ''), ...(j.meshes ?? []).map((m) => m.name ?? '')])
const sha10 = (path: string) => createHash('sha1').update(readFileSync(path)).digest('hex').slice(0, 10)

describe('the Ultra registry (Art 2.1)', () => {
  it('lists Puddlepup first, real breeds and their grown forms, each once, named by their files', () => {
    expect(ULTRA_IDS[0]).toBe('puddlepup')
    expect(new Set(ULTRA_IDS).size).toBe(ULTRA_IDS.length)
    for (const id of ULTRA_IDS) {
      const look = ULTRA_LOOKS[id]!
      expect(look.id).toBe(id)
      expect(BREED_IDS).toContain(look.breed)
      // a young (or only) form is its breed's id; a grown form is <breed>-grown, for a breed that has one
      if (look.stage === 'grown') {
        expect(id).toBe(`${look.breed}-grown`)
        expect(hasGrownForm(look.breed), `${look.breed} has no grown form`).toBe(true)
      } else expect(id).toBe(look.breed)
      expect(look.glb).toBe(`models/monsters-ultra/${id}.glb`)
      expect(look.heightUnits).toBeGreaterThan(0)
      // its variants are its breed's secret variants
      for (const v of look.variants) expect(SECRETS.find((s) => s.id === v)?.breed).toBe(look.breed)
    }
    expect(ultraHeightPct(ULTRA_LOOKS.puddlepup!)).toBe(100)
  })

  for (const breed of ULTRA_IDS) {
    const look = ULTRA_LOOKS[breed]!
    describe(breed, () => {
      const glbPath = join(PUBLIC, look.glb)
      const metaPath = join(PUBLIC, look.meta)

      it('has its files in public/', () => {
        expect(existsSync(glbPath), look.glb).toBe(true)
        expect(existsSync(metaPath), look.meta).toBe(true)
        expect(existsSync(join(PUBLIC, look.lite.glb)), look.lite.glb).toBe(true)
        if (look.fallback) for (const f of [look.fallback.glb, look.fallback.meta]) expect(existsSync(join(PUBLIC, f)), f).toBe(true)
      })

      it('its sidecar has every clip Battle 3D plays, its scale and a build tag that matches the file', () => {
        const side = JSON.parse(readFileSync(metaPath, 'utf8')) as Sidecar
        // its true size: the registry's height is the recipe's (the sidecar's)
        expect(side.heightUnits).toBe(look.heightUnits)
        const has = (c: string) => Object.prototype.hasOwnProperty.call(side.clips ?? {}, c)
        for (const c of DUEL_REQUIRED_CLIPS) expect(has(c), `${breed} lacks ${c}`).toBe(true)
        for (const c of DUEL_FALLBACK_OK) expect(resolveClipName(has, c), `${breed}: nothing for ${c}`).not.toBeNull()
        // the glb really holds them, by the same names
        const anims = new Set((glbJson(glbPath).animations ?? []).map((a) => a.name))
        for (const c of DUEL_REQUIRED_CLIPS) expect(anims.has(c), `${breed}.glb lacks the ${c} clip`).toBe(true)
        if (typeof side.build === 'string') expect(side.build).toBe(sha10(glbPath))
      })

      it('a normal entry (when it has one) has a usable scale', () => {
        const side = JSON.parse(readFileSync(metaPath, 'utf8')) as Sidecar
        if (side.normal === undefined || (side.normal as { scale?: unknown }).scale === undefined) return
        expect(normalScaleOf(side), `${breed}.json normal ${JSON.stringify(side.normal)}`).not.toBeNull()
      })

      it('a cards entry (when it has one) has a usable edge fade', () => {
        const side = JSON.parse(readFileSync(metaPath, 'utf8')) as Sidecar
        if (side.cards === undefined || (side.cards as { edgeFade?: unknown }).edgeFade === undefined) return
        expect(cardEdgeFadeOf(side), `${breed}.json cards ${JSON.stringify(side.cards)}`).not.toBeNull()
      })

      it('a glow entry (when it has one) has a usable strength and tint', () => {
        const side = JSON.parse(readFileSync(metaPath, 'utf8')) as Sidecar
        if (side.glow === undefined) return
        const g = glowOf(side, ART.ultra.film.glow.maxStrength)
        expect(g, `${breed}.json glow ${JSON.stringify(side.glow)}`).not.toBeNull()
        expect(g!.strength).toBeGreaterThan(0)
        if (side.fins !== undefined) expect(typeof (side.fins as { soft?: unknown }).soft === 'boolean' || (side.fins as { soft?: unknown }).soft === undefined).toBe(true)
      })

      it('holds each variant the registry lists, and each variant own props show only with it', () => {
        const side = JSON.parse(readFileSync(metaPath, 'utf8')) as Sidecar
        const j = glbJson(glbPath)
        const nodes = names(j)
        for (const v of look.variants) {
          expect(side.variants?.[v], `${breed}.json lacks ${v}`).toBeTruthy()
          expect(nodes.has(side.variants![v]!.holder ?? `__variant_${v}`), `${breed}.glb lacks the ${v} holder`).toBe(true)
        }
        for (const [vid, v] of Object.entries(side.variants ?? {})) {
          for (const m of v.meshes ?? []) {
            expect(nodes.has(m), `${breed}.glb lacks ${m} (${vid})`).toBe(true)
            expect(partVisible(m, null, side.variants), `${m} shows on the usual look`).toBe(false)
            expect(partVisible(m, vid, side.variants), `${m} hides on ${vid}`).toBe(true)
          }
        }
        // every variant-only prop (lo_props_<short>) is hidden on the usual look; the always-worn parts show
        for (const n of nodes) {
          if (/^lo_props_/.test(n) && !/^lo_props_\d+$/.test(n)) expect(partVisible(n, null, side.variants), `${n} shows on the usual look`).toBe(false)
          if (/^lo_(body|eyes|fins|cards|tuft|props)$/.test(n)) expect(partVisible(n, null, side.variants)).toBe(true)
        }
      })

      it('fits the Ultra budget: ≤ 100k triangles, ≤ 8 MB', () => {
        expect(triangles(glbJson(glbPath))).toBeLessThanOrEqual(100_000)
        expect(statSync(glbPath).size).toBeLessThanOrEqual(8 * MB)
      })

      it('its Lite copy (where it has one) fits ≤ 12k triangles and ≤ 1.5 MB, with the same clips', () => {
        const side = JSON.parse(readFileSync(metaPath, 'utf8')) as Sidecar
        const lites = new Set<string>([join(PUBLIC, look.lite.glb)])
        if (side.lite?.file) lites.add(join(PUBLIC, look.glb.slice(0, look.glb.lastIndexOf('/') + 1), side.lite.file))
        for (const p of lites) {
          expect(existsSync(p), p).toBe(true)
          const j = glbJson(p)
          expect(triangles(j), p).toBeLessThanOrEqual(12_000)
          expect(statSync(p).size, p).toBeLessThanOrEqual(1.5 * MB)
          const anims = new Set((j.animations ?? []).map((a) => a.name))
          for (const c of DUEL_REQUIRED_CLIPS) expect(anims.has(c), `${p} lacks ${c}`).toBe(true)
          if (side.lite?.file && typeof side.lite.build === 'string' && p.endsWith(side.lite.file)) expect(side.lite.build).toBe(sha10(p))
        }
      })
    })
  }
})

describe('the registry helpers', () => {
  it('build tags: the pipeline short hash, never the old statistics object', () => {
    expect(buildTagOf({ build: '3f9a0c11be' })).toBe('3f9a0c11be')
    expect(buildTagOf({ build: { cards: { total: 2199 } } })).toBeNull()
    expect(buildTagOf(null)).toBeNull()
    expect(buildTagOf({ build: 'bad tag with spaces' })).toBeNull()
  })

  it('versioned model URLs', () => {
    expect(versionedUrl('/wildsong-ranch/models/monsters-ultra/puddlepup.glb', 'abc123')).toBe('/wildsong-ranch/models/monsters-ultra/puddlepup.glb?v=abc123')
    expect(versionedUrl('/x.glb?a=1', 'b')).toBe('/x.glb?a=1&v=b')
    expect(versionedUrl('/x.glb', null)).toBe('/x.glb')
  })

  it('reads the fighters from ?a=&b=, Puddlepup for anything else', () => {
    expect(looksFromQuery('')).toEqual(['puddlepup', 'puddlepup'])
    expect(looksFromQuery('?a=nothing&b=PUDDLEPUP')).toEqual(['puddlepup', 'puddlepup'])
    const other = ULTRA_IDS[ULTRA_IDS.length - 1]!
    expect(looksFromQuery(`?a=${other}&b=puddlepup`)).toEqual([other, 'puddlepup'])
    expect(isUltraId('puddlepup')).toBe(true)
    expect(isUltraId('not-a-breed')).toBe(false)
    expect(isUltraId(null)).toBe(false)
    expect(isUltraId('toString')).toBe(false)
  })

  it('a monster shows its grown look when it has grown and the registry has one, else its breed', () => {
    expect(ultraIdFor('puddlepup', false)).toBe('puddlepup')
    expect(ultraIdFor('puddlepup', true)).toBe('puddlepup')
    expect(ultraIdFor('frostlance', false)).toBe(isUltraId('frostlance') ? 'frostlance' : null)
    for (const id of ULTRA_IDS) {
      const look = ULTRA_LOOKS[id]!
      if (look.stage === 'grown') expect(ultraIdFor(look.breed, true)).toBe(id)
    }
  })

  it('a variant shows only on its own breed', () => {
    expect(ultraVariant('puddlepup', 'songheart-puddlepup')).toBe('songheart-puddlepup')
    expect(ultraVariant('puddlepup', 'town-crier-tumblefox')).toBeNull()
    expect(ultraVariant('puddlepup', null)).toBeNull()
  })
})

describe('Ultra parts (tools/art/ultra.ts names)', () => {
  const variants = { 'town-crier-tumblefox': { meshes: ['lo_props_town-crier'] }, 'glitch-tumblefox': {} }

  it('gives every part its film material, any part may be missing, props are body without sheen', () => {
    const meshes = { lo_body: 'body', lo_eyes: 'eye', lo_fins: 'fin', lo_cards: 'card', lo_tuft: 'lock' }
    expect(partKind('lo_body', meshes)).toBe('body')
    expect(partKind('lo_body001', meshes)).toBe('body')
    expect(partKind('lo_cards', meshes)).toBe('card')
    expect(partKind('lo_eyes', meshes)).toBe('eye')
    expect(partKind('lo_tuft', {})).toBe('lock')
    expect(partKind('lo_paw')).toBe('body')
    expect(partKind('lo_props')).toBe('prop')
    expect(partKind('lo_props_town-crier', { ...meshes, 'lo_props_town-crier': 'prop' })).toBe('prop')
    expect(partKind('lo_props_town-crier')).toBe('prop')
    expect(partKind('lo_mane')).toBe('body')
    expect(partKind('Armature')).toBeNull()
  })

  it('reads a glow entry: a strength in range, a #rrggbb tint (linear) or none; anything else is no glow', () => {
    const max = ART.ultra.film.glow.maxStrength
    expect(glowOf({ glow: { strength: 2, tint: null } }, max)).toEqual({ strength: 2, tint: null })
    const t = glowOf({ glow: { strength: 1.5, tint: '#ffffff' } }, max)!
    expect(t.tint).toEqual([1, 1, 1])
    expect(glowOf({ glow: { strength: 1, tint: '#808080' } }, max)!.tint![0]).toBeCloseTo(0.2159, 3)
    expect(glowOf({}, max)).toBeNull()
    expect(glowOf({ glow: { strength: 0 } }, max)).toBeNull()
    expect(glowOf({ glow: { strength: max + 1 } }, max)).toBeNull()
    expect(glowOf({ glow: { strength: '2' } }, max)).toBeNull()
    expect(glowOf({ glow: { strength: 2, tint: 'gold' } }, max)).toBeNull()
    expect(softFinsOf({ fins: { soft: true } })).toBe(true)
    expect(normalScaleOf({ normal: { scale: 1.2 } })).toBe(1.2)
    expect(normalScaleOf({ normal: { scale: 2 } })).toBe(2)
    expect(normalScaleOf({})).toBeNull()
    expect(normalScaleOf({ normal: { scale: 0 } })).toBeNull()
    expect(normalScaleOf({ normal: { scale: 2.5 } })).toBeNull()
    expect(normalScaleOf({ normal: { scale: Number.NaN } })).toBeNull()
    expect(normalScaleOf({ normal: { scale: '1' } })).toBeNull()
    expect(cardEdgeFadeOf({ cards: { edgeFade: [0.1, 0.4] } })).toEqual([0.1, 0.4])
    expect(cardEdgeFadeOf({})).toBeNull()
    expect(cardEdgeFadeOf({ cards: { edgeFade: [0.5, 0.2] } })).toBeNull()
    expect(cardEdgeFadeOf({ cards: { edgeFade: [-0.1, 0.4] } })).toBeNull()
    expect(cardEdgeFadeOf({ cards: { edgeFade: [0.1, 1.2] } })).toBeNull()
    expect(cardEdgeFadeOf({ cards: { edgeFade: ['0.1', 0.4] } })).toBeNull()
    expect(softFinsOf({})).toBe(false)
  })

  it("a variant's own props show only with it; the always-worn props and the body always", () => {
    expect(variantOfPart('lo_props_town-crier', variants)).toBe('town-crier-tumblefox')
    expect(variantOfPart('lo_props_town-crier_1', variants)).toBe('town-crier-tumblefox')
    expect(variantOfPart('lo_props', variants)).toBeNull()
    expect(variantOfPart('lo_props_1', variants)).toBeNull()
    expect(variantOfPart('lo_props_glitch', variants)).toBe('glitch-tumblefox')
    expect(variantOfPart('lo_props_unknown', variants)).toBe('?')
    expect(partVisible('lo_props_town-crier', null, variants)).toBe(false)
    expect(partVisible('lo_props_town-crier', 'glitch-tumblefox', variants)).toBe(false)
    expect(partVisible('lo_props_town-crier', 'town-crier-tumblefox', variants)).toBe(true)
    expect(partVisible('lo_props_unknown', null, variants)).toBe(false)
    expect(partVisible('lo_props', null, variants)).toBe(true)
    expect(partVisible('lo_body', 'glitch-tumblefox', variants)).toBe(true)
    expect(partVisible('__variant_glitch-tumblefox', 'glitch-tumblefox', variants)).toBe(false)
  })
})
