import { describe, expect, it } from 'vitest'
import { findClicks, findDropouts } from './clicks.ts'
import { crestDb, kWeighting, loudness, peakDb, rmsDb } from './loudness.ts'
import { bandShares } from './spectrum.ts'
import { truePeakDb } from './truepeak.ts'
import { decodeWav, encodeWav } from './wav.ts'

const SR = 48000

function sine(hz: number, amp: number, seconds: number, sr = SR): Float32Array {
  const out = new Float32Array(Math.round(seconds * sr))
  for (let i = 0; i < out.length; i++) out[i] = amp * Math.sin((2 * Math.PI * hz * i) / sr)
  return out
}

describe('loudness (BS.1770-4)', () => {
  it('reproduces the published 48 kHz K-weighting coefficients', () => {
    const [shelf, hp] = kWeighting(48000)
    expect(shelf.b0).toBeCloseTo(1.53512485958697, 6)
    expect(shelf.b1).toBeCloseTo(-2.69169618940638, 6)
    expect(shelf.b2).toBeCloseTo(1.19839281085285, 6)
    expect(shelf.a1).toBeCloseTo(-1.69065929318241, 6)
    expect(shelf.a2).toBeCloseTo(0.73248077421585, 6)
    expect(hp.a1).toBeCloseTo(-1.99004745483398, 6)
    expect(hp.a2).toBeCloseTo(0.99007225036621, 6)
  })

  it('reads a −20 dBFS 1 kHz sine at −23 LUFS in one channel and −20 LUFS in two', () => {
    const s = sine(1000, 0.1, 5)
    expect(loudness([s], SR).integrated).toBeCloseTo(-23.0, 1)
    expect(loudness([s, s], SR).integrated).toBeCloseTo(-20.0, 1)
    const s441 = sine(1000, 0.1, 5, 44100)
    const r = loudness([s441, s441], 44100)
    expect(r.integrated).toBeCloseTo(-20.0, 1)
    expect(r.shortTermMax).toBeCloseTo(-20.0, 1)
    expect(r.momentaryMax).toBeCloseTo(-20.0, 1)
  })

  it('gates silence and quiet tails out of the integrated value', () => {
    const loud = sine(1000, 0.1, 3)
    const tail = new Float32Array(SR * 5)
    const joined = new Float32Array(loud.length + tail.length)
    joined.set(loud)
    joined.set(tail, loud.length)
    // The 400 ms blocks straddling the edge pass the gates, as in every BS.1770 meter: within half an LU.
    expect(loudness([joined], SR).integrated).toBeCloseTo(-23.0, 0)
    expect(loudness([tail], SR).integrated).toBe(-Infinity)
  })

  it('peak, rms and crest', () => {
    const s = sine(440, 0.5, 1)
    expect(peakDb([s])).toBeCloseTo(-6.02, 1)
    expect(rmsDb([s])).toBeCloseTo(-9.03, 1)
    expect(crestDb([s])).toBeCloseTo(3.01, 1)
  })
})

describe('true peak', () => {
  it('finds the sample peak of a sine and the inter-sample peak of a Nyquist-ish tone', () => {
    expect(truePeakDb([sine(440, 0.5, 0.5)])).toBeCloseTo(-6.02, 1)
    // A tone at a quarter of the sample rate sampled at 45° phase: every sample reads 0.354 (−9 dBFS) but the
    // waveform peaks at 0.5 (−6 dBTP) between them.
    const x = new Float32Array(SR / 10)
    for (let i = 0; i < x.length; i++) x[i] = 0.5 * Math.sin((Math.PI / 2) * i + Math.PI / 4)
    expect(peakDb([x])).toBeCloseTo(-9.03, 1)
    const tp = truePeakDb([x])
    expect(tp).toBeGreaterThan(-6.5)
    expect(tp).toBeLessThan(-5.7)
  })
})

describe('spectrum', () => {
  it('puts a 4 kHz tone in the 2–6 kHz band and a 100 Hz tone outside both', () => {
    const [mid, high] = bandShares([sine(4000, 0.3, 1)], SR, [
      [2000, 6000],
      [8000, 24000],
    ])
    expect(mid).toBeGreaterThan(0.95)
    expect(high).toBeLessThan(0.01)
    const [mid2, high2] = bandShares([sine(100, 0.3, 1)], SR, [
      [2000, 6000],
      [8000, 24000],
    ])
    expect(mid2).toBeLessThan(0.01)
    expect(high2).toBeLessThan(0.01)
  })
})

describe('clicks and dropouts', () => {
  it('reports a step unless it sits on a scheduled onset', () => {
    const x = new Float32Array(SR)
    for (let i = SR / 2; i < SR; i++) x[i] = 0.5
    const found = findClicks([x], SR)
    expect(found).toHaveLength(1)
    expect(found[0]!.t).toBeCloseTo(0.5, 3)
    expect(findClicks([x], SR, [0.502])).toHaveLength(0)
    expect(findClicks([sine(440, 0.9, 0.2)], SR)).toHaveLength(0)
  })

  it('finds a silent second but not a written rest', () => {
    const a = sine(440, 0.3, 1)
    const x = new Float32Array(SR * 3)
    x.set(a)
    x.set(a, SR * 2)
    const d = findDropouts([x], SR)
    expect(d).toHaveLength(1)
    expect(d[0]!.start).toBeCloseTo(1, 1)
    expect(d[0]!.end).toBeCloseTo(2, 1)
    expect(findDropouts([x], SR, -60, 300, [[1, 2]])).toHaveLength(0)
  })
})

describe('wav', () => {
  it('round-trips 16-bit and float files', () => {
    const l = sine(440, 0.5, 0.05)
    const r = sine(660, 0.25, 0.05)
    const back16 = decodeWav(encodeWav([l, r], 44100, 16))
    expect(back16.sampleRate).toBe(44100)
    expect(back16.channels).toHaveLength(2)
    expect(back16.channels[0]![100]).toBeCloseTo(l[100]!, 3)
    expect(back16.channels[1]![100]).toBeCloseTo(r[100]!, 3)
    const back32 = decodeWav(encodeWav([l], 48000, 32))
    expect(back32.channels[0]![7]).toBeCloseTo(l[7]!, 6)
    expect(() => decodeWav(new Uint8Array(20))).toThrow()
  })
})
