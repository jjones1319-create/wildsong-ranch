import { describe, expect, it } from 'vitest'
import { AbcError, beatsPerBar, isCompound, parseAbc, parseKey, scaleOf, strongBeats } from './abc.ts'

const tune = (body: string, head = 'X:1\nM:4/4\nL:1/8\nQ:1/4=100\nK:C\n') => parseAbc(head + body)

describe('ABC keys (§6.2)', () => {
  it('reads modes and explicit accidentals', () => {
    expect(parseKey('D lyd')).toMatchObject({ tonic: 2, mode: 'lydian', accidentals: { F: 1, C: 1, G: 1 } })
    expect(parseKey('G mix')).toMatchObject({ tonic: 7, mode: 'mixolydian', accidentals: { F: 0 } })
    expect(parseKey('E dor').accidentals).toMatchObject({ F: 1, C: 1, G: 0 })
    expect(parseKey('A min').accidentals).toMatchObject({ F: 0, C: 0, G: 0 })
    expect(parseKey('Am').mode).toBe('aeolian')
    expect(parseKey('A phr ^c').accidentals).toMatchObject({ B: -1, C: 1, F: 0 })
    expect(parseKey('C min =b').accidentals).toMatchObject({ E: -1, A: -1, B: 0 })
    expect(parseKey('F').accidentals).toMatchObject({ B: -1 })
    expect(scaleOf(parseKey('D lyd'))).toEqual([2, 4, 6, 8, 9, 11, 1])
    expect(() => parseKey('H maj')).toThrow()
    expect(() => parseKey('C wat')).toThrow()
  })
})

describe('ABC notes and bars', () => {
  it('reads pitches, octaves, accidentals that last to the bar line, and durations', () => {
    const t = tune('V:lead\n[P:A] C D E F G A B c | G4 A4 | ^c =c c _d e2 f2 | B,4 b4 |\n')
    const bars = t.voices[0]!.sections[0]!.bars
    expect(bars).toHaveLength(4)
    expect(bars[0]!.events.map((e) => e.pitches[0])).toEqual([60, 62, 64, 65, 67, 69, 71, 72])
    expect(bars[0]!.events.map((e) => e.dur)).toEqual([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    expect(bars[1]!.events.map((e) => e.dur)).toEqual([2, 2])
    expect(bars[2]!.events.slice(0, 4).map((e) => e.pitches[0])).toEqual([73, 72, 72, 73])
    expect(bars[3]!.events.map((e) => e.pitches[0])).toEqual([59, 83])
    expect(bars[3]!.events[0]!.dur).toBe(2)
  })

  it('reads halves, dotted pairs, triplets, ties, chords, rests and grace notes', () => {
    const t = tune('V:lead\n[P:A] C/2 D/ E3/2 F/2 | A>B c<d A>B c<d | (3efg a2 b2 z2 | [CEG]4 z2 x2 | {g}a8- | a8 |\n')
    const bars = t.voices[0]!.sections[0]!.bars
    expect(bars[0]!.events.map((e) => e.dur)).toEqual([0.25, 0.25, 0.75, 0.25])
    expect(bars[0]!.length).toBe(1.5)
    expect(bars[1]!.events.slice(0, 4).map((e) => e.dur)).toEqual([0.75, 0.25, 0.25, 0.75])
    expect(bars[2]!.events.slice(0, 3).map((e) => e.dur)).toEqual([1 / 3, 1 / 3, 1 / 3])
    expect(bars[3]!.events[0]!.pitches).toEqual([60, 64, 67])
    expect(bars[3]!.events[1]!.pitches).toEqual([])
    expect(bars[4]!.events[0]!.grace).toEqual([79])
    expect(bars[4]!.events[0]!.tie).toBe(true)
    expect(bars[5]!.events[0]!.tie).toBe(false)
  })

  it('carries the key signature and lets a pickup bar be short only at the start', () => {
    const t = tune('V:lead\n[P:A] F2 | G8 | F4 =F4 |\n', 'X:1\nM:4/4\nL:1/8\nQ:1/4=100\nK:G\n')
    const bars = t.voices[0]!.sections[0]!.bars
    expect(bars[0]!.events[0]!.pitches).toEqual([66])
    expect(bars[2]!.events.map((e) => e.pitches[0])).toEqual([66, 65])
    expect(() => tune('V:lead\n[P:A] G8 | F2 |\n')).toThrow(/beats/)
  })

  it('reports errors with a line and column', () => {
    expect(() => tune('V:lead\n[P:A] C D E F | G2 A2 | $ |\n')).toThrow(AbcError)
    try {
      tune('V:lead\n[P:A] C8 |\nG4 A4 | $ |\n')
    } catch (e) {
      expect((e as AbcError).line).toBe(8)
      expect((e as AbcError).col).toBe(9)
    }
    expect(() => tune('V:lead\n[P:A] !sforzando! C8 |\n')).toThrow(/decoration/)
    expect(() => tune('V:lead\nC8 |\n')).toThrow(/P:section/)
    expect(() => parseAbc('X:1\nK:C\n')).toThrow(/voices/)
  })
})

describe('ABC structure', () => {
  it('reads voices, sections, chord symbols, dynamics and inline fields', () => {
    const t = tune('V:chords\n[P:A] "C"z8 | "G/B"z4 "Am"z4 |\n[P:B] "F"z8 | "Fadd9"z8 |\nV:lead\n[P:A] !p! C8 | !crescendo(! D2 E2 F2 G2 | [P:B] !f! A8 | [K:D] F8 |\n')
    expect(t.sections).toEqual(['A', 'B'])
    const chords = t.voices.find((v) => v.id === 'chords')!
    expect(chords.sections[0]!.bars[1]!.events.map((e) => e.chord)).toEqual(['G/B', 'Am'])
    const lead = t.voices.find((v) => v.id === 'lead')!
    expect(lead.sections[0]!.bars[0]!.events[0]!.vel).toBeCloseTo(0.38)
    const ramp = lead.sections[0]!.bars[1]!.events.map((e) => e.vel)
    expect(ramp[0]).toBeGreaterThan(0.38)
    expect(ramp[3]).toBeCloseTo(0.78)
    expect(lead.sections[1]!.bars[0]!.events[0]!.vel).toBeCloseTo(0.78)
    // [K:D] applies from there: F becomes F#.
    expect(lead.sections[1]!.bars[1]!.events[0]!.pitches).toEqual([66])
  })

  it('unrolls repeats and endings', () => {
    const t = tune('V:lead\n[P:A] |: C8 | D8 |[1 E8 :|[2 F8 |\n')
    const bars = t.voices[0]!.sections[0]!.bars.map((b) => b.events[0]!.pitches[0])
    expect(bars).toEqual([60, 62, 64, 60, 62, 65])
    const plain = tune('V:lead\n[P:A] |: C8 | D8 :|\n')
    expect(plain.voices[0]!.sections[0]!.bars).toHaveLength(4)
  })

  it('reads meter, unit length and tempo, including compound meters', () => {
    const t = parseAbc('X:1\nM:6/8\nL:1/8\nQ:3/8=60\nK:G mix\nV:lead\n[P:A] d2B G2A | B3- B2z |\n')
    expect(t.meter).toEqual([6, 8])
    expect(t.bpm).toBe(90)
    expect(t.tempoText).toBe('3/8=60')
    expect(t.voices[0]!.sections[0]!.bars[0]!.length).toBe(3)
    expect(beatsPerBar([6, 8])).toBe(3)
    expect(isCompound([6, 8])).toBe(true)
    expect(isCompound([3, 4])).toBe(false)
    expect(strongBeats([4, 4])).toEqual([0, 2])
    expect(strongBeats([6, 8])).toEqual([0, 1.5])
    expect(strongBeats([3, 4])).toEqual([0])
    const c = parseAbc('X:1\nM:C\nL:1/8\nQ:1/4=84\nK:C lyd\nV:lead\n[P:A] C8 |\n')
    expect(c.meter).toEqual([4, 4])
    expect(c.bpm).toBe(84)
  })

  it('insists that every voice has every section at the same length', () => {
    expect(() => tune('V:a\n[P:A] C8 | D8 |\nV:b\n[P:A] C8 |\n')).toThrow(/differ in length/)
    expect(() => tune('V:a\n[P:A] C8 |\nV:b\n[P:B] C8 |\n')).toThrow(/no section/)
  })
})
