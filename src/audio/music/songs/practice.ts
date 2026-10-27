/**
 * Practice (SOUND_UPGRADE §7.4): the Monster Lab's Versus and the Battle Lab. Light and neutral. C Ionian,
 * 4/4, 112. A marimba tune in skipping dotted rhythms, kalimba answers, harp, viola pizzicato pulse and a
 * pizzicato bass, the meadow kit with a busy shaker. No crowd. The lobby is the marimba alone. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'practice',
  kind: 'battle',
  brief: 'Practice in the Monster Lab: a light, neutral C major tune on marimba in skipping dotted rhythms, kalimba answers, pizzicato and shaker. Friendly and focused, no pressure.',
  energy: 3,
  musicSend: 0.18,
  kit: 'meadow',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=112
K:C
V:chords
[P:lobby] "C"z8 | "F"z8 | "G"z8 | "C"z8 | "Am"z8 | "F"z8 | "G"z8 | "C"z8 |
[P:intro] "C"z8 | "C"z8 |
[P:A] "C"z8 | "G"z8 | "Am"z8 | "F"z8 | "C"z8 | "Dm"z8 | "G"z8 | "C"z8 |
[P:B] "F"z8 | "G"z8 | "Em"z8 | "Am"z8 | "Dm"z8 | "G"z8 | "C"z8 | "G"z8 |
[P:A2] "C"z8 | "G"z8 | "Am"z8 | "F"z8 | "C"z8 | "Dm"z8 | "G"z8 | "C"z8 |
[P:C] "Am"z8 | "Em"z8 | "F"z8 | "C"z8 | "Am"z8 | "Em"z8 | "Dm"z8 | "G"z8 |
[P:B2] "F"z8 | "G"z8 | "Em"z8 | "Am"z8 | "Dm"z8 | "G"z8 | "C"z8 | "C"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] c>d e>d c2 G2 | B>A G>A B4 | c>B A>B c2 A2 | A2 G2 F4 | c>d e>f e2 c2 | d>e f>e d2 A2 | B>A G>A B2 d2 | c6 z2 |
[P:B] a4 g2 f2 | g4 f2 d2 | e4 d2 B2 | c4 B2 A2 | d2 e2 f2 e2 | d2 c2 B2 d2 | c2 e2 d2 c2 | B4 z4 |
[P:A2] c>d e>d c2 G2 | B>A G>A B4 | c>B A>B c2 A2 | A2 G2 F4 | G>A B>c d2 G2 | A>B c>d f2 d2 | d>c B>A G2 B2 | c6 z2 |
[P:C] !mp! e6 c2 | B6 A2 | A4 F4 | G6 z2 | A2 B2 c4 | B2 c2 B4 | d2 e2 f2 e2 | d6 z2 |
[P:B2] !mf! a4 g2 f2 | g4 f2 d2 | e4 d2 B2 | c4 B2 A2 | f2 e2 d2 c2 | B2 A2 B2 d2 | c>d e>f g2 e2 | c6 z2 |
V:lobbyLead
[P:lobby] !p! e4 c4 | c4 A4 | B4 d4 | c6 z2 | c4 d4 | f4 e4 | d4 B4 | c6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z6 d2 | z8 | z6 f2 | z8 | z6 a2 | z8 | z6 g2 |
[P:B] z8 | z6 g2 | z8 | z6 c'2 | z8 | z6 d'2 | z8 | z6 d2 |
[P:A2] z8 | z6 d2 | z8 | z6 f2 | z8 | z6 a2 | z8 | z6 e2 |
[P:C] z8 | z8 | z8 | z6 e2 | z8 | z8 | z8 | z6 d2 |
[P:B2] z8 | z6 g2 | z8 | z6 c'2 | z8 | z6 d'2 | z8 | z6 e2 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [C,E,G,C]4 z4 | z8 |
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
    lead: { inst: 'marimba', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 0, pan: 0.05 },
    lobbyLead: { inst: 'marimba', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    colour: { inst: 'kalimba', role: 'colour', layers: ['drive', 'tension'], gain: -10, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -11, pan: -0.2 },
    pulse: { inst: 'violas', art: 'pizz', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -13, pan: -0.1 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['base', 'drive', 'tension'], octave: 3, size: 3, gain: -18, pan: 0.15 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -20, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -9 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'xxx.xxx.xxx.xxx.', gain: -18, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ............x...', gain: -15, pan: -0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 7.2 },
  },
})
