/**
 * The Crown of Frost (SOUND_UPGRADE §7.4): crystalline. B Aeolian, 3/4, 108. The vibes carry a clear waltz
 * tune, wine glasses hold one cold note every four bars, a low violin tremolo shivers beneath, the harp
 * turns in arpeggios, and the frost kit (timpani on the downbeat, sleigh bells on two and three, finger
 * cymbals) keeps it light. The lobby is bowed vibes over the harp, very still. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'crown-frost',
  kind: 'battle',
  brief: 'The Crown of Frost: a crystalline B minor waltz, vibes over a shivering violin tremolo, wine glasses ringing, harp, timpani and sleigh bells. Clear and cold and beautiful.',
  energy: 5,
  musicSend: 0.3,
  kit: 'frost',
  abc: `
X:1
M:3/4
L:1/8
Q:1/4=108
K:B min
V:chords
[P:lobby] "Bm"z6 | "G"z6 | "D"z6 | "A"z6 | "Bm"z6 | "Em"z6 | "F#m"z6 | "Bm"z6 |
[P:intro] "Bm"z6 | "Bm"z6 |
[P:A] "Bm"z6 | "G"z6 | "D"z6 | "A"z6 | "Em"z6 | "G"z6 | "F#m"z6 | "Bm"z6 |
[P:B] "G"z6 | "D"z6 | "A"z6 | "Bm"z6 | "G"z6 | "D"z6 | "Em"z6 | "F#m"z6 |
[P:A2] "Bm"z6 | "G"z6 | "D"z6 | "A"z6 | "Em"z6 | "G"z6 | "A"z6 | "Bm"z6 |
[P:C] "Em"z6 | "Bm"z6 | "G"z6 | "D"z6 | "Em"z6 | "Bm"z6 | "G"z6 | "A"z6 |
[P:B2] "G"z6 | "D"z6 | "A"z6 | "Bm"z6 | "G"z6 | "D"z6 | "Em"z6 | "Bm"z6 |
[P:A3] "Bm"z6 | "G"z6 | "D"z6 | "A"z6 | "Em"z6 | "G"z6 | "F#m"z6 | "Bm"z6 |
V:lead
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] z6 | z6 |
[P:A] f2 e2 d2 | B3 c d2 | e2 d2 A2 | B2 c2 z2 | e2 f2 g2 | g3 f e2 | f2 e2 c2 | d2 c2 B2 |
[P:B] B2 d2 g2 | f3 g a2 | a2 e2 c2 | B4 z2 | d2 e2 g2 | a3 g f2 | g2 e2 c2 | c4 z2 |
[P:A2] f2 e2 d2 | B3 c d2 | e2 d2 A2 | B2 c2 z2 | B2 e2 f2 | g2 f2 d2 | c2 d2 e2 | d4 B2 |
[P:C] !mp! e6 | d2 B2 F2 | B2 G2 A2 | d4 z2 | G2 A2 B2 | d3 e f2 | g2 d2 B2 | e4 z2 |
[P:B2] !mf! B2 d2 g2 | f3 g a2 | a2 e2 c2 | B4 z2 | d2 g2 f2 | f2 a2 f2 | e2 B2 G2 | f4 z2 |
[P:A3] f2 e2 d2 | B3 c d2 | e2 d2 A2 | B2 c2 z2 | g2 e2 B2 | B2 A2 B2 | c2 A2 c2 | B6 |
V:lobbyLead
[P:lobby] !p! f6 | d6 | d3 c3 | c6 | B3 d3 | e6 | c3 f3 | f6 |
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
[P:A] !mp! f6 | z6 | z6 | z6 | g6 | z6 | z6 | z6 |
[P:B] d6 | z6 | z6 | z6 | d6 | z6 | z6 | z6 |
[P:A2] f6 | z6 | z6 | z6 | g6 | z6 | z6 | z6 |
[P:C] e6 | z6 | z6 | z6 | e6 | z6 | z6 | z6 |
[P:B2] d6 | z6 | z6 | z6 | d6 | z6 | z6 | z6 |
[P:A3] f6 | z6 | z6 | z6 | g6 | z6 | z6 | z6 |
V:hit
[P:lobby] z6 | z6 | z6 | z6 | z6 | z6 | z6 | z6 |
[P:intro] !mf! [B,DFB]4 z2 | z6 |
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
    lead: { inst: 'vibes', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 0, pan: 0.05 },
    lobbyLead: { inst: 'vibes', art: 'bowed', role: 'lead', layers: ['lobby'], gain: 1, pan: 0.05 },
    colour: { inst: 'wine-glasses', art: 'slow', role: 'colour', layers: ['drive', 'tension'], gain: -13, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -6, pan: -0.2 },
    shiver: { inst: 'violins', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['drive', 'tension'], octave: 3, size: 3, gain: -16, pan: 0.15 },
    bass: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    pulse: { inst: 'violas', art: 'pizz', role: 'accomp', pattern: 'waltz', layers: ['drive'], octave: 3, gain: -13, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -16, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 12,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X...........', gain: -9, pitch: 'root' },
      high: { role: 'high', layers: ['drive'], steps: '....x...x...', gain: -18, pan: 0.25 },
      accent: { role: 'accent', layers: ['drive'], steps: 'X........... | ............ | ............ | ............', gain: -16, pan: -0.2 },
      riser: { role: 'low', layers: ['tension'], steps: 'x...x...x...', gain: -15, pitch: 'root' },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2', 'A3'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 9.1 },
  },
})
