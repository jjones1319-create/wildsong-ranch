/**
 * The Crown of Dawn (SOUND_UPGRADE §7.4): sunrise, hopeful. D Lydian, 4/4, 116. The violins rise through
 * every phrase (the raised fourth, G♯, gives the light), horn calls answer from below, harp arpeggios and a
 * viola pad keep it warm, the glock sparkles at the phrase ends, the ceremony kit underneath. The lobby is
 * the violins alone, quiet, over harp and pad. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'crown-dawn',
  kind: 'battle',
  brief: 'The Crown of Dawn: a sunrise in D Lydian, violins climbing phrase by phrase, horn calls and glock light at the ends, timpani and triangle. Hopeful and bright, a big day beginning.',
  energy: 5,
  musicSend: 0.27,
  kit: 'ceremony',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=116
K:D lyd
V:chords
[P:lobby] "D"z8 | "E/D"z8 | "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "A"z8 | "D"z8 |
[P:intro] "D"z8 | "D"z8 |
[P:A] "D"z8 | "E"z8 | "D"z8 | "E"z8 | "Bm"z8 | "F#m"z8 | "E"z8 | "A"z8 |
[P:B] "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "Bm"z8 | "C#m"z8 | "E"z8 | "A"z8 |
[P:A2] "D"z8 | "E"z8 | "D"z8 | "E"z8 | "Bm"z8 | "F#m"z8 | "A"z8 | "D"z8 |
[P:C] "F#m"z8 | "Bm"z8 | "E"z8 | "D"z8 | "F#m"z8 | "Bm"z8 | "C#m"z8 | "E"z8 |
[P:B2] "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "Bm"z8 | "C#m"z8 | "E"z8 | "D"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] D2 E2 F2 A2 | B3 A G2 B2 | A2 d2 c d e2 | e6 z2 | f3 e d2 B2 | c3 B A2 c2 | B2 c d B2 G2 | A6 z2 |
[P:B] B2 d2 f4 | e3 d c2 A2 | A3 B d2 f2 | g4 e2 z2 | f3 g a2 f2 | e3 d c2 e2 | B3 c d2 B2 | c6 z2 |
[P:A2] D2 E2 F2 A2 | B3 A G2 B2 | A2 d2 c d e2 | e6 z2 | d3 c B2 d2 | c3 d e2 c2 | e3 d c2 B2 | d6 z2 |
[P:C] !mp! A3 B c4 | d2 c2 B4 | G3 A B2 e2 | f6 z2 | f3 e c2 A2 | B3 c d2 f2 | g3 f e2 c2 | B6 z2 |
[P:B2] !mf! B2 d2 f4 | e3 d c2 A2 | A3 B d2 f2 | g4 e2 z2 | d3 e f2 d2 | c3 d e2 g2 | f3 e B2 G2 | A6 z2 |
V:lobbyLead
[P:lobby] !p! F4 A4 | G4 B4 | B4 d4 | c6 z2 | d4 c4 | B4 G4 | A4 c4 | d6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z4 B,2 E2 | z8 | z4 E2 B,2 | z8 | z4 C2 A,2 | z8 | z4 A,2 C2 |
[P:B] z8 | z4 C2 E2 | z8 | z4 B,2 E2 | z8 | z4 E2 C2 | z8 | z4 E2 A,2 |
[P:A2] z8 | z4 B,2 E2 | z8 | z4 E2 B,2 | z8 | z4 C2 A,2 | z8 | z4 A,2 D2 |
[P:C] !p! A,8 | B,8 | B,8 | A,8 | A,8 | B,8 | C8 | B,8 |
[P:B2] !mp! z8 | z4 C2 E2 | z8 | z4 B,2 E2 | z8 | z4 E2 C2 | z8 | z4 D2 A,2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !p! z8 | z8 | z8 | z4 b2 e'2 | z8 | z8 | z8 | z4 a2 c'2 |
[P:B] z8 | z8 | z8 | z4 g'2 b'2 | z8 | z8 | z8 | z4 e'2 a'2 |
[P:A2] z8 | z8 | z8 | z4 b2 e'2 | z8 | z8 | z8 | z4 a2 d'2 |
[P:C] z8 | z8 | z8 | z4 f'2 a'2 | z8 | z8 | z8 | z4 e'2 g'2 |
[P:B2] z8 | z8 | z8 | z4 g'2 b'2 | z8 | z8 | z8 | z4 f'2 a'2 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [D,F,A,D]4 z4 | z8 |
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
    lead: { inst: 'violins', art: 'vib', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 6, pan: 0.05 },
    lobbyLead: { inst: 'violins', art: 'vib', role: 'lead', layers: ['lobby'], gain: -2, pan: 0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['drive', 'tension'], gain: -3, pan: -0.25 },
    colour: { inst: 'glock', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -1 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -11 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -5, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -9, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -5 },
    pulse: { inst: 'violas', art: 'pizz', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -10, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 3, gain: -14, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -16, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -6, pitch: 'root' },
      mid: { role: 'mid', layers: ['drive'], steps: 'x...............', gain: -10 },
      high: { role: 'high', layers: ['drive'], steps: '..x...x...x...x.', gain: -16, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ................ | ................ | ................ | ................ | ................ | ................ | ........X.......', gain: -12 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -12, pitch: 'root' },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 3.1 },
  },
})
