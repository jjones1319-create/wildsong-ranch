/**
 * SOUND_UPGRADE §7.6: the interrupting stingers (1.5–10 s). Written in C and transposed to the area song's
 * tonic at play time; the area music fades out over 150 ms before them and restarts at its next section
 * after them (several in a row play as a chain, §4.7). S1: the match and first-place stingers; S2: the cup
 * placings, one stinger per Crown quoting its theme, the Legend's Hall of Fame anthem, rank and title. All
 * original.
 */
import { defineSong, type Song } from './song.ts'

export const STINGER_IDS = ['matchWin', 'matchLoss', 'matchDraw', 'cupWin', 'promotion', 'cupPlaced', 'cupOut', 'crownWonDawn', 'crownWonTides', 'crownWonEmbers', 'crownWonFrost', 'legendWon', 'rankUp', 'titleEarned'] as const
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

/** 3 s: second or third place. A modest rising phrase on alto recorder, harp and a viola pad, one tambourine. */
const cupPlaced = defineSong({
  id: 'cupPlaced',
  kind: 'stinger',
  brief: 'Second or third place: a short, warm rising phrase on alto recorder over harp, settling home. Proud, not triumphant.',
  energy: 3,
  musicSend: 0.3,
  abc: `
X:1
M:3/4
L:1/8
Q:1/4=120
K:C
V:chords
[P:A] "C"z6 | "G"z4 "C"z2 |
V:lead
[P:A] G2 c2 e2 | d4 c2 |
`,
  parts: { lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: 0, pan: 0.1 } },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, size: 3, gain: -14 },
  },
  perc: { grid: 12, lines: { drum: { inst: 'frame-drum', layers: ['main'], steps: 'X...........', gain: -8 }, tamb: { inst: 'tambourine', layers: ['main'], steps: '........X... | ............', gain: -12 } } },
  order: ['A'],
  loopFrom: 0,
})

/** 2 s: knocked out. A gentle falling phrase on tenor recorder over a soft harp chord; kind, never a buzzer. */
const cupOut = defineSong({
  id: 'cupOut',
  kind: 'stinger',
  brief: 'Knocked out of the cup: two seconds of a gentle falling recorder phrase over a soft harp chord. A pat on the shoulder.',
  energy: 1,
  musicSend: 0.35,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=120
K:C
V:chords
[P:A] "F"z4 "C"z4 |
V:lead
[P:A] !mp! A2 G2 E4 |
`,
  parts: { lead: { inst: 'recorder-tenor', role: 'lead', layers: ['main'], gain: 3 } },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -7 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, size: 3, gain: -11 },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 8 s: the Crown of Dawn won. Its rising head in C Lydian on violins, horn beneath, timpani and a cymbal swell. */
const crownWonDawn = defineSong({
  id: 'crownWonDawn',
  kind: 'stinger',
  brief: 'The Crown of Dawn won: the Crown theme’s rising head on violins in full sunlight, horn underneath, harp and glock, timpani and a cymbal swell into a held last chord.',
  energy: 5,
  musicSend: 0.32,
  derivedFrom: 'crown-dawn',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=116
K:C lyd
V:chords
[P:A] "C"z8 | "D"z8 | "Em"z8 | "C"z8 |
V:lead
[P:A] C2 D2 E2 G2 | A3 G F2 A2 | B2 c2 d2 e2 | e8 |
V:horn
[P:A] C,8 | D,8 | E,8 | C,8 |
`,
  parts: {
    lead: { inst: 'violins', art: 'vib', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['main'], gain: -6, pan: -0.2 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, size: 3, gain: -14 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -17, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      timp: { inst: 'timpani', layers: ['main'], steps: 'X.......x.......', gain: -9, pitch: 'root' },
      swell: { inst: 'cymbal-swell', layers: ['main'], steps: '................ | ................ | ........X....... | ................', gain: -15 },
    },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 8 s: the Crown of Tides won. Its swell in C Dorian 6/8 on flute over harp waves and an ocean-drum swell. */
const crownWonTides = defineSong({
  id: 'crownWonTides',
  kind: 'stinger',
  brief: 'The Crown of Tides won: the Crown theme’s swell on flute in a broad 6/8, harp waves and cellos, one ocean-drum swell. The sea applauding.',
  energy: 5,
  musicSend: 0.32,
  derivedFrom: 'crown-tides',
  abc: `
X:1
M:6/8
L:1/8
Q:3/8=76
K:C dor
V:chords
[P:A] "Cm"z6 | "F"z6 | "Cm"z6 | "Gm"z6 | "Cm"z6 |
V:lead
[P:A] g2 e c2 d | e2 f a2 z | g3 f2 e | d3 c2 B | c6 |
`,
  parts: { lead: { inst: 'flute', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 } },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -8, pan: -0.2 },
    pad: { inst: 'cellos', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 2, size: 3, gain: -14 },
  },
  perc: {
    grid: 12,
    lines: {
      drum: { inst: 'frame-drum', layers: ['main'], steps: 'X.....x.....', gain: -9 },
      sea: { inst: 'ocean-drum', layers: ['main'], steps: 'X........... | ............ | ............ | ............ | ............', gain: -14 },
    },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 8 s: the Crown of Embers won. Its winding head in C Phrygian dominant on flute, strums, spiccato and darbuka. */
const crownWonEmbers = defineSong({
  id: 'crownWonEmbers',
  kind: 'stinger',
  brief: 'The Crown of Embers won: the Crown theme’s winding head on flute in C Phrygian dominant, strumstick strums, cello spiccato, darbuka and tambourine, ending on a bright major chord. Glowing.',
  energy: 5,
  musicSend: 0.28,
  derivedFrom: 'crown-embers',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=126
K:C phr ^e
V:chords
[P:A] "C"z8 | "Db"z8 | "Fm"z8 | "C"z8 |
V:lead
[P:A] c2 d e g2 f e | f2 d2 A2 B c | d2 c B A2 z2 | c8 |
`,
  parts: { lead: { inst: 'flute', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 } },
  accomp: {
    strum: { inst: 'strumstick', role: 'accomp', pattern: 'strum', layers: ['main'], octave: 3, gain: -11, pan: -0.2 },
    pulse: { inst: 'cellos', art: 'spic', role: 'accomp', pattern: 'pulse', layers: ['main'], octave: 2, gain: -12 },
  },
  perc: {
    grid: 16,
    lines: {
      drum: { inst: 'frame-drum', layers: ['main'], steps: 'X.....x.X.......', gain: -9 },
      darb: { inst: 'darbuka', layers: ['main'], steps: '...x..x....x.x..', gain: -13 },
      tamb: { inst: 'tambourine', layers: ['main'], steps: '................ | ................ | ................ | X...............', gain: -11 },
    },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 8 s: the Crown of Frost won. Its waltz head in C minor on vibes, wine glasses, violin tremolo and sleigh bells. */
const crownWonFrost = defineSong({
  id: 'crownWonFrost',
  kind: 'stinger',
  brief: 'The Crown of Frost won: the Crown theme’s waltz head on vibes, wine glasses ringing over a violin tremolo, harp, timpani and sleigh bells. Clear and shining.',
  energy: 5,
  musicSend: 0.34,
  derivedFrom: 'crown-frost',
  abc: `
X:1
M:3/4
L:1/8
Q:1/4=108
K:C min
V:chords
[P:A] "Cm"z6 | "Ab"z6 | "Gm"z6 | "Cm"z6 | "Cm"z6 |
V:lead
[P:A] g2 f2 e2 | c3 d e2 | d2 c2 B2 | c4 G2 | c6 |
V:glass
[P:A] !mp! g6 | z6 | z6 | e6 | z6 |
`,
  parts: {
    lead: { inst: 'vibes', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    glass: { inst: 'wine-glasses', art: 'slow', role: 'colour', layers: ['main'], gain: -12, pan: 0.3 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9, pan: -0.2 },
    shiver: { inst: 'violins', art: 'trem', role: 'accomp', pattern: 'tremolo', layers: ['main'], octave: 3, size: 3, gain: -15 },
  },
  perc: {
    grid: 12,
    lines: {
      timp: { inst: 'timpani', layers: ['main'], steps: 'X...........', gain: -9, pitch: 'root' },
      bells: { inst: 'sleigh-bells', layers: ['main'], steps: '....x...x...', gain: -17 },
      cym: { inst: 'finger-cymbals', layers: ['main'], steps: '............ | ............ | ............ | ............ | X...........', gain: -15 },
    },
  },
  order: ['A'],
  loopFrom: 0,
})

/** 10 s: the Legend won, the Hall of Fame anthem: the Wildsong motif on violins with the horn below, held high. */
const legendWon = defineSong({
  id: 'legendWon',
  kind: 'stinger',
  brief: 'The Wildsong Legend won, the Hall of Fame anthem: the Wildsong motif sung out on violins with the horn two octaves below, harp, timpani and a cymbal swell, ending on a long held chord. The land’s own song, for you.',
  energy: 5,
  musicSend: 0.34,
  derivedFrom: 'wildsong',
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=96
K:C lyd
V:chords
[P:A] "C"z8 | "D"z8 | "Am"z8 | "C"z8 |
V:lead
[P:A] c2 d2 g4 | f e d4 z2 | e2 f2 e2 d2 | g8 |
V:horn
[P:A] C,2 D,2 G,4 | F, E, D,4 z2 | E,2 F,2 E,2 D,2 | G,8 |
`,
  parts: {
    lead: { inst: 'violins', art: 'vib', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['main'], gain: -6, pan: -0.2 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9, pan: -0.2 },
    pad: { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, size: 3, gain: -14 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -17, pan: 0.3 },
  },
  perc: {
    grid: 16,
    lines: {
      timp: { inst: 'timpani', layers: ['main'], steps: 'X.......x.......', gain: -9, pitch: 'root' },
      swell: { inst: 'cymbal-swell', layers: ['main'], steps: '................ | ................ | ........X....... | ................', gain: -15 },
    },
  },
  order: ['A'],
  loopFrom: 0,
  motifQuote: { part: 'lead', section: 'A' },
})

/** 4 s: the breeder rank went up. A rising flute phrase over horn, harp, timpani and a glock flourish. */
const rankUp = defineSong({
  id: 'rankUp',
  kind: 'stinger',
  brief: 'The breeder rank went up: a four-second rising flute phrase over horn and harp, a timpani on each bar and a glock flourish. A step up the ladder.',
  energy: 4,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=120
K:C
V:chords
[P:A] "C"z8 | "G"z4 "C"z4 |
V:lead
[P:A] G2 A2 c2 e2 | d4 c4 |
V:horn
[P:A] C,4 G,4 | G,4 C4 |
`,
  parts: {
    lead: { inst: 'flute', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    horn: { inst: 'horn', art: 'sus', role: 'accomp', layers: ['main'], gain: -7, pan: -0.2 },
  },
  accomp: {
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -9, pan: -0.2 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['main'], octave: 5, gain: -17, pan: 0.3 },
  },
  perc: { grid: 16, lines: { timp: { inst: 'timpani', layers: ['main'], steps: 'X...............', gain: -9, pitch: 'root' } } },
  order: ['A'],
  loopFrom: 0,
})

/** 2 s: a title earned. Three kalimba notes up the chord, glock an octave above. A little seal. */
const titleEarned = defineSong({
  id: 'titleEarned',
  kind: 'stinger',
  brief: 'A title earned: three kalimba notes up the chord with the glock an octave above, over one harp chord. A little seal of approval.',
  energy: 3,
  musicSend: 0.3,
  abc: `
X:1
M:4/4
L:1/8
Q:1/4=120
K:C
V:chords
[P:A] "C"z8 |
V:lead
[P:A] c2 e2 g4 |
V:sparkle
[P:A] !p! c'2 e'2 g'4 |
`,
  parts: {
    lead: { inst: 'kalimba', role: 'lead', layers: ['main'], gain: 5, pan: 0.05 },
    sparkle: { inst: 'glock', role: 'colour', layers: ['main'], gain: -8, pan: 0.3 },
  },
  accomp: { harp: { inst: 'harp', role: 'accomp', pattern: 'padSustain', layers: ['main'], octave: 3, size: 3, gain: -5 } },
  order: ['A'],
  loopFrom: 0,
})

export const STINGERS: Record<StingerId, Song> = { matchWin, matchLoss, matchDraw, cupWin, promotion, cupPlaced, cupOut, crownWonDawn, crownWonTides, crownWonEmbers, crownWonFrost, legendWon, rankUp, titleEarned }

/** Each Crown's own stinger, by event id. */
export const CROWN_STINGERS: Readonly<Record<string, StingerId>> = {
  'crown-of-dawn': 'crownWonDawn',
  'crown-of-tides': 'crownWonTides',
  'crown-of-embers': 'crownWonEmbers',
  'crown-of-frost': 'crownWonFrost',
}

/** Moments without their own stinger yet (S3's) use the nearest written one (§15). */
export const STINGER_STAND_INS: Record<string, StingerId> = {
  birth: 'promotion',
  farewell: 'matchLoss',
  birthday: 'matchWin',
  monsterSong: 'matchDraw',
  rest: 'matchDraw',
  play: 'matchDraw',
  journeyDepart: 'matchDraw',
  journeyReturn: 'matchWin',
}
