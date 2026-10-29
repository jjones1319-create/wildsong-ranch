import { describe, expect, it } from 'vitest'
import { ART, STAGES } from '../data/tuning.ts'
import { memoryStore } from './db.ts'
import { bandStage, isBasePortrait, PORTRAIT_PREFIX, PortraitCache, portraitBand, portraitKey, type PortraitJob } from './portraitCache.ts'

const blob = (tag: string) => new Blob([tag], { type: 'image/webp' })

describe('portrait cache (ART_2_PLAN §3.3)', () => {
  it('bands follow the drawn sizes and the old fade', () => {
    expect(portraitBand(1)).toBe('small')
    expect(portraitBand(STAGES.sizePct.smallUntil)).toBe('small')
    expect(portraitBand(STAGES.sizePct.mediumUntil)).toBe('medium')
    expect(portraitBand(STAGES.prime[0])).toBe('full')
    expect(portraitBand(STAGES.visiblyOld)).toBe('old')
    expect(portraitBand(10)).toBe('old')
    expect(portraitBand(bandStage('medium'))).toBe('medium')
    expect(portraitBand(bandStage('old'))).toBe('old')
    expect(isBasePortrait({ look: 'puddlepup', variant: null, stage: 5, face: 'neutral' })).toBe(true)
    expect(isBasePortrait({ look: 'puddlepup', variant: null, stage: 5, face: 'happy' })).toBe(false)
  })

  it('keys are prefixed, versioned and shared per band', () => {
    const a = portraitKey({ look: 'puddlepup', variant: null, stage: 1, face: 'sad' })
    const b = portraitKey({ look: 'puddlepup', variant: null, stage: 2, face: 'sad' })
    expect(a).toBe(b)
    expect(a.startsWith(`${PORTRAIT_PREFIX}v${ART.portrait.version}/puddlepup/small/`)).toBe(true)
    expect(portraitKey({ look: 'puddlepup', variant: 'songheart-puddlepup', stage: 5, face: 'neutral' })).toContain('puddlepup.songheart-puddlepup/full/neutral')
  })

  it('draws once, serves from memory and the store, and queues jobs one at a time', async () => {
    const store = memoryStore()
    const jobs: PortraitJob[] = []
    let running = 0
    let maxRunning = 0
    const cache = new PortraitCache(
      store,
      async (job) => {
        jobs.push(job)
        running++
        maxRunning = Math.max(maxRunning, running)
        await new Promise((r) => setTimeout(r, 5))
        running--
        return blob(job.face)
      },
      (b) => `url:${b.size}:${b.type}`,
    )
    const req = { look: 'puddlepup' as const, variant: null, stage: 3, face: 'happy' }
    const [u1, u2] = await Promise.all([cache.get(req), cache.get({ ...req, stage: 4 })])
    expect(u1).toBe(u2)
    expect(jobs).toHaveLength(1)
    expect(jobs[0]).toMatchObject({ band: 'medium', drawStage: bandStage('medium') })
    expect(cache.peek(req)).toBe(u1)
    await cache.get({ ...req, face: 'sad' })
    await Promise.all([cache.get({ ...req, face: 'tired' }), cache.get({ ...req, face: 'angry' })])
    expect(maxRunning).toBe(1)
    // a fresh cache over the same store finds the stored picture without drawing
    const again = new PortraitCache(store, async () => {
      throw new Error('should not draw')
    }, (b) => `url:${b.size}:${b.type}`)
    expect(await again.get(req)).toBe(u1)
    const keys = (await store.keys()).filter((k) => k.startsWith(PORTRAIT_PREFIX))
    expect(keys).toHaveLength(4)
  })

  it('a failed draw gives null and nothing is stored; the store never throws out', async () => {
    const store = memoryStore()
    const cache = new PortraitCache(store, async () => null, () => 'x')
    expect(await cache.get({ look: 'puddlepup', variant: null, stage: 5, face: 'sad' })).toBeNull()
    expect((await store.keys()).length).toBe(0)
    const bad = {
      get: async () => {
        throw new Error('broken')
      },
      set: async () => {
        throw new Error('broken')
      },
      del: async () => undefined,
      keys: async () => [] as string[],
    }
    const c2 = new PortraitCache(bad, async () => blob('ok'), () => 'ok-url')
    expect(await c2.get({ look: 'puddlepup', variant: null, stage: 5, face: 'sad' })).toBe('ok-url')
  })

  it('trims the oldest past the cap and sweeps older art versions', async () => {
    const store = memoryStore()
    for (let i = 0; i < ART.portrait.cacheMaxEntries + 3; i++) await store.set(`${PORTRAIT_PREFIX}v${ART.portrait.version}/puddlepup/full/f${i}`, { at: i, type: 'image/webp', blob: blob('x') })
    await store.set(`${PORTRAIT_PREFIX}v0/puddlepup/full/neutral`, { at: 1, type: 'image/webp', blob: blob('old') })
    await store.set('wildsong/settings', { keep: true })
    const cache = new PortraitCache(store, async () => blob('n'), () => 'u')
    expect(await cache.sweepOldVersions()).toBe(1)
    expect(await cache.trim()).toBe(3)
    const keys = await store.keys()
    expect(keys.filter((k) => k.startsWith(PORTRAIT_PREFIX))).toHaveLength(ART.portrait.cacheMaxEntries)
    expect(keys.some((k) => k.endsWith('/f0'))).toBe(false)
    expect(keys).toContain('wildsong/settings')
  })
})
