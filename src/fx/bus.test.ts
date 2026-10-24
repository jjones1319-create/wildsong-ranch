import { describe, expect, it } from 'vitest'
import type { BattleEvent } from '../core/battle/types.ts'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { CHEST_Y, FEET_Y, fxEventsFor, hitStrength, isHeavyHit, publishFx, subscribeFx, type FighterPose } from './bus.ts'

const poses: [FighterPose, FighterPose] = [
  { x: -230, maxHp: 200 },
  { x: 230, maxHp: 400 },
]

describe('fx bus: engine events → FxEvents (VISUAL_V1_EFFECTS §3)', () => {
  it('a melee fire is a lunge toward the other side with the technique element', () => {
    const [e] = fxEventsFor({ t: 1, kind: 'fire', side: 0, tech: 'cinderlynx.ember-swipe', cost: 13 }, poses)
    expect(e).toMatchObject({ kind: 'fire', side: 0, element: 'Fire', ranged: false, from: { x: -230, y: CHEST_Y }, to: { x: 230, y: CHEST_Y } })
  })

  it('a Mid or Far technique is ranged', () => {
    const [e] = fxEventsFor({ t: 1, kind: 'fire', side: 1, tech: 'frostlance.blizzard-lance', cost: 46 }, poses)
    expect(e).toMatchObject({ kind: 'fire', side: 1, element: 'Ice', ranged: true, from: { x: 230 }, to: { x: -230 } })
  })

  it('a hit lands on the target; a crit is its own kind; wither adds a second event', () => {
    const plain = fxEventsFor({ t: 1, kind: 'hit', side: 0, target: 1, tech: 'puddlepup.splash-nip', damage: 20, crit: false, wither: 0, hitNo: 1, of: 1 }, poses)
    expect(plain).toHaveLength(1)
    expect(plain[0]).toMatchObject({ kind: 'hit', side: 1, element: 'Water', to: { x: 230 }, crit: false })
    const crit = fxEventsFor({ t: 1, kind: 'hit', side: 0, target: 1, tech: 'puddlepup.soggy-cloud', damage: 60, crit: true, wither: 42, hitNo: 1, of: 1 }, poses)
    expect(crit.map((e) => e.kind)).toEqual(['crit', 'wither'])
    expect(crit[0]!.strength).toBeGreaterThanOrEqual(0.7)
  })

  it('maps the rest: miss, ko, special, push (not when blocked), dash, heal, distracted; ignores plan and end', () => {
    expect(fxEventsFor({ t: 1, kind: 'miss', side: 1, target: 0, tech: 'zipwisp.zigzag-bolt', hitNo: 1, of: 1 }, poses)[0]).toMatchObject({ kind: 'miss', side: 0, element: 'Lightning' })
    expect(fxEventsFor({ t: 1, kind: 'ko', side: 1 }, poses)[0]).toMatchObject({ kind: 'ko', side: 1, strength: 1 })
    expect(fxEventsFor({ t: 1, kind: 'special', side: 0, special: 'valor' }, poses)[0]).toMatchObject({ kind: 'special', element: 'Light' })
    expect(fxEventsFor({ t: 1, kind: 'push', side: 0, target: 1, blocked: true }, poses)).toEqual([])
    expect(fxEventsFor({ t: 1, kind: 'push', side: 0, target: 1, blocked: false }, poses)[0]).toMatchObject({ kind: 'push', side: 1, to: { y: FEET_Y } })
    expect(fxEventsFor({ t: 1, kind: 'dash', side: 0 }, poses)[0]).toMatchObject({ kind: 'dash', element: 'Wind' })
    expect(fxEventsFor({ t: 1, kind: 'heal', side: 0, amount: 30, why: 'tech' }, poses)[0]).toMatchObject({ kind: 'heal', element: 'Light', strength: 0.3 })
    expect(fxEventsFor({ t: 1, kind: 'distracted', side: 0 }, poses)[0]).toMatchObject({ kind: 'distract' })
    expect(fxEventsFor({ t: 1, kind: 'plan', side: 0, band: 2, mode: 'pressing' } as BattleEvent, poses)).toEqual([])
    expect(fxEventsFor({ t: 1, kind: 'end', outcome: { how: 'time', winner: null, hpPct: [500, 500], ticks: 1800 } }, poses)).toEqual([])
  })

  it('hit strength grows with the damage share and jumps for crits; heavy hits are 12 % of max HP', () => {
    expect(hitStrength(0, 200, false)).toBe(0)
    expect(hitStrength(24, 200, false)).toBeCloseTo(0.75)
    expect(hitStrength(80, 200, false)).toBe(1)
    expect(hitStrength(4, 200, true)).toBeGreaterThanOrEqual(0.7)
    expect(isHeavyHit(24, 200)).toBe(true)
    expect(isHeavyHit(23, 200)).toBe(false)
    expect(isHeavyHit(5, 0)).toBe(false)
  })

  it('an unknown technique falls back to Physical', () => {
    expect(TECHNIQUE_BY_ID['nope.nothing']).toBeUndefined()
    expect(fxEventsFor({ t: 1, kind: 'fire', side: 0, tech: 'nope.nothing', cost: 10 }, poses)[0]).toMatchObject({ element: 'Physical' })
  })

  it('publishes to every subscriber until it unsubscribes', () => {
    const got: string[] = []
    const off = subscribeFx((e) => got.push(e.kind))
    publishFx(fxEventsFor({ t: 1, kind: 'dash', side: 0 }, poses))
    off()
    publishFx(fxEventsFor({ t: 1, kind: 'dash', side: 0 }, poses))
    expect(got).toEqual(['dash'])
  })
})
