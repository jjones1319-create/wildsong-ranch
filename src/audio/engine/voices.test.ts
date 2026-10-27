import { describe, expect, it } from 'vitest'
import type { Voice } from './sampler.ts'
import { VoicePool } from './voices.ts'

function fakeVoice(endsAt: number): Voice & { stops: number[] } {
  const v = {
    endsAt,
    out: {} as AudioNode,
    source: null,
    rate: null,
    stopped: false,
    stops: [] as number[],
    stop(at: number) {
      v.stopped = true
      v.stops.push(at)
    },
  }
  return v
}

describe('the voice pool (§2, §4.4)', () => {
  it('steals silent-layer voices first, then the quietest, then the oldest', () => {
    const pool = new VoicePool('music', 3)
    const a = fakeVoice(100)
    const b = fakeVoice(100)
    const c = fakeVoice(100)
    pool.add({ voice: a, startedAt: 0, level: 0.9, silentLayer: false, owner: 'lead' })
    pool.add({ voice: b, startedAt: 1, level: 0.2, silentLayer: false, owner: 'harp' })
    pool.add({ voice: c, startedAt: 2, level: 0.9, silentLayer: true, owner: 'pad' })
    expect(pool.count(3)).toBe(3)
    expect(pool.makeRoom(3)).toBe(1)
    expect(c.stopped).toBe(true)
    pool.add({ voice: fakeVoice(100), startedAt: 3, level: 0.9, silentLayer: false, owner: 'lead' })
    pool.makeRoom(4)
    expect(b.stopped).toBe(true)
    pool.add({ voice: fakeVoice(100), startedAt: 4, level: 0.9, silentLayer: false, owner: 'lead' })
    pool.makeRoom(5)
    expect(a.stopped).toBe(true)
    expect(pool.stolen).toBe(3)
  })

  it('prunes voices that ended on their own and stops an owner', () => {
    const pool = new VoicePool('sfx', 16)
    pool.add({ voice: fakeVoice(1), startedAt: 0, level: 1, silentLayer: false, owner: 'hit' })
    pool.add({ voice: fakeVoice(10), startedAt: 0, level: 1, silentLayer: false, owner: 'hit' })
    pool.add({ voice: fakeVoice(10), startedAt: 0, level: 1, silentLayer: false, owner: 'miss' })
    expect(pool.count(5)).toBe(2)
    expect(pool.owners()).toEqual({ hit: 1, miss: 1 })
    pool.stopOwner('hit', 5)
    expect(pool.count(5)).toBe(1)
    pool.setSilent('miss', true)
    expect(pool.makeRoom(5)).toBe(0)
  })
})
