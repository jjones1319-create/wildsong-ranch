/**
 * The Crown of Embers (SOUND_UPGRADE §7.4): warm fire. A Phrygian dominant (`K:A phr ^c`), 4/4, 126. A low
 * flute winds through the scale's step-and-a-half (B♭ to C♯), the strumstick strums under it, cello
 * spiccato ticks like embers, and the harvest kit (frame drum, darbuka, woodblock, tambourine) keeps a
 * dancing pulse. The chords lean on B♭ against A. The lobby is the flute alone over strums and a viola
 * pad. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'crown-embers',
  kind: 'battle',
  brief: 'The Crown of Embers: warm fire in A Phrygian dominant, a low flute winding over strumstick strums and cello spiccato, darbuka and woodblock dancing. Glowing and rhythmic, never fierce.',
  energy: 5,
  musicSend: 0.24,
  kit: 'harvest',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=126
K:A phr ^c
V:chords
[P:lobby] "A"z8 | "Bb"z8 | "A"z8 | "Dm"z8 | "Gm"z8 | "Bb"z8 | "A"z8 | "A"z8 |
[P:intro] "A"z8 | "A"z8 |
[P:A] "A"z8 | "Bb"z8 | "A"z8 | "Gm"z8 | "Dm"z8 | "Bb"z8 | "Gm"z8 | "A"z8 |
[P:B] "Dm"z8 | "Gm"z8 | "Bb"z8 | "A"z8 | "Dm"z8 | "Gm"z8 | "Bb"z8 | "A"z8 |
[P:A2] "A"z8 | "Bb"z8 | "A"z8 | "Gm"z8 | "Dm"z8 | "Gm"z8 | "Bb"z8 | "A"z8 |
[P:C] "Bb"z8 | "A"z8 | "Bb"z8 | "A"z8 | "Gm"z8 | "Dm"z8 | "Bb"z8 | "A"z8 |
[P:B2] "Dm"z8 | "Gm"z8 | "Bb"z8 | "A"z8 | "Dm"z8 | "Gm"z8 | "Bb"z8 | "A"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] A2 B c e2 d c | d2 B2 F2 G A | B2 A G A4 | G6 z2 | F2 A d2 c d e | f3 e d2 B2 | d2 c B G2 B2 | A6 z2 |
[P:B] d3 e f2 d2 | B3 c d2 B2 | f2 e d B2 d2 | c4 e2 z2 | f3 g f e d2 | g3 f d2 B2 | c2 d2 B2 F2 | c6 z2 |
[P:A2] A2 B c e2 d c | d2 B2 F2 G A | B2 A G A4 | G6 z2 | A2 d2 e f d2 | B2 d2 c B G2 | F2 G A B2 d2 | c2 B2 A2 z2 |
[P:C] !mp! F4 B4 | A4 c4 | d4 B2 G2 | A6 z2 | G3 A B2 d2 | f3 e d2 A2 | B3 c d2 f2 | e6 z2 |
[P:B2] !mf! d3 e f2 d2 | B3 c d2 B2 | f2 e d B2 d2 | c4 e2 z2 | A3 B A2 F2 | G2 A B d2 B2 | d3 c B2 G2 | A6 z2 |
V:lobbyLead
[P:lobby] !p! A4 c4 | d4 B4 | A4 G4 | F6 z2 | G4 B4 | d4 c4 | B4 A4- | A6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z8 | z8 | z4 B2 d2 | z8 | z8 | z8 | z4 c2 e2 |
[P:B] z8 | z8 | z8 | z4 a2 e2 | z8 | z8 | z8 | z4 e2 a2 |
[P:A2] z8 | z8 | z8 | z4 B2 d2 | z8 | z8 | z8 | z4 c2 e2 |
[P:C] z8 | z8 | z8 | z4 c2 e2 | z8 | z8 | z8 | z4 a2 c'2 |
[P:B2] z8 | z8 | z8 | z4 a2 e2 | z8 | z8 | z8 | z4 c2 e2 |
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
    lead: { inst: 'flute', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 3, pan: 0.05 },
    lobbyLead: { inst: 'flute', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    colour: { inst: 'strumstick', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    strum: { inst: 'strumstick', role: 'accomp', pattern: 'strum', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -9, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, size: 3, gain: -15, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, gain: -7 },
    pulse: { inst: 'cellos', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 2, gain: -12, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.....x.X.......', gain: -8 },
      mid: { role: 'mid', layers: ['drive'], steps: '...x..x....x.x..', gain: -12, pan: -0.2 },
      high: { role: 'high', layers: ['drive'], steps: '..x...x...x...x.', gain: -17, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ........X.......', gain: -13, pan: 0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 1.1 },
  },
})
