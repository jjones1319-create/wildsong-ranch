/**
 * Wildsong: the main theme (SOUND_UPGRADE §7.1). D Lydian, 4/4, 72. The Wildsong motif in full on ocarina
 * over a harp arpeggio, a viola pad and cello pizzicato; the B section passes to the alto recorder with
 * wonder in the raised 4th; a glockenspiel sparkle answers at section ends; a soft frame drum keeps the
 * ground. Arrangements: `lobby` (the new-game screen: harp, pad and bass only, half time) and `credits`
 * (every section twice, a held ending). All original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'wildsong',
  kind: 'place',
  brief: 'The title: the land sings its own song. Calm, warm and wide: an ocarina states the Wildsong motif over harp and strings, the recorder wonders in the raised 4th, a glock sparkles at the turns. The listener should feel at home and a little curious.',
  energy: 2,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=72
K:D lyd
V:chords
[P:intro] "D"z8 | "E/D"z8 | "D"z8 | "A/C#"z8 |
[P:A] "D"z8 | "E"z8 | "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "Bm"z8 | "A"z4 "D"z4 |
[P:B] "E"z8 | "A"z8 | "Bm"z8 | "F#m"z8 | "E"z8 | "A"z8 | "D"z8 | "D"z8 |
[P:A2] "D"z8 | "E"z8 | "Bm"z8 | "A"z8 | "D"z8 | "E"z8 | "Bm"z8 | "A"z4 "D"z4 |
[P:B2] "E"z8 | "A"z8 | "Bm"z8 | "F#m"z8 | "E"z8 | "A"z8 | "D"z8 | "D"z8 |
V:lead
[P:intro] z8 | z8 | z8 | z8 |
[P:A] !mp! d2 e2 a4 | g f e5 z | b2 a2 f4 | e2 c2 e3 z | d2 e2 a3 b | a g f2 e3 z | b2 a2 f2 d2 | e2 c2 d3 z |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] !mp! d2 e2 a4 | g f e5 z | b2 a2 f4 | e2 c2 e3 z | a2 b2 a2 f2 | e2 d2 e3 z | f2 a2 b2 a2 | f2 e2 d3 z |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:recorder
[P:intro] z8 | z8 | z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] !mp! e2 f2 g2 b2 | a4 e3 z | f2 a2 b2 d'2 | c'2 a2 f3 z | g2 f2 e2 g2 | a2 b2 c'3 z | d'2 b2 a2 f2 | e2 f2 d3 z |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] !mp! e2 f2 g2 b2 | a4 e3 z | f2 a2 b2 d'2 | c'2 a2 f3 z | g2 f2 e2 f2 | e2 d2 c3 z | d2 e2 f2 a2 | f2 e2 d3 z |
`,
  parts: {
    lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    recorder: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: -2, pan: -0.1 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -7, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -15, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -9 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -18, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      drum: { inst: 'frame-drum', art: 'muted', layers: ['main'], steps: 'X.......x.......', gain: -14 },
    },
  },
  order: ['intro', 'A', 'B', 'A2', 'B2'],
  loopFrom: 1,
  arrangements: {
    lobby: { lines: ['harp', 'pad', 'bass'], order: ['intro', 'A', 'B'], loopFrom: 0, halfTime: true, gainDb: -2 },
    credits: { order: ['intro', 'A', 'B', 'A2', 'B2', 'A2', 'B2'], loopFrom: 0, heldEnding: true, gainDb: 1 },
  },
  motifQuote: { part: 'lead', section: 'A' },
})
