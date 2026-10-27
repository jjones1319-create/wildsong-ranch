/**
 * SOUND_UPGRADE §7.6: the S1 interrupting stingers (1.5–10 s). Written in C and transposed to the area
 * song's tonic at play time; the area music fades out over 150 ms before them and restarts at its next
 * section after them. All original.
 */
import { defineSong, type Song } from './song.ts'

export const STINGER_IDS = ['matchWin', 'matchLoss', 'matchDraw', 'cupWin', 'promotion'] as const
export type StingerId = (typeof STINGER_IDS)[number]

/** 4 s: a bright little fanfare, recorder over horn and harp, a drum and a tambourine on the way up. */
const matchWin = defineSong({
  id: 'matchWin',
  kind: 'stinger',
  brief: 'The match is won: a bright four-second fanfare on recorder and horn, harp underneath, one drum hit and a tambourine.',
  energy: 4,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=108
K:C
V:chords
[P:A] "C"z4 "F"z4 | "G"z4 "C"z4 |
V:lead
[P:A] G2 c2 e4 | d2 f2 e4 |
V:horn
[P:A] C4 A,4 | B,4 C4 |
`,
  parts: {
    lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: 0, pan: 0.1 },
    horn: { inst: 'horn', art: 'sus', role: 'counter', layers: ['main'], gain: -5, pan: -0.15 },
  },
  accomp: { harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 4, gain: -8 } },
  perc: { grid: 16, lines: { drum: { inst: 'frame-drum', layers: ['main'], steps: 'X.......x.......', gain: -6 }, tamb: { inst: 'tambourine', layers: ['main'], steps: '........X.......', gain: -10 } } },
  order: ['A'],
  loopFrom: 0,
})

/** 3 s: a soft falling phrase on ocarina over a viola pad, sympathetic, never a buzzer. */
const matchLoss = defineSong({
  id: 'matchLoss',
  kind: 'stinger',
  brief: 'The match is lost: three soft falling ocarina notes over a viola pad and one low harp note. Sympathetic, not sad.',
  energy: 1,
  musicSend: 0.35,
  abc: `
X:1
M:2/4
L:1/8
Q:1/4=80
K:C min
V:chords
[P:A] "Cm"z4 | "Fm"z4 |
V:lead
[P:A] _e2 d2 | c2 z2 |
`,
  parts: { lead: { inst: 'ocarina', role: 'lead', layers: ['main'], gain: -2 } },
  accomp: {
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, gain: -12 },
    bass: { inst: 'harp', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 3, gain: -10 },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 2.5 s: a shrug on alto recorder and kalimba, neither up nor down. */
const matchDraw = defineSong({
  id: 'matchDraw',
  kind: 'stinger',
  brief: 'A draw: a short recorder turn with a kalimba underneath, going nowhere in particular.',
  energy: 2,
  musicSend: 0.3,
  abc: `
X:1
M:2/4
L:1/8
Q:1/4=96
K:C mix
V:chords
[P:A] "C"z4 | "C"z4 |
V:lead
[P:A] G2 A2 | G4 |
`,
  parts: { lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: -2 } },
  accomp: { kal: { inst: 'kalimba', role: 'accomp', pattern: 'kalimbaOstinato', layers: ['main'], octave: 4, gain: -10 } },
  order: ['A'],
  loopFrom: 0,
})

/** 6 s: first place. Recorder and horn in call and answer over violins, harp, a timpani and a cymbal swell. */
const cupWin = defineSong({
  id: 'cupWin',
  kind: 'stinger',
  brief: 'First place: a six-second fanfare, recorder rising to a high C answered by the horn, violins and harp beneath, timpani on the downbeats and one cymbal swell into it.',
  energy: 5,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=112
K:C
V:chords
[P:A] "C"z8 | "F"z4 "G"z4 | "C"z8 |
V:lead
[P:A] !mp! e2 g2 c'4 | b2 a2 g4 | e2 d2 c4 |
V:horn
[P:A] C4 E4 | A,4 B,4 | C4 C4 |
`,
  parts: {
    lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: 1, pan: 0.1 },
    horn: { inst: 'horn', art: 'sus', role: 'counter', layers: ['main'], gain: -4, pan: -0.15 },
  },
  accomp: {
    strings: { inst: 'violins', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 4, gain: -12 },
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -8 },
  },
  perc: {
    grid: 16,
    lines: {
      timp: { inst: 'timpani', layers: ['main'], steps: 'X.......x.......', gain: -8, pitch: 'root' },
      swell: { inst: 'cymbal-swell', layers: ['main'], steps: 'X............... | ................ | ................', gain: -14 },
    },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 6 s: "Ascended!" A proud horn ascent with violins above, harp and timpani under it. */
const promotion = defineSong({
  id: 'promotion',
  kind: 'stinger',
  brief: 'Ascended: the horn climbs a proud six-second phrase, violins hold above it, harp and timpani underneath. Noble, not loud.',
  energy: 4,
  musicSend: 0.35,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=120
K:C
V:chords
[P:A] "C"z8 | "Dm"z4 "C/G"z4 | "C"z8 |
V:lead
[P:A] C2 D2 E4 | D4 E4 | C8 |
V:vln
[P:A] e4 g4 | a4 g4 | e8 |
`,
  parts: {
    lead: { inst: 'horn', art: 'sus', role: 'lead', layers: ['main'], gain: -2 },
    vln: { inst: 'violins', art: 'vib', role: 'counter', layers: ['main'], gain: -8, pan: 0.2 },
  },
  accomp: { harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9 } },
  perc: { grid: 16, lines: { timp: { inst: 'timpani', layers: ['main'], steps: 'X...x...X...x... | X.......X....... | X...............', gain: -8, pitch: 'root' } } },
  order: ['A'],
  loopFrom: 0,
})

export const STINGERS: Record<StingerId, Song> = { matchWin, matchLoss, matchDraw, cupWin, promotion }

/** Moments without their own stinger yet use the nearest S1 one (§15). */
export const STINGER_STAND_INS: Record<string, StingerId> = {
  cupPlaced: 'matchWin',
  cupOut: 'matchLoss',
  crownWon: 'cupWin',
  legendWon: 'cupWin',
  rankUp: 'promotion',
  titleEarned: 'matchWin',
  birth: 'promotion',
  farewell: 'matchLoss',
  birthday: 'matchWin',
  monsterSong: 'matchDraw',
  rest: 'matchDraw',
  play: 'matchDraw',
  journeyDepart: 'matchDraw',
  journeyReturn: 'matchWin',
}
