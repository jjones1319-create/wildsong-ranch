/**
 * The Vale–Coast Summit (SOUND_UPGRADE §7.4): a festival team anthem in call and response. F Ionian, 4/4,
 * 116. The Vale (ocarina, with the alto recorder a third below) sings two bars, the Coast (flute, the horn
 * holding under it) answers with two; the B section trades single bars; in C both teams sing together in
 * thirds. Claps on two and four are written in, with cajon, bongos and shaker. The `qualifier` arrangement
 * (the Summit Qualifier) drops the horn, the colour and the tension extras. The lobby is the recorder alone
 * over harp. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'summit',
  kind: 'battle',
  brief: 'The Vale–Coast Summit: a festival team anthem in F major, the Vale on ocarina and recorder calling, the Coast on flute and horn answering, both teams together in the middle, claps on two and four. Friendly rivalry, a stadium of neighbours.',
  energy: 4,
  musicSend: 0.24,
  kit: 'festival',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=116
K:F
V:chords
[P:lobby] "F"z8 | "Bb"z8 | "C"z8 | "F"z8 | "Dm"z8 | "Bb"z8 | "C"z8 | "F"z8 |
[P:intro] "F"z8 | "F"z8 |
[P:A] "F"z8 | "C"z8 | "Dm"z8 | "Bb"z8 | "F"z8 | "C"z8 | "Bb"z8 | "F"z8 |
[P:B] "Bb"z8 | "F"z8 | "Gm"z8 | "C"z8 | "Bb"z8 | "F"z8 | "Gm"z8 | "C"z8 |
[P:A2] "F"z8 | "C"z8 | "Dm"z8 | "Bb"z8 | "F"z8 | "C"z8 | "Bb"z8 | "F"z8 |
[P:C] "Dm"z8 | "Am"z8 | "Bb"z8 | "F"z8 | "Dm"z8 | "Am"z8 | "Gm"z8 | "C"z8 |
[P:B2] "Bb"z8 | "F"z8 | "Gm"z8 | "C"z8 | "Bb"z8 | "F"z8 | "C"z8 | "F"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] c2 A c f2 e d | e2 g2 e2 z2 | z8 | z8 | f2 e f a2 g f | g2 e2 c2 z2 | z8 | z8 |
[P:B] d2 e f d2 z2 | z8 | B2 c d B2 z2 | z8 | f2 g f d2 z2 | z8 | d3 c B2 z2 | c4 z4 |
[P:A2] c2 A c f2 e d | e2 g2 e2 z2 | z8 | z8 | a2 g f g2 a b | g2 c2 e2 z2 | z8 | z8 |
[P:C] !mp! a3 g f2 d2 | e3 d c2 A2 | B3 c d2 f2 | f6 z2 | f3 e d2 A2 | c3 d e2 c2 | B3 c d2 B2 | c6 z2 |
[P:B2] !mf! d2 e f d2 z2 | z8 | B2 c d B2 z2 | z8 | f2 g f d2 z2 | z8 | c2 d2 e2 z2 | f6 z2 |
V:counter
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | d2 f e d2 A2 | B2 d2 f2 z2 | z8 | z8 | d2 c B c2 d2 | c6 z2 |
[P:B] z8 | c2 A2 F2 z2 | z8 | e2 d c2 G2 z | z8 | c2 A G F2 z2 | G2 A2 B2 z2 | G4 z4 |
[P:A2] z8 | z8 | d2 f e d2 A2 | B2 d2 f2 z2 | z8 | z8 | f2 e d e2 f2 | f6 z2 |
[P:C] !mp! f3 e d2 A2 | c3 B A2 c2 | B3 A B2 d2 | c6 z2 | d3 c A2 F2 | A3 B c2 A2 | G3 A B2 G2 | G6 z2 |
[P:B2] !mf! z8 | c2 A2 F2 z2 | z8 | e2 d c2 G2 z | z8 | c2 A G F2 z2 | G2 B2 c2 z2 | c6 z2 |
V:vale2
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! A4 G4 | G4 G2 z2 | z8 | z8 | A4 B4 | c4 c2 z2 | z8 | z8 |
[P:B] B4 B2 z2 | z8 | B4 B2 z2 | z8 | d4 d2 z2 | z8 | z8 | z8 |
[P:A2] A4 G4 | G4 G2 z2 | z8 | z8 | c4 B4 | G4 G2 z2 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] B4 B2 z2 | z8 | B4 B2 z2 | z8 | d4 d2 z2 | z8 | z8 | z8 |
V:lobbyLead
[P:lobby] !p! A4 c4 | d4 B4 | c4 G4 | A6 z2 | A4 G4 | B4 d4 | c4 B4 | A6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z8 | D4 A,4 | B,4 D4 | z8 | z8 | B,4 C4 | A,6 z2 |
[P:B] z8 | A,4 F,4 | z8 | E4 C4 | z8 | A,4 C4 | z8 | z8 |
[P:A2] z8 | z8 | D4 A,4 | B,4 D4 | z8 | z8 | B,4 C4 | A,6 z2 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | A,4 F,4 | z8 | E4 C4 | z8 | A,4 C4 | z8 | z8 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z6 c'2 | z8 | z6 f'2 | z8 | z6 c'2 | z8 | z6 a2 |
[P:B] z8 | z8 | z8 | z6 g'2 | z8 | z8 | z8 | z6 c'2 |
[P:A2] z8 | z6 c'2 | z8 | z6 f'2 | z8 | z6 c'2 | z8 | z6 a2 |
[P:C] z8 | z8 | z8 | z6 f'2 | z8 | z8 | z8 | z6 e'2 |
[P:B2] z8 | z8 | z8 | z6 g'2 | z8 | z8 | z8 | z6 f'2 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [F,A,CF]4 z4 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:boom
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! C2 z6 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
`,
  parts: {
    lead: { inst: 'ocarina', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 0, pan: -0.15 },
    counter: { inst: 'flute', role: 'counter', layers: ['base', 'drive', 'tension'], gain: -1, pan: 0.2 },
    vale2: { inst: 'recorder-alto', role: 'counter', layers: ['drive', 'tension'], gain: -6, pan: -0.25 },
    lobbyLead: { inst: 'recorder-alto', role: 'lead', layers: ['lobby'], gain: -4, pan: -0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['drive', 'tension'], gain: -7, pan: 0.25 },
    colour: { inst: 'glock', role: 'colour', layers: ['drive', 'tension'], gain: -14, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -9, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -16, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -8 },
      mid: { role: 'mid', layers: ['drive'], steps: '..x...x...x..x..', gain: -14, pan: -0.2 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -17, pan: 0.3 },
      claps: { inst: 'claps', layers: ['base', 'drive', 'tension'], steps: '....X.......X...', gain: -11 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 2 },
    // The Summit Qualifier: the same anthem with fewer layers (no horn, no colour, no tension extras).
    qualifier: { lines: ['lead', 'counter', 'vale2', 'lobbyLead', 'hit', 'boom', 'harp', 'pad', 'bass', 'low', 'mid', 'shaker', 'claps'], gainDb: 0.5 },
  },
})
