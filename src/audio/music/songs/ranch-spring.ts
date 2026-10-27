/**
 * The spring ranch (SOUND_UPGRADE §7.2). G Mixolydian, 6/8, dotted quarter = 60. Ocarina lead with the
 * alto recorder answering in the B section, harp arpeggio, cello pizzicato, a soft shaker; the Wildsong
 * motif is quoted at the top of B (on F, where Mixolydian holds its shape). A breath of meadow between
 * passes. Weather rules: cloudy mutes the sparkle; rain mutes the shaker and recorder, swaps the lead to
 * vibes and adds a viola pad; storm keeps only pad, harp and lead fragments with longer breaths. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'ranch-spring',
  kind: 'ranch',
  brief: 'Spring on the ranch: a lilting 6/8 ocarina tune over harp and pizzicato, a recorder answering in the gaps, birds and a brook between passes. Fresh and unhurried.',
  energy: 2,
  musicSend: 0.28,
  abc: `
X:1
M:6/8
L:1/8
Q:3/8=60
K:G mix
V:chords
[P:intro] "G"z6 | "C/G"z6 | "G"z6 | "F"z6 |
[P:A] "G"z6 | "C/G"z6 | "G"z6 | "F"z6 | "C"z6 | "G"z6 | "F"z6 | "G"z6 |
[P:B] "F"z6 | "G"z6 | "C"z6 | "G"z6 | "F"z6 | "C"z6 | "Dm"z6 | "G"z6 |
[P:A2] "G"z6 | "C/G"z6 | "G"z6 | "F"z6 | "C"z6 | "G"z6 | "F"z6 | "G"z6 |
[P:B2] "F"z6 | "G"z6 | "C"z6 | "G"z6 | "F"z6 | "C"z6 | "Dm"z6 | "G"z6 |
[P:A3] "G"z6 | "C/G"z6 | "G"z6 | "F"z6 | "C"z6 | "G"z6 | "F"z6 | "G"z6 |
V:lead
[P:intro] z6 | z6 | z6 | z6 |
[P:A] !mp! g2 e d2 e | g3- g2 z | a2 g e2 d | c3- c2 z | e2 g a2 g | b3- b2 z | a2 g f2 e | d3- d2 z |
[P:B] f2 g c'3 | b a g3 z | e2 g a2 b | c' b g3 z | c2 B c2 d | g3 e2 z | f2 e d2 e | d3 e d z |
[P:A2] g2 e d2 e | g2 a g2 z | a2 g e2 d | c2 d c2 z | e2 d c2 d | g3 d2 z | a2 g f2 g | g3- g2 z |
[P:B2] f2 g c'3 | b a g3 z | e2 g a2 b | c' b g3 z | a2 b a2 g | e3- e2 z | d2 e f2 e | d2 e d2 z |
[P:A3] g2 e d2 e | g3- g2 z | a2 g e2 d | c3- c2 z | g2 a g2 e | d3 B2 z | c2 d c2 A | B3- B2 z |
V:counter
[P:intro] z6 | z6 | z6 | z6 |
[P:A] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B] !p! z6 | z5 d | e3 c3 | d3- d2 z | z6 | z5 e | f3 a3 | g3- g2 z |
[P:A2] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:B2] !p! z6 | z5 d | e3 c3 | d3- d2 z | z6 | z5 e | f3 d3 | d3- d2 z |
[P:A3] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
`,
  parts: {
    lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    counter: { inst: 'recorder-alto', role: 'counter', layers: ['main'], gain: -5, pan: -0.25 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -7, pan: -0.15 },
    pizz: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['main'], octave: 2, gain: -9 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['weather'], octave: 3, gain: -14, pan: 0.2 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -18, pan: 0.3 },
  },
  perc: {
    grid: 12,
    lines: {
      shaker: { inst: 'shaker', layers: ['main'], steps: '..x..x..x..x', gain: -16, pan: 0.2 },
    },
  },
  order: ['intro', 'A', 'B', 'A2', 'breath', 'B2', 'A3'],
  loopFrom: 1,
  breath: [8, 20],
  weather: {
    cloudy: { gainDb: -1.5, mute: ['sparkle'] },
    rain: { mute: ['shaker', 'counter', 'sparkle'], add: ['pad'], swap: { lead: 'vibes' } },
    storm: { mute: ['shaker', 'counter', 'sparkle', 'pizz'], add: ['pad'], fragments: ['lead'], breath: [15, 30] },
  },
  motifQuote: { part: 'lead', section: 'B' },
})
