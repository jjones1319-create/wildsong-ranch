/**
 * The Elders' Cup (SOUND_UPGRADE §7.4): nostalgic. F Ionian, 4/4, 100. The Sprout Cup's chord track at an
 * older, slower pace: a tenor recorder sings long, mostly stepwise phrases with room to breathe, the harp
 * arpeggiates, cellos hold a warm pad and walk the bass, and the meadow kit plays softly. The lobby is the
 * recorder alone. Derived from `sprout`. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'elders',
  kind: 'battle',
  brief: 'The Elders’ Cup: the Sprout Cup’s chords at an older pace, a tenor recorder remembering over harp and cellos, a soft frame drum. Warm, a little wistful, still game for a match.',
  energy: 3,
  musicSend: 0.28,
  kit: 'meadow',
  derivedFrom: 'sprout',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=100
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
[P:A] A4 G2 A2 | c2 B2 A2 z2 | B4 c2 d2 | c4- c2 z2 | c2 A2 B2 c2 | d2 c2 A2 z2 | B2 A2 G2 A2 | G4 z4 |
[P:B] d4 c2 B2 | c4 G2 z2 | A4 B2 c2 | d4- d2 z2 | f4 e2 d2 | c2 d2 e2 z2 | f4 e2 c2 | A4 z4 |
[P:A2] A4 G2 A2 | c2 B2 A2 z2 | B4 c2 d2 | c4- c2 z2 | A2 B2 c2 d2 | d2 c2 A2 z2 | G2 A2 B2 c2 | c4 A2 z2 |
[P:C] !mp! F4 E2 D2 | C4 E2 z2 | D4 F4 | F4- F2 z2 | D2 E2 F2 A2 | A4 E2 z2 | G2 A2 B2 A2 | G4 z4 |
[P:B2] !mf! d4 c2 B2 | c4 G2 z2 | A4 B2 c2 | d4- d2 z2 | d2 e2 d2 B2 | c2 B2 G2 z2 | A4 G2 F2 | F4 z4 |
V:lobbyLead
[P:lobby] !p! A4 G4 | G4 E2 z2 | F4 E4 | D4 z4 | F4 G4 | B4 G2 z2 | G4 E4 | F4 z4 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z8 | z8 | z6 g2 | z8 | z8 | z8 | z6 e2 |
[P:B] z8 | z6 e2 | z8 | z6 a2 | z8 | z8 | z8 | z6 c'2 |
[P:A2] z8 | z8 | z8 | z6 g2 | z8 | z8 | z8 | z6 f2 |
[P:C] z8 | z6 e2 | z8 | z6 c'2 | z8 | z6 e2 | z8 | z6 g2 |
[P:B2] z8 | z6 e2 | z8 | z6 a2 | z8 | z8 | z8 | z6 c'2 |
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
    lead: { inst: 'recorder-tenor', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 3, pan: 0.05 },
    lobbyLead: { inst: 'recorder-tenor', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    colour: { inst: 'harp', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 2, gain: -7, pan: -0.2 },
    pad: { inst: 'cellos', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 2, size: 3, gain: -13, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    pulse: { inst: 'cellos', art: 'pizz', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 2, gain: -14, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -20, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', art: 'muted', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -10 },
      shaker: { role: 'shaker', layers: ['drive'], steps: '..x...x...x...x.', gain: -18, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ............x...', gain: -15, pan: -0.1 },
      riser: { role: 'low', layers: ['tension'], steps: 'x...x...x...x...', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 2.1 },
  },
})
