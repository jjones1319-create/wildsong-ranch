/**
 * SOUND_UPGRADE §3.6: the motifs, written once here and quoted by the songs. All original.
 *
 * The Wildsong motif (the land's own song): six notes in D Lydian, singable, one rising 4th, the raised 4th
 * touched once, ending on a held non-tonic note so it can lead anywhere. The checker finds it by its exact
 * pitch-interval sequence in any transposition, with free rhythm.
 */

export interface Motif {
  id: string
  /** Sounding MIDI as written (the reference transposition). */
  pitches: readonly number[]
  /** Beats per note, in quarter notes (free in quotes; this is the reference shape). */
  beats: readonly number[]
  /** Semitone intervals between successive notes. */
  intervals: readonly number[]
}

function motif(id: string, pitches: readonly number[], beats: readonly number[]): Motif {
  const intervals = pitches.slice(1).map((p, i) => p - pitches[i]!)
  return { id, pitches, beats, intervals }
}

/** D4 E4 A4 G#4 F#4 E4: up a step, up a 4th, then down through the raised 4th to a held E. */
export const WILDSONG_MOTIF: Motif = motif('wildsong', [62, 64, 69, 68, 66, 64], [1, 1, 2, 0.5, 0.5, 3])

/** Corin's calling card: a cocky rising shape, G B D G. */
export const CORIN_MOTIF: Motif = motif('corin', [67, 71, 74, 79], [0.5, 0.5, 0.5, 1.5])

/** The Masked Breeder: a chromatic turn, C C# C B C. */
export const MASKED_MOTIF: Motif = motif('masked', [72, 73, 72, 71, 72], [0.5, 0.5, 0.5, 0.5, 2])

/** True when `pitches` contains the motif's interval sequence as a contiguous run (any transposition). */
export function containsMotif(pitches: readonly number[], m: Motif = WILDSONG_MOTIF): boolean {
  const n = m.intervals.length
  if (pitches.length < n + 1) return false
  outer: for (let i = 0; i + n < pitches.length; i++) {
    for (let k = 0; k < n; k++) if (pitches[i + k + 1]! - pitches[i + k]! !== m.intervals[k]) continue outer
    return true
  }
  return false
}

/** The motif transposed so its first note is `startMidi`. */
export function transposeMotif(m: Motif, startMidi: number): number[] {
  const shift = startMidi - m.pitches[0]!
  return m.pitches.map((p) => p + shift)
}
