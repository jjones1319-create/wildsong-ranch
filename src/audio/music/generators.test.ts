import { describe, expect, it } from 'vitest'
import { parseAbc } from './abc.ts'
import { chordTrack } from './chords.ts'
import { generate, PATTERN_IDS } from './patterns.ts'
import { defaultGrid, parseSteps, percEvents } from './perc.ts'

const track = (abc: string) => {
  const t = parseAbc(abc)
  return chordTrack(t.voices[0]!.sections[0]!).track
}
const FOUR = track('X:1\nM:4/4\nL:1/8\nK:C\nV:chords\n[P:A] "C"z8 | "G/B"z8 | "Am"z4 "F"z4 | "G"z8 |\n')
const SIX = track('X:1\nM:6/8\nL:1/8\nK:G mix\nV:chords\n[P:A] "G"z6 | "F/G"z6 |\n')

describe('accompaniment generators (§6.3)', () => {
  it('every pattern stays inside the range, keeps the bass at the bottom and fills the bars', () => {
    for (const id of PATTERN_IDS) {
      const ev = generate(id, FOUR, 4, [4, 4], { octave: 3, range: [48, 84] })
      if (id === 'flourish') {
        expect(ev.every((e) => e.bar === 3)).toBe(true)
        continue
      }
      expect(ev.length).toBeGreaterThan(0)
      for (const e of ev) {
        expect(e.bar).toBeGreaterThanOrEqual(0)
        expect(e.bar).toBeLessThan(4)
        expect(e.t).toBeGreaterThanOrEqual(0)
        expect(e.t + e.dur).toBeLessThanOrEqual(4 + 1e-6)
        for (const p of e.pitches) {
          expect(p).toBeGreaterThanOrEqual(48)
          expect(p).toBeLessThanOrEqual(84)
        }
        expect(e.vel).toBeGreaterThan(0)
        expect(e.vel).toBeLessThanOrEqual(1)
      }
    }
  })

  it('harp arpeggios rise and fall through 1-5-8-10 and follow a mid-bar chord change', () => {
    const ev = generate('harpArp', FOUR, 4, [4, 4], { octave: 3, range: [48, 84] })
    const bar0 = ev.filter((e) => e.bar === 0).map((e) => e.pitches[0]!)
    expect(bar0).toHaveLength(8)
    expect(bar0[0]! % 12).toBe(0)
    expect(bar0[1]! % 12).toBe(7)
    expect(bar0[2]! % 12).toBe(0)
    expect(bar0[3]! % 12).toBe(4)
    expect(bar0[0]).toBeLessThan(bar0[1]!)
    expect(bar0[3]).toBeGreaterThan(bar0[2]!)
    const bar2 = ev.filter((e) => e.bar === 2)
    expect(bar2.filter((e) => e.t < 2).every((e) => [9, 0, 4].includes(e.pitches[0]! % 12))).toBe(true)
    expect(bar2.filter((e) => e.t >= 2).every((e) => [5, 9, 0].includes(e.pitches[0]! % 12))).toBe(true)
    const six = generate('harpArp', SIX, 2, [6, 8], { octave: 3, range: [48, 84] })
    expect(six.filter((e) => e.bar === 0)).toHaveLength(6)
  })

  it('waltz puts the bass on 1 and the chord on 2 and 3; pizz walks root-5-6-5 with an approach', () => {
    const w = generate('waltz', track('X:1\nM:3/4\nL:1/8\nK:F\nV:chords\n[P:A] "F"z6 | "C"z6 |\n'), 2, [3, 4], { octave: 3, range: [41, 84] })
    const bar = w.filter((e) => e.bar === 0)
    expect(bar.map((e) => e.t)).toEqual([0, 1, 2])
    expect(bar[0]!.pitches).toHaveLength(1)
    expect(bar[1]!.pitches.length).toBeGreaterThanOrEqual(2)
    const p = generate('pizzWalk', FOUR, 4, [4, 4], { octave: 2, range: [36, 72] })
    const b0 = p.filter((e) => e.bar === 0).map((e) => e.pitches[0]!)
    expect(b0).toHaveLength(4)
    expect(b0[0]! % 12).toBe(0)
    expect(b0[1]! % 12).toBe(7)
    expect(b0[2]! % 12).toBe(9)
    // The last beat leads into G/B's bass (B) by a half step from below or a whole step from above.
    expect([10, 1]).toContain(b0[3]! % 12)
  })

  it('kalimba ostinato is 3+3+2, pads hold and tie across equal chords, drones are a tonic-fifth pedal', () => {
    const k = generate('kalimbaOstinato', FOUR, 1, [4, 4], { octave: 4, range: [55, 91] })
    expect(k.map((e) => e.t)).toEqual([0, 0.75, 1.5, 2, 2.75, 3.5])
    const pad = generate('padSustain', track('X:1\nM:4/4\nL:1/8\nK:C\nV:chords\n[P:A] "C"z8 | z8 | "F"z8 |\n'), 3, [4, 4], { octave: 3, range: [48, 84] })
    expect(pad[0]!.tie).toBe(true)
    expect(pad[1]!.tie).toBe(false)
    expect(pad[0]!.dur).toBe(4)
    const d = generate('drone', FOUR, 2, [4, 4], { octave: 2, range: [36, 72] })
    expect(d[0]!.pitches[1]! - d[0]!.pitches[0]!).toBe(7)
    expect(d[0]!.tie).toBe(true)
  })

  it('strums carry a string delay and bassRoot can jump octaves', () => {
    const s = generate('strum', FOUR, 1, [4, 4], { octave: 3, range: [50, 81] })
    expect(s.every((e) => e.strumMs === 15)).toBe(true)
    expect(s.some((e) => e.pitches.length >= 3)).toBe(true)
    const b = generate('bassRoot', FOUR, 1, [4, 4], { octave: 2, range: [36, 72], octaveJumps: true })
    expect(b.map((e) => e.t)).toEqual([0, 2])
    expect(b[1]!.pitches[0]! - b[0]!.pitches[0]!).toBe(12)
  })
})

describe('percussion lines (§6.4)', () => {
  it('reads step strings one bar per segment and cycles them', () => {
    expect(parseSteps('X.....x.....')).toEqual(['X.....x.....'])
    expect(parseSteps('X...x... | x...X...')).toHaveLength(2)
    expect(() => parseSteps('X..?')).toThrow()
    expect(defaultGrid([4, 4])).toBe(16)
    expect(defaultGrid([3, 4])).toBe(12)
    expect(defaultGrid([6, 8])).toBe(12)
    const ev = percEvents('X.....x..... | ...o..x.....', 12, 3, [6, 8])
    expect(ev.filter((e) => e.bar === 0).map((e) => [e.t, e.vel])).toEqual([
      [0, 0.9],
      [1.5, 0.6],
    ])
    expect(ev.filter((e) => e.bar === 1).map((e) => e.vel)).toEqual([0.3, 0.6])
    expect(ev.filter((e) => e.bar === 2).map((e) => e.t)).toEqual([0, 1.5])
    expect(() => percEvents('X...', 16, 1, [4, 4])).toThrow(/grid/)
  })
})
