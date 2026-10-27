/**
 * The Crown of Tides (SOUND_UPGRADE §7.4): a rolling sea. G Dorian, 6/8, dotted quarter = 76 (114 quarter
 * BPM). The flute rides the swell in long-short phrases, a tenor cello line answers when the flute holds,
 * the harp arpeggios roll like waves, cellos hold the floor, and the tide kit (frame drum, shaker) breathes
 * with an ocean-drum swell every four bars. The lobby is the flute alone over harp and cellos. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'crown-tides',
  kind: 'battle',
  brief: 'The Crown of Tides: a rolling sea in G Dorian 6/8, the flute riding long-short swells, a cello answering, harp waves and an ocean-drum swell every four bars. Broad and moving, salt air.',
  energy: 5,
  musicSend: 0.28,
  kit: 'tide',
  abc: `
X:1
M:6/8
L:1/8
Q:3/8=76
K:G dor
V:chords
[P:lobby] "Gm"z6 | "C"z6 | "Gm"z6 | "F"z6 | "Gm"z6 | "C"z6 | "Dm"z6 | "Gm"z6 |
[P:intro] "Gm"z6 | "Gm"z6 |
[P:A] "Gm"z6 | "C"z6 | "Gm"z6 | "F"z6 | "Bb"z6 | "C"z6 | "Dm"z6 | "Gm"z6 |
[P:B] "Bb"z6 | "F"z6 | "C"z6 | "Gm"z6 | "Bb"z6 | "F"z6 | "C"z6 | "Dm"z6 |
[P:A2] "Gm"z6 | "C"z6 | "Gm"z6 | "F"z6 | "Bb"z6 | "C"z6 | "F"z6 | "Gm"z6 |
[P:C] "Dm"z6 | "Am"z6 | "Bb"z6 | "C"z6 | "Dm"z6 | "Am"z6 | "Bb"z6 | "C"z6 |
[P:B2] "Bb"z6 | "F"z6 | "C"z6 | "Gm"z6 | "Bb"z6 | "F"z6 | "Dm"z6 | "Gm"z6 |
[P:A3] "Gm"z6 | "C"z6 | "Gm"z6 | "F"z6 | "Bb"z6 | "C"z6 | "Dm"z6 | "Gm"z6 |
V:lead
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] z6 | z6 |
[P:A] d2 B G2 A | B2 c d2 e | d3- d2 z | c2 A F2 A | B2 c d2 f | e2 d c2 z | A2 B c2 d | B3 G2 z |
[P:B] f3 d2 B | c3 A2 c | e2 f g2 e | d3- d2 z | f2 g f2 d | c2 d c2 A | G2 A B2 c | d3 A2 z |
[P:A2] d2 B G2 A | B2 c d2 e | d3- d2 z | c2 A F2 A | d2 c B2 F | G2 c e2 z | A2 B c2 A | G3- G2 z |
[P:C] !mp! A3 F3 | A3 c3 | B3 d3 | c3- c2 z | d2 e f2 d | c2 B A2 c | d2 c B2 d | e3- e2 z |
[P:B2] !mf! f3 d2 B | c3 A2 c | e2 f g2 e | d3- d2 z | B2 d f2 d | A2 c d2 c | d2 e f2 e | d3 B2 z |
[P:A3] d2 B G2 A | B2 c d2 e | d3- d2 z | c2 A F2 A | f2 e d2 B | c2 d e2 z | f2 e d2 A | G3- G2 z |
V:lobbyLead
[P:lobby] !p! d6 | e3 c3 | d6 | c3 z3 | B3 c3 | d3 e3 | d3 c3 | G3 z3 |
[P:intro] z6 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
V:counter
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] z6 | z6 |
[P:A] !mp! z6 | z6 | z3 D2 E | E3 F3 | z6 | z6 | z3 A,2 B, | D3 z3 |
[P:B] z6 | z6 | z6 | z3 A,2 B, | z6 | z6 | z6 | z3 E2 F |
[P:A2] z6 | z6 | z3 D2 E | E3 F3 | z6 | z6 | z3 A,2 B, | D3 z3 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z3 A,2 B, | z6 | z6 | z6 | z3 A,2 B, |
[P:A3] z6 | z6 | z3 D2 E | E3 F3 | z6 | z6 | z3 A,2 B, | D3 z3 |
V:colour
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] z6 | z6 |
[P:A] !mp! z6 | z6 | z6 | z3 f2 a | z6 | z6 | z6 | z3 g2 b |
[P:B] z6 | z6 | z6 | z3 b2 d' | z6 | z6 | z6 | z3 a2 d' |
[P:A2] z6 | z6 | z6 | z3 f2 a | z6 | z6 | z6 | z3 g2 b |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z3 b2 d' | z6 | z6 | z6 | z3 g2 b |
[P:A3] z6 | z6 | z6 | z3 f2 a | z6 | z6 | z6 | z3 g2 b |
V:hit
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] !mf! [G,B,DG]3 z3 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
V:boom
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] !mf! C3 z3 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
`,
  parts: {
    lead: { inst: 'flute', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 3, pan: 0.05 },
    lobbyLead: { inst: 'flute', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    counter: { inst: 'cellos', art: 'vib', role: 'counter', layers: ['drive', 'tension'], gain: -7, pan: -0.25 },
    colour: { inst: 'harp', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -6, pan: -0.2 },
    pad: { inst: 'cellos', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 2, size: 3, gain: -13, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    pulse: { inst: 'violas', art: 'pizz', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -14, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 3, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 12,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.....x.....', gain: -8 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x..x..x..x..', gain: -17, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: 'X........... | ............ | ............ | ............', gain: -14 },
      riser: { role: 'low', layers: ['tension'], steps: 'x..x..x..x..', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2', 'A3'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 1.3 },
  },
})
