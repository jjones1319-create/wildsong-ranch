import { describe, expect, it } from 'vitest'
import { duelPaced, duelWindup } from '../../core/battle/pace.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { ART, BATTLE } from '../../data/tuning.ts'
import { isRangedTech } from '../duel/fxRecipe.ts'
import { canFly, FLY_CLIPS, resolveClipName } from './clips.ts'
import { breathPlan, flightPlan, flyKindOf, withPeak, lapAllowed, lapDelayMs, lapPlan, lapPose, flyTimes, framedLift, hopPlan, landingPlan, landNow, liftAt, mouthShare, shadowAt, takeoffPlan, type FlightPlan, type FlyTimes } from './flight.ts'

const FL = ART.duel.flight
/** Clips as the builder made them (Nov 12): take-off, a wingbeat and the landing 0.8 s, the cast 1.6 s (two beats). */
const LENGTHS = { fly_takeoff: 0.8, fly: 0.8, fly_cast: 1.6, fly_land: 0.8 }
const TIMES: FlyTimes = flyTimes((c) => LENGTHS[c])

/** A Hearthwing technique as Battle 3D times it at this speed. */
function timed(id: string, speed: number) {
  const t = TECHNIQUE_BY_ID[id]!
  const toSec = (ticks: number) => ticks / BATTLE.ticksPerSecond / speed
  return {
    tech: t,
    windupSec: toSec(duelWindup(t.family)),
    busySec: toSec(duelPaced(t.anim)),
    hits: t.effect?.kind === 'multi' ? t.effect.hits : 1,
  }
}

function plan(id: string, speed = 1, heightM = 1, now = 10): FlightPlan | null {
  const m = timed(id, speed)
  return flightPlan({ now, windupSec: m.windupSec, busySec: m.busySec, hits: m.hits, speed, heightM, times: TIMES })
}

describe('which looks fly', () => {
  it('needs all four flying clips; a look without them (every shipped one today) keeps its ground moves', () => {
    expect(canFly((c) => (FLY_CLIPS as readonly string[]).includes(c))).toBe(true)
    expect(canFly((c) => c !== 'fly_land' && (FLY_CLIPS as readonly string[]).includes(c))).toBe(false)
    expect(canFly(() => false)).toBe(false)
  })

  it('never falls a flying clip back onto a ground clip (no flight means the old moves, not a stand-in)', () => {
    for (const c of FLY_CLIPS) expect(resolveClipName((n) => n === 'cast' || n === 'hop' || n === 'battle_idle', c)).toBeNull()
  })

  it("flies Hearthwing's Special and Signature, hops its Wingbeat Jab, and leaves its other moves on the floor", () => {
    const kind = (id: string) => {
      const t = TECHNIQUE_BY_ID[id]!
      return flyKindOf(t.family, isRangedTech(t))
    }
    expect(kind('hearthwing.bellows-blaze')).toBe('flight')
    expect(kind('hearthwing.hearthfire-torrent')).toBe('flight')
    expect(kind('hearthwing.wingbeat-jab')).toBe('hop')
    const others = Object.values(TECHNIQUE_BY_ID).filter((t) => t.breed === 'hearthwing' && !/bellows-blaze|hearthfire-torrent|wingbeat-jab/.test(t.id))
    expect(others.length).toBeGreaterThan(0)
    for (const t of others) expect(kind(t.id)).toBeNull()
  })
})

describe('flyTimes', () => {
  it("reads the leap, release and land markers, else the tuning shares", () => {
    expect(TIMES.liftoffSec).toBeCloseTo((0.8 * FL.liftoffPct) / 100)
    expect(TIMES.releaseSec).toBeCloseTo((1.6 * FL.releasePct) / 100)
    expect(TIMES.touchSec).toBeCloseTo((0.8 * FL.touchPct) / 100)
    const marked = flyTimes(() => 1, {
      fly_takeoff: { markers: [{ name: 'leap', t: 0.2 }] },
      fly_cast: { markers: [{ name: 'release', t: 0.7 }] },
      fly_land: { markers: [{ name: 'land', t: 0.5 }] },
    })
    expect(marked).toMatchObject({ liftoffSec: 0.2, releaseSec: 0.7, touchSec: 0.5 })
  })
})

describe('the height over a flying move', () => {
  for (const id of ['hearthwing.bellows-blaze', 'hearthwing.hearthfire-torrent']) {
    for (const speed of [1, 2]) {
      it(`${id} at ×${speed}: up in the wind-up, hovering through the hits, down by the time it can act`, () => {
        const m = timed(id, speed)
        const now = 10
        const p = plan(id, speed)!
        expect(p).not.toBeNull()
        const lands = now + m.windupSec
        const lastHit = lands + (Math.min(m.hits, 4) - 1) * ART.duel.fx.hitGapSec
        // on the floor at the fire, off it during the wind-up, at the hover height by the end of the take-off
        expect(liftAt(p, now)).toBe(0)
        expect(p.liftOff).toBeLessThan(lands)
        expect(liftAt(p, p.top)).toBeCloseTo(p.peakM)
        expect(p.peakM).toBeGreaterThanOrEqual(1)
        expect(p.peakM).toBeLessThanOrEqual(1.5)
        // at ×1 the take-off fits the wind-up exactly, so it breathes from the hover height as the hit lands
        if (speed === 1) expect(p.top).toBeCloseTo(lands, 5)
        // the fire leaves the mouth well off the floor, before the landing, on the cast's release
        expect(p.release).not.toBeNull()
        const release = p.release!
        expect(release).toBeGreaterThan(p.liftOff)
        expect(release).toBeLessThanOrEqual(lands - FL.minBreathSec / speed + 1e-9)
        expect(liftAt(p, release)).toBeGreaterThan(p.peakM * 0.5)
        const cast = p.steps.find((s) => s.clip === 'fly_cast')!
        expect(cast.at + (TIMES.releaseSec - cast.offset) / cast.rate).toBeCloseTo(release, 6)
        expect(cast.at).toBeGreaterThanOrEqual(10)
        // hovering through every hit
        for (let t = Math.max(p.top, lands); t <= lastHit; t += 0.01) expect(liftAt(p, t)).toBeGreaterThan(p.peakM - p.bobM - 1e-9)
        expect(p.descend).toBeGreaterThan(lastHit)
        // back on the floor by the end of the recovery, and the plan ends then
        expect(p.touch).toBeLessThanOrEqual(p.end)
        expect(p.end).toBeCloseTo(now + m.busySec)
        expect(liftAt(p, p.touch)).toBe(0)
        expect(liftAt(p, p.end)).toBe(0)
        // the clips in order, none faster than maxRate × the speed
        expect(p.steps.map((s) => s.clip).filter((c) => c !== 'fly')).toEqual(['fly_takeoff', 'fly_cast', 'fly_land'])
        for (let i = 1; i < p.steps.length; i++) expect(p.steps[i]!.at).toBeGreaterThanOrEqual(p.steps[i - 1]!.at)
        for (const s of p.steps) expect(s.rate).toBeLessThanOrEqual(FL.maxRate * speed + 1e-9)
        expect(p.steps.find((s) => s.clip === 'fly_land')!.at).toBeCloseTo(p.descend)
      })
    }
  }

  it('is smooth: no jumps from frame to frame, rising then falling', () => {
    const p = plan('hearthwing.bellows-blaze')!
    let prev = 0
    for (let t = 10; t <= p.end + 0.05; t += 1 / 240) {
      const y = liftAt(p, t)
      expect(Math.abs(y - prev)).toBeLessThan(p.peakM * 0.06)
      if (t < p.top) expect(y).toBeGreaterThanOrEqual(prev - 1e-9)
      if (t > p.descend) expect(y).toBeLessThanOrEqual(prev + 1e-9)
      prev = y
    }
  })

  it('flies lower with the same timing when its cut needs it (withPeak)', () => {
    const p = plan('hearthwing.bellows-blaze', 1, 2)!
    const low = withPeak(p, 1.6)
    expect(low.peakM).toBe(1.6)
    for (const k of ['liftOff', 'top', 'release', 'descend', 'touch', 'end'] as const) expect(low[k]).toBe(p[k])
    expect(low.steps).toEqual(p.steps)
    expect(liftAt(low, low.top)).toBeCloseTo(1.6)
    for (let t = p.liftOff; t <= p.end; t += 0.05) expect(liftAt(low, t)).toBeCloseTo((liftAt(p, t) * 1.6) / p.peakM, 6)
  })

  it("is the monster's own size: a grown Hearthwing (2 m) flies twice as high", () => {
    expect(plan('hearthwing.bellows-blaze', 1, 2)!.peakM).toBeCloseTo(2 * plan('hearthwing.bellows-blaze', 1, 1)!.peakM)
  })

  it('stays on the floor at ×4 (too quick to read) and when the move is too short to fit a flight', () => {
    expect(plan('hearthwing.bellows-blaze', 4)).toBeNull()
    expect(flightPlan({ now: 0, windupSec: 0.27, busySec: 0.35, hits: 3, speed: 1, heightM: 1, times: TIMES })).toBeNull()
  })

  it('falls fast when KO’d in the air, and Skip lands it at once, from where it is', () => {
    const p = plan('hearthwing.bellows-blaze')!
    const t = p.top + 0.05
    const before = liftAt(p, t)
    const fall = landNow(p, t, FL.fallSec, 'fall')
    expect(liftAt(fall, t)).toBeCloseTo(before)
    expect(liftAt(fall, t + FL.fallSec / 2)).toBeGreaterThan(before / 2)
    expect(liftAt(fall, t + FL.fallSec)).toBe(0)
    expect(fall.end).toBeCloseTo(t + FL.fallSec)
    expect(fall.steps.every((s) => s.at <= t)).toBe(true)
    const settle = landNow(p, t, FL.settleSec, 'soft')
    expect(liftAt(settle, t + FL.settleSec)).toBe(0)
  })

  it('hops a melee jab: up as it leans in, at the top on the impact, down as it returns (its strike plays)', () => {
    const h = hopPlan({ start: 1, impact: 1.2, end: 1.54 }, 1)
    expect(liftAt(h, 1)).toBe(0)
    expect(liftAt(h, 1.2)).toBeCloseTo((1 * FL.hopPct) / 100)
    expect(liftAt(h, 1.54)).toBe(0)
    expect(h.steps).toEqual([])
  })
})

describe('the Gallery flight', () => {
  it('breathes in the air: the whole cast at its own pace, then the fly loop', () => {
    const up = takeoffPlan(0, TIMES, 1)
    const b = breathPlan(up, 3, TIMES)
    expect(b.steps.slice(-2)).toEqual([
      { clip: 'fly_cast', at: 3, rate: 1, loop: false, offset: 0 },
      { clip: 'fly', at: 3 + TIMES.castSec, rate: 1, loop: true, offset: 0 },
    ])
    expect(b.release).toBeCloseTo(3 + TIMES.releaseSec)
    expect(liftAt(b, 3.5)).toBeCloseTo(liftAt(up, 3.5))
  })

  it('takes off and hovers until told to land, then lands from where it is', () => {
    const up = takeoffPlan(0, TIMES, 1)
    expect(liftAt(up, 0)).toBe(0)
    expect(liftAt(up, TIMES.takeoffSec)).toBeCloseTo(up.peakM)
    expect(liftAt(up, 60)).toBeGreaterThan(up.peakM - up.bobM - 1e-9)
    expect(up.steps.map((s) => s.clip)).toEqual(['fly_takeoff', 'fly'])
    const down = landingPlan(up, 5, TIMES)
    expect(liftAt(down, 5)).toBeCloseTo(liftAt(up, 5))
    expect(liftAt(down, 5 + TIMES.touchSec)).toBe(0)
    expect(down.end).toBeCloseTo(5 + TIMES.landSec)
    expect(down.steps.at(-1)!.clip).toBe('fly_land')
  })
})

describe('the shadow, the effects and the cameras', () => {
  it('shrinks and fades the contact shadow with height, at most at fullAtPct', () => {
    expect(shadowAt(0, 1)).toEqual({ scale: 1, opacity: 1 })
    const mid = shadowAt(0.6, 1)
    expect(mid.scale).toBeLessThan(1)
    expect(mid.opacity).toBeLessThan(1)
    const full = shadowAt(10, 1)
    expect(full.scale).toBeCloseTo(1 - FL.shadow.shrinkPct / 100)
    expect(full.opacity).toBeCloseTo(1 - FL.shadow.fadePct / 100)
  })

  it('moves the effects to the mouth as it climbs, only in a flight', () => {
    const p = plan('hearthwing.bellows-blaze')!
    expect(mouthShare(p, 0)).toBe(0)
    expect(mouthShare(p, p.peakM)).toBe(1)
    expect(mouthShare(null, 1)).toBe(0)
    expect(mouthShare(hopPlan({ start: 0, impact: 0.2, end: 0.5 }, 1), 0.3)).toBe(0)
  })

  it('frames the hover height for the whole flight (the camera settles once)', () => {
    const p = plan('hearthwing.bellows-blaze')!
    expect(framedLift(p, 0)).toBe(p.peakM)
    expect(framedLift(null, 0)).toBe(0)
    expect(framedLift(hopPlan({ start: 0, impact: 0.2, end: 0.5 }, 1), 0.3)).toBe(0)
  })
})

describe("the ranch's lap", () => {
  const LAP = ART.ranch3d.flyLap

  it('takes off, flies one circle round behind its spot and back, and lands, its clips at their own pace', () => {
    const p = lapPlan(100, TIMES, 1)
    expect(p.steps.map((s) => s.clip)).toEqual(['fly_takeoff', 'fly', 'fly_land'])
    expect(p.steps.every((s) => s.rate === 1)).toBe(true)
    expect(liftAt(p, 100)).toBe(0)
    expect(liftAt(p, p.top)).toBeCloseTo((LAP.peakPct / 100) * 1)
    expect(p.descend - p.top).toBeCloseTo(LAP.lapSec)
    expect(liftAt(p, p.touch)).toBe(0)
    expect(p.end).toBeCloseTo(p.descend + TIMES.landSec)
    // on its spot, facing front, at both ends; behind it (never toward the camera) on the way; one whole turn
    const R = 0.55
    for (const t of [100, p.liftOff, p.touch, p.end]) {
      const q = lapPose(p, t, R)
      expect(Math.abs(q.x)).toBeLessThan(1e-9)
      expect(Math.abs(q.z)).toBeLessThan(1e-9)
      expect(Math.abs(Math.sin(q.turn))).toBeLessThan(1e-9)
    }
    let prev = lapPose(p, p.liftOff, R)
    for (let t = p.liftOff; t <= p.touch; t += 0.02) {
      const q = lapPose(p, t, R)
      expect(q.z).toBeLessThanOrEqual(1e-9)
      expect(Math.hypot(q.x - prev.x, q.z - prev.z)).toBeLessThan(0.1)
      expect(q.turn).toBeGreaterThanOrEqual(prev.turn - 1e-9)
      prev = q
    }
    expect(lapPose(p, p.touch, R).turn).toBeCloseTo(2 * Math.PI)
    // half way round it is furthest behind its spot, along the circle (facing back the way it came, a half turn)
    const half = lapPose(p, (p.liftOff + p.touch) / 2, R)
    expect(half.z).toBeCloseTo(-2 * R)
    expect(half.turn).toBeCloseTo(Math.PI + Math.PI / 2)
  })

  it('comes about once a minute, and never with Reduce motion, hidden, busy, or for a look that does not fly', () => {
    expect(lapDelayMs(0)).toBe(LAP.minMs)
    expect(lapDelayMs(1)).toBe(LAP.maxMs)
    expect((lapDelayMs(0) + lapDelayMs(1)) / 2).toBeGreaterThanOrEqual(45_000)
    expect((lapDelayMs(0) + lapDelayMs(1)) / 2).toBeLessThanOrEqual(75_000)
    const ok = { flies: true, reduceMotion: false, hidden: false, busy: false }
    expect(lapAllowed(ok)).toBe(true)
    expect(lapAllowed({ ...ok, flies: false })).toBe(false)
    expect(lapAllowed({ ...ok, reduceMotion: true })).toBe(false)
    expect(lapAllowed({ ...ok, hidden: true })).toBe(false)
    expect(lapAllowed({ ...ok, busy: true })).toBe(false)
  })
})
