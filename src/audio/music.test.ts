import { describe, expect, it } from 'vitest'
import { SEASONS } from '../data/types.ts'
import { midiToHz, parsePattern, parseToken, ranchTrackFor, renderTrack, sampleCount, stepsOf, TRACK_IDS, TRACKS } from './music.ts'
import { SFX, SFX_IDS } from './sfx.ts'

describe('the music sequencer (§23)', () => {
  it('reads note tokens, rests and holds', () => {
    expect(parseToken('c4')).toBe(60)
    expect(parseToken('a4')).toBe(69)
    expect(parseToken('f#3')).toBe(54)
    expect(parseToken('bb3')).toBe(58)
    expect(parseToken('-')).toBe(0)
    expect(parseToken('.')).toBe(-1)
    expect(() => parseToken('h4')).toThrow()
    expect(parsePattern(' c4  . - e4 ')).toEqual([60, -1, 0, 64])
    expect(midiToHz(69)).toBe(440)
    expect(midiToHz(81)).toBeCloseTo(880)
  })

  it('every track parses, fills whole bars and renders finite samples within range', () => {
    for (const id of TRACK_IDS) {
      const track = TRACKS[id]
      expect(track.id).toBe(id)
      const steps = stepsOf(track)
      expect(steps % 16).toBe(0)
      for (const v of track.voices) expect(steps % parsePattern(v.pattern).length).toBe(0)
      const samples = renderTrack(track, 11025)
      expect(samples.length).toBe(sampleCount(track, 11025))
      let peak = 0
      let energy = 0
      for (let i = 0; i < samples.length; i++) {
        const x = samples[i]!
        expect(Number.isFinite(x)).toBe(true)
        peak = Math.max(peak, Math.abs(x))
        energy += x * x
      }
      expect(peak).toBeLessThanOrEqual(1)
      expect(peak).toBeGreaterThan(0.05)
      expect(energy / samples.length).toBeGreaterThan(0.0005)
    }
  })

  it('renders the same bytes every time, and the loop length follows the tempo', () => {
    const a = renderTrack(TRACKS.town, 11025)
    const b = renderTrack(TRACKS.town, 11025)
    expect(Buffer.from(a.buffer).equals(Buffer.from(b.buffer))).toBe(true)
    // 64 sixteenth steps at 124 bpm = 64 × 60 / 124 / 4 seconds.
    expect(sampleCount(TRACKS.town, 11025)).toBe(Math.round(((64 * 60) / 124 / 4) * 11025))
    expect(TRACKS.victory.loop).toBe(false)
    expect(TRACKS.battle.loop).toBe(true)
  })

  it('picks a ranch track for every season', () => {
    const picked = new Set(SEASONS.map(ranchTrackFor))
    expect(picked.size).toBe(4)
  })
})

describe('the sound table (§23)', () => {
  it('has sane ZzFX parameters for every effect', () => {
    for (const id of SFX_IDS) {
      const p = SFX[id]
      expect(p.length).toBeGreaterThanOrEqual(6)
      expect(p.length).toBeLessThanOrEqual(21)
      expect(p.every((n) => Number.isFinite(n))).toBe(true)
      expect(p[0]).toBeGreaterThan(0)
      expect(p[0]).toBeLessThanOrEqual(1.2)
      expect(p[2]).toBeGreaterThan(20)
      expect(p[2]).toBeLessThan(4000)
    }
  })
})
