/**
 * Town (SOUND_UPGRADE §7.3): one piece, F major, a 3/4 folk waltz at 108, with a stem for every Town screen
 * so the music never restarts between shops. Strumstick and alto recorder lead the square; the shop keeps
 * kalimba, harp and bass; the market adds a tambourine and claps; the guild is proud with horn and soft
 * timpani; the library and journal are harp and music box; mail is pizzicato and kalimba; the workshop has a
 * woodblock; the fair has recorder, tambourine and pizz. Original.
 */
import { defineSong } from '../song.ts'

export default defineSong({
  id: 'town',
  kind: 'town',
  brief: 'Town: a cheerful folk waltz, strummed strings and a recorder tune, bass on one and chords on two and three. Each shop hears its own slice of the same tune: the market claps, the guild is proud with horn and timpani, the library is harp and a music box.',
  energy: 3,
  musicSend: 0.22,
  abc: `
X:1
M:3/4
L:1/8
Q:1/4=108
K:F
V:chords
[P:intro] "F"z6 | "Bb"z6 | "F"z6 | "C"z6 |
[P:A] "F"z6 | "Bb"z6 | "F"z6 | "C"z6 | "Dm"z6 | "Bb"z6 | "C"z6 | "F"z6 |
[P:B] "Bb"z6 | "F"z6 | "Gm"z6 | "C"z6 | "Bb"z6 | "F"z6 | "C"z6 | "F"z6 |
[P:A2] "F"z6 | "Bb"z6 | "F"z6 | "C"z6 | "Dm"z6 | "Bb"z6 | "C"z6 | "F"z6 |
[P:C] "Gm"z6 | "C"z6 | "F"z6 | "Dm"z6 | "Bb"z6 | "C"z6 | "F"z6 | "C"z6 |
[P:B2] "Bb"z6 | "F"z6 | "Gm"z6 | "C"z6 | "Bb"z6 | "F"z6 | "C"z6 | "F"z6 |
V:lead
[P:intro] z6 | z6 | z6 | z6 |
[P:A] !mp! f2 g2 a2 | b4 z2 | a2 f2 g2 | g2 e2 z2 | f2 e2 d2 | f4 z2 | e2 g2 b2 | a4 z2 |
[P:B] d'2 c'2 b2 | a2 f2 z2 | g2 b2 a2 | c'4 z2 | d'4 b2 | c'2 a2 z2 | g2 e2 g2 | f2 a2 z2 |
[P:A2] f2 g2 a2 | b4 z2 | a2 f2 g2 | g2 e2 z2 | d2 e2 f2 | d4 z2 | e2 g2 c'2 | c'4 z2 |
[P:C] b2 a2 g2 | e2 g2 z2 | a2 b2 a2 | f2 d2 z2 | b2 a2 b2 | g2 e2 z2 | f2 g2 a2 | e2 g2 z2 |
[P:B2] d'2 c'2 b2 | a2 f2 z2 | g2 b2 a2 | c'4 z2 | d'2 c'2 d'2 | c'2 a4 | e2 g2 e2 | f2 a4 |
V:horn
[P:intro] z6 | z6 | z6 | z6 |
[P:A] !p! C4 z2 | D4 z2 | C4 z2 | E4 z2 | D4 z2 | D4 z2 | E4 z2 | C4 z2 |
[P:B] !p! D4 z2 | C4 z2 | D4 z2 | E4 z2 | D4 z2 | C4 z2 | E4 z2 | C4 z2 |
[P:A2] !p! C4 z2 | D4 z2 | C4 z2 | E4 z2 | D4 z2 | D4 z2 | E4 z2 | C4 z2 |
[P:C] !p! D4 z2 | E4 z2 | C4 z2 | D4 z2 | D4 z2 | E4 z2 | C4 z2 | E4 z2 |
[P:B2] !p! D4 z2 | C4 z2 | D4 z2 | E4 z2 | D4 z2 | C4 z2 | E4 z2 | C4 z2 |
V:musicbox
[P:intro] z6 | z6 | z6 | z6 |
[P:A] !p! a2 g2 f2 | d'4 z2 | c'2 b2 a2 | g4 z2 | f2 e2 d2 | d4 z2 | e2 g2 b2 | a4 z2 |
[P:B] !p! b2 a2 g2 | f4 z2 | g2 b2 d'2 | c'4 z2 | b2 c'2 d'2 | c'4 z2 | g2 e2 g2 | f4 z2 |
[P:A2] !p! a2 g2 f2 | d'4 z2 | c'2 b2 a2 | g4 z2 | f2 e2 d2 | d4 z2 | e2 g2 b2 | a4 z2 |
[P:C] !p! b2 a2 g2 | e4 z2 | a2 b2 c'2 | d'4 z2 | b2 d'2 c'2 | g4 z2 | a2 g2 f2 | e4 z2 |
[P:B2] !p! b2 a2 g2 | f4 z2 | g2 b2 d'2 | c'4 z2 | b2 c'2 d'2 | c'4 z2 | g2 e2 g2 | f4 z2 |
`,
  parts: {
    lead: { inst: 'recorder-alto', role: 'lead', layers: ['main'], gain: 0, pan: 0.1 },
    horn: { inst: 'horn', art: 'sus', role: 'counter', layers: ['main'], gain: -6, pan: -0.2 },
    musicbox: { inst: 'music-box', role: 'counter', layers: ['main'], gain: -6, pan: 0.2 },
  },
  accomp: {
    strum: { inst: 'strumstick', role: 'accomp', pattern: 'strum', layers: ['main'], octave: 3, gain: -8, pan: -0.15, density: 'normal' },
    pizz: { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'waltz', layers: ['main'], octave: 2, gain: -8 },
    kalimba: { inst: 'kalimba', role: 'accomp', pattern: 'kalimbaOstinato', layers: ['main'], octave: 3, gain: -10, pan: 0.25 },
    harp: { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -8, pan: -0.1 },
    bass: { inst: 'contrabass', art: 'pizz', role: 'bass', pattern: 'bassRoot', layers: ['main'], octave: 2, gain: -9 },
  },
  perc: {
    grid: 12,
    lines: {
      drum: { inst: 'frame-drum', layers: ['main'], steps: 'X...x...x...', gain: -12 },
      tamb: { inst: 'tambourine', layers: ['main'], steps: '....x...x...', gain: -16, pan: 0.3 },
      claps: { inst: 'claps', layers: ['main'], steps: '....x.......', gain: -12, pan: -0.2 },
      timp: { inst: 'timpani', layers: ['main'], steps: 'X...........', gain: -14, pitch: 'root' },
      wood: { inst: 'woodblock', layers: ['main'], steps: 'x.....x..x..', gain: -14, pan: 0.2 },
    },
  },
  order: ['intro', 'A', 'B', 'A2', 'C', 'B2'],
  loopFrom: 1,
  stems: {
    town: ['lead', 'strum', 'pizz', 'drum', 'tamb'],
    shop: ['kalimba', 'harp', 'bass'],
    market: ['lead', 'strum', 'pizz', 'drum', 'tamb', 'claps'],
    guild: ['lead', 'strum', 'pizz', 'drum', 'horn', 'timp'],
    library: ['harp', 'musicbox'],
    journal: ['musicbox', 'harp'],
    mail: ['pizz', 'kalimba'],
    upgrades: ['wood', 'strum', 'lead'],
    oddJobs: ['lead', 'tamb', 'pizz'],
  },
})
