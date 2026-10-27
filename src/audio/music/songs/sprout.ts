/**
 * The Sprout Cup (SOUND_UPGRADE §7.4): young and bright. F Ionian, 4/4, 108. A kalimba tune that skips in
 * after an eighth rest and runs down the scale, a music box answering in the B sections, glock sparkles,
 * harp, a viola pad, marimba pulse and pizzicato bass, the meadow kit (frame drum, shaker, tambourine). The
 * lobby is the music box alone over the harp. `elders` is derived from it. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'sprout',
  kind: 'battle',
  brief: 'The Sprout Cup: a bright, skipping F major tune for the youngest monsters, kalimba and music box over harp and marimba, shaker and tambourine. Sunny and small and brave.',
  energy: 4,
  musicSend: 0.24,
  kit: 'meadow',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=108
K:F
V:chords
[P:lobby] "F"z8 | "C"z8 | "Dm"z8 | "Bb"z8 | "F"z8 | "Gm"z8 | "C"z8 | "F"z8 |
[P:intro] "F"z8 | "F"z8 |
[P:A] "F"z8 | "F"z8 | "Bb"z8 | "C"z8 | "F"z8 | "Dm"z8 | "Gm"z8 | "C"z8 |
[P:B] "Bb"z8 | "C"z8 | "Am"z8 | "Dm"z8 | "Bb"z8 | "C"z8 | "F"z8 | "F"z8 |
[P:A2] "F"z8 | "F"z8 | "Bb"z8 | "C"z8 | "F"z8 | "Dm"z8 | "C"z8 | "F"z8 |
[P:C] "Dm"z8 | "Am"z8 | "Bb"z8 | "F"z8 | "Dm"z8 | "Am"z8 | "Gm"z8 | "C"z8 |
[P:B2] "Bb"z8 | "C"z8 | "Am"z8 | "Dm"z8 | "Bb"z8 | "C"z8 | "F"z8 | "F"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] z c B A G2 A2 | c2 f2 e d c2 | z d c B A2 B2 | c2 e2 g4 | z a g f e2 f2 | a2 f2 d2 e f | g2 d2 B2 c d | e2 c2 G2 z2 |
[P:B] d4 f4 | e2 d2 c2 z2 | c4 e4 | d2 c2 A2 z2 | B2 d2 f2 g2 | a2 g2 e2 c2 | f2 a2 g2 f2 | f4 z4 |
[P:A2] z c B A G2 A2 | c2 f2 e d c2 | z d c B A2 B2 | c2 e2 g4 | z f e d c2 A2 | d2 f2 a2 g f | e2 g2 c2 d e | f6 z2 |
[P:C] !mp! f6 e2 | e4 c4 | d4 B4 | c4 z4 | A2 d2 f4 | e2 c2 A4 | B2 d2 g4 | e4 z4 |
[P:B2] !mf! d4 f4 | e2 d2 c2 z2 | c4 e4 | d2 c2 A2 z2 | d2 f2 d2 B c | e2 c2 G2 c2 | A2 c2 f2 e2 | f6 z2 |
V:lobbyLead
[P:lobby] !p! c'4 b4 | g4 e4 | f4 g4 | f6 z2 | a4 g4 | b4 a4 | g4 e4 | f6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:answer
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] !p! z8 | z6 g'2 | z8 | z6 f'2 | z8 | z8 | z8 | z4 c''2 a'2 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z6 c''2 | z8 | z8 | z8 | z6 g'2 |
[P:B2] z8 | z6 g'2 | z8 | z6 f'2 | z8 | z8 | z8 | z4 c''2 a'2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !p! z8 | z6 c'2 | z8 | z4 g'2 c''2 | z8 | z6 a'2 | z8 | z6 g'2 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z6 c'2 | z8 | z4 g'2 c''2 | z8 | z6 a'2 | z8 | z6 f'2 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [F,A,CF]4 z4 | z8 |
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
    lead: { inst: 'kalimba', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 6, pan: 0.05 },
    lobbyLead: { inst: 'music-box', role: 'lead', layers: ['lobby'], gain: -1, pan: 0.05 },
    answer: { inst: 'music-box', role: 'colour', layers: ['drive', 'tension'], gain: -7, pan: -0.3 },
    colour: { inst: 'glock', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -1 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -11 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -4, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['base', 'drive', 'tension'], octave: 3, size: 3, gain: -11, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, gain: -5 },
    pulse: { inst: 'marimba', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 3, gain: -10, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -14, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -16, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -6 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -14, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ....x.......x...', gain: -11, pan: -0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -12 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 3.2 },
  },
})
