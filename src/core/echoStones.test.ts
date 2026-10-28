import { describe, expect, it } from 'vitest'
import { ECHO_STONES, TITLES } from '../data/tuning.ts'
import { applyEchoStones, canPlayEchoStones, echoMelody, echoPay, echoStoneCount, echoTempo, MOON_STONE } from './echoStones.ts'
import { applyOddJob } from './oddJobs.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('Echo Stones (CONTENT §13)', () => {
  it('deals a seeded melody: four stones to round 10, the Moon at round 11, then all five; never three of a stone in a row', () => {
    const a = echoMelody(7, 60)
    expect(a).toEqual(echoMelody(7, 60))
    expect(a).toHaveLength(60)
    expect(a).not.toEqual(echoMelody(8, 60))
    for (let i = 2; i < a.length; i++) expect(a[i] === a[i - 1] && a[i] === a[i - 2]).toBe(false)
    expect(echoMelody(9, 5)).toHaveLength(5)
    // The first ten notes are what the four-stone game always dealt (an inline copy of the old rule).
    const oldMelody = (seed: number): number[] => {
      const rng = createRng(seed)
      const out: number[] = []
      while (out.length < 10) {
        const s = rng.nextInt(0, 3)
        const n = out.length
        if (n >= 2 && out[n - 1] === s && out[n - 2] === s) continue
        out.push(s)
      }
      return out
    }
    for (let seed = 1; seed <= 50; seed++) {
      const m = echoMelody(seed, 80)
      expect(m.slice(0, 10)).toEqual(oldMelody(seed))
      expect(m[ECHO_STONES.moonRound - 1]).toBe(MOON_STONE)
      for (const s of m) expect([0, 1, 2, 3, 4]).toContain(s)
      // A longer melody starts with the shorter one, so a game can extend it.
      expect(echoMelody(seed, 15)).toEqual(m.slice(0, 15))
    }
    // All five stones show up in a long melody.
    expect(new Set(echoMelody(3, 200)).size).toBe(5)
    expect(echoStoneCount(1)).toBe(4)
    expect(echoStoneCount(ECHO_STONES.moonRound - 1)).toBe(4)
    expect(echoStoneCount(ECHO_STONES.moonRound)).toBe(5)
    expect(echoStoneCount(500)).toBe(5)
  })

  it('quickens every four rounds to round 10, then by 1% every two rounds, never below the floor; Relaxed stretches it by half', () => {
    const t = ECHO_STONES.tempo
    expect(echoTempo(1, false)).toEqual({ noteMs: t.noteMs, gapMs: t.gapMs })
    expect(echoTempo(4, false)).toEqual({ noteMs: 520, gapMs: 200 })
    expect(echoTempo(5, false)).toEqual({ noteMs: 458, gapMs: 176 })
    expect(echoTempo(8, false)).toEqual({ noteMs: 458, gapMs: 176 })
    expect(echoTempo(9, false)).toEqual({ noteMs: 403, gapMs: 155 })
    expect(echoTempo(10, false)).toEqual({ noteMs: 403, gapMs: 155 })
    expect(echoTempo(11, false)).toEqual(echoTempo(10, false))
    expect(echoTempo(12, false)).toEqual({ noteMs: 399, gapMs: 153 })
    // Very slowly: round 30 is only about 10% quicker than round 10.
    expect(echoTempo(30, false).noteMs).toBeGreaterThanOrEqual(360)
    let last = echoTempo(1, false)
    for (let r = 2; r <= 400; r++) {
      const now = echoTempo(r, false)
      expect(now.noteMs).toBeLessThanOrEqual(last.noteMs)
      expect(now.gapMs).toBeLessThanOrEqual(last.gapMs)
      last = now
    }
    expect(echoTempo(5000, false)).toEqual({ noteMs: t.minNoteMs, gapMs: t.minGapMs })
    expect(echoTempo(1, true)).toEqual({ noteMs: Math.round((t.noteMs * t.relaxedPct) / 100), gapMs: Math.round((t.gapMs * t.relaxedPct) / 100) })
    expect(echoTempo(0, false)).toEqual(echoTempo(1, false))
  })

  it('pays 15G a round with no cap', () => {
    expect(echoPay(0)).toBe(0)
    expect(echoPay(1)).toBe(ECHO_STONES.payPerRound)
    expect(echoPay(7)).toBe(105)
    expect(echoPay(10)).toBe(150)
    expect(echoPay(30)).toBe(450)
    expect(echoPay(-3)).toBe(0)
    expect(echoPay(2.9)).toBe(30)
    expect(echoPay(Number.NaN)).toBe(0)
  })

  it('pays once a week, independent of Turnip Sort, and needs a monster', () => {
    const g = createGameState({ monster: makeMonster() })
    g.week = 20
    expect(canPlayEchoStones(g)).toEqual({ ok: true })
    const r = applyEchoStones(g, 6, false)
    expect(r.refused).toBeNull()
    expect(r.pay).toBe(90)
    expect(r.state.money).toBe(g.money + 90)
    expect(r.state.echoStonesWeek).toBe(20)
    expect(r.state.echoStonesBest).toBe(6)
    expect(r.newBest).toBe(true)
    expect(r.stressRelief).toBe(0)
    // The same week again: refused, nothing changes.
    expect(applyEchoStones(r.state, 9, false)).toMatchObject({ pay: 0, refused: 'played' })
    // No cap: a long game pays every round.
    expect(applyEchoStones(g, 24, false).pay).toBe(360)
    expect(canPlayEchoStones(r.state)).toEqual({ ok: false, reason: 'played' })
    // Turnip Sort has its own week.
    const t = applyOddJob(r.state, 10, 0)
    expect(t.refused).toBeNull()
    expect(t.state.oddJobWeek).toBe(20)
    expect(canPlayEchoStones({ ...r.state, week: 21 })).toEqual({ ok: true })
    expect(applyEchoStones({ ...g, monster: null }, 5, false).refused).toBe('noMonster')
    expect(applyEchoStones({ ...g, monster: null }, 5, true).refused).toBe('noMonster')
  })

  it('round 8 takes 5 stress off the monster, once per paid play, never below 0', () => {
    const g = createGameState({ monster: makeMonster() })
    g.monster!.stress = 40
    const r = applyEchoStones(g, ECHO_STONES.stressRound, false)
    expect(r.stressRelief).toBe(ECHO_STONES.stressRelief)
    expect(r.state.monster!.stress).toBe(35)
    const low = createGameState({ monster: makeMonster() })
    low.monster!.stress = 2
    const r2 = applyEchoStones(low, 12, false)
    expect(r2.state.monster!.stress).toBe(0)
    expect(r2.stressRelief).toBe(2)
    const short = applyEchoStones(g, ECHO_STONES.stressRound - 1, false)
    expect(short.stressRelief).toBe(0)
    expect(short.state.monster!.stress).toBe(40)
  })

  it('practice pays nothing, leaves the week and the stress alone, but keeps a best score', () => {
    const g = createGameState({ monster: makeMonster() })
    g.monster!.stress = 40
    g.week = 5
    const p = applyEchoStones(g, 9, true)
    expect(p.refused).toBeNull()
    expect(p.pay).toBe(0)
    expect(p.state.money).toBe(g.money)
    expect(p.state.echoStonesWeek).toBeNull()
    expect(p.state.monster!.stress).toBe(40)
    expect(p.state.echoStonesBest).toBe(9)
    expect(canPlayEchoStones(p.state)).toEqual({ ok: true })
    // A worse practice game does not lower the best; a played week still allows practice.
    const paid = applyEchoStones(p.state, 3, false)
    expect(paid.state.echoStonesBest).toBe(9)
    expect(paid.newBest).toBe(false)
    const again = applyEchoStones(paid.state, 4, true)
    expect(again.refused).toBeNull()
    expect(again.state.money).toBe(paid.state.money)
  })

  it('round 15 earns the Perfect Pitch title at once, for the ranch and the monster, only once', () => {
    const g = createGameState({ monster: makeMonster() })
    const near = applyEchoStones(g, TITLES.perfectPitchRound - 1, true)
    expect(near.titles).toEqual([])
    const r = applyEchoStones(near.state, TITLES.perfectPitchRound, true)
    expect(r.titles).toEqual(['Perfect Pitch'])
    expect(r.state.titles).toContain('Perfect Pitch')
    expect(r.state.monster!.records.titles).toContain('Perfect Pitch')
    const r2 = applyEchoStones(r.state, 20, false)
    expect(r2.titles).toEqual([])
    expect(r2.state.titles.filter((t) => t === 'Perfect Pitch')).toHaveLength(1)
  })
})
