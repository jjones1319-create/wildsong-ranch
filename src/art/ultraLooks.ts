import type { BreedId } from '../data/types.ts'

/**
 * Art 2.1 Ultra (docs/ART_2_DETAIL.md): which breeds (and grown forms) have a high-detail model, for the Lab → 3D
 * Gallery and Battle 3D.
 * Normal play (the ranch, the Monster Card, the cups) still uses MODEL_LOOKS and the Classic drawings until a later
 * step. This file lives in the main chunk (no three), so the UI can list the breeds without loading the 3D code.
 *
 * Files (tools/art/ultra.ts ships them): `models/monsters-ultra/<breed>.glb` with its sidecar `<breed>.json`, and for
 * phones set to Lite effects a lighter `<breed>.lite.glb` (≤ 12k triangles, no fur cards, the same skeleton and clips;
 * the sidecar's `lite` entry names it). Puddlepup, the pilot, can still fall back to its Art 2.0 model.
 */

/**
 * A look's id: a breed id for its (young or only) form, or `<breed>-grown` for a grown form shipped as its own look
 * (Hearthwing's). The files are named by it: `<id>.glb`, `<id>.json`, `<id>.lite.glb`.
 */
export type UltraId = string

export interface UltraLook {
  id: UltraId
  breed: BreedId
  /** Which form it is (src/art/monster/render.ts formForStage: two-form breeds grow up at Prime). */
  stage: 'young' | 'grown'
  /** The model and its sidecar, under the base URL. */
  glb: string
  meta: string
  /**
   * The look's height in game units (its recipe's HEIGHT_UNITS, the sidecar's `heightUnits`; Puddlepup 150): every
   * model is built `heightUnits / 150` metres tall (tools/blender/monsters/breeds/RECIPE.md), so Battle 3D and the
   * Gallery's "beside Puddlepup" show each at its true size beside Puddlepup (ultraHeightPct).
   */
  heightUnits: number
  /** Secret variants (CONTENT §12) whose colours the file holds (a hidden `__variant_<id>` mesh each). */
  variants: readonly string[]
  /** Lite effects: the lighter copy (the sidecar's `lite.file` wins when it names one). */
  lite: { glb: string }
  /** When the Ultra files can't load at all: an older model to show instead (Puddlepup's Art 2.0 one), with its sidecar. */
  fallback?: { glb: string; meta: string }
}

const DIR = 'models/monsters-ultra/'

/** A shipped look, by the pipeline's file names: one line in ULTRA_LOOKS. */
function shipped(breed: BreedId, heightUnits: number, variants: readonly string[] = [], stage: 'young' | 'grown' = 'young'): UltraLook {
  const id = stage === 'grown' ? `${breed}-grown` : breed
  return {
    id,
    breed,
    stage,
    glb: `${DIR}${id}.glb`,
    meta: `${DIR}${id}.json`,
    heightUnits,
    variants,
    lite: { glb: `${DIR}${id}.lite.glb` },
  }
}

/**
 * The registry, in the order the Gallery and the Battle 3D chips list it (Puddlepup first). A look appears here only
 * once its files are in public/models/monsters-ultra/ (src/art/ultraLooks.test.ts checks them, their clips and budgets).
 *
 * To add a look once tools/art/ultra.ts has shipped it: one line, `<id>: shipped('<breed>', <HEIGHT_UNITS>,
 * [<its variants>])` (a grown form: `'<breed>-grown': shipped('<breed>', <HEIGHT_UNITS>, [], 'grown')`), with the
 * sidecar's heightUnits and the variants it lists; then run the test.
 */
export const ULTRA_LOOKS: Readonly<Record<UltraId, UltraLook>> = {
  puddlepup: {
    ...shipped('puddlepup', 150, ['songheart-puddlepup']),
    fallback: { glb: 'models/monsters/puddlepup.glb', meta: 'models/monsters/puddlepup.json' },
  },
  // the first batch (P3, shipped Nov 7)
  tumblefox: shipped('tumblefox', 135, ['town-crier-tumblefox', 'glitch-tumblefox']),
  cinderlynx: shipped('cinderlynx', 165, ['bonfire-cinderlynx']),
  starhowl: shipped('starhowl', 195),
  nimbusheep: shipped('nimbusheep', 165, ['stormcrown-nimbusheep']),
  rammerjack: shipped('rammerjack', 195),
  // the second batch (B2, Nov 7–8)
  stripeneck: shipped('stripeneck', 300, ['ezgi-stripeneck']),
  cobblemaw: shipped('cobblemaw', 225, ['granite-cobblemaw']),
  petalphant: shipped('petalphant', 210),
  hearthwing: shipped('hearthwing', 150),
  'hearthwing-grown': shipped('hearthwing', 300, [], 'grown'),
}

/** How tall a look stands beside Puddlepup, in percent (Puddlepup 100). */
export function ultraHeightPct(look: UltraLook): number {
  return (look.heightUnits * 100) / (ULTRA_LOOKS.puddlepup?.heightUnits ?? 150)
}

/** The registry's looks, Puddlepup first. */
export const ULTRA_IDS: readonly UltraId[] = Object.keys(ULTRA_LOOKS)

export function isUltraId(id: string | null | undefined): id is UltraId {
  return !!id && Object.prototype.hasOwnProperty.call(ULTRA_LOOKS, id)
}

export function ultraLook(id: UltraId): UltraLook | null {
  return isUltraId(id) ? ULTRA_LOOKS[id]! : null
}

/** The look a monster of this breed shows in its form (grown when `grown` and the breed has a grown look), or null. */
export function ultraIdFor(breed: BreedId, grown: boolean): UltraId | null {
  if (grown && isUltraId(`${breed}-grown`)) return `${breed}-grown`
  return isUltraId(breed) ? breed : null
}

/** The variant to show, if this look's file holds it; otherwise the look's own colours (null). */
export function ultraVariant(id: UltraId, variant: string | null | undefined): string | null {
  const look = ultraLook(id)
  return look && variant && look.variants.includes(variant) ? variant : null
}

/**
 * The tag a sidecar gives its model's build: a short hash of the `.glb` (the pipeline's `build` field). Older sidecars
 * used `build` for the build's statistics (an object), which is not a tag; a missing or odd one gives null.
 */
export function buildTagOf(sidecar: unknown): string | null {
  if (!sidecar || typeof sidecar !== 'object') return null
  const s = sidecar as Record<string, unknown>
  for (const v of [s.build, s.buildHash, s.hash, (s.build as Record<string, unknown> | null)?.hash]) {
    if (typeof v === 'string' && /^[\w.-]{1,64}$/.test(v)) return v
  }
  return null
}

/**
 * A model's URL with its build tag, so a phone that cached the old model fetches the re-shipped one (the art cache is
 * cache-first by URL; the sidecar itself is fetched network-first, see vite.config.ts).
 */
export function versionedUrl(url: string, build: string | null): string {
  if (!build) return url
  return `${url}${url.includes('?') ? '&' : '?'}v=${encodeURIComponent(build)}`
}

/** The fighters' looks from a page's query (`?a=<look>&b=<look>`, e.g. `hearthwing-grown`), each defaulting to Puddlepup. */
export function looksFromQuery(search: string): [UltraId, UltraId] {
  const q = new URLSearchParams(search)
  const pick = (k: string): UltraId => {
    const v = q.get(k)?.trim().toLowerCase()
    return isUltraId(v) ? v : 'puddlepup'
  }
  return [pick('a'), pick('b')]
}
