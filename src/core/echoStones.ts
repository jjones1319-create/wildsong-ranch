import { ECHO_STONES } from '../data/tuning.ts'
import { addCondition } from './monster.ts'
import { divRound } from './mathx.ts'
import { createRng } from './rng.ts'
import type { GameState } from './state.ts'
import { awardTitles, type TitleId } from './titles.ts'

/**
 * CONTENT §13 Odd Jobs: Echo Stones, a memory game. The stones play a melody that grows by one note each
 * round; the player repeats it by tapping. Four stones to start; at round 11 the Moon stone joins. The tempo
 * quickens every four rounds to round 10, then very slowly, and there is no last round: a slip (after the one
 * retry) ends the game. The round runs in the UI (it is a real-time game), but the melody, the tempo, the pay,
 * the weekly limit, the stress relief and the title are rules here, so a game can be replayed in a test.
 * Practice plays pay nothing and leave the week alone, but a best score (and the Perfect Pitch title) counts
 * however it was reached.
 */

export type Stone = 0 | 1 | 2 | 3 | 4

/** The fifth stone, which joins at `ECHO_STONES.moonRound`. */
export const MOON_STONE: Stone = 4

export type EchoRefusal = 'noMonster' | 'played'

/** How many stones are on the board in round `round` (1-based). */
export function echoStoneCount(round: number): number {
  return round >= ECHO_STONES.moonRound ? ECHO_STONES.stones : ECHO_STONES.firstStones
}

/**
 * The game's melody from a seed, `length` notes long: round r repeats its first r notes. Notes before the Moon's
 * round use the first four stones, the Moon's round adds the Moon (no draw), and later notes use all five. Never
 * three of a stone in a row. Each note depends only on the ones before it, so a longer melody from the same seed
 * starts with the shorter one (the UI extends it as a game goes on).
 */
export function echoMelody(seed: number, length: number): Stone[] {
  const rng = createRng(seed)
  const out: Stone[] = []
  const moonAt = ECHO_STONES.moonRound - 1
  while (out.length < length) {
    const n = out.length
    if (n === moonAt) {
      out.push(MOON_STONE)
      continue
    }
    const count = n < moonAt ? ECHO_STONES.firstStones : ECHO_STONES.stones
    const s = rng.nextInt(0, count - 1) as Stone
    if (n >= 2 && out[n - 1] === s && out[n - 2] === s) continue
    out.push(s)
  }
  return out
}

/** 15G per round cleared, with no cap. */
export function echoPay(roundsCleared: number): number {
  return Number.isFinite(roundsCleared) ? Math.max(0, Math.floor(roundsCleared)) * ECHO_STONES.payPerRound : 0
}

/**
 * How long a stone glows and the pause after it in round `round` (1-based): quicker every four rounds up to
 * round 10, then by 1% every two rounds, never below the floor; Relaxed stretches both.
 */
export function echoTempo(round: number, relaxed: boolean): { noteMs: number; gapMs: number } {
  const t = ECHO_STONES.tempo
  const r = Math.max(1, Math.floor(round))
  const early = Math.floor((Math.min(r, t.speedUpUntil) - 1) / t.speedUpEvery)
  const late = Math.floor(Math.max(0, r - t.speedUpUntil) / t.lateEvery)
  let note: number = t.noteMs
  let gap: number = t.gapMs
  for (let i = 0; i < early; i++) {
    note = divRound(note * (100 - t.speedUpPct), 100)
    gap = divRound(gap * (100 - t.speedUpPct), 100)
  }
  for (let i = 0; i < late && (note > t.minNoteMs || gap > t.minGapMs); i++) {
    note = divRound(note * (100 - t.latePct), 100)
    gap = divRound(gap * (100 - t.latePct), 100)
  }
  note = Math.max(t.minNoteMs, note)
  gap = Math.max(t.minGapMs, gap)
  if (relaxed) {
    note = divRound(note * t.relaxedPct, 100)
    gap = divRound(gap * t.relaxedPct, 100)
  }
  return { noteMs: note, gapMs: gap }
}

export function canPlayEchoStones(state: GameState): { ok: true } | { ok: false; reason: EchoRefusal } {
  if (!state.monster || state.ended) return { ok: false, reason: 'noMonster' }
  if (state.echoStonesWeek !== null && state.echoStonesWeek === state.week) return { ok: false, reason: 'played' }
  return { ok: true }
}

export interface EchoResult {
  state: GameState
  pay: number
  /** Stress taken off the monster (0 when the round was not reached, or in practice). */
  stressRelief: number
  /** True when this game set a new best. */
  newBest: boolean
  titles: TitleId[]
  refused: EchoRefusal | null
}

/**
 * Settles a finished game. A paid play stamps the week, pays by rounds, and relieves stress from round 8;
 * practice only records the best. The Perfect Pitch title is awarded at once when round 15 is reached.
 */
export function applyEchoStones(input: GameState, roundsCleared: number, practice: boolean): EchoResult {
  const rounds = Math.max(0, Math.floor(roundsCleared))
  if (!input.monster || input.ended) return { state: input, pay: 0, stressRelief: 0, newBest: false, titles: [], refused: 'noMonster' }
  if (!practice) {
    const can = canPlayEchoStones(input)
    if (!can.ok) return { state: input, pay: 0, stressRelief: 0, newBest: false, titles: [], refused: can.reason }
  }
  let state = structuredClone(input)
  let pay = 0
  let stressRelief = 0
  if (!practice) {
    pay = echoPay(rounds)
    state.money += pay
    state.echoStonesWeek = state.week
    if (rounds >= ECHO_STONES.stressRound && state.monster) {
      const before = state.monster.stress
      state.monster.stress = addCondition(before, -ECHO_STONES.stressRelief)
      stressRelief = before - state.monster.stress
    }
  }
  const newBest = rounds > state.echoStonesBest
  if (newBest) state.echoStonesBest = rounds
  const awarded = awardTitles(state)
  state = awarded.state
  return { state, pay, stressRelief, newBest, titles: awarded.titles, refused: null }
}
