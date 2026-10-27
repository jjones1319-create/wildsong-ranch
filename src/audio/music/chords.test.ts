import { describe, expect, it } from 'vitest'
import { parseAbc } from './abc.ts'
import { chordAt, chordPcs, chordTrack, isChordTone, parseChord, voiceChord } from './chords.ts'

describe('chord symbols (§6.3)', () => {
  it('parses qualities and slash basses', () => {
    expect(parseChord('C')).toMatchObject({ root: 0, bass: 0, intervals: [0, 4, 7] })
    expect(parseChord('Dm7')).toMatchObject({ root: 2, intervals: [0, 3, 7, 10] })
    expect(parseChord('G/B')).toMatchObject({ root: 7, bass: 11 })
    expect(parseChord('Fadd9').intervals).toEqual([0, 4, 7, 14])
    expect(parseChord('Asus4').intervals).toEqual([0, 5, 7])
    expect(parseChord('Bbmaj7')).toMatchObject({ root: 10 })
    expect(parseChord('F#m')).toMatchObject({ root: 6, intervals: [0, 3, 7] })
    expect(chordPcs(parseChord('G7'))).toEqual([7, 11, 2, 5])
    expect(isChordTone(parseChord('Am'), 76)).toBe(true)
    expect(isChordTone(parseChord('Am'), 77)).toBe(false)
    expect(() => parseChord('Cx9')).toThrow()
    expect(() => parseChord('H')).toThrow()
  })

  it('builds the chord track from the chords voice and carries chords forward', () => {
    const t = parseAbc('X:1\nM:4/4\nL:1/8\nK:C\nV:chords\n[P:A] "C"z8 | z8 | "F"z4 "G"z4 |\n')
    const { track, last } = chordTrack(t.voices[0]!.sections[0]!)
    expect(track.map((c) => [c.bar, c.beat, c.chord.text])).toEqual([
      [0, 0, 'C'],
      [1, 0, 'C'],
      [2, 0, 'F'],
      [2, 2, 'G'],
    ])
    expect(last?.text).toBe('G')
    expect(chordAt(track, 2, 1)?.text).toBe('F')
    expect(chordAt(track, 2, 3.5)?.text).toBe('G')
    expect(chordAt(track, 1, 0)?.text).toBe('C')
  })

  it('voices chords low to high with the bass at the bottom and little movement', () => {
    const c = voiceChord(parseChord('C'), 43, 72, null)
    expect(c[0]).toBe(48)
    expect(c.length).toBe(3)
    const g = voiceChord(parseChord('G/B'), 43, 72, c)
    expect(g[0] % 12).toBe(11)
    expect(g[0]).toBeGreaterThanOrEqual(43)
    const moved = g.slice(1).reduce((s, n, i) => s + Math.abs(n - c[i + 1]!), 0)
    expect(moved).toBeLessThanOrEqual(6)
    for (const n of g) expect(n).toBeLessThanOrEqual(72)
    const four = voiceChord(parseChord('Dm7'), 48, 72, null, 4)
    expect(four).toHaveLength(4)
    expect(new Set(four.map((n) => n % 12)).size).toBe(4)
  })
})
