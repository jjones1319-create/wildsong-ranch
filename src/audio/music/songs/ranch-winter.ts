/**
 * The winter ranch (SOUND_UPGRADE §7.2). A Aeolian, 4/4, 66, sparse. Soft vibes carry long notes with a
 * glockenspiel doubling an octave up at pp in the A sections, a harp waltz figure and bowed vibes underneath,
 * cello pizzicato on the roots, sleigh bells only on the downbeats of B. The Wildsong motif opens B (on F,
 * where Aeolian keeps its shape). Weather: cloudy mutes the double; rain mutes bells and double, swaps the
 * lead to harp and adds a viola pad; snow adds a glock sparkle. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'ranch-winter',
  kind: 'ranch',
  brief: 'Winter on the ranch: slow, sparse vibes with a glock shadow an octave up, a harp turning gently underneath, bowed vibes humming, sleigh bells only on the downbeats of the B section. Hushed, cold outside, warm within.',
  energy: 2,
  musicSend: 0.35,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=66
K:A min
V:chords
[P:intro] "Am"z8 | "F"z8 |
[P:A] "Am"z8 | "F"z8 | "C"z8 | "G"z8 | "Am"z8 | "Dm"z8 | "Em"z8 | "Am"z8 |
[P:B] "F"z8 | "C"z8 | "G"z8 | "Am"z8 | "F"z8 | "C"z8 | "G"z8 | "Am"z8 |
[P:A2] "Am"z8 | "F"z8 | "C"z8 | "G"z8 | "Am"z8 | "Dm"z8 | "Em"z8 | "Am"z8 |
[P:B2] "F"z8 | "C"z8 | "G"z8 | "Am"z8 | "F"z8 | "C"z8 | "G"z8 | "Am"z8 |
V:lead
[P:intro] z8 | z8 |
[P:A] !mp! e4 d4 | c4- c2 z2 | g4 e4 | d4- d2 z2 | c4 e4 | f4 d4 | e4 g4 | a6 z2 |
[P:B] f4 g4 | c'4 b2 a2 | g6 z2 | c4 d4 | f4 e4 | g4 f4 | B4 d4 | e6 z2 |
[P:A2] e4 d4 | c4- c2 z2 | g4 e4 | d4- d2 z2 | a4 g4 | f4 e4 | e2 f2 d4 | c6 z2 |
[P:B2] f4 g4 | c'4 b2 a2 | g6 z2 | e2 d2 c4 | a2 g2 f4 | g2 f2 e4 | d2 c2 B4 | c2 d2 e4 |
V:double
[P:intro] z8 | z8 |
[P:A] !pp! e'4 d'4 | c'4- c'2 z2 | g'4 e'4 | d'4- d'2 z2 | c'4 e'4 | f'4 d'4 | e'4 g'4 | a'6 z2 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] !pp! e'4 d'4 | c'4- c'2 z2 | g'4 e'4 | d'4- d'2 z2 | a'4 g'4 | f'4 e'4 | e'4 d'4 | c'6 z2 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:bells
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] !p! C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] !p! C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 | C2 z6 |
`,
  parts: {
    lead: { inst: 'vibes', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    double: { inst: 'glock', role: 'colour', layers: ['main'], gain: -16, pan: 0.25 },
    bells: { inst: 'sleigh-bells', role: 'perc', layers: ['main'], gain: -16, pan: -0.3 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'waltz', layers: ['main'], octave: 3, gain: -9, pan: -0.2 },
    bowed: { inst: 'vibes', art: 'bowed', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -16, pan: 0.2 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -12 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['weather'], octave: 3, gain: -14, pan: -0.15 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['weather'], octave: 5, gain: -18, pan: 0.3 },
  },
  order: ['intro', 'A', 'B', 'A2', 'breath', 'B2'],
  loopFrom: 1,
  breath: [8, 20],
  weather: {
    cloudy: { gainDb: -1.5, mute: ['double'] },
    rain: { mute: ['bells', 'double'], add: ['pad'], swap: { lead: 'harp' } },
    storm: { mute: ['bells', 'double', 'bass'], add: ['pad'], fragments: ['lead'], breath: [15, 30] },
    snow: { add: ['sparkle'] },
  },
  motifQuote: { part: 'lead', section: 'B' },
})
