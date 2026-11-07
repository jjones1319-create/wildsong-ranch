import { pathOf, type TechPath } from '../../data/paths.ts'
import { ART } from '../../data/tuning.ts'
import type { Element, Technique } from '../../data/types.ts'
import { styleOf, type ProjectileShape } from '../../fx/elements.ts'

/**
 * docs/BATTLE_3D.md §7: what each technique looks like in Battle 3D. Pure data, no three.js: a technique in, a recipe
 * out. It reuses the classic battle's effect mapping so the 2-D and 3-D battles agree:
 * - the technique's **element** (CONTENT §3, `Technique.element`);
 * - the element's look from `src/fx/elements.ts` (its colour ramp, core, glow and smoke colours, and its projectile:
 *   orb, drop, lance, bolt, blade, boulder, leaf or note);
 * - the hit recipe of `src/fx/recipes.ts` per element (Water splashes, Earth throws debris and a ground ring,
 *   Lightning branches and flashes, Ice breaks into chunky shards and mist, Fire bursts and smokes, Wind scatters fast,
 *   Nature drifts, Light sparkles and glows, Dark pulls inward with mist, Sound rings and floats notes).
 * The **shape** comes from the rules' own data: the path (a sweep sends a wave across the floor), the family (the
 * size; Sharp slashes; Special and Signature are grand), and the effect (hits, knockback, drain, heal, stun).
 */

const F = ART.duel.fx

/** The cells of the effects' texture atlas (fxAtlas.ts draws them in this order, 4 × 4). */
export const CELL = { dot: 0, puff: 1, ring: 2, crescent: 3, shard: 4, leaf: 5, drop: 6, star: 7, streak: 8, crack: 9, note: 10, gust: 11, bolt: 12, rock: 13, orb: 14, flame: 15 } as const
export type Cell = (typeof CELL)[keyof typeof CELL]

/** An impact's look, one per element. */
export type FxMotif = 'embers' | 'splash' | 'shards' | 'crackle' | 'gust' | 'rubble' | 'leaves' | 'stars' | 'smoke' | 'notes' | 'thud'

export const MOTIF_OF: Readonly<Record<Element, FxMotif>> = {
  Fire: 'embers', Water: 'splash', Ice: 'shards', Lightning: 'crackle', Wind: 'gust', Earth: 'rubble',
  Nature: 'leaves', Light: 'stars', Dark: 'smoke', Sound: 'notes', Physical: 'thud',
}

/** The extra layer an impact draws with its burst (the second call of the 2-D hit recipe). */
export type FxExtra = 'flames' | 'ring' | 'mist' | 'bolts' | 'spiral' | 'crack' | 'whirl' | 'glow' | 'smoke' | 'rings' | 'dust'

export interface MotifLook {
  /** Burst particles: atlas cell; glowing (added light) or solid; speed (m/s); gravity (m/s², + falls); life (s); size (m). */
  cell: Cell
  glow: boolean
  speed: number
  gravity: number
  life: number
  sizeM: number
  /** Drawn stretched along their flight (drops, shards, sparks); spin (rad/s) for tumbling bits. */
  stretch: boolean
  spin: number
  /** Behind a projectile or a lunge, and along a sweep's wave front. */
  trail: Cell
  trailGlow: boolean
  trailGravity: number
  /** The burst gathers into the target instead of flying out (Dark: `inward` in the 2-D style). */
  inward: boolean
  /** The bits stream level (Wind): a burst flies out flat, a sweep's bits run on along its front. */
  flow?: boolean
  extra: FxExtra
}

const L = (l: MotifLook) => l

export const MOTIF_LOOKS: Readonly<Record<FxMotif, MotifLook>> = {
  embers: L({ cell: CELL.flame, glow: false, speed: 1.8, gravity: -1.4, life: 0.55, sizeM: 0.17, stretch: false, spin: 0, trail: CELL.flame, trailGlow: false, trailGravity: -1.2, inward: false, extra: 'flames' }),
  splash: L({ cell: CELL.drop, glow: false, speed: 2.4, gravity: 7, life: 0.6, sizeM: 0.13, stretch: true, spin: 0, trail: CELL.drop, trailGlow: false, trailGravity: 5, inward: false, extra: 'ring' }),
  shards: L({ cell: CELL.shard, glow: false, speed: 2.6, gravity: 5, life: 0.6, sizeM: 0.17, stretch: true, spin: 0, trail: CELL.star, trailGlow: false, trailGravity: 0.5, inward: false, extra: 'mist' }),
  crackle: L({ cell: CELL.bolt, glow: false, speed: 3.2, gravity: 0, life: 0.24, sizeM: 0.28, stretch: true, spin: 0, trail: CELL.streak, trailGlow: false, trailGravity: 0, inward: false, extra: 'bolts' }),
  gust: L({ cell: CELL.gust, glow: false, speed: 2.6, gravity: -0.3, life: 0.42, sizeM: 0.16, stretch: true, spin: 0, trail: CELL.gust, trailGlow: false, trailGravity: 0, inward: false, flow: true, extra: 'spiral' }),
  rubble: L({ cell: CELL.rock, glow: false, speed: 2.4, gravity: 9, life: 0.7, sizeM: 0.13, stretch: false, spin: 6, trail: CELL.puff, trailGlow: false, trailGravity: -0.2, inward: false, extra: 'crack' }),
  leaves: L({ cell: CELL.leaf, glow: false, speed: 1.5, gravity: 1.2, life: 0.9, sizeM: 0.16, stretch: false, spin: 7, trail: CELL.leaf, trailGlow: false, trailGravity: 0.6, inward: false, extra: 'whirl' }),
  stars: L({ cell: CELL.star, glow: false, speed: 2, gravity: -0.6, life: 0.6, sizeM: 0.17, stretch: false, spin: 3, trail: CELL.star, trailGlow: false, trailGravity: -0.4, inward: false, extra: 'glow' }),
  smoke: L({ cell: CELL.puff, glow: false, speed: 1.3, gravity: -0.4, life: 0.7, sizeM: 0.24, stretch: false, spin: 1, trail: CELL.puff, trailGlow: false, trailGravity: -0.3, inward: true, extra: 'smoke' }),
  notes: L({ cell: CELL.note, glow: false, speed: 1.1, gravity: -1, life: 0.8, sizeM: 0.17, stretch: false, spin: 0, trail: CELL.note, trailGlow: false, trailGravity: -0.6, inward: false, extra: 'rings' }),
  thud: L({ cell: CELL.streak, glow: false, speed: 2.8, gravity: 3, life: 0.28, sizeM: 0.15, stretch: true, spin: 0, trail: CELL.streak, trailGlow: false, trailGravity: 0, inward: false, extra: 'dust' }),
}

export interface AttackFxRecipe {
  tech: string
  element: Element
  motif: FxMotif
  look: MotifLook
  /** Colours (0xRRGGBB) from the 2-D element style: the ramp bright → dim, the core, the glow, the smoke. */
  ramp: readonly number[]
  core: number
  glow: number
  smoke: number
  /** A projectile (INT or range 3+, as the cast clip) or a melee lunge; a sweep also sends a wave across the floor. */
  ranged: boolean
  path: TechPath
  projectile: ProjectileShape
  /** Size of everything and the particle counts (%), by family. */
  sizePct: number
  /** Special and Signature: drawn-in motes, a ring at the release and a flash at the impact; a Signature gets the most. */
  grand: boolean
  signature: boolean
  /** Sharp: a slash arc across the target. */
  slash: boolean
  /** Impacts (a multi-hit's several smaller ones); knockback's shockwave; Wither and drain send wisps back; heal; stun. */
  hits: number
  shockwave: boolean
  drain: boolean
  heal: boolean
  stun: boolean
}

/** The same split as the 3-D attack clips: INT techniques and range 3+ are cast from afar; the rest strike. */
export function isRangedTech(t: Pick<Technique, 'type' | 'range'>): boolean {
  return t.type === 'INT' || t.range >= 3
}

export function attackFxFor(t: Technique): AttackFxRecipe {
  const motif = MOTIF_OF[t.element]
  const s = styleOf(t.element)
  const e = t.effect
  return {
    tech: t.id,
    element: t.element,
    motif,
    look: MOTIF_LOOKS[motif],
    ramp: s.ramp,
    core: s.core,
    glow: s.glow,
    smoke: s.smoke,
    ranged: isRangedTech(t),
    path: pathOf(t),
    projectile: s.projectile,
    sizePct: F.familyPct[t.family],
    grand: t.family === 'Special' || t.family === 'Signature',
    signature: t.family === 'Signature',
    slash: t.family === 'Sharp',
    hits: e?.kind === 'multi' ? e.hits : 1,
    shockwave: e?.kind === 'push',
    drain: t.family === 'Wither' || e?.kind === 'drain' || e?.kind === 'gutsSteal',
    heal: e?.kind === 'heal',
    stun: e?.kind === 'stun',
  }
}

export interface FxQuality {
  /** Share of the particles drawn (%). */
  particlePct: number
  /** Whether the grand moves flash. */
  flash: boolean
  /** Lifetimes (×) at this battle speed. */
  life: number
}

/** Lite and Reduce motion draw fewer particles and never flash; faster battle speeds shorten the effects. */
export function fxQuality(o: { lite: boolean; reduceMotion: boolean; speed: number }): FxQuality {
  const q = o.reduceMotion ? F.quality.reduced : o.lite ? F.quality.lite : F.quality.full
  const life = F.lifeBySpeed[o.speed >= 4 ? 2 : o.speed >= 2 ? 1 : 0]!
  return { particlePct: o.lite && o.reduceMotion ? Math.min(F.quality.lite.particlePct, q.particlePct) : q.particlePct, flash: q.flash, life }
}

/** How many particles: a base count, scaled by the family's size and the quality, never fewer than one. */
export function fxCount(base: number, r: Pick<AttackFxRecipe, 'sizePct'>, q: Pick<FxQuality, 'particlePct'>): number {
  return Math.max(1, Math.round((base * r.sizePct * q.particlePct) / 10_000))
}
