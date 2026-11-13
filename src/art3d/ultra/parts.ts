import type { Kind } from '../perf/content.ts'

/**
 * Art 2.1 Ultra parts (tools/art/ultra.ts names them): which film material each mesh gets, and which meshes belong to
 * one variant only. Plain functions (no three), so src/art/ultraLooks.test.ts checks them against the shipped files.
 *
 * Mesh names: lo_body, lo_eyes, lo_fins, lo_cards, lo_tuft (any may be missing), `lo_props` (always-worn rigid props:
 * horns, rope, a scarf) and `lo_props_<short>` (a variant's own props, e.g. `lo_props_town-crier`: the sidecar lists
 * them as `variants[vid].meshes`), plus the hidden `__variant_<vid>` holders of each variant's colour map.
 */

/** The sidecar's per-variant entries, as far as the parts go. */
export type VariantParts = Readonly<Record<string, { meshes?: readonly string[]; cards?: boolean } | undefined>>

/** GLTFLoader drops these characters from node names (PropertyBinding.sanitizeNodeName). */
export function sanitizeNodeName(name: string): string {
  return name.replace(/\s/g, '_').replace(/[[\]./:]/g, '')
}

const KIND_WORDS: Readonly<Record<string, Kind>> = {
  body: 'body', paw: 'body', eye: 'eye', eyes: 'eye', fin: 'fin', fins: 'fin', membrane: 'fin', card: 'card', cards: 'card',
  lock: 'lock', locks: 'lock', tuft: 'lock', prop: 'prop', props: 'prop', horn: 'prop', horns: 'prop',
}

/**
 * The film material kind of a part, by its mesh name: the sidecar's `meshes` map first (the longest name that starts
 * it), then the pipeline's names (lo_body, lo_cards, …; lo_props and lo_props_<short>, rigid horns, rope or a bell,
 * are props: the body's film material without the fur's sheen); any other `lo_` part is body. A breed may lack any
 * part (no fins, no tuft): nothing expects one. Null keeps the file's material.
 */
export function partKind(name: string, meshes?: Readonly<Record<string, string>>): Kind | null {
  let best = ''
  let kind: Kind | null = null
  for (const [mesh, k] of Object.entries(meshes ?? {})) {
    const key = sanitizeNodeName(mesh)
    if (key.length > best.length && name.startsWith(key) && KIND_WORDS[k]) {
      best = key
      kind = KIND_WORDS[k]!
    }
  }
  if (kind) return kind
  if (/^lo_card/.test(name)) return 'card'
  if (/^lo_(tuft|lock)/.test(name)) return 'lock'
  if (/^lo_eye/.test(name)) return 'eye'
  if (/^lo_(fin|membrane)/.test(name)) return 'fin'
  if (/^lo_prop/.test(name)) return 'prop'
  if (/^lo_/.test(name)) return 'body'
  return null
}

/** `name` is `base` itself, or a primitive or copy of it (GLTFLoader appends `_1`, `_2`, … to repeated names). */
function isNamed(name: string, base: string): boolean {
  return name === base || (name.startsWith(`${base}_`) && /^\d+$/.test(name.slice(base.length + 1)))
}

/**
 * The variant a mesh belongs to only, or null for a part every look wears. Listed in the sidecar's
 * `variants[vid].meshes` (by the raw name or GLTFLoader's), or named `lo_props_<short>` where the variant id starts
 * with `<short>` (`lo_props_town-crier` → `town-crier-tumblefox`). An unlisted `lo_props_<short>` whose variant isn't
 * known still belongs to "some variant" (`?`): hidden on the usual look.
 */
export function variantOfPart(name: string, variants?: VariantParts): string | null {
  for (const [vid, v] of Object.entries(variants ?? {})) {
    for (const m of v?.meshes ?? []) if (isNamed(name, m) || isNamed(name, sanitizeNodeName(m))) return vid
  }
  const own = /^lo_props_(.+)$/.exec(name)
  if (!own) return null
  // lo_props itself repeated (lo_props_1) is the always-worn set
  if (/^\d+$/.test(own[1]!)) return null
  const short = own[1]!.replace(/_\d+$/, '')
  for (const vid of Object.keys(variants ?? {})) if (vid === short || vid.startsWith(`${short}-`)) return vid
  return '?'
}

/**
 * Whether a variant hides the fur cards (a recipe's VARIANT_CARDS_OFF; the sidecar's `variants[vid].cards: false`):
 * Granite Cobblemaw is bare polished stone, and its moss cards read as fibres on it.
 */
export function variantCardsOff(active: string | null, variants?: VariantParts): boolean {
  return active !== null && variants?.[active]?.cards === false
}

/**
 * Whether a part shows for the active look (`active`: a variant id, or null for the breed's usual look): every
 * always-worn part does, except the fur cards on a variant that hides them; a variant's own props only with that
 * variant; the colour holders never.
 */
export function partVisible(name: string, active: string | null, variants?: VariantParts): boolean {
  if (name.startsWith('__variant_')) return false
  if (variantCardsOff(active, variants) && partKind(name) === 'card') return false
  const owner = variantOfPart(name, variants)
  return owner === null || owner === active
}

/** A sidecar's glow, ready for the film material: strength, and a linear-RGB tint or null for the base colour. */
export interface GlowSpec {
  strength: number
  tint: readonly [number, number, number] | null
}

/** sRGB (0–1) to linear, as three's colour management does for a hex colour. */
function linear(c: number): number {
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

/**
 * The sidecar's `glow: { strength, tint }` (tools/art/ultra.ts; present only when the breed glows; its mask is the
 * ORM map's alpha), or null: missing, a strength that isn't a number in (0, maxStrength], or a tint that isn't
 * `#rrggbb` (null tint = the part's own base colour).
 */
export function glowOf(sidecar: unknown, maxStrength: number): GlowSpec | null {
  const g = (sidecar as { glow?: unknown } | null)?.glow
  if (!g || typeof g !== 'object') return null
  const { strength, tint } = g as { strength?: unknown; tint?: unknown }
  if (typeof strength !== 'number' || !Number.isFinite(strength) || strength <= 0 || strength > maxStrength) return null
  if (tint === null || tint === undefined) return { strength, tint: null }
  const hex = typeof tint === 'string' ? /^#?([0-9a-f]{6})$/i.exec(tint.trim()) : null
  if (!hex) return null
  const n = parseInt(hex[1]!, 16)
  return { strength, tint: [linear(((n >> 16) & 255) / 255), linear(((n >> 8) & 255) / 255), linear((n & 255) / 255)] }
}

/** The sidecar's `fins: { soft: true }`: fins (the mane's fin locks) take received shadows instead of staying flat. */
export function softFinsOf(sidecar: unknown): boolean {
  const f = (sidecar as { fins?: { soft?: unknown } } | null)?.fins
  return f?.soft === true
}

/**
 * The sidecar's `cards: { edgeFade: [lo, hi] }` (a recipe's CARD_EDGE_FADE): where a look's fur cards fade in, in
 * 1 − |N·V| (0 = facing the camera, 1 = edge-on). A long mane wants a gentler fade (cards show more face-on) than short
 * fur at the outline. Null when absent or invalid (0 ≤ lo < hi ≤ 1): the film's default (film.cardEdgeFade).
 */
export function cardEdgeFadeOf(sidecar: unknown): readonly [number, number] | null {
  const f = (sidecar as { cards?: { edgeFade?: unknown } } | null)?.cards?.edgeFade
  if (!Array.isArray(f) || f.length !== 2) return null
  const [lo, hi] = f as unknown[]
  if (typeof lo !== 'number' || typeof hi !== 'number' || !Number.isFinite(lo) || !Number.isFinite(hi)) return null
  return lo >= 0 && hi <= 1 && lo < hi ? [lo, hi] : null
}

/**
 * The sidecar's `normal: { scale }` (a recipe's NORMAL_SCALE): how strongly a look's body and props show their normal
 * map (Hearthwing's scales want more relief than fur). Null when absent or invalid (finite, 0 < scale ≤ 2): the film's
 * default (film.normalScale).
 */
export function normalScaleOf(sidecar: unknown): number | null {
  const s = (sidecar as { normal?: { scale?: unknown } } | null)?.normal?.scale
  return typeof s === 'number' && Number.isFinite(s) && s > 0 && s <= 2 ? s : null
}

/**
 * The sidecar's `body: { sheen }` (a recipe's BODY_SHEEN): the body's fur sheen, instead of film.furSheen (a stone
 * breed wants none: on Cobblemaw's jaw, chest and legs it read as felt with a soft halo). Null when absent or invalid
 * (finite, 0 ≤ sheen ≤ 1): the film's default.
 */
export function bodySheenOf(sidecar: unknown): number | null {
  const s = (sidecar as { body?: { sheen?: unknown } } | null)?.body?.sheen
  return typeof s === 'number' && Number.isFinite(s) && s >= 0 && s <= 1 ? s : null
}

/**
 * Whether a variant ships its own ORM map (a recipe's VARIANT_ORM; the sidecar's `variants[vid].orm: true`): its own
 * roughness, clearcoat and glow mask, carried by its `__variant_<vid>` holder. Otherwise (and for the usual look) the
 * breed's shared ORM, exactly as before.
 */
export function variantHasOwnOrm(sidecar: unknown, variant: string | null): boolean {
  if (!variant) return false
  const v = (sidecar as { variants?: Record<string, { orm?: unknown } | undefined> } | null)?.variants?.[variant]
  return v?.orm === true
}

/**
 * Whether a variant's eyes differ from the usual look's (its `variants[vid].eyeColor` against the sidecar's
 * `palette.eye`). Its colour atlas then holds its own eye colours (a recipe's eye_material with the palette parameter),
 * so the eyes take that atlas too; otherwise they keep the usual look's, exactly as before.
 */
export function variantEyesDiffer(sidecar: unknown, variant: string | null): boolean {
  if (!variant) return false
  const s = sidecar as { palette?: { eye?: unknown }; variants?: Record<string, { eyeColor?: unknown } | undefined> } | null
  const own = s?.variants?.[variant]?.eyeColor
  const base = s?.palette?.eye
  return typeof own === 'string' && typeof base === 'string' && own.toLowerCase() !== base.toLowerCase()
}

/**
 * The glow for the look on show: a variant with its own ORM glows by its own `variants[vid].glow` (null: it doesn't
 * glow, even on a breed that does; missing: the breed's glow), as its ORM's alpha holds its own mask; any other look
 * glows by the breed's `glow`.
 */
export function glowFor(sidecar: unknown, variant: string | null, maxStrength: number): GlowSpec | null {
  if (variantHasOwnOrm(sidecar, variant)) {
    const v = (sidecar as { variants: Record<string, { glow?: unknown }> }).variants[variant!]!
    if ('glow' in v) return glowOf({ glow: v.glow }, maxStrength)
  }
  return glowOf(sidecar, maxStrength)
}
