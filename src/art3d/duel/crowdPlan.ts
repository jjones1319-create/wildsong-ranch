import { BREED_IDS, type BreedId } from '../../data/types.ts'
import { ART } from '../../data/tuning.ts'

const CROWD = ART.duel.crowd

/**
 * docs/BATTLE_3D.md §8: who sits where in the Guild arena's stands, and how a cheer travels. Pure (no three, no DOM):
 * every choice is a hash of the seed and the seat, so the same Fame always gives the same crowd, and a higher Fame only
 * adds people (nobody already seated moves or changes).
 */

export type Tuning = typeof CROWD

/** One spot from the arena's guild.json (glTF frame, metres; the person faces (sin yaw, 0, cos yaw)). */
export interface Seat {
  p: [number, number, number]
  yaw: number
  row: number
  section: string
  kind: 'seat' | 'ground' | 'stand'
  lite: boolean
}

export type CheerKind = 'small' | 'big' | 'huge' | 'ovation'

export interface Occupant {
  /** Index into the arena's seats. */
  seat: number
  what: 'person' | 'cutout'
  x: number
  y: number
  z: number
  yaw: number
  /** Around the ring (radians, atan2(x, z)) and the distance from the centre: for the cheer's ripple. */
  angle: number
  radius: number
  pose: 'sit' | 'stand'
  kid: boolean
  /** Height and width multipliers (1 = a base adult). */
  height: number
  width: number
  skin: number
  shirt: number
  hair: number
  hat: number
  headwear: 'hair' | 'hat' | 'none'
  scarf: number
  held: 'pennant' | 'foam' | null
  heldColour: number
  /** Idle rhythm: phase 0–1 and Hz. */
  phase: number
  hz: number
  /** The cut-out's breed (and whether its picture is mirrored). */
  breed: BreedId | null
  mirror: boolean
}

/** A small integer hash of (seed, a, b) → [0, 1): the crowd's only source of variety. */
export function hash01(seed: number, a: number, b: number): number {
  let h = Math.imul(seed ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(a + 0x632be5ab, 0xc2b2ae35) ^ Math.imul(b + 0x2545f491, 0x27d4eb2f)
  h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d)
  h = Math.imul(h ^ (h >>> 12), 0x297a2d39)
  h ^= h >>> 15
  return (h >>> 0) / 4294967296
}

/** The share of spots filled (0–1) at a Fame of 0–100. */
export function fillShare(fame: number, T: Tuning = CROWD): number {
  const f = Math.max(0, Math.min(100, Number.isFinite(fame) ? fame : 0))
  return (T.fillPct.fame0 + ((T.fillPct.fame100 - T.fillPct.fame0) * f) / 100) / 100
}

/** How much a spot is wanted (bigger fills first): good stands and front rows, plus a seeded random share. */
export function preference(s: Seat, index: number, seed: number, T: Tuning = CROWD): number {
  const P = T.prefer
  const base = s.kind === 'ground' ? P.ground : ((P as Record<string, number>)[s.section] ?? P.front)
  return base - P.perRow * Math.max(0, s.row) + P.jitter * hash01(seed, index, 1)
}

/** Spot indices (into `seats`) in fill order. */
export function fillOrder(seats: readonly Seat[], seed: number, T: Tuning = CROWD): number[] {
  return seats.map((s, i) => ({ i, w: preference(s, i, seed, T) })).sort((a, b) => b.w - a.w || a.i - b.i).map((x) => x.i)
}

const pick = (n: number, u: number) => Math.min(n - 1, Math.floor(u * n))

/** Everyone in the stands for this Fame: the first fillShare of the fill order, each with a look fixed by its seat. */
export function planCrowd(all: readonly Seat[], o: { fame: number; lite: boolean; seed: number }, T: Tuning = CROWD): Occupant[] {
  const ids = all.map((_, i) => i).filter((i) => !o.lite || all[i]!.lite)
  const seats = ids.map((i) => all[i]!)
  const order = fillOrder(seats, o.seed, T)
  const n = Math.round(fillShare(o.fame, T) * seats.length)
  // the breeds go round the cut-out seats in a seeded shuffle, so every breed shows before any repeats
  const breeds = [...BREED_IDS].sort((a, b) => hash01(o.seed, BREED_IDS.indexOf(a), 7) - hash01(o.seed, BREED_IDS.indexOf(b), 7))
  // cut-outs sit on the benches among the people (never in front of the stands, where they'd hide them)
  const cutSeats = ids.filter((i) => all[i]!.kind === 'seat' && hash01(o.seed, i, 2) * 100 < T.cutoutPct)
  const P = T.palette
  const L = T.looks
  const S = T.size
  return order.slice(0, n).sort((a, b) => a - b).map((k) => {
    const i = ids[k]!
    const s = all[i]!
    const h = (salt: number) => hash01(o.seed, i, salt)
    const cut = cutSeats.indexOf(i)
    const kid = s.kind === 'ground' || (s.kind === 'seat' && h(3) * 100 < T.kidPct)
    const look = h(5) * 100
    const heldU = h(10) * 100
    return {
      seat: i,
      what: cut >= 0 ? 'cutout' : 'person',
      x: s.p[0],
      y: s.p[1],
      z: s.p[2],
      yaw: s.yaw,
      angle: Math.atan2(s.p[0], s.p[2]),
      radius: Math.hypot(s.p[0], s.p[2]),
      pose: s.kind === 'seat' ? 'sit' : 'stand',
      kid,
      height: (kid ? S.kid / 100 : 1) * ((S.heightMin + (S.heightMax - S.heightMin) * h(4)) / 100),
      width: (S.widthMin + (S.widthMax - S.widthMin) * h(11)) / 100,
      skin: pick(P.skin.length, h(6)),
      shirt: pick(P.clothes.length, h(7)),
      hair: pick(P.hair.length, h(8)),
      hat: pick(P.hats.length, h(9)),
      headwear: look < L.hatPct ? 'hat' : look < L.hatPct + L.hairPct ? 'hair' : 'none',
      // Lite keeps the crowd plainer: no scarves, pennants or foam hands
      scarf: !o.lite && h(12) * 100 < L.scarfPct ? pick(P.accents.length, h(13)) : -1,
      held: o.lite ? null : heldU < L.pennantPct ? 'pennant' : heldU < L.pennantPct + L.foamPct ? 'foam' : null,
      heldColour: pick(P.accents.length, h(14)),
      phase: h(15),
      hz: T.idle.hzMin + (T.idle.hzMax - T.idle.hzMin) * h(16),
      breed: cut >= 0 ? breeds[cut % breeds.length]! : null,
      mirror: h(17) < 0.5,
    }
  })
}

/* ------------------------------------------------------------------------------------------------ cheers */

const smooth = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x))

/** A cheer's excitement (0–1 of its peak) `t` seconds after it reaches someone: rise, hold, fall. */
export function envelope(kind: CheerKind, t: number, T: Tuning = CROWD): number {
  const c = T.cheer[kind]
  if (t <= 0) return 0
  if (t < c.attack) return smooth(t / c.attack)
  if (t < c.attack + c.hold) return 1
  return 1 - smooth((t - c.attack - c.hold) / c.decay)
}

/** How long a cheer's whole envelope lasts, in seconds. */
export function cheerSeconds(kind: CheerKind, T: Tuning = CROWD): number {
  const c = T.cheer[kind]
  return c.attack + c.hold + c.decay
}

export interface Cheer {
  kind: CheerKind
  /** When it started (seconds of crowd time), from where round the ring (radians), and its index (for who joins). */
  at: number
  from: number
  id: number
}

/** When a cheer that started at angle `from` reaches someone at (angle, radius): the shorter way round, plus a lag. */
export function rippleDelay(from: number, angle: number, radius: number, lag: number, T: Tuning = CROWD): number {
  let d = Math.abs(angle - from) % (Math.PI * 2)
  if (d > Math.PI) d = Math.PI * 2 - d
  return (d * radius) / T.ripple.speedMps + lag * T.ripple.lagSec
}

/** When a cheer reaches someone (seconds of crowd time), or NaN if they sit this one out (their seat decides both). */
export function cheerStart(c: Cheer, o: Occupant, seed: number, T: Tuning = CROWD): number {
  if (hash01(seed, o.seat, 100 + c.id) * 100 >= T.cheer[c.kind].joinPct) return Number.NaN
  return c.at + rippleDelay(c.from, o.angle, o.radius, hash01(seed, o.seat, 200 + c.id), T)
}

/** The excitement (0–1) of a cheer that reached someone at `start` (NaN: not joining). */
export function cheerLevel(kind: CheerKind, start: number, now: number, T: Tuning = CROWD): number {
  return Number.isNaN(start) ? 0 : (envelope(kind, now - start, T) * T.cheer[kind].peak) / 100
}

/**
 * One occupant's excitement now (0–1) over every live cheer they join, and how much of it is the ovation (0–1, for
 * standing up). The crowd caches each cheer's start per person (cheerStart) and adds them up the same way.
 */
export function excitement(cheers: readonly Cheer[], now: number, o: Occupant, seed: number, T: Tuning = CROWD): { e: number; ovation: number } {
  let e = 0
  let ovation = 0
  for (const c of cheers) {
    const v = cheerLevel(c.kind, cheerStart(c, o, seed, T), now, T)
    if (v > e) e = v
    if (c.kind === 'ovation' && v > ovation) ovation = v
  }
  return { e, ovation }
}
