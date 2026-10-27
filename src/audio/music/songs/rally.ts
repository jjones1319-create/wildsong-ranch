/**
 * Hero's Rally (SOUND_UPGRADE §7.4): heroic. E Ionian, 4/4, 118. The violins sing a bold tune that leaps up
 * a fourth and a third and comes down by step; the horn doubles it two octaves below in the A sections
 * (horn and violins in octaves, since the horn's samples stop at middle C) and calls in the B sections. Harp,
 * viola pad, cello spiccato, a march-like bass, the wild kit (frame drum, darbuka, shaker, a bass-drum boom
 * every four bars). The lobby is the violins alone. `rally-rogue` is derived from it. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'rally',
  kind: 'battle',
  brief: 'Hero’s Rally: a bold, open-hearted E major tune for the brave, violins and horn in octaves over frame drum and darbuka, a bass-drum boom every four bars. Heroic and generous.',
  energy: 4,
  musicSend: 0.24,
  kit: 'wild',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=118
K:E
V:chords
[P:lobby] "E"z8 | "A"z8 | "B"z8 | "E"z8 | "C#m"z8 | "A"z8 | "B"z8 | "E"z8 |
[P:intro] "E"z8 | "E"z8 |
[P:A] "E"z8 | "B"z8 | "C#m"z8 | "A"z8 | "E"z8 | "F#m"z8 | "B"z8 | "E"z8 |
[P:B] "A"z8 | "E"z8 | "F#m"z8 | "C#m"z8 | "A"z8 | "E"z8 | "F#m"z8 | "B"z8 |
[P:A2] "E"z8 | "B"z8 | "C#m"z8 | "A"z8 | "E"z8 | "F#m"z8 | "B"z8 | "E"z8 |
[P:C] "C#m"z8 | "G#m"z8 | "A"z8 | "E"z8 | "C#m"z8 | "G#m"z8 | "F#m"z8 | "B"z8 |
[P:B2] "A"z8 | "E"z8 | "F#m"z8 | "C#m"z8 | "A"z8 | "E"z8 | "B"z8 | "E"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] B3 B e2 g2 | f4 d2 B2 | c3 d e2 c2 | A6 z2 | B3 c B2 e2 | a3 g f2 c2 | d3 e f2 d2 | e6 z2 |
[P:B] c2 e2 a4 | g3 f e2 B2 | c3 d c2 A2 | G6 z2 | A3 B c2 e2 | g3 a g2 e2 | f2 e c A2 c2 | B6 z2 |
[P:A2] B3 B e2 g2 | f4 d2 B2 | c3 d e2 c2 | A6 z2 | e3 f g2 e2 | c3 B A2 F2 | F3 G A2 d2 | e6 z2 |
[P:C] !mp! e4 c4 | B4 d4 | c3 B A2 c2 | g6 z2 | g2 e2 f e c2 | d3 c B2 G2 | A3 B c2 f2 | f6 z2 |
[P:B2] !mf! c2 e2 a4 | g3 f e2 B2 | c3 d c2 A2 | G6 z2 | e3 d c2 A2 | B3 c e2 g2 | f2 g2 f d B2 | e6 z2 |
V:lobbyLead
[P:lobby] !p! G4 B4 | A4 c4 | B4 d4 | e6 z2 | e4 c4 | c4 A4 | B4 A4 | G6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mf! B,,3 B,, E,2 G,2 | F,4 D,2 B,,2 | C,3 D, E,2 C,2 | A,,6 z2 | B,,3 C, B,,2 E,2 | A,3 G, F,2 C,2 | D,3 E, F,2 D,2 | E,6 z2 |
[P:B] !mp! z8 | z4 B,2 E2 | z8 | z4 G,2 C2 | z8 | z4 B,2 E2 | z8 | z4 D2 B,2 |
[P:A2] !mf! B,,3 B,, E,2 G,2 | F,4 D,2 B,,2 | C,3 D, E,2 C,2 | A,,6 z2 | E,3 F, G,2 E,2 | C,3 B,, A,,2 F,,2 | F,,3 G,, A,,2 D,2 | E,6 z2 |
[P:C] !p! E,8 | D,8 | C,8 | B,,8 | E,8 | D,8 | C,8 | D,8 |
[P:B2] !mp! z8 | z4 B,2 E2 | z8 | z4 G,2 C2 | z8 | z4 B,2 E2 | z8 | z4 D2 B,2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! e2 z6 | z8 | z8 | z8 | e2 z6 | z8 | z8 | z8 |
[P:B] a2 z6 | z8 | z8 | z8 | a2 z6 | z8 | z8 | z8 |
[P:A2] e2 z6 | z8 | z8 | z8 | e2 z6 | z8 | z8 | z8 |
[P:C] e2 z6 | z8 | z8 | z8 | g2 z6 | z8 | z8 | z8 |
[P:B2] a2 z6 | z8 | z8 | z8 | a2 z6 | z8 | z8 | z8 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [E,G,B,E]4 z4 | z8 |
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
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['drive', 'tension'], gain: -3, pan: -0.2 },
    colour: { inst: 'harp', role: 'colour', layers: ['drive', 'tension'], gain: -8, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -1 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -11 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -7, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -11, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, octaveJumps: true, gain: -4 },
    pulse: { inst: 'cellos', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 2, gain: -9, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -13, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -16, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......X...x...', gain: -5 },
      mid: { role: 'mid', layers: ['drive'], steps: '..x...x...x...x.', gain: -10, pan: -0.2 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -14, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: 'X............... | ................ | ................ | ................', gain: -8 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -12 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 5.4 },
  },
})
