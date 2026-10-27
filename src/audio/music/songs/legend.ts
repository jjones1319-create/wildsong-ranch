/**
 * The Wildsong Legend (SOUND_UPGRADE §7.4): the main theme as a grand battle. D Lydian, 4/4, 120. The
 * violins sing the Wildsong melody with the horn two octaves below, the B section climbs to a heroic new
 * phrase, the C section drops to a breakdown where the ocarina plays alone over the harp, and the last B
 * comes home on D. The ceremony kit (timpani, bass drum, triangle, a cymbal swell into each section). The
 * lobby is the motif on a quiet ocarina. Derived from `wildsong` (its A phrases quote the title theme).
 * Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'legend',
  kind: 'battle',
  brief: 'The Wildsong Legend: the main theme as the grandest battle, violins and horn in octaves over timpani, a heroic climb, then an ocarina alone over harp before the last rise. Warm, full and moving, never bombastic.',
  energy: 5,
  musicSend: 0.28,
  kit: 'ceremony',
  derivedFrom: 'wildsong',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=120
K:D lyd
V:chords
[P:lobby] "D"z8 | "E/D"z8 | "D"z8 | "A/C#"z8 | "D"z8 | "E"z8 | "Bm"z8 | "A"z8 |
[P:intro] "D"z8 | "D"z8 |
[P:A] "D"z8 | "E"z8 | "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "Bm"z8 | "A"z4 "D"z4 |
[P:B] "E"z8 | "A"z8 | "Bm"z8 | "F#m"z8 | "E"z8 | "A"z8 | "D"z8 | "D"z8 |
[P:A2] "D"z8 | "E"z8 | "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "Bm"z8 | "A"z4 "D"z4 |
[P:C] "Bm"z8 | "F#m"z8 | "E"z8 | "A"z8 | "Bm"z8 | "F#m"z8 | "E"z8 | "E"z8 |
[P:B2] "E"z8 | "A"z8 | "Bm"z8 | "F#m"z8 | "E"z8 | "A"z8 | "D"z8 | "D"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] d2 e2 a4 | g f e4 z2 | f2 a b a2 f2 | e2 c2 e2 z2 | d2 e2 a3 b | a g f2 e2 z2 | f2 a2 f2 d2 | e2 c2 d2 z2 |
[P:B] B3 c e2 g2 | a4 e2 c2 | d3 e f2 d2 | c6 z2 | e3 f g2 e2 | a3 g e2 c2 | d3 e f2 a2 | f6 z2 |
[P:A2] d2 e2 a4 | g f e4 z2 | f2 a b a2 f2 | e2 c2 e2 z2 | a2 b a f2 d2 | e2 d2 e2 z2 | f2 a2 b a f2 | f2 e2 d2 z2 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] B3 c e2 g2 | a4 e2 c2 | d3 e f2 d2 | c6 z2 | e3 g f2 B2 | c3 d e2 a2 | f3 e d2 A2 | d6 z2 |
V:solo
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] !mp! f4 e2 d2 | c4 z4 | B2 c2 e2 f2 | e4 z4 | b3 a f2 d2 | c3 d e2 c2 | e3 f g2 a2 | g6 z2 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:lobbyLead
[P:lobby] !p! d2 e2 a4 | g f e4 z2 | f4 d4 | c6 z2 | d2 e2 f4 | e4 B4 | d4 f4 | e6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mf! D,2 E,2 A,4 | G, F, E,4 z2 | F,2 A, B, A,2 F,2 | E,2 C,2 E,2 z2 | D,2 E,2 A,3 B, | A, G, F,2 E,2 z2 | F,2 A,2 F,2 D,2 | E,2 C,2 D,2 z2 |
[P:B] B,,3 C, E,2 G,2 | A,4 E,2 C,2 | z8 | z4 C,2 E,2 | z8 | z8 | D,3 E, F,2 A,2 | F,6 z2 |
[P:A2] D,2 E,2 A,4 | G, F, E,4 z2 | F,2 A, B, A,2 F,2 | E,2 C,2 E,2 z2 | A,2 B, A, F,2 D,2 | E,2 D,2 E,2 z2 | F,2 A,2 B, A, F,2 | F,2 E,2 D,2 z2 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] B,,3 C, E,2 G,2 | A,4 E,2 C,2 | z8 | z4 C,2 E,2 | z8 | z8 | F,3 E, D,2 A,,2 | D,6 z2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z6 e'2 | z8 | z4 c'2 e'2 | z8 | z6 e'2 | z8 | z4 a2 d'2 |
[P:B] z8 | z4 e'2 a'2 | z8 | z6 c'2 | z8 | z4 e'2 a'2 | z8 | z4 f'2 a'2 |
[P:A2] z8 | z6 e'2 | z8 | z4 c'2 e'2 | z8 | z6 e'2 | z8 | z4 a2 d'2 |
[P:C] f'4 z4 | z8 | z8 | z8 | f'4 z4 | z8 | z8 | z8 |
[P:B2] z8 | z4 e'2 a'2 | z8 | z6 c'2 | z8 | z4 e'2 a'2 | z8 | z4 f'2 a'2 |
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
    lead: { inst: 'violins', art: 'vib', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 2, pan: 0.05 },
    solo: { inst: 'ocarina', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 2, pan: 0.05 },
    lobbyLead: { inst: 'ocarina', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['drive', 'tension'], gain: -6, pan: -0.2 },
    colour: { inst: 'glock', role: 'colour', layers: ['drive', 'tension'], gain: -14, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -9, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -14, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, octaveJumps: true, gain: -7 },
    pulse: { inst: 'cellos', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 2, gain: -12, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -16, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -9, pitch: 'root' },
      mid: { role: 'mid', layers: ['drive'], steps: 'x...............', gain: -13 },
      high: { role: 'high', layers: ['drive'], steps: '....x.......x...', gain: -19, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ................ | ................ | ................ | ................ | ................ | ................ | ........X.......', gain: -14 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -15, pitch: 'root' },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  motifQuote: { part: 'lead', section: 'A' },
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: -0.5 },
  },
})
