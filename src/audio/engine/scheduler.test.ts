import { describe, expect, it } from 'vitest'
import { fakeDriver } from './driver.ts'
import { beatGrid, beatToTime, nextBoundary, quantisedTime, Scheduler, timeToBeat, type Transport } from './scheduler.ts'

describe('the scheduler (§4.4)', () => {
  it('plays every event within the lookahead, in order, and drops only events later than 5 ms', () => {
    const d = fakeDriver()
    const s = new Scheduler(d)
    const played: number[] = []
    s.start()
    for (const t of [0.5, 0.3, 1.2, 0.9]) s.add(t, (at) => played.push(at))
    d.run(0.2)
    // 0.3 is within 0.4 of 0.2, 0.5 too; 0.9 and 1.2 are not yet.
    expect(played).toEqual([0.3, 0.5])
    d.run(0.4)
    expect(played).toEqual([0.3, 0.5, 0.9])
    d.run(0.4)
    expect(played).toEqual([0.3, 0.5, 0.9, 1.2])
    expect(s.lateEvents).toBe(0)
    // An event 4 ms late plays at "now"; one 20 ms late is dropped.
    s.add(d.now() - 0.004, (at) => played.push(at))
    s.add(d.now() - 0.02, (at) => played.push(at))
    d.advance(0)
    expect(played).toHaveLength(5)
    expect(played[4]).toBeCloseTo(d.now())
    expect(s.lateEvents).toBe(1)
  })

  it('a 300 ms stall gives zero late events for a steady stream of beats', () => {
    const d = fakeDriver()
    const s = new Scheduler(d)
    let nextBeat = 0
    const bpm = 120
    const spb = 60 / bpm
    let played = 0
    s.addFiller((until) => {
      while (nextBeat * spb < until) {
        s.add(nextBeat * spb, () => {
          played++
        })
        nextBeat++
      }
    })
    s.start()
    d.run(2)
    d.advance(0.3)
    d.run(2)
    expect(s.lateEvents).toBe(0)
    expect(played).toBeGreaterThanOrEqual(Math.floor(4.3 / spb))
  })

  it('cancels a tagged group and tells how many were pending', () => {
    const d = fakeDriver()
    const s = new Scheduler(d)
    s.add(3, () => {}, 'song-a')
    s.add(4, () => {}, 'song-a')
    s.add(5, () => {}, 'song-b')
    expect(s.cancel('song-a')).toBe(2)
    expect(s.pending()).toBe(1)
  })

  it('transports convert beats to times and quantise changes to beats, bars and sections', () => {
    const t: Transport = { startTime: 10, bpm: 120, beatsPerBar: 3 }
    expect(beatToTime(t, 4)).toBeCloseTo(12)
    expect(timeToBeat(t, 12)).toBeCloseTo(4)
    expect(nextBoundary(t, 12.1, 'beat')).toBe(5)
    expect(nextBoundary(t, 12.1, 'bar')).toBe(6)
    expect(nextBoundary(t, 13, 'bar')).toBe(9)
    expect(quantisedTime(t, 12.1, 'now')).toBe(12.1)
    expect(quantisedTime(t, 12.1, 'beat')).toBeCloseTo(12.5)
    expect(quantisedTime(t, 12.1, 'bar')).toBeCloseTo(13)
    expect(quantisedTime(t, 12.1, 'section', 12)).toBeCloseTo(16)
    expect(quantisedTime(t, 12.1, 'section', 2)).toBeCloseTo(12.1)
  })

  it('two transports with different tempos coexist', () => {
    const a: Transport = { startTime: 0, bpm: 60, beatsPerBar: 4 }
    const b: Transport = { startTime: 0.5, bpm: 90, beatsPerBar: 4 }
    expect(beatToTime(a, 8)).toBeCloseTo(8)
    expect(beatToTime(b, 8)).toBeCloseTo(0.5 + 8 * (60 / 90))
    expect(nextBoundary(a, 2.2, 'bar')).toBe(4)
    expect(nextBoundary(b, 2.2, 'bar')).toBe(4)
  })
})

describe('the beat grid (§9.4, the crowd claps along)', () => {
  it('lists the beats in a window with their place in the bar, dotted quarters in compound time', () => {
    const t: Transport = { startTime: 1, bpm: 120, beatsPerBar: 4 }
    const g = beatGrid(t, [4, 4], 1, 3)
    expect(g.map((b) => b.time)).toEqual([1, 1.5, 2, 2.5])
    expect(g.map((b) => b.beat)).toEqual([0, 1, 2, 3])
    expect(beatGrid(t, [4, 4], 1.2, 1.4)).toEqual([])
    expect(beatGrid(t, [4, 4], 0, 1.1).map((b) => b.time)).toEqual([1])
    const c = beatGrid({ startTime: 0, bpm: 114, beatsPerBar: 3 }, [6, 8], 0, 3.2)
    expect(c.map((b) => b.beat)).toEqual([0, 1, 0, 1, 0])
    expect(c[1]!.time).toBeCloseTo(60 / 114 * 1.5, 6)
    expect(beatGrid({ startTime: 0, bpm: 108, beatsPerBar: 3 }, [3, 4], 0, 2).map((b) => b.beat)).toEqual([0, 1, 2, 0])
  })
})
