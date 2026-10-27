/**
 * The Journey Trials (SOUND_UPGRADE §7.4): wild, earthy. E Dorian, 4/4, 116, moved to each site's tonic by
 * its row (Iron Quarry E on tenor recorder, Windrun Steppe A on flute, Starfall Observatory B on vibes with
 * wine glass, Archer's Glade G on alto recorder with balafon, Glacier Bastion D on violin tremolo with
 * vibes). The lead climbs the Dorian scale in short, breathing phrases; the `colour` line doubles it in the
 * A sections (the site's second instrument); strumstick strums, a cello drone, spiccato and the wild kit
 * (frame drum, darbuka, shaker, a bass-drum boom every other bar). The lobby is the lead alone. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'trial',
  kind: 'battle',
  brief: 'A Journey Trial: wild and earthy in E Dorian, a recorder (or the site’s own voice) climbing in short breathing phrases over a cello drone, strums, frame drum and darbuka. Out in the open, testing yourself.',
  energy: 4,
  musicSend: 0.2,
  kit: 'wild',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=116
K:E dor
V:chords
[P:lobby] "Em"z8 | "D"z8 | "A"z8 | "Em"z8 | "G"z8 | "D"z8 | "A"z8 | "Em"z8 |
[P:intro] "Em"z8 | "Em"z8 |
[P:A] "Em"z8 | "D"z8 | "Em"z8 | "A"z8 | "G"z8 | "D"z8 | "A"z8 | "Em"z8 |
[P:B] "G"z8 | "D"z8 | "A"z8 | "Em"z8 | "G"z8 | "D"z8 | "Bm"z8 | "Em"z8 |
[P:A2] "Em"z8 | "D"z8 | "Em"z8 | "A"z8 | "G"z8 | "D"z8 | "Bm"z8 | "Em"z8 |
[P:C] "Bm"z8 | "A"z8 | "G"z8 | "D"z8 | "Bm"z8 | "A"z8 | "G"z8 | "A"z8 |
[P:B2] "G"z8 | "D"z8 | "A"z8 | "Em"z8 | "G"z8 | "D"z8 | "A"z8 | "Em"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] E2 F G A2 B2 | A2 G F D2 z2 | E2 F G B2 A2 | B2 c2 A2 z2 | B2 c d e2 d2 | d2 c B A2 F2 | E2 A2 B c B A | G4 E2 z2 |
[P:B] d2 c B c2 d2 | f2 e d A2 z2 | c2 d e c2 A2 | B2 A2 G2 z2 | B2 d2 e d B2 | A2 B A F2 A2 | B2 c d f2 e2 | e4 z4 |
[P:A2] E2 F G A2 B2 | A2 G F D2 z2 | E2 F G B2 A2 | B2 c2 A2 z2 | G2 A B d2 B2 | A2 B c d2 A2 | B2 A F A2 B2 | B4 E2 z2 |
[P:C] !mp! B2 c2 d2 z2 | c2 B2 A2 z2 | B2 A2 G2 z2 | F2 E2 F2 z2 | F2 A2 B2 z2 | c2 B2 c2 z2 | d2 B2 G2 z2 | A4 z4 |
[P:B2] !mf! d2 c B c2 d2 | f2 e d A2 z2 | c2 d e c2 A2 | B2 A2 G2 z2 | d2 e f g2 d2 | f2 e d A2 d2 | c2 B A B2 c2 | B4 z4 |
V:lobbyLead
[P:lobby] !p! B4 A4 | A4 F2 z2 | E4 A4 | G4 z4 | G4 A4 | A4 F2 z2 | E4 c4 | B4 z4 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! E2 F G A2 B2 | A2 G F D2 z2 | E2 F G B2 A2 | B2 c2 A2 z2 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] E2 F G A2 B2 | A2 G F D2 z2 | E2 F G B2 A2 | B2 c2 A2 z2 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [E,G,B,E]4 z4 | z8 |
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
    lead: { inst: 'recorder-tenor', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 2, pan: 0.05 },
    lobbyLead: { inst: 'recorder-tenor', role: 'lead', layers: ['lobby'], gain: -4, pan: 0.05 },
    colour: { inst: 'strumstick', role: 'colour', layers: ['drive', 'tension'], gain: -9, pan: 0.3 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
    boom: { inst: 'frame-drum', role: 'perc', layers: ['base', 'drive', 'tension'], gain: -14 },
  },
  accomp: {
    strum: { inst: 'strumstick', role: 'accomp', pattern: 'strum', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -10, pan: -0.2 },
    drone: { inst: 'cellos', art: 'vib', role: 'accomp', pattern: 'drone', layers: ['lobby', 'base', 'drive', 'tension'], octave: 2, gain: -17, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['base', 'drive', 'tension'], octave: 2, gain: -8 },
    pulse: { inst: 'cellos', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 2, gain: -13, pan: -0.1 },
    trem: { inst: 'cellos', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 2, gain: -16, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -19, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X...x.....X.x...', gain: -8 },
      mid: { role: 'mid', layers: ['drive'], steps: '..x.x..x..x...x.', gain: -12, pan: -0.2 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -17, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: 'X............... | ................', gain: -12 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -15 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 1.7 },
  },
})
