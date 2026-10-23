import { describe, expect, it } from 'vitest'
import { SEASONS, WEATHERS } from '../data/types.ts'
import { ranchBackground, sceneBackground } from './backgrounds.ts'

describe('backgrounds (§22)', () => {
  it('draws every season × weather as one svg with the right layer classes', () => {
    for (const season of SEASONS) {
      for (const weather of WEATHERS) {
        const svg = ranchBackground({ season, weather, seed: 4 })
        expect(svg.startsWith('<svg')).toBe(true)
        expect(svg.endsWith('</svg>')).toBe(true)
        expect(svg).toContain(`ws-bg--${season.toLowerCase()}`)
        expect(svg).toContain(`ws-bg--${weather.toLowerCase()}`)
        expect(svg).toContain('ws-bg__barn')
        expect(svg.includes('ws-bg__rain')).toBe(weather === 'Rain' || weather === 'Storm')
        expect(svg.includes('ws-bg__snow')).toBe(weather === 'Snow')
        expect(svg.includes('ws-bg__storm')).toBe(weather === 'Storm')
        expect(svg.includes('ws-bg__sun')).toBe(weather === 'Sunny')
        expect(svg.includes('ws-bg__leaves')).toBe(season !== 'Winter')
      }
    }
  })

  it('is deterministic for a seed and lighter in lite mode', () => {
    const a = ranchBackground({ season: 'Summer', weather: 'Rain', seed: 9 })
    expect(ranchBackground({ season: 'Summer', weather: 'Rain', seed: 9 })).toBe(a)
    expect(ranchBackground({ season: 'Summer', weather: 'Rain', seed: 10 })).not.toBe(a)
    const full = (a.match(/ws-bg__drop/g) ?? []).length
    const lite = (ranchBackground({ season: 'Summer', weather: 'Rain', seed: 9, lite: true }).match(/ws-bg__drop/g) ?? []).length
    expect(lite).toBeLessThan(full)
  })

  it('has a lighter scene for Town, the Shrine and the arena', () => {
    expect(sceneBackground({ season: 'Autumn', weather: 'Cloudy', scene: 'town' })).toContain('ws-bg__town')
    expect(sceneBackground({ season: 'Autumn', weather: 'Cloudy', scene: 'shrine' })).toContain('ws-bg__shrine')
    expect(sceneBackground({ season: 'Autumn', weather: 'Cloudy', scene: 'arena' })).toContain('ws-bg__arena')
    expect(sceneBackground({ season: 'Autumn', weather: 'Cloudy', scene: 'town' })).not.toContain('ws-bg__barn')
  })
})
