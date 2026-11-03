import { FRIENDS } from '../data/tuning.ts'
import type { DrillId } from '../data/types.ts'
import { availability } from './aging.ts'
import { hasPerk } from './farm.ts'
import { autoRestReason } from './herd.ts'
import { findOwned } from './legacy.ts'
import { addCondition, type Monster } from './monster.ts'
import type { Friendship, GameState, Ranchmate } from './state.ts'

/**
 * GAME_DESIGN §6.11 friendships (v1.21.0): monsters at home together grow closer. Every pair at home gains
 * FRIENDS.perWeek a week (+ playBonus when either is a ranch-mate on Play, + campfireBonus with the Campfire Circle),
 * up to maxPoints. Tiers: Friends, Close, Best (FRIENDS.tiers). Small effects, nothing in battle: each monster at home
 * loses a little stress by its best present friend's tier, and the star's training partner adds FRIENDS.buddyGain to
 * a good drill. Pure, and never touches the RNG; with fewer than two monsters at home nothing happens.
 */

/** 0 = getting to know each other; 1 Friends, 2 Close, 3 Best. */
export type FriendTier = 0 | 1 | 2 | 3

export function tierOf(points: number): FriendTier {
  let tier = 0
  for (const at of FRIENDS.tiers) if (points >= at) tier += 1
  return tier as FriendTier
}

/** The pair's ids, sorted (`a < b`), as the save keeps them. */
export function pairOf(x: string, y: string): { a: string; b: string } {
  return x < y ? { a: x, b: y } : { a: y, b: x }
}

export function friendshipOf(state: Pick<GameState, 'friendships'>, x: string, y: string): Friendship | null {
  const { a, b } = pairOf(x, y)
  return state.friendships.find((f) => f.a === a && f.b === b) ?? null
}

export function friendPoints(state: Pick<GameState, 'friendships'>, x: string, y: string): number {
  return friendshipOf(state, x, y)?.points ?? 0
}

/** Who is at home this week: the star (not away on a Journey or expedition, not missing, at the clinic or in a cocoon, life not ended), then every ranch-mate not away. */
export function atHome(state: GameState): { m: Monster; play: boolean }[] {
  const home: { m: Monster; play: boolean }[] = []
  const star = state.monster
  if (star && !state.ended && !state.journey && !state.expedition && !availability(star).locked) home.push({ m: star, play: false })
  for (const r of state.ranchmates) if (!availability(r.monster).locked) home.push({ m: r.monster, play: r.order.kind === 'play' })
  return home
}

/** A pair reached a new tier this week (Wren says so in the week summary). */
export interface FriendNews {
  aId: string
  bId: string
  a: string
  b: string
  tier: 1 | 2 | 3
}

/** The pair's record, made at 0 points when it is new (unless the save already keeps FRIENDS.maxPairs). */
function pairMut(state: GameState, x: string, y: string): Friendship | null {
  const found = friendshipOf(state, x, y)
  if (found) return found
  if (state.friendships.length >= FRIENDS.maxPairs) return null
  const made: Friendship = { ...pairOf(x, y), points: 0 }
  state.friendships.push(made)
  return made
}

/** The best tier among this monster's friends who are at home right now. */
function bestPresentTier(state: GameState, id: string, home: readonly { m: Monster }[]): FriendTier {
  let best: FriendTier = 0
  for (const h of home) if (h.m.id !== id) best = Math.max(best, tierOf(friendPoints(state, id, h.m.id))) as FriendTier
  return best
}

/**
 * The end of the week, after the herd's tick (week.ts): every pair at home grows closer, then each monster at home is
 * calmed by its best present friend (FRIENDS.stressByTier). Frozen monsters and Elders keep their points. Mutates
 * `state`; returns the tiers reached.
 */
export function friendsWeekMut(state: GameState): FriendNews[] {
  const home = atHome(state)
  if (home.length < 2) return []
  const base = FRIENDS.perWeek + (hasPerk(state, 'campfire') ? FRIENDS.campfireBonus : 0)
  const news: FriendNews[] = []
  for (let i = 0; i < home.length; i++) {
    for (let j = i + 1; j < home.length; j++) {
      const x = home[i]!
      const y = home[j]!
      const f = pairMut(state, x.m.id, y.m.id)
      if (!f) continue
      const before = tierOf(f.points)
      f.points = Math.min(FRIENDS.maxPoints, f.points + base + (x.play || y.play ? FRIENDS.playBonus : 0))
      const after = tierOf(f.points)
      if (after > before) news.push({ aId: x.m.id, bId: y.m.id, a: x.m.name, b: y.m.name, tier: after as 1 | 2 | 3 })
    }
  }
  for (const h of home) {
    const tier = bestPresentTier(state, h.m.id, home)
    const calm = tier > 0 ? (FRIENDS.stressByTier[tier - 1] ?? 0) : 0
    if (calm > 0 && h.m.stress > 0) h.m.stress = addCondition(h.m.stress, -calm)
  }
  return news
}

/**
 * The star's training partner for this drill: a ranch-mate at home whose standing order is the same drill (and that
 * will really train this week, not rest by itself), Friends or better with the star. The closest friend wins; ties go
 * to the first pen. Null when there is none.
 */
export function trainingPartner(state: GameState, drill: DrillId): Ranchmate | null {
  const star = state.monster
  if (!star) return null
  let best: Ranchmate | null = null
  let bestPoints = -1
  for (const r of state.ranchmates) {
    if (r.order.kind !== 'drill' || r.order.drill !== drill) continue
    if (availability(r.monster).locked || autoRestReason(state, r.monster, r.order)) continue
    const points = friendPoints(state, star.id, r.monster.id)
    if (tierOf(points) < 1 || points <= bestPoints) continue
    best = r
    bestPoints = points
  }
  return best
}

/** One monster's friendships for the Monster Card: owned friends with any points, closest first. */
export function friendsOf(state: GameState, id: string): { id: string; name: string; points: number; tier: FriendTier }[] {
  const out: { id: string; name: string; points: number; tier: FriendTier }[] = []
  for (const f of state.friendships) {
    if (f.points <= 0 || (f.a !== id && f.b !== id)) continue
    const other = findOwned(state, f.a === id ? f.b : f.a)
    if (other) out.push({ id: other.monster.id, name: other.monster.name, points: f.points, tier: tierOf(f.points) })
  }
  return out.sort((x, y) => y.points - x.points || (x.name < y.name ? -1 : x.name > y.name ? 1 : 0))
}
