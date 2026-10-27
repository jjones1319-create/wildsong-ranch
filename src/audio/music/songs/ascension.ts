/**
 * The Ascensions (SOUND_UPGRADE §7.4): the promotion fights, a proud ceremonial march. B♭ Ionian, 4/4, 112.
 * Violins carry the tune with the horn doubling it an octave below in the A sections and calling back in
 * the B sections; the B section climbs through the Wildsong motif (from E♭, where it sits in B♭ major).
 * A viola pad, cello spiccato and a march bass underneath, the ceremony kit (timpani on one and three,
 * a soft bass drum, triangle, a cymbal swell into each new section). The lobby is a processional: organ and
 * horn alone. A `colour` line rings at each phrase start in the season's colour. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'ascension',
  kind: 'battle',
  brief: 'An Ascension: a proud, warm march in B♭ major, violins and horn in octaves, the Wildsong motif rising through the middle, timpani on one and three. Ceremonial and hopeful, never pompous.',
  energy: 4,
  musicSend: 0.26,
  kit: 'ceremony',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=112
K:Bb
V:chords
[P:lobby] "Bb"z8 | "Eb"z8 | "F"z8 | "Bb"z8 | "Gm"z8 | "Eb"z8 | "F"z8 | "Bb"z8 |
[P:intro] "Bb"z8 | "Bb"z8 |
[P:A] "Bb"z8 | "F"z8 | "Gm"z8 | "Eb"z8 | "Bb"z8 | "Eb"z8 | "F"z8 | "Bb"z8 |
[P:B] "Eb"z8 | "F"z8 | "Dm"z8 | "Gm"z8 | "Eb"z8 | "F"z8 | "Gm"z8 | "F"z8 |
[P:A2] "Bb"z8 | "F"z8 | "Gm"z8 | "Eb"z8 | "Bb"z8 | "Eb"z8 | "F"z8 | "Bb"z8 |
[P:C] "Gm"z8 | "Dm"z8 | "Eb"z8 | "Bb"z8 | "Gm"z8 | "Cm"z8 | "F"z8 | "F"z8 |
[P:B2] "Eb"z8 | "F"z8 | "Dm"z8 | "Gm"z8 | "Eb"z8 | "F"z8 | "Eb"z8 | "Bb"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] F3 F B2 c2 | d4 c2 A2 | B3 c d2 B2 | G6 z2 | F3 F B2 d2 | e4 d2 c2 | c3 d c2 A2 | B6 z2 |
[P:B] E2 F2 B4 | A2 G2 F4 | A3 B c2 d2 | d6 z2 | e3 d c2 B2 | c3 B A2 F2 | G3 A B2 d2 | c6 z2 |
[P:A2] F3 F B2 c2 | d4 c2 A2 | B3 c d2 B2 | G6 z2 | d3 c B2 F2 | G3 A B2 e2 | d3 c A2 c2 | B6 z2 |
[P:C] !mp! d4 B4 | A4 F4 | G3 A B2 G2 | F6 z2 | B3 c d2 g2 | g3 f e2 c2 | c4 A2 F2 | A6 z2 |
[P:B2] !mf! E2 F2 B4 | A2 G2 F4 | A3 B c2 d2 | d6 z2 | G3 B e2 d2 | c3 d e2 c2 | B3 A G2 B2 | B6 z2 |
V:lobbyLead
[P:lobby] !p! F4 G4 | B4 G4 | A4 c4 | B6 z2 | B4 c4 | d4 e4 | c4 A4 | B6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:lobbyHorn
[P:lobby] !p! D8 | E8 | C8 | D8 | D8 | E8 | C8 | D8 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:horn
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! F,3 F, B,2 C2 | D4 C2 A,2 | B,3 C D2 B,2 | G,6 z2 | z8 | z8 | z4 C2 F,2 | z4 F,2 B,2 |
[P:B] z8 | z4 A,2 C2 | z8 | z4 B,2 D2 | z8 | z4 A,2 F,2 | z8 | z4 C2 A,2 |
[P:A2] F,3 F, B,2 C2 | D4 C2 A,2 | B,3 C D2 B,2 | G,6 z2 | z8 | z8 | z4 C2 F,2 | z4 F,2 B,2 |
[P:C] !p! G,8 | A,8 | G,8 | F,8 | G,8 | G,8 | A,8 | C8 |
[P:B2] !mp! z8 | z4 A,2 C2 | z8 | z4 B,2 D2 | z8 | z4 A,2 F,2 | z8 | z4 F,2 B,2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! d2 z6 | z8 | z8 | z8 | f2 z6 | z8 | z8 | z8 |
[P:B] g2 z6 | z8 | z8 | z8 | g2 z6 | z8 | z8 | z8 |
[P:A2] d2 z6 | z8 | z8 | z8 | f2 z6 | z8 | z8 | z8 |
[P:C] d2 z6 | z8 | z8 | z8 | d2 z6 | z8 | z8 | z8 |
[P:B2] g2 z6 | z8 | z8 | z8 | g2 z6 | z8 | z8 | z8 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [B,DFB]4 z4 | z8 |
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
    lobbyLead: { inst: 'organ', role: 'lead', layers: ['lobby'], gain: -10 },
    lobbyHorn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['lobby'], gain: -9, pan: -0.2 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['drive', 'tension'], gain: -3, pan: -0.2 },
    colour: { inst: 'harp', role: 'colour', layers: ['drive', 'tension'], gain: -8, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -1 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -11 },
  },
  accomp: {
    lobbyOrgan: { inst: 'organ', role: 'accomp', pattern: 'padSustain', layers: ['lobby'], octave: 3, gain: -19 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['base', 'drive', 'tension'], octave: 3, size: 3, gain: -9, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, octaveJumps: true, gain: -4 },
    pulse: { inst: 'cellos', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -10, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -13, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -16, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -6, pitch: 'root' },
      mid: { role: 'mid', layers: ['drive'], steps: 'x...............', gain: -10 },
      high: { role: 'high', layers: ['drive'], steps: '....x.......x...', gain: -16, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ................ | ................ | ................ | ................ | ................ | ................ | ........X.......', gain: -12 },
      riser: { role: 'low', layers: ['tension'], steps: 'x...x...x...x...', gain: -11, pitch: 'root' },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  motifQuote: { part: 'lead', section: 'B' },
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: -0.6 },
  },
})
