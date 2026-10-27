/**
 * The summer ranch (SOUND_UPGRADE §7.2). C Lydian, 4/4, 84 with a light swing. Marimba carries the A
 * sections, the flute takes B (where it quotes the Wildsong motif, which sits naturally in Lydian), a
 * kalimba ostinato keeps the afternoon moving, contrabass pizzicato underneath, soft bongos and a shaker.
 * Weather: cloudy mutes the sparkle; rain mutes the drums, swaps the marimba to harp and the flute to vibes
 * and adds a viola pad; storm keeps only pad, kalimba and lead fragments with longer breaths. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'ranch-summer',
  kind: 'ranch',
  brief: 'Summer on the ranch: a lazy, swung marimba tune with a kalimba ticking underneath, the flute taking over for the brighter B section, bongos and a shaker far back. Warm, unhurried, a little playful.',
  energy: 2,
  musicSend: 0.25,
  swing: 0.56,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=84
K:C lyd
V:chords
[P:intro] "C"z8 | "D/C"z8 | "C"z8 | "G/B"z8 |
[P:A] "C"z8 | "D/C"z8 | "C"z8 | "G/B"z8 | "Am"z8 | "D"z8 | "G"z8 | "C"z8 |
[P:B] "C"z8 | "D/C"z8 | "Am"z8 | "G"z8 | "C"z8 | "D"z8 | "G"z8 | "C"z8 |
[P:A2] "C"z8 | "D/C"z8 | "C"z8 | "G/B"z8 | "Am"z8 | "D"z8 | "G"z8 | "C"z8 |
[P:B2] "C"z8 | "D/C"z8 | "Am"z8 | "G"z8 | "C"z8 | "D"z8 | "G"z8 | "C"z8 |
[P:A3] "C"z8 | "D/C"z8 | "C"z8 | "G/B"z8 | "Am"z8 | "D"z8 | "G"z8 | "C"z8 |
V:lead
[P:intro] z8 | z8 | z8 | z8 |
[P:A] !mp! e2 g2 a2 g2 | f4 d2 z2 | e2 g2 a2 b2 | g4- g2 z2 | a2 c'2 b2 a2 | f2 a2 d2 z2 | g2 a2 b2 a2 | g2 a2 g2 z2 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] !mp! e2 g2 a2 g2 | f4 d2 z2 | e2 g2 a2 b2 | g4- g2 z2 | a2 b2 c'2 b2 | a2 f2 d2 z2 | g2 b2 a2 g2 | e4- e2 z2 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A3] !mp! e2 g2 a2 g2 | f4 d2 z2 | e2 g2 a2 b2 | g2 e2 g2 z2 | c'2 b2 a2 g2 | f4 a2 z2 | b2 a2 g2 a2 | c'4- c'2 z2 |
V:flute
[P:intro] z8 | z8 | z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] !mp! c2 d2 g4 | f2 e2 d3 z | e2 g2 a4 | b2 a2 g3 z | c'2 b2 a2 g2 | a2 f2 d3 z | g2 a2 b2 d'2 | e'2 d'2 c'3 z |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] !mp! c2 d2 g4 | f2 e2 d3 z | e2 g2 a4 | b2 a2 g3 z | e2 g2 a2 b2 | f2 a2 d3 z | d2 e2 f2 g2 | g4- g2 z2 |
[P:A3] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
`,
  parts: {
    lead: { inst: 'marimba', role: 'lead', layers: ['main'], gain: 0, pan: -0.05 },
    flute: { inst: 'flute', role: 'lead', layers: ['main'], gain: -2, pan: 0.15 },
  },
  accomp: {
    kalimba: { inst: 'kalimba', role: 'accomp', pattern: 'kalimbaOstinato', layers: ['main'], octave: 3, gain: -9, pan: 0.25 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -8 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['weather'], octave: 3, gain: -14, pan: -0.2 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -18, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      bongos: { inst: 'bongos', layers: ['main'], steps: 'x..x..x...x.x...', gain: -14, pan: -0.3 },
      shaker: { inst: 'shaker', layers: ['main'], steps: '..x...x...x...x.', gain: -18, pan: 0.3 },
    },
  },
  order: ['intro', 'A', 'B', 'A2', 'breath', 'B2', 'A3'],
  loopFrom: 1,
  breath: [8, 20],
  weather: {
    cloudy: { gainDb: -1.5, mute: ['sparkle'] },
    rain: { mute: ['bongos', 'shaker', 'sparkle'], add: ['pad'], swap: { lead: 'harp', flute: 'vibes' } },
    storm: { mute: ['bongos', 'shaker', 'sparkle', 'bass', 'flute'], add: ['pad'], fragments: ['lead'], breath: [15, 30] },
  },
  motifQuote: { part: 'flute', section: 'B' },
})
