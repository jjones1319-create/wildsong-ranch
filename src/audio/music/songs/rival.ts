/**
 * The Rival Showdown (SOUND_UPGRADE §7.4), and any match against Corin Hale: confident, cheeky. G
 * Mixolydian, 4/4, 124. The violins open every A section on Corin's motif (a cocky rising G–B–D–G) and the
 * horn echoes it from below; the C section is stop-time, the tune in little step-pairs with gaps for the
 * crowd. Strumstick strums, violin spiccato, pizzicato bass, the festival kit with syncopated cajon and
 * claps every other bar. The lobby is the violins alone, warm. In another event it takes that event's lead
 * and kit (the Corin rule). Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'rival',
  kind: 'battle',
  brief: 'The Rival Showdown: a confident, cheeky G Mixolydian tune that struts in on Corin’s rising motif, horn echoes, a stop-time middle, strumstick and spiccato strings, syncopated cajon. Playful swagger, never mean.',
  energy: 4,
  musicSend: 0.22,
  kit: 'festival',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=124
K:G mix
V:chords
[P:lobby] "G"z8 | "F"z8 | "C"z8 | "G"z8 | "Em"z8 | "F"z8 | "Dm"z8 | "G"z8 |
[P:intro] "G"z8 | "G"z8 |
[P:A] "G"z8 | "F"z8 | "G"z8 | "C"z8 | "G"z8 | "Am"z8 | "Dm"z8 | "G"z8 |
[P:B] "C"z8 | "G"z8 | "F"z8 | "C"z8 | "Am"z8 | "Em"z8 | "F"z8 | "G"z8 |
[P:A2] "G"z8 | "F"z8 | "G"z8 | "C"z8 | "Em"z8 | "Am"z8 | "Dm"z8 | "G"z8 |
[P:C] "Em"z8 | "Am"z8 | "F"z8 | "G"z8 | "Em"z8 | "Am"z8 | "Dm"z8 | "G"z8 |
[P:B2] "C"z8 | "G"z8 | "F"z8 | "C"z8 | "Am"z8 | "Em"z8 | "F"z8 | "G"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] G B d g3 f e | d2 c2 A2 c2 | B3 c d2 B2 | e6 z2 | d2 B2 G2 A B | c3 B A2 E2 | F3 G A2 c2 | B6 z2 |
[P:B] e2 f g2 e c d | B2 d2 z4 | c2 d e f2 a2 | g2 e2 z4 | a3 g e2 c2 | B3 c B2 G2 | A2 c2 f2 e2 | d6 z2 |
[P:A2] G B d g3 f e | d2 c2 A2 c2 | B3 c d2 B2 | e6 z2 | e2 B2 G2 B c | A3 B c2 e2 | d3 c A2 F2 | G6 z2 |
[P:C] !mp! B2 c2 B2 z2 | A2 B2 c2 z2 | c2 d2 c2 z2 | B2 A2 G2 z2 | G2 A2 B2 z2 | c2 d2 e2 z2 | f2 e2 d2 z2 | g6 z2 |
[P:B2] !mf! e2 f g2 e c d | B2 d2 z4 | c2 d e f2 a2 | g2 e2 z4 | e3 d c2 A2 | G2 B2 e2 d2 | c3 B A2 c2 | B2 d2 g2 z2 |
V:lobbyLead
[P:lobby] !p! B4 A4 | A4 c4 | c4 e4 | d6 z2 | e4 d4 | c4 A4 | A4 F4 | G6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z8 | z8 | z4 C,E,G,C | z8 | z8 | z8 | z4 G,2 D2 |
[P:B] z8 | z4 D2 B,2 | z8 | z4 E2 C2 | z8 | z4 B,2 E2 | z8 | z4 D2 G,2 |
[P:A2] z8 | z8 | z8 | z4 C,E,G,C | z8 | z8 | z8 | z4 G,2 D2 |
[P:C] G,2 z6 | A,2 z6 | A,2 z6 | B,2 z6 | B,2 z6 | A,2 z6 | A,2 z6 | B,2 z6 |
[P:B2] z8 | z4 D2 B,2 | z8 | z4 E2 C2 | z8 | z4 B,2 E2 | z8 | z4 D2 G,2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z6 f2 | z8 | z8 | z8 | z6 a2 | z8 | z8 |
[P:B] z8 | z6 g2 | z8 | z8 | z8 | z6 e2 | z8 | z8 |
[P:A2] z8 | z6 f2 | z8 | z8 | z8 | z6 a2 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z6 g2 | z8 | z8 | z8 | z6 e2 | z8 | z8 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [G,B,DG]4 z4 | z8 |
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
    colour: { inst: 'strumstick', role: 'colour', layers: ['drive', 'tension'], gain: -8, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -1 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -11 },
  },
  accomp: {
    strum: { inst: 'strumstick', role: 'accomp', pattern: 'strum', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -6, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -10, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -5 },
    pulse: { inst: 'violins', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -10, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -13, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -16, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X..x..x.X.......', gain: -5 },
      mid: { role: 'mid', layers: ['drive'], steps: '....x.x.....x.x.', gain: -10, pan: -0.2 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -14, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ....X.......X...', gain: -9, pan: 0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -12 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  quotes: [
    { motif: 'corin', part: 'lead', section: 'A' },
    { motif: 'corin', part: 'horn', section: 'A' },
  ],
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: -0.8 },
  },
})
