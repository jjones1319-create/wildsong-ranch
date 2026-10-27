import { describe, expect, it } from 'vitest'
import { CROWD_PROFILES, CROWD_SIZES, CROWDS } from './recipes/ambience.ts'

/** SOUND_UPGRADE §9.4: every crowd size sounds and behaves like itself. */
describe('crowds (§9.4)', () => {
  const main = (size: keyof typeof CROWD_PROFILES) => {
    const l = CROWD_PROFILES[size].layers.find((x) => x.id === 'crowd')
    return l && l.kind === 'noise' ? l.levelDb : -120
  }

  it('grow louder, busier and bigger from small to huge', () => {
    const order = ['small', 'medium', 'large', 'large+', 'huge'] as const
    for (let i = 1; i < order.length; i++) {
      const a = CROWD_PROFILES[order[i - 1]!]
      const b = CROWD_PROFILES[order[i]!]
      expect(main(order[i]!), order[i]).toBeGreaterThan(main(order[i - 1]!))
      expect(b.applause.rate, order[i]).toBeGreaterThan(a.applause.rate)
      expect(b.clap.voices, order[i]).toBeGreaterThan(a.clap.voices)
      expect(b.react, order[i]).toBeGreaterThanOrEqual(a.react)
      expect(b.layers.length, order[i]).toBeGreaterThanOrEqual(a.layers.length)
    }
  })

  it('a hushed hall is quiet and only applauds politely; a chanting crowd claps on two and four', () => {
    expect(main('hushed')).toBeLessThan(main('small'))
    expect(CROWD_PROFILES.hushed.polite).toBe(true)
    expect(CROWD_PROFILES.hushed.react).toBe(0)
    expect(CROWD_PROFILES.hushed.clap.voices).toBe(0)
    expect(CROWD_PROFILES.hushed.applause.rate).toBeGreaterThan(0)
    expect(CROWD_PROFILES.chanting.clap.backbeat).toBe(true)
    for (const size of CROWD_SIZES) if (size !== 'chanting') expect(CROWD_PROFILES[size].clap.backbeat, size).toBe(false)
  })

  it('every size is its own sound, and every crowd layer is lowpassed at 4 kHz or below (no whistles, no voices)', () => {
    const signatures = new Set(CROWD_SIZES.filter((s) => s !== 'chanting' && s !== 'none').map((s) => JSON.stringify(CROWD_PROFILES[s].layers)))
    expect(signatures.size).toBe(CROWD_SIZES.length - 2)
    for (const [size, layers] of Object.entries(CROWDS)) {
      for (const l of layers) if (l.kind === 'noise') expect(l.filters?.some((f) => f.type === 'lowpass' && f.hz <= 4000), `${size}/${l.id}`).toBe(true)
    }
  })
})
