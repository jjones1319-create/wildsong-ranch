import type { BattleEvent, Side } from '../core/battle/types.ts'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { FX } from '../data/tuning.ts'
import type { Element } from '../data/types.ts'

/**
 * VISUAL_V1_EFFECTS §3: the bridge between the battle and the effects. The battle store turns engine events into
 * FxEvents with `fxEventsFor` (pure, tested) and publishes them; whichever arena is on screen subscribes.
 * V1 draws a default recipe per element for each event (recipes.ts); V2 adds per-technique recipes.
 */

export type FxEventKind = 'fire' | 'travel' | 'hit' | 'miss' | 'crit' | 'ko' | 'special' | 'push' | 'dash' | 'distract' | 'wither' | 'heal'

export interface FxPoint {
  x: number
  /** World y, negative is up (0 = floor). */
  y: number
}

export interface FxEvent {
  kind: FxEventKind
  side: Side
  techId?: string
  element: Element
  from: FxPoint
  to: FxPoint
  /** 0..1: how big the moment is (damage share, crit, heavy). */
  strength: number
  /** Melee (Close/Near) or ranged (Mid/Far) for 'fire'. */
  ranged?: boolean
  crit?: boolean
}

export interface FighterPose {
  /** Arena units. */
  x: number
  maxHp: number
  /** The technique being animated, if any (for hit events, which carry their own). */
  busyTech?: string | null
}

/** Height above the floor where projectiles and impacts land (about the chest), in world units (negative = up). */
export const CHEST_Y = -100
export const FEET_Y = -4

type Listener = (e: FxEvent) => void
const listeners = new Set<Listener>()

export function subscribeFx(fn: Listener): () => void {
  listeners.add(fn)
  return () => {
    listeners.delete(fn)
  }
}

export function publishFx(events: readonly FxEvent[]): void {
  if (events.length === 0) return
  for (const fn of listeners) for (const e of events) fn(e)
}

function elementOfTech(id: string | undefined): Element {
  return (id && TECHNIQUE_BY_ID[id]?.element) || 'Physical'
}

/** Damage as a share of max HP, mapped to 0..1 with heavyHitPct at about 0.75. */
export function hitStrength(damage: number, maxHp: number, crit: boolean): number {
  const pct = maxHp > 0 ? (damage / maxHp) * 100 : 0
  const base = Math.min(1, (pct / FX.heavyHitPct) * 0.75)
  return Math.min(1, crit ? Math.max(0.7, base + 0.25) : base)
}

export function isHeavyHit(damage: number, maxHp: number): boolean {
  return maxHp > 0 && (damage / maxHp) * 100 >= FX.heavyHitPct
}

/** The FxEvents one engine event produces, given both fighters' positions. */
export function fxEventsFor(e: BattleEvent, fighters: readonly [FighterPose, FighterPose]): FxEvent[] {
  const at = (side: Side, y = CHEST_Y): FxPoint => ({ x: fighters[side].x, y })
  const other = (side: Side): Side => (side === 0 ? 1 : 0)
  switch (e.kind) {
    case 'fire': {
      const tech = TECHNIQUE_BY_ID[e.tech]
      const ranged = (tech?.range ?? 1) >= 3
      return [{ kind: 'fire', side: e.side, techId: e.tech, element: elementOfTech(e.tech), from: at(e.side), to: at(other(e.side)), strength: tech ? Math.min(1, tech.cost / 60) : 0.3, ranged }]
    }
    case 'hit': {
      const target = fighters[e.target]
      const element = elementOfTech(e.tech)
      const strength = hitStrength(e.damage, target.maxHp, e.crit)
      const out: FxEvent[] = [{ kind: e.crit ? 'crit' : 'hit', side: e.target, techId: e.tech, element, from: at(e.side), to: at(e.target), strength, crit: e.crit }]
      if (e.wither > 0) out.push({ kind: 'wither', side: e.target, techId: e.tech, element, from: at(e.side), to: at(e.target), strength: Math.min(1, e.wither / 50) })
      return out
    }
    case 'miss':
      return [{ kind: 'miss', side: e.target, techId: e.tech, element: elementOfTech(e.tech), from: at(e.side), to: at(e.target), strength: 0.3 }]
    case 'ko':
      return [{ kind: 'ko', side: e.side, element: 'Physical', from: at(e.side), to: at(e.side), strength: 1 }]
    case 'special':
      return [{ kind: 'special', side: e.side, element: 'Light', from: at(e.side), to: at(e.side), strength: 0.8 }]
    case 'push':
      return e.blocked ? [] : [{ kind: 'push', side: e.target, element: 'Physical', from: at(e.side, FEET_Y), to: at(e.target, FEET_Y), strength: 0.6 }]
    case 'dash':
      return [{ kind: 'dash', side: e.side, element: 'Wind', from: at(e.side, FEET_Y), to: at(other(e.side), FEET_Y), strength: 0.5 }]
    case 'distracted':
      return [{ kind: 'distract', side: e.side, element: 'Nature', from: at(e.side), to: at(e.side), strength: 0.2 }]
    case 'heal':
      return [{ kind: 'heal', side: e.side, element: 'Light', from: at(e.side, FEET_Y), to: at(e.side), strength: Math.min(1, e.amount / 100) }]
    default:
      return []
  }
}
