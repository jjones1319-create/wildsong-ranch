import { describe, expect, it } from 'vitest'
import { BREED_IDS } from '../../data/types.ts'
import { cheerSeconds, envelope, excitement, fillOrder, fillShare, hash01, planCrowd, rippleDelay, type Cheer, type Seat } from './crowdPlan.ts'
import { armRot, m3, poseOf, rotYXZ } from './crowdPose.ts'
import { ART } from '../../data/tuning.ts'

const CROWD = ART.duel.crowd

/** A stand like the Guild arena's: three tiers of 40, a row of kids on the ground, and some standing folk. */
function seats(): Seat[] {
  const out: Seat[] = []
  const add = (r: number, a: number, h: number, row: number, section: string, kind: Seat['kind'], i: number) =>
    out.push({ p: [Math.sin(a) * r, h, Math.cos(a) * r], yaw: a + Math.PI, row, section, kind, lite: i % 2 === 0 })
  for (let t = 0; t < 3; t++) for (let i = 0; i < 40; i++) add(8.55 + 0.86 * t, -1 + (2 * i) / 40, 0.44 + 0.42 * t, t, 'long', 'seat', i)
  for (let i = 0; i < 20; i++) add(7.85, -1 + i / 10, 0, -1, 'long', 'ground', i)
  for (let i = 0; i < 16; i++) add(8, 2 + i / 16, 0, -1, i < 8 ? 'gateA' : 'front', 'stand', i)
  return out
}

describe('fillShare', () => {
  it('runs from about a quarter at Fame 0 to full at 100, and clamps', () => {
    expect(fillShare(0)).toBeCloseTo(0.25)
    expect(fillShare(100)).toBe(1)
    expect(fillShare(40)).toBeCloseTo(0.55)
    expect(fillShare(-5)).toBeCloseTo(0.25)
    expect(fillShare(250)).toBe(1)
    expect(fillShare(Number.NaN)).toBeCloseTo(0.25)
  })
})

describe('planCrowd', () => {
  const S = seats()
  it('fills the share of the spots that Fame asks for', () => {
    for (const fame of [0, 10, 40, 70, 100]) expect(planCrowd(S, { fame, lite: false, seed: 1 }).length).toBe(Math.round(fillShare(fame) * S.length))
  })
  it('is deterministic for a seed', () => {
    expect(planCrowd(S, { fame: 60, lite: false, seed: 9 })).toEqual(planCrowd(S, { fame: 60, lite: false, seed: 9 }))
    expect(planCrowd(S, { fame: 60, lite: false, seed: 9 })).not.toEqual(planCrowd(S, { fame: 60, lite: false, seed: 10 }))
  })
  it('only adds people as Fame grows: nobody already seated moves or changes', () => {
    let prev = planCrowd(S, { fame: 0, lite: false, seed: 3 })
    for (const fame of [10, 40, 70, 100]) {
      const next = planCrowd(S, { fame, lite: false, seed: 3 })
      const bySeat = new Map(next.map((o) => [o.seat, o]))
      for (const o of prev) expect(bySeat.get(o.seat)).toEqual(o)
      prev = next
    }
  })
  it('fills the best seats first: the front tier before the back one', () => {
    const order = fillOrder(S, 5)
    const firstQuarter = order.slice(0, 40).map((i) => S[i]!)
    const front = firstQuarter.filter((s) => s.row === 0).length
    const back = firstQuarter.filter((s) => s.row === 2).length
    expect(front).toBeGreaterThan(back)
  })
  it('Lite uses only its own half of the spots', () => {
    const lite = planCrowd(S, { fame: 100, lite: true, seed: 2 })
    expect(lite.length).toBe(S.filter((s) => s.lite).length)
    expect(lite.every((o) => S[o.seat]!.lite)).toBe(true)
  })
  it('holds about a tenth cut-outs, each a breed, every breed before any repeats', () => {
    const full = planCrowd(S, { fame: 100, lite: false, seed: 4 })
    const cuts = full.filter((o) => o.what === 'cutout')
    const share = (cuts.length / full.length) * 100
    expect(share).toBeGreaterThan(CROWD.cutoutPct - 6)
    expect(share).toBeLessThan(CROWD.cutoutPct + 6)
    expect(cuts.every((o) => o.breed && BREED_IDS.includes(o.breed))).toBe(true)
    const first = cuts.slice(0, Math.min(cuts.length, BREED_IDS.length)).map((o) => o.breed)
    expect(new Set(first).size).toBe(first.length)
  })
  it('puts kids on the ground spots and stands the standing folk', () => {
    const full = planCrowd(S, { fame: 100, lite: false, seed: 6 })
    for (const o of full) {
      const s = S[o.seat]!
      if (s.kind === 'ground') expect(o.kid).toBe(true)
      expect(o.pose).toBe(s.kind === 'seat' ? 'sit' : 'stand')
    }
  })
})

describe('cheers', () => {
  it('rise, hold and fall back to nothing', () => {
    for (const kind of ['small', 'big', 'huge', 'ovation'] as const) {
      const c = CROWD.cheer[kind]
      expect(envelope(kind, -0.1)).toBe(0)
      expect(envelope(kind, c.attack / 2)).toBeGreaterThan(0)
      expect(envelope(kind, c.attack / 2)).toBeLessThan(1)
      expect(envelope(kind, c.attack + c.hold / 2)).toBe(1)
      expect(envelope(kind, cheerSeconds(kind) + 0.01)).toBe(0)
    }
  })
  it('grow with the moment: a KO is bigger than a hit', () => {
    expect(CROWD.cheer.huge.peak).toBeGreaterThan(CROWD.cheer.big.peak)
    expect(CROWD.cheer.big.peak).toBeGreaterThan(CROWD.cheer.small.peak)
    expect(cheerSeconds('huge')).toBeGreaterThan(cheerSeconds('small'))
  })
  it('ripple outward: the far side hears it later, the shorter way round', () => {
    expect(rippleDelay(0, 0, 9, 0)).toBe(0)
    expect(rippleDelay(0, Math.PI, 9, 0)).toBeGreaterThan(rippleDelay(0, 1, 9, 0))
    expect(rippleDelay(0.2, -0.2, 9, 0)).toBeCloseTo(rippleDelay(-0.2, 0.2, 9, 0))
    expect(rippleDelay(3, -3, 9, 0)).toBeLessThan(rippleDelay(3, 0, 9, 0))
  })
  it('excite everyone who joins a huge cheer, and the ovation stands the benches up', () => {
    const crowd = planCrowd(seats(), { fame: 100, lite: false, seed: 8 }).filter((o) => o.what === 'person')
    const huge: Cheer[] = [{ kind: 'huge', at: 0, from: 0, id: 0 }]
    // everyone peaks at some moment as it ripples past them
    const peak = crowd.map((o) => Math.max(...Array.from({ length: 60 }, (_, k) => excitement(huge, k / 10, o, 8).e)))
    expect(Math.min(...peak)).toBeGreaterThan(0.9)
    const sitter = crowd.find((o) => o.pose === 'sit')!
    const ov = excitement([{ kind: 'ovation', at: 0, from: 0, id: 1 }], 4, sitter, 8)
    expect(poseOf(sitter, 4, ov.e, ov.ovation, false, 8).standing).toBe(true)
    expect(poseOf(sitter, 4, ov.e, ov.ovation, true, 8).standing).toBe(false)
  })
  it('small cheers move only some people', () => {
    const crowd = planCrowd(seats(), { fame: 100, lite: false, seed: 8 })
    const joined = crowd.filter((o) => excitement([{ kind: 'small', at: 0, from: 0, id: 0 }], 0.6, o, 8).e > 0).length
    expect(joined / crowd.length).toBeGreaterThan(0.15)
    expect(joined / crowd.length).toBeLessThan(0.6)
  })
})

describe('poses', () => {
  const someone = planCrowd(seats(), { fame: 100, lite: false, seed: 1 }).find((o) => o.what === 'person' && o.held === null)!
  it('never sink below the seat, and Reduce motion never hops', () => {
    for (let t = 0; t < 4; t += 0.05) {
      expect(poseOf(someone, t, 1, 0, false, 1).lift).toBeGreaterThanOrEqual(0)
      expect(poseOf(someone, t, 1, 0, true, 1).lift).toBeLessThanOrEqual(CROWD.idle.bobM)
    }
  })
  it('raise the arms when excited', () => {
    const calm = poseOf(someone, 1, 0, 0, false, 1)
    const wild = poseOf(someone, 1, 1, 0, false, 1)
    expect(Math.abs(wild.leftSpread) + Math.abs(wild.rightSpread)).toBeGreaterThan(Math.abs(calm.leftSpread) + Math.abs(calm.rightSpread) + 3)
  })
  it('turn arms the way they say: raise forward, spread out to the side and up', () => {
    const R = armRot(m3(), Math.PI / 2, 0)
    // the arm hangs down −y; raised 90° it points forward (+z)
    expect(-R[1]!).toBeCloseTo(0)
    expect(-R[4]!).toBeCloseTo(0)
    expect(-R[7]!).toBeCloseTo(1)
    const U = armRot(m3(), 0, Math.PI)
    expect(Math.round(-U[4]! * 1000) / 1000).toBe(1)
    const B = rotYXZ(m3(), 0, 0.3, 0)
    expect(B[5]!).toBeLessThan(0)
    expect(B[7]!).toBeGreaterThan(0)
  })
  it('hash01 stays in [0, 1)', () => {
    for (let i = 0; i < 500; i++) {
      const v = hash01(7, i, i * 3)
      expect(v).toBeGreaterThanOrEqual(0)
      expect(v).toBeLessThan(1)
    }
  })
})

describe('readSeats', () => {
  it('keeps good seats and skips bad ones without crashing', async () => {
    const { readSeats } = await import('./crowd.ts')
    const good = { p: [1, 0.44, -8], yaw: 3, row: 0, section: 'long', kind: 'seat', lite: true }
    const out = readSeats({ seats: [good, null, 7, { p: [1, 2] }, { p: [1, Number.NaN, 2], yaw: 0 }, { p: [0, 0, 9], yaw: 1, kind: 'weird' }] })
    expect(out.length).toBe(2)
    expect(out[0]).toEqual(good)
    expect(out[1]!.kind).toBe('seat')
    expect(readSeats(null)).toEqual([])
    expect(readSeats({ seats: 'nope' })).toEqual([])
  })
})
