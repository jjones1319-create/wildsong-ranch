import { describe, expect, it } from 'vitest'
import { createRng } from '../engine/rng.ts'
import { containsMotif, CORIN_MOTIF, MASKED_MOTIF, transposeMotif, WILDSONG_MOTIF } from './motifs.ts'
import { breathSeconds, defineSong, instrumentFor, passSeconds, sounding, type SongDef } from './song.ts'

const ABC = `
X:1
M:4/4
L:1/8
Q:1/4=80
K:G
V:chords
[P:A] "G"z8 | "C"z8 |
[P:B] "Em"z8 | "D"z8 |
V:lead
[P:A] G4 A4 | B4- B4 |
[P:B] E4 D4 | F4 z4 |
`

const DEF: SongDef = {
  id: 'test-song',
  kind: 'ranch',
  brief: 'A test.',
  energy: 2,
  musicSend: 0.2,
  abc: ABC,
  parts: { lead: { inst: 'ocarina', role: 'lead', layers: ['main'] } },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -6 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['weather'], gain: -12 },
  },
  perc: { lines: { drum: { inst: 'frame-drum', role: 'low', layers: ['main'], steps: 'X.......x.......' }, timp: { role: 'low', layers: ['main'], steps: 'X...............', pitch: 'root' } } },
  kit: 'frost',
  order: ['A', 'B', 'breath', 'A'],
  loopFrom: 1,
  breath: [8, 20],
  weather: { rain: { mute: ['drum'], add: ['pad'], swap: { lead: 'vibes' } }, storm: { breath: [15, 30], fragments: ['lead'] } },
  stems: { quiet: ['lead', 'harp'] },
}

describe('the song model (§6.1, §6.5)', () => {
  it('compiles parts, generators and percussion into events per section', () => {
    const s = defineSong(DEF)
    expect(s.bpm).toBe(80)
    expect(Object.keys(s.sections)).toEqual(['A', 'B'])
    expect(s.sections.A!.bars).toBe(2)
    expect(s.sections.A!.beats).toBe(8)
    const lead = s.sections.A!.events.lead!
    // G, A, then B tied across the bar line: three events, the last 4 beats long.
    expect(lead.map((e) => [e.pitches[0], e.dur])).toEqual([
      [67, 2],
      [69, 2],
      [71, 4],
    ])
    expect(lead[0]!.phraseStart).toBe(true)
    expect(lead[1]!.phraseStart).toBeUndefined()
    expect(s.sections.A!.events.harp!.length).toBe(16)
    expect(s.sections.A!.events.drum!.map((e) => e.t)).toEqual([0, 2, 0, 2])
    const timp = s.sections.A!.events.timp!
    expect(timp.map((e) => e.pitches[0]! % 12)).toEqual([7, 0])
    expect(s.sections.A!.voiceBars.lead).toEqual([[67, 69], [71, 71]])
    expect(s.lines.map((l) => l.id)).toEqual(['lead', 'harp', 'pad', 'drum', 'timp'])
    expect(s.lines.find((l) => l.id === 'timp')!.inst).toBe('timpani')
  })

  it('applies the sounding rule: stems, layers, weather', () => {
    const s = defineSong(DEF)
    const main = sounding(s, { layers: new Set(['main']) })
    expect([...main]).toEqual(['lead', 'harp', 'drum', 'timp'])
    const rain = sounding(s, { layers: new Set(['main']), weather: s.weather!.rain })
    expect([...rain]).toEqual(['lead', 'harp', 'pad', 'timp'])
    expect(instrumentFor(s, 'lead', { weather: s.weather!.rain })).toBe('vibes')
    expect(instrumentFor(s, 'lead', {})).toBe('ocarina')
    const quiet = sounding(s, { layers: new Set(['main']), stem: 'quiet' })
    expect([...quiet]).toEqual(['lead', 'harp'])
    const none = sounding(s, { layers: new Set(['lobby']) })
    expect(none.size).toBe(0)
  })

  it('draws breaths from the song or the weather and measures a pass', () => {
    const s = defineSong(DEF)
    const rng = createRng(7)
    for (let i = 0; i < 20; i++) {
      const b = breathSeconds(s, rng)
      expect(b).toBeGreaterThanOrEqual(8)
      expect(b).toBeLessThanOrEqual(20)
      const st = breathSeconds(s, rng, s.weather!.storm)
      expect(st).toBeGreaterThanOrEqual(15)
      expect(st).toBeLessThanOrEqual(30)
    }
    // A, B, A at 80 BPM: 24 beats = 18 s, the breath excluded.
    expect(passSeconds(s)).toBeCloseTo(18)
  })

  it('rejects bad definitions', () => {
    expect(() => defineSong({ ...DEF, order: ['A', 'Z'] })).toThrow(/unknown section/)
    expect(() => defineSong({ ...DEF, kind: 'town', breath: [1, 2] })).toThrow(/breathe/)
    expect(() => defineSong({ ...DEF, parts: { lead: { inst: 'ocarina', role: 'lead', layers: ['main'], voice: 'nope' } } })).toThrow(/no ABC voice/)
    expect(() => defineSong({ ...DEF, stems: { x: ['ghost'] } })).toThrow(/unknown line/)
    expect(() => defineSong({ ...DEF, parts: { lead: { inst: 'trumpet' as never, role: 'lead', layers: ['main'] } } })).toThrow(/unknown instrument/)
  })
})

describe('motifs (§3.6)', () => {
  it('the Wildsong motif has the required shape and is found in any transposition', () => {
    const m = WILDSONG_MOTIF
    expect(m.pitches.length).toBeGreaterThanOrEqual(5)
    expect(m.pitches.length).toBeLessThanOrEqual(7)
    expect(m.intervals.some((i) => i === 5 || i === 7)).toBe(true)
    // Touches the raised 4th of D (G#) exactly once and ends on a non-tonic held note.
    expect(m.pitches.filter((p) => p % 12 === 8)).toHaveLength(1)
    expect(m.pitches[m.pitches.length - 1]! % 12).not.toBe(2)
    expect(m.beats[m.beats.length - 1]).toBeGreaterThanOrEqual(2)
    expect(containsMotif([60, 62, 64, 69, 68, 66, 64, 67])).toBe(true)
    expect(containsMotif(transposeMotif(m, 79))).toBe(true)
    expect(containsMotif([62, 64, 69, 68, 66, 65])).toBe(false)
    expect(containsMotif([67, 71, 74, 79], CORIN_MOTIF)).toBe(true)
    expect(containsMotif([72, 73, 72, 71, 72], MASKED_MOTIF)).toBe(true)
  })
})
