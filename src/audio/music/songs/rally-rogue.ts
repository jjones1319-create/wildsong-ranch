/**
 * Rogue's Rally (SOUND_UPGRADE §7.4): Hero's Rally turned sly. E Aeolian, 4/4, 118. The same tune and form
 * as `rally`, written in the minor: the clarinet sneaks it over pizzicato cellos and plucked violins, a soft
 * harp underneath, the knockout kit (cajon, darbuka, claves on the off-beats, claps every other bar). The
 * chord track follows the original by degree (I→i, V→v, vi→VI, IV and ii→iv, iii→VII). Derived from
 * `rally`. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'rally-rogue',
  kind: 'battle',
  brief: 'Rogue’s Rally: the heroes’ tune turned sly in E minor, a clarinet sneaking over pizzicato strings, claves on the off-beats and the odd clap. Mischievous, light on its feet.',
  energy: 4,
  musicSend: 0.2,
  kit: 'knockout',
  derivedFrom: 'rally',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=118
K:E min
V:chords
[P:lobby] "Em"z8 | "Am"z8 | "Bm"z8 | "Em"z8 | "C"z8 | "Am"z8 | "Bm"z8 | "Em"z8 |
[P:intro] "Em"z8 | "Em"z8 |
[P:A] "Em"z8 | "Bm"z8 | "C"z8 | "Am"z8 | "Em"z8 | "Am"z8 | "Bm"z8 | "Em"z8 |
[P:B] "Am"z8 | "Em"z8 | "Am"z8 | "C"z8 | "Am"z8 | "Em"z8 | "Am"z8 | "Bm"z8 |
[P:A2] "Em"z8 | "Bm"z8 | "C"z8 | "Am"z8 | "Em"z8 | "Am"z8 | "Bm"z8 | "Em"z8 |
[P:C] "C"z8 | "G"z8 | "Am"z8 | "Em"z8 | "C"z8 | "G"z8 | "Am"z8 | "Bm"z8 |
[P:B2] "Am"z8 | "Em"z8 | "Am"z8 | "C"z8 | "Am"z8 | "Em"z8 | "Bm"z8 | "Em"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] B3 B e2 g2 | f4 d2 B2 | c2 d2 e2 c2 | A6 z2 | B3 c B2 e2 | a3 g f2 c2 | d2 e2 f2 d2 | e6 z2 |
[P:B] c2 e2 a4 | g3 f e2 B2 | c3 d c2 A2 | G6 z2 | A3 B c2 e2 | g3 a g2 e2 | f2 e c A2 c2 | B6 z2 |
[P:A2] B3 B e2 g2 | f4 d2 B2 | c2 d2 e2 c2 | A6 z2 | e3 f g2 e2 | c3 B A2 F2 | F2 A2 B2 d2 | e6 z2 |
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
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z6 e2 | z8 | z8 | z8 | z6 e2 | z8 | z8 | z8 |
[P:B] z6 a2 | z8 | z8 | z8 | z6 a2 | z8 | z8 | z8 |
[P:A2] z6 e2 | z8 | z8 | z8 | z6 e2 | z8 | z8 | z8 |
[P:C] z6 e2 | z8 | z8 | z8 | z6 g2 | z8 | z8 | z8 |
[P:B2] z6 a2 | z8 | z8 | z8 | z6 a2 | z8 | z8 | z8 |
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
    lead: { inst: 'clarinet', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 2, pan: 0.05 },
    lobbyLead: { inst: 'clarinet', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    colour: { inst: 'harp', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base'], octave: 3, gain: -12, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -17, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -7 },
    pulse: { inst: 'violins', art: 'pizz', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -12, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -16, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X..x....X..x....', gain: -8 },
      mid: { role: 'mid', layers: ['drive'], steps: '....x......x....', gain: -13, pan: -0.2 },
      high: { role: 'high', layers: ['drive'], steps: '..x...x...x...x.', gain: -17, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ....X...........', gain: -13, pan: 0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 4.7 },
  },
})
