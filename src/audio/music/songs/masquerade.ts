/**
 * The Masquerade Cup (SOUND_UPGRADE §7.4): a masked ball. C harmonic minor (`K:C min =b`), 3/4, 126. The
 * clarinet leads a sly, elegant waltz that opens on the masked motif (a chromatic turn, G–A♭–G–F♯–G) and
 * turns it again before the end; the harpsichord plays the waltz and answers each phrase, pizzicato cellos
 * walk the bass, a thin viola pad, and the masque kit (a muted frame drum, a light tambourine, a finger
 * cymbal every other bar). The lobby is the clarinet alone over the harpsichord. The crowd is hushed.
 * Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'masquerade',
  kind: 'battle',
  brief: 'The Masquerade: a masked ball in C harmonic minor, a sly clarinet waltz over harpsichord and pizzicato, the masked chromatic turn, a muted drum and finger cymbals. Elegant and mysterious, a little playful.',
  energy: 4,
  musicSend: 0.27,
  kit: 'masque',
  abc: `
X:1
M:3/4
L:1/8
Q:1/4=126
K:C min =b
V:chords
[P:lobby] "Cm"z6 | "Fm"z6 | "G"z6 | "Cm"z6 | "Ab"z6 | "Fm"z6 | "G"z6 | "G"z6 |
[P:intro] "Cm"z6 | "Cm"z6 |
[P:A] "Cm"z6 | "G"z6 | "Cm"z6 | "Fm"z6 | "Ab"z6 | "Fm"z6 | "G"z6 | "Cm"z6 |
[P:B] "Fm"z6 | "Cm"z6 | "Ab"z6 | "G"z6 | "Fm"z6 | "Cm"z6 | "Ab"z6 | "G"z6 |
[P:A2] "Cm"z6 | "G"z6 | "Cm"z6 | "Fm"z6 | "Ab"z6 | "Fm"z6 | "G"z6 | "Cm"z6 |
[P:C] "Ab"z6 | "Fm"z6 | "Cm"z6 | "G"z6 | "Ab"z6 | "Fm"z6 | "G"z6 | "G"z6 |
[P:B2] "Fm"z6 | "Cm"z6 | "Ab"z6 | "G"z6 | "Fm"z6 | "Cm"z6 | "G"z6 | "Cm"z6 |
[P:A3] "Cm"z6 | "G"z6 | "Cm"z6 | "Fm"z6 | "Ab"z6 | "Fm"z6 | "G"z6 | "Cm"z6 |
V:lead
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] z6 | z6 |
[P:A] G A G ^F G2 | B2 c2 d2 | e3 d c2 | A4 z2 | c2 e2 A2 | F3 G A2 | B2 d2 B2 | c4 z2 |
[P:B] f3 e d2 | e2 c2 G2 | A2 c2 e2 | d4 z2 | c3 d e2 | g3 f e2 | e2 d2 c2 | B4 z2 |
[P:A2] G A G ^F G2 | B2 c2 d2 | e3 d c2 | A4 z2 | A3 B c2 | d2 c2 A2 | G2 B2 d2 | c2 G2 E2 |
[P:C] !mp! c6 | A4 F2 | G3 A G2 | D4 z2 | E2 A2 c2 | f3 e c2 | d2 B2 G2 | d4 z2 |
[P:B2] !mf! f3 e d2 | e2 c2 G2 | A2 c2 e2 | d4 z2 | A3 G F2 | G2 c2 e2 | d3 c B2 | c6 |
[P:A3] G A G ^F G2 | B2 c2 d2 | e3 d c2 | A4 z2 | e2 c2 A2 | F2 A2 c2 | B c B ^A B2 | c4 z2 |
V:lobbyLead
[P:lobby] !p! G4 F2 | A4 G2 | B4 c2 | c4 z2 | c4 B2 | A4 G2 | G4 F2 | G4 z2 |
[P:intro] z6 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
V:colour
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] z6 | z6 |
[P:A] !mp! z6 | z6 | z6 | z2 A2 c2 | z6 | z6 | z6 | z2 e2 g2 |
[P:B] z6 | z6 | z6 | z2 B2 d2 | z6 | z6 | z6 | z2 d2 B2 |
[P:A2] z6 | z6 | z6 | z2 A2 c2 | z6 | z6 | z6 | z2 e2 g2 |
[P:C] z6 | z6 | z6 | z2 B2 d2 | z6 | z6 | z6 | z2 g2 d2 |
[P:B2] z6 | z6 | z6 | z2 B2 d2 | z6 | z6 | z6 | z2 e2 c2 |
[P:A3] z6 | z6 | z6 | z2 A2 c2 | z6 | z6 | z6 | z2 e2 g2 |
V:hit
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] !mf! [C,E,G,C]4 z2 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
V:boom
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] !mf! C2 z4 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:C] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
`,
  parts: {
    lead: { inst: 'clarinet', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 1, pan: 0.05 },
    lobbyLead: { inst: 'clarinet', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    colour: { inst: 'harpsichord', role: 'colour', layers: ['drive', 'tension'], gain: -10, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    waltz: { inst: 'harpsichord', role: 'accomp', pattern: 'waltz', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -10, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['base', 'drive', 'tension'], octave: 3, size: 3, gain: -17, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -16, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -20, pan: 0.3 },
  },
  perc: {
    grid: 12,
    lines: {
      low: { role: 'low', art: 'muted', layers: ['base', 'drive'], steps: 'X...........', gain: -10 },
      high: { role: 'high', layers: ['drive'], steps: '............ | ........x...', gain: -20, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: '....x...x...', gain: -17, pan: -0.15 },
      riser: { role: 'low', art: 'muted', layers: ['tension'], steps: 'x...x...x...', gain: -14 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2', 'A3'],
  loopFrom: 2,
  quotes: [
    { motif: 'masked', part: 'lead', section: 'A' },
    { motif: 'masked', part: 'lead', section: 'A3' },
  ],
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 5.8 },
  },
})
