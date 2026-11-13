import { ART } from '../../data/tuning.ts'
import type { FlyClip } from './clips.ts'

/**
 * Flight for a look whose file has the flying clips (ultra/clips.ts FLY_CLIPS; the owner, Nov 12: Hearthwing "should
 * fly in a special attack"). Pure timing, no three: when it leaves the floor, how high it is at any moment, which
 * flying clip plays when and how fast, and how its contact shadow shrinks. Picture only: the engine's timing is what it
 * was (it lands on the engine's landing tick and is back on the floor when it can act again).
 *
 * Times are stage seconds (Battle 3D's clock, already divided by the battle's speed).
 */

const FL = ART.duel.flight

/**
 * A look's flying clips: their lengths (s at rate 1), where the feet leave the floor (the take-off's leap), where the
 * fire leaves the mouth (the cast's release) and where the feet touch down (the landing's land), s into each clip.
 */
export interface FlyTimes {
  takeoffSec: number
  liftoffSec: number
  flySec: number
  castSec: number
  releaseSec: number
  landSec: number
  touchSec: number
}

type ClipMeta = { seconds?: number; markers?: { name: string; t: number }[] } | undefined

const markerAt = (c: ClipMeta, names: readonly string[]): number | null => {
  const m = c?.markers?.find((x) => names.includes(x.name))
  return m && Number.isFinite(m.t) ? m.t : null
}

/**
 * The flying clips' times: the lengths from the file (`seconds`), the moments from the sidecar's markers (`leap` in
 * fly_takeoff, `release` in fly_cast, `land` in fly_land), else liftoffPct, releasePct and touchPct.
 */
export function flyTimes(seconds: (clip: FlyClip) => number, clips?: Record<string, ClipMeta>): FlyTimes {
  const len = (c: FlyClip) => Math.max(0.05, seconds(c))
  const takeoffSec = len('fly_takeoff')
  const castSec = len('fly_cast')
  const landSec = len('fly_land')
  const lift = markerAt(clips?.fly_takeoff, ['leap', 'liftoff'])
  const release = markerAt(clips?.fly_cast, ['release'])
  const touch = markerAt(clips?.fly_land, ['land', 'touch'])
  return {
    takeoffSec,
    liftoffSec: Math.min(takeoffSec * 0.9, Math.max(0, lift ?? (takeoffSec * FL.liftoffPct) / 100)),
    flySec: len('fly'),
    castSec,
    releaseSec: Math.min(castSec * 0.95, Math.max(0, release ?? (castSec * FL.releasePct) / 100)),
    landSec,
    touchSec: Math.min(landSec, Math.max(0.01, touch ?? (landSec * FL.touchPct) / 100)),
  }
}

/** Whether a technique flies (a flight), hops as it lunges, or stays on the floor, for a look that can fly. */
export function flyKindOf(family: string, ranged: boolean): 'flight' | 'hop' | null {
  if (ranged && FL.families.includes(family)) return 'flight'
  if (!ranged && FL.hopFamilies.includes(family)) return 'hop'
  return null
}

/** One flying clip, from `at` (stage s), at `rate`, starting `offset` seconds into the clip. */
export interface FlyStep {
  clip: FlyClip
  at: number
  rate: number
  loop: boolean
  offset: number
}

/**
 * A flight (or a hop) laid out in time: off the floor at liftOff, up at `top`, hovering until `descend`, from `from`
 * metres down to the floor at `touch`; over at `end` (it can act again). The fire leaves its mouth at `release` (null
 * for a hop). `steps`: its clips (none for a hop: its own strike plays).
 */
export interface FlightPlan {
  kind: 'flight' | 'hop'
  liftOff: number
  top: number
  release: number | null
  descend: number
  touch: number
  end: number
  /** The hover height (feet off the floor, m), the bob below it and its period (one wingbeat). */
  peakM: number
  bobM: number
  beatSec: number
  /** The height the descent starts from (m). */
  from: number
  /** A soft landing (eases in and out), or a fall (speeds up to the floor). */
  ease: 'soft' | 'fall'
  steps: FlyStep[]
}

export interface FlightInput {
  /** The fire (stage s), its wind-up to the landing and the whole busy time (wind-up and recovery), stage s. */
  now: number
  windupSec: number
  busySec: number
  /** The hits it lands (a multi-hit's later ones follow a beat apart, as the effects show them). */
  hits: number
  /** The battle's speed (×1, ×2, ×4). */
  speed: number
  /** Its standing height (m). */
  heightM: number
  times: FlyTimes
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

/** The hover: the peak, dipping by the bob once a wingbeat (starting and ending each beat at rest, so no kinks). */
function hoverLift(p: FlightPlan, t: number): number {
  if (p.bobM <= 0 || p.beatSec <= 0) return p.peakM
  const k = (t - p.top) / p.beatSec
  return p.peakM - (p.bobM * (1 - Math.cos(2 * Math.PI * k))) / 2
}

/**
 * The flight for a ranged technique fired at `now`, inside the duel's own timing (a Special's wind-up is 0.27 s at
 * ×1): the take-off fills the wind-up (its leap starts the rise); breathAtPct of the way through the climb (so well
 * off the floor, and at least minBreathSec before the landing) the cast's release opens the jaw and the fire leaves
 * the mouth, arriving on the landing tick; it hovers through the hits as the cast plays out (then the fly loop if
 * there is time); the landing fills the rest of the recovery, so it is back on the floor when it can act again.
 * Null when it can't fit (or above maxSpeed): then it attacks from the floor as before.
 */
export function flightPlan(i: FlightInput): FlightPlan | null {
  if (i.speed > FL.maxSpeed || !(i.busySec > i.windupSec) || i.heightM <= 0) return null
  const T = i.times
  const kMax = FL.maxRate * i.speed
  const kMin = FL.minRate
  // the take-off fills the wind-up (as fast as kMax allows: a short wind-up is a quick leap)
  const rT = clamp(T.takeoffSec / Math.max(1e-3, i.windupSec), kMin, kMax)
  const top = i.now + T.takeoffSec / rT
  const liftOff = i.now + T.liftoffSec / rT
  const land = i.now + i.windupSec
  const release = clamp(liftOff + ((top - liftOff) * FL.breathAtPct) / 100, i.now, Math.max(i.now, land - FL.minBreathSec / i.speed))
  const lastHit = land + (Math.min(Math.max(1, i.hits), 4) - 1) * ART.duel.fx.hitGapSec
  const end = i.now + i.busySec
  // the landing ends the recovery: at landRate × its own pace (× the speed) when there is time, the hover taking the
  // rest; faster (up to kMax) when the hits leave less
  const room = end - (Math.max(top, lastHit) + FL.hoverMinSec / i.speed)
  const fastest = T.landSec / kMax
  if (room < fastest) return null
  const landDur = Math.min(room, T.landSec / (FL.landRate * i.speed))
  const descend = end - landDur
  const rL = T.landSec / landDur
  // the cast: its release on the plan's, the rest of it (back to level flight) played out by the descent; it cuts in
  // just before the release (castLeadSec, so the take-off's spring shows)
  const after = Math.max(0.05, T.castSec - T.releaseSec)
  const castRate = clamp(after / Math.max(1e-3, descend - release), kMin, kMax)
  const lead = Math.min(T.releaseSec / castRate, FL.castLeadSec / i.speed, release - i.now)
  const castAt = release - lead
  const castEnd = release + after / castRate
  const steps: FlyStep[] = [
    { clip: 'fly_takeoff', at: i.now, rate: rT, loop: false, offset: 0 },
    { clip: 'fly_cast', at: castAt, rate: castRate, loop: false, offset: Math.max(0, T.releaseSec - lead * castRate) },
  ]
  // the fly loop only when the cast ends with time to spare (not a rounding hair before the landing)
  if (castEnd < descend - FL.fadeSec / i.speed) steps.push({ clip: 'fly', at: castEnd, rate: i.speed, loop: true, offset: 0 })
  steps.push({ clip: 'fly_land', at: descend, rate: rL, loop: false, offset: 0 })
  const p: FlightPlan = {
    kind: 'flight',
    liftOff,
    top,
    release,
    descend,
    touch: descend + T.touchSec / rL,
    end,
    peakM: (i.heightM * FL.peakPct) / 100,
    bobM: (i.heightM * FL.bobPct) / 100,
    beatSec: T.flySec / i.speed,
    from: 0,
    ease: 'soft',
    steps,
  }
  p.from = hoverLift(p, descend)
  return p
}

/** A hop for a melee technique: up as it leans in, at its top on the impact, down as it returns (its strike plays). */
export function hopPlan(lunge: { start: number; impact: number; end: number }, heightM: number): FlightPlan {
  const peakM = (heightM * FL.hopPct) / 100
  const descend = Math.min(lunge.end, lunge.impact + ART.duel.attack.lungeHoldSec)
  return { kind: 'hop', liftOff: lunge.start, top: lunge.impact, release: null, descend, touch: lunge.end, end: lunge.end, peakM, bobM: 0, beatSec: 0, from: peakM, ease: 'soft', steps: [] }
}

/** How high its feet are off the floor (m) at `t`. */
export function liftAt(p: FlightPlan, t: number): number {
  if (t >= p.touch) return 0
  if (t >= p.descend) {
    const k = clamp((t - p.descend) / Math.max(1e-3, p.touch - p.descend), 0, 1)
    const e = p.ease === 'fall' ? k * k : k * k * (3 - 2 * k)
    return p.from * (1 - e)
  }
  if (t < p.liftOff) return 0
  if (t < p.top) {
    // a leap: fastest as the feet leave the floor, easing to the top
    const k = (t - p.liftOff) / Math.max(1e-3, p.top - p.liftOff)
    return p.peakM * (1 - (1 - k) * (1 - k))
  }
  return hoverLift(p, t)
}

/** The Gallery's take-off (its clips at their own pace): up, then hovering (the fly loop) until told to land. */
export function takeoffPlan(now: number, times: FlyTimes, heightM: number): FlightPlan {
  const top = now + times.takeoffSec
  const peakM = (heightM * FL.peakPct) / 100
  return {
    kind: 'flight',
    liftOff: now + times.liftoffSec,
    top,
    release: null,
    descend: Infinity,
    touch: Infinity,
    end: Infinity,
    peakM,
    bobM: (heightM * FL.bobPct) / 100,
    beatSec: times.flySec,
    from: peakM,
    ease: 'soft',
    steps: [
      { clip: 'fly_takeoff', at: now, rate: 1, loop: false, offset: 0 },
      { clip: 'fly', at: top, rate: 1, loop: true, offset: 0 },
    ],
  }
}

/** The Gallery's breath in the air: the whole cast at its own pace (its hover beats, the release), then the fly loop. */
export function breathPlan(p: FlightPlan, now: number, times: FlyTimes): FlightPlan {
  return {
    ...p,
    release: now + times.releaseSec,
    steps: [...p.steps.filter((s) => s.at <= now), { clip: 'fly_cast', at: now, rate: 1, loop: false, offset: 0 }, { clip: 'fly', at: now + times.castSec, rate: 1, loop: true, offset: 0 }],
  }
}

/** The Gallery's landing, from wherever it is now (the fly_land clip at its own pace); over when the clip ends. */
export function landingPlan(p: FlightPlan, now: number, times: FlyTimes): FlightPlan {
  const from = liftAt(p, now)
  return { ...p, top: Math.min(p.top, now), liftOff: Math.min(p.liftOff, now), descend: now, touch: now + times.touchSec, end: now + times.landSec, from, ease: 'soft', steps: [...p.steps.filter((s) => s.at <= now), { clip: 'fly_land', at: now, rate: 1, loop: false, offset: 0 }] }
}

/** The same flight at another hover height (its timing as it was): the climb, the hover, the bob and the descent scale. */
export function withPeak(p: FlightPlan, peakM: number): FlightPlan {
  const k = peakM / Math.max(1e-6, p.peakM)
  return { ...p, peakM, bobM: p.bobM * k, from: p.from * k }
}

/** Ends a plan early from `t`: down in `sec` (a fall when KO'd in the air, a quick landing on Skip), no more clips. */
export function landNow(p: FlightPlan, t: number, sec: number, ease: 'soft' | 'fall'): FlightPlan {
  if (t >= p.touch) return { ...p, end: Math.min(p.end, t), steps: p.steps.filter((s) => s.at <= t) }
  const from = liftAt(p, t)
  const touch = t + Math.max(0.01, sec)
  return { ...p, liftOff: Math.min(p.liftOff, t), top: Math.min(p.top, t), descend: t, touch, end: touch, from, ease, steps: p.steps.filter((s) => s.at <= t) }
}

/**
 * Its soft contact shadow at this height: smaller and fainter the higher it flies (shares of its size and opacity on
 * the floor), at their least from fullAtPct of its height up.
 */
export function shadowAt(liftM: number, heightM: number): { scale: number; opacity: number } {
  const S = FL.shadow
  const k = clamp(liftM / Math.max(1e-3, (heightM * S.fullAtPct) / 100), 0, 1)
  return { scale: 1 - (k * S.shrinkPct) / 100, opacity: 1 - (k * S.fadePct) / 100 }
}

/** How far the effects' source has moved from its chest to its mouth (0–1): all the way once mouthBlendPct up. */
export function mouthShare(p: FlightPlan | null, liftM: number): number {
  if (!p || p.kind !== 'flight') return 0
  return clamp(liftM / Math.max(1e-3, (p.peakM * FL.mouthBlendPct) / 100), 0, 1)
}

/** The height a camera frames it at: the hover's for a whole flight (so the camera settles once); a hop moves no camera. */
export function framedLift(p: FlightPlan | null, liftM: number): number {
  return p && p.kind === 'flight' ? Math.max(liftM, p.peakM) : 0
}

/* ---------------------------------------------------------------------------------------------- the ranch's lap */

const LAP = ART.ranch3d.flyLap

/**
 * The ranch's flight (the owner, Nov 12: Hearthwing "should fly … in the ranch"): now and then it takes off, flies one
 * circle round behind its spot and back, and lands, its clips at their own pace. Lower than a battle flight (the box
 * has little headroom): peakPct of its height.
 */
export function lapPlan(now: number, times: FlyTimes, heightM: number): FlightPlan {
  const top = now + times.takeoffSec
  const descend = top + LAP.lapSec
  const peakM = (heightM * LAP.peakPct) / 100
  const p: FlightPlan = {
    kind: 'flight',
    liftOff: now + times.liftoffSec,
    top,
    release: null,
    descend,
    touch: descend + times.touchSec,
    end: descend + times.landSec,
    peakM,
    bobM: (heightM * FL.bobPct) / 100,
    beatSec: times.flySec,
    from: peakM,
    ease: 'soft',
    steps: [
      { clip: 'fly_takeoff', at: now, rate: 1, loop: false, offset: 0 },
      { clip: 'fly', at: top, rate: 1, loop: true, offset: 0 },
      { clip: 'fly_land', at: descend, rate: 1, loop: false, offset: 0 },
    ],
  }
  p.from = hoverLift(p, descend)
  return p
}

/**
 * Where the lap has carried it at `t`, from its spot (m, in its own frame: x to its side, z toward the camera, so a
 * negative z is behind its spot), which way it is turned from its rest heading (radians: one full turn over the lap,
 * along the circle in the middle, facing front at both ends) and how far round it is (0–1). The circle starts as it
 * leaves the floor and ends as it touches down.
 */
export function lapPose(p: FlightPlan, t: number, radiusM: number): { x: number; z: number; turn: number; k: number } {
  const k = clamp((t - p.liftOff) / Math.max(1e-3, p.touch - p.liftOff), 0, 1)
  const e = k * k * (3 - 2 * k)
  const th = 2 * Math.PI * e
  // along the circle in the middle of the lap (the tangent is a quarter turn ahead), facing front at both ends
  const w = Math.sin(Math.PI * k)
  return { x: radiusM * Math.sin(th), z: -radiusM * (1 - Math.cos(th)), turn: th + (Math.PI / 2) * w * w, k }
}

/** How long until the next lap (ms) from a roll in 0–1: minMs to maxMs (about once a minute while you watch). */
export function lapDelayMs(roll: number): number {
  return LAP.minMs + clamp(roll, 0, 1) * (LAP.maxMs - LAP.minMs)
}

/** Whether a lap may start now: the look flies, no Reduce motion, the page is shown and nothing else is playing. */
export function lapAllowed(o: { flies: boolean; reduceMotion: boolean; hidden: boolean; busy: boolean }): boolean {
  return o.flies && !o.reduceMotion && !o.hidden && !o.busy
}
