/**
 * The autumn ranch (SOUND_UPGRADE §7.2). D Dorian, 3/4, 88. An ocarina waltz with a cello countermelody
 * answering in the rests, strumstick strums, a frame drum on the downbeats and cello pizzicato. The Wildsong
 * motif opens B (on F, where Dorian keeps its shape). Weather: cloudy mutes the sparkle; rain mutes the drum
 * and the cello line, swaps the lead to harp and adds a viola pad; storm keeps pad, strums and lead
 * fragments with longer breaths. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'ranch-autumn',
  kind: 'ranch',
  brief: 'Autumn on the ranch: a slow waltz, ocarina over strummed chords with a cello answering between the phrases, a frame drum marking the downbeats. Wistful but warm, like a long golden afternoon.',
  energy: 2,
  musicSend: 0.3,
  abc: `
X:1
M:3/4
L:1/8
Q:1/4=88
K:D dor
V:chords
[P:intro] "Dm"z6 | "G"z6 | "Dm"z6 | "C"z6 |
[P:A] "Dm"z6 | "G"z6 | "Dm"z6 | "C"z6 | "Am"z6 | "G"z6 | "C"z6 | "Dm"z6 |
[P:B] "F"z6 | "G"z6 | "Dm"z6 | "Am"z6 | "F"z6 | "C"z6 | "G"z6 | "Dm"z6 |
[P:A2] "Dm"z6 | "G"z6 | "Dm"z6 | "C"z6 | "Am"z6 | "G"z6 | "C"z6 | "Dm"z6 |
[P:B2] "F"z6 | "G"z6 | "Dm"z6 | "Am"z6 | "F"z6 | "C"z6 | "G"z6 | "Dm"z6 |
[P:A3] "Dm"z6 | "G"z6 | "Dm"z6 | "C"z6 | "Am"z6 | "G"z6 | "C"z6 | "Dm"z6 |
V:lead
[P:intro] z6 | z6 | z6 | z6 |
[P:A] !mp! d2 e2 f2 | g4 z2 | a2 f2 d2 | e4 z2 | c2 e2 a2 | g2 a2 g2 | e2 d2 c2 | d4 z2 |
[P:B] f2 g2 c'2 | b a g3 z | a2 f2 e2 | e2 c4 | f2 g2 a2 | g2 e2 z2 | b2 a2 g2 | f4- f z |
[P:A2] d2 e2 f2 | g4 z2 | a2 f2 d2 | e4 z2 | a2 g2 e2 | d2 e d2 z | e2 g2 e2 | d4 a z |
[P:B2] f2 g2 c'2 | b a g3 z | a2 f2 e2 | e2 c4 | a2 g2 f2 | e2 g2 z2 | d2 e2 g2 | e2 d4 |
[P:A3] d2 e2 f2 | g4 z2 | a2 f2 d2 | e4 z2 | c2 e2 g2 | a2 g2 b2 | c'2 b2 g2 | a4 z2 |
V:counter
[P:intro] z6 | z6 | z6 | z6 |
[P:A] !p! z6 | z4 B,2 | z6 | z4 C2 | z6 | z4 D2 | z6 | z4 D2 |
[P:B] !p! z6 | z4 D2 | F4 D2 | C4 z2 | z6 | z4 E2 | D4 D2 | D4 z2 |
[P:A2] !p! z6 | z4 B,2 | z6 | z4 C2 | z6 | z6 | z6 | z4 D2 |
[P:B2] !p! z6 | z4 D2 | F4 D2 | C4 z2 | z6 | z4 E2 | D4 D2 | D4 z2 |
[P:A3] !p! z6 | z4 B,2 | z6 | z4 C2 | z6 | z6 | z6 | z4 D2 |
`,
  parts: {
    lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    counter: { inst: 'cellos', art: 'vib', role: 'counter', layers: ['main'], gain: -6, pan: -0.25 },
  },
  accomp: {
    strum: { inst: 'strumstick', role: 'accomp', pattern: 'strum', layers: ['main'], octave: 3, gain: -9, pan: 0.2, density: 'normal' },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -10 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['weather'], octave: 3, gain: -14, pan: -0.15 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 12,
    lines: {
      drum: { inst: 'frame-drum', layers: ['main'], steps: 'X.....x.....', gain: -12 },
    },
  },
  order: ['intro', 'A', 'B', 'A2', 'breath', 'B2', 'A3'],
  loopFrom: 1,
  breath: [8, 20],
  weather: {
    cloudy: { gainDb: -1.5, mute: ['sparkle'] },
    rain: { mute: ['drum', 'counter', 'sparkle'], add: ['pad'], swap: { lead: 'harp' } },
    storm: { mute: ['drum', 'counter', 'sparkle', 'bass'], add: ['pad'], fragments: ['lead'], breath: [15, 30] },
  },
  motifQuote: { part: 'lead', section: 'B' },
})
