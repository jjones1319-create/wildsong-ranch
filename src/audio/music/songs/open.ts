/**
 * The New Year Open (SOUND_UPGRADE §7.4): a winter festival. A Mixolydian, 4/4, 126. A plucky strumstick
 * tune that steps up and down the scale like a dance, doubled by the glock in its A sections, horn calls
 * answering at the end of each phrase, harp and pizzicato underneath, festival percussion with claps on two
 * and four. The lobby is the violins alone over harp and a viola pad, slow and warm. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'open',
  kind: 'battle',
  brief: 'The New Year Open: a bright winter-festival dance in A Mixolydian, a strumstick tune with glock sparkle and horn calls, cajon, bongos and claps on two and four. Cheerful and busy, never loud.',
  energy: 4,
  musicSend: 0.24,
  kit: 'festival',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=126
K:A mix
V:chords
[P:lobby] "A"z8 | "G"z8 | "D"z8 | "A"z8 | "F#m"z8 | "G"z8 | "D"z8 | "A"z8 |
[P:intro] "A"z8 | "A"z8 |
[P:A] "A"z8 | "A"z8 | "G"z8 | "D"z8 | "A"z8 | "Em"z8 | "G"z8 | "A"z8 |
[P:B] "D"z8 | "A"z8 | "G"z8 | "D"z8 | "Bm"z8 | "G"z8 | "Em"z8 | "A"z8 |
[P:A2] "A"z8 | "A"z8 | "G"z8 | "D"z8 | "Bm"z8 | "G"z8 | "D"z8 | "A"z8 |
[P:C] "F#m"z8 | "D"z8 | "G"z8 | "A"z8 | "F#m"z8 | "D"z8 | "Em"z8 | "A"z8 |
[P:B2] "D"z8 | "A"z8 | "G"z8 | "D"z8 | "Bm"z8 | "G"z8 | "Em"z8 | "A"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] A2 B c d2 c B | c2 e2 A2 z2 | B2 d2 g2 f e | d2 f2 d2 z2 | e2 c A B c d e | g2 f e d2 B2 | d2 B G A2 B2 | c4 A2 z2 |
[P:B] f3 e d2 A2 | c d e2 a2 z2 | g2 f g d2 B2 | c2 d4 z2 | f2 f e d c B2 | d2 e d B2 G2 | G2 A B e2 d2 | c6 z2 |
[P:A2] A2 B c d2 c B | c2 e2 A2 z2 | B2 d2 g2 f e | d2 f2 d2 z2 | d2 f2 e d c B | B c d2 g2 f e | f2 e d A2 B2 | A6 z2 |
[P:C] A3 B c2 A2 | B2 A2 F4 | G2 A B d2 B2 | c4 z4 | c3 d e2 c2 | d2 e f a4 | g2 f e B2 d2 | c2 B2 A2 z2 |
[P:B2] f3 e d2 A2 | c d e2 a2 z2 | g2 f g d2 B2 | c2 d4 z2 | B2 d2 f e d B | d2 B c d2 g2 | f2 e d B2 e2 | e2 c2 A2 z2 |
V:lobbyLead
[P:lobby] !p! c4 e4 | d4 B4 | A4 B4 | c6 z2 | c4 B4 | B4 d4 | d4 e4 | c6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z4 A,2 C2 | z8 | z4 A,2 D2 | z8 | z4 B,2 E2 | z8 | z4 E2 C2 |
[P:B] z8 | z4 C2 E2 | z8 | z4 D2 A,2 | z8 | z4 D2 B,2 | z8 | z4 C2 A,2 |
[P:A2] z8 | z4 A,2 C2 | z8 | z4 A,2 D2 | z8 | z4 B,2 E2 | z8 | z4 E2 C2 |
[P:C] !p! A,8 | A,8 | B,8 | C8 | C8 | D8 | B,8 | C4 z4 |
[P:B2] !mp! z8 | z4 C2 E2 | z8 | z4 D2 A,2 | z8 | z4 D2 B,2 | z8 | z4 C2 A,2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !p! a2 b c' d'2 c' b | c'2 e'2 a2 z2 | b2 d'2 g'2 f' e' | d'2 f'2 d'2 z2 | z8 | z8 | z8 | z8 |
[P:B] f'2 z6 | z8 | z8 | z8 | f'2 z6 | z8 | z8 | z8 |
[P:A2] a2 b c' d'2 c' b | c'2 e'2 a2 z2 | b2 d'2 g'2 f' e' | d'2 f'2 d'2 z2 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] f'2 z6 | z8 | z8 | z8 | f'2 z6 | z8 | z8 | z8 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [A,CEA]4 z4 | z8 |
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
    lead: { inst: 'strumstick', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 2, pan: 0.05 },
    lobbyLead: { inst: 'violins', art: 'vib', role: 'lead', layers: ['lobby'], gain: -5, pan: -0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['drive', 'tension'], gain: -7, pan: -0.25 },
    colour: { inst: 'glock', role: 'colour', layers: ['drive', 'tension'], gain: -14, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -9, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, gain: -15, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -7 },
    pulse: { inst: 'violas', art: 'pizz', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -12, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 3, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.....x...X.....', gain: -8 },
      mid: { role: 'mid', layers: ['drive'], steps: '....x.....x.x...', gain: -12, pan: -0.2 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -16, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: '....X.......X...', gain: -12, pan: 0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -16 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 8.2 },
  },
})
