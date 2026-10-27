/**
 * The cup (SOUND_UPGRADE §7.4–7.5): every regular cup's battle. E Dorian, 4/4, 120, bright sporting folk.
 * Layers: `lobby` (a half-time version with long lead notes over harp and pad, looped on the cup screens),
 * `base` (the theme over harp, pad, pizz bass and a low drum), `drive` (spiccato strings pulse, a kalimba
 * counter and the rest of the kit from bar 3), `tension` (string tremolo, a double-time drum and a glock
 * flourish when someone is low or the clock is nearly out). The intro bar carries the match-start drum
 * hit and harp chord. The lead instrument, the kit and the key move with the season palette and the event
 * row, written as arrangement data by the director; a `colour` line rings at phrase starts in the season's
 * colour (or an event's own). Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'cup',
  kind: 'battle',
  brief: 'A regular cup: a bright, bouncing folk tune in E Dorian, the lead changing with the season, strings pulsing under it from bar three, drums building, tremolo and a double-time pulse when a fighter is low or the clock runs out. Sporting, never grim.',
  energy: 4,
  musicSend: 0.22,
  kit: 'meadow',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=120
K:E dor
V:chords
[P:lobby] "Em"z8 | "A"z8 | "Em"z8 | "D"z8 | "Em"z8 | "A"z8 | "Bm"z8 | "Em"z8 |
[P:intro] "Em"z8 | "Em"z8 |
[P:A] "Em"z8 | "Em"z8 | "A"z8 | "Em"z8 | "D"z8 | "A"z8 | "Bm"z8 | "Em"z8 |
[P:B] "G"z8 | "D"z8 | "Em"z8 | "Bm"z8 | "G"z8 | "D"z8 | "A"z8 | "Em"z8 |
[P:A2] "Em"z8 | "Em"z8 | "A"z8 | "Em"z8 | "D"z8 | "A"z8 | "Bm"z8 | "Em"z8 |
[P:C] "Bm"z8 | "A"z8 | "Em"z8 | "D"z8 | "Bm"z8 | "A"z8 | "G"z8 | "Em"z8 |
[P:B2] "G"z8 | "D"z8 | "Em"z8 | "Bm"z8 | "G"z8 | "D"z8 | "A"z8 | "Em"z8 |
V:lead
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] e2 e2 g2 a2 | b a g2 e4 | a2 b c' b a a2 | g4 e2 z2 | f2 a2 b a g2 | a2 c' b a2 f2 | b a f2 d4 | e4- e2 z2 |
[P:B] g2 a2 b a a2 | f2 e2 d4 | e2 g2 b a g2 | f4 d2 z2 | g2 b a b a g2 | a2 f2 d4 | e2 f2 g2 a2 | b a g2 e2 z2 |
[P:A2] e2 e2 g2 a2 | b a g2 e4 | a2 b c' b a a2 | g4 e2 z2 | f2 e2 d2 f2 | a2 b a f2 e2 | d2 f2 b a g2 | g2 e4 z2 |
[P:C] f2 d2 f2 a2 | a2 c' b a2 e2 | e2 g2 a2 b a | a4 f2 z2 | b a f2 d2 f2 | e2 a2 c' b a2 | b a g2 a2 g2 | f2 e4 z2 |
[P:B2] g2 a2 b a a2 | f2 e2 d4 | e2 g2 b a g2 | f4 d2 z2 | g2 a2 b a g2 | f2 e2 d2 f2 | e2 a2 c' b a2 | g2 e4 z2 |
V:lobbyLead
[P:lobby] !p! e4 g4 | a8 | g4 e4 | f4- f2 z2 | e4 g4 | a4 b4 | f4 d4 | e6 z2 |
[P:intro] z8 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
V:counter
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! z8 | z4 f2 e2 | z8 | z4 a2 g2 | z8 | z4 b2 a2 | z8 | z4 f2 e2 |
[P:B] !mp! z8 | z4 e2 d2 | z8 | z4 g2 f2 | z8 | z4 e2 d2 | z8 | z4 f2 e2 |
[P:A2] !mp! z8 | z4 f2 e2 | z8 | z4 a2 g2 | z8 | z4 b2 a2 | z8 | z4 f2 e2 |
[P:C] !mp! z8 | z4 b2 a2 | z8 | z4 e2 d2 | z8 | z4 b2 a2 | z8 | z4 f2 e2 |
[P:B2] !mp! z8 | z4 e2 d2 | z8 | z4 g2 f2 | z8 | z4 e2 d2 | z8 | z4 f2 e2 |
V:colour
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] z8 | z8 |
[P:A] !mp! B2 z6 | z8 | c2 z6 | z8 | d2 z6 | z4 c2 e2 | d2 z6 | z4 B4 |
[P:B] B2 z6 | z8 | B2 z6 | z8 | d2 z6 | z8 | c2 z6 | z4 B4 |
[P:A2] B2 z6 | z8 | c2 z6 | z8 | d2 z6 | z4 c2 e2 | d2 z6 | z4 B4 |
[P:C] d2 z6 | z8 | B2 z6 | z8 | d2 z6 | z8 | d2 z6 | z4 B4 |
[P:B2] B2 z6 | z8 | B2 z6 | z8 | d2 z6 | z8 | c2 z6 | z4 B4 |
V:hit
[P:lobby] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:intro] !mf! [E,G,B,E]4 z4 | z8 |
[P:A] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:A2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:C] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
[P:B2] z8 | z8 | z8 | z8 | z8 | z8 | z8 | z8 |
`,
  parts: {
    lead: { inst: 'ocarina', role: 'lead', layers: ['base', 'drive', 'tension'], gain: 0, pan: 0.05 },
    lobbyLead: { inst: 'ocarina', role: 'lead', layers: ['lobby'], gain: -3, pan: 0.05 },
    counter: { inst: 'kalimba', role: 'counter', layers: ['drive', 'tension'], gain: -7, pan: 0.3 },
    // The season's colour (harp, glock, strumstick) or an event's own (hand chimes, wine glasses), from the row.
    colour: { inst: 'harp', role: 'colour', layers: ['drive', 'tension'], gain: -11, pan: -0.35 },
    hit: { inst: 'harp', role: 'accomp', layers: ['base', 'drive', 'tension'], gain: -4 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['lobby', 'base', 'drive'], octave: 3, gain: -8, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['lobby', 'base', 'drive', 'tension'], octave: 3, gain: -14, pan: 0.15 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['base', 'drive', 'tension'], octave: 2, gain: -7 },
    pulse: { inst: 'violins', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['drive'], octave: 4, gain: -10, pan: -0.1 },
    trem: { inst: 'violins', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['tension'], octave: 4, gain: -17, pan: 0.1 },
    flourish: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['tension'], octave: 5, gain: -18, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      low: { role: 'low', layers: ['base', 'drive'], steps: 'X.......x.......', gain: -8 },
      mid: { role: 'mid', layers: ['drive'], steps: '..x...x...x...x.', gain: -12, pan: -0.2 },
      high: { role: 'high', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -16, pan: 0.2 },
      shaker: { role: 'shaker', layers: ['drive'], steps: 'x.x.x.x.x.x.x.x.', gain: -16, pan: 0.3 },
      accent: { role: 'accent', layers: ['drive'], steps: '................ | ............X...', gain: -10 },
      riser: { role: 'low', layers: ['tension'], steps: 'x.x.x.x.x.x.x.x.', gain: -16 },
    },
  },
  order: ['lobby', 'intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 2,
  arrangements: {
    lobby: { order: ['lobby'], loopFrom: 0, gainDb: 2.5 },
  },
})
