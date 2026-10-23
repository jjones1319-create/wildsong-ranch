import { describe, expect, it } from 'vitest'
import { weekIndexOf } from '../../core/calendar.ts'
import { trackFor } from './music.ts'

describe('music follows the screen (§23)', () => {
  it('ranch screens play the season, town screens play town, battles play battle', () => {
    const jan = weekIndexOf({ year: 1, month: 1, week: 1 })
    const jul = weekIndexOf({ year: 2, month: 7, week: 3 })
    expect(trackFor('ranch', jan, false)).toBe('ranchWinter')
    expect(trackFor('title', jul, false)).toBe('ranchSummer')
    expect(trackFor('title', null, false)).toBe('ranchSpring')
    expect(trackFor('shop', jan, false)).toBe('town')
    expect(trackFor('journal', jan, false)).toBe('town')
    expect(trackFor('shrine', jan, false)).toBe('shrine')
    expect(trackFor('farewell', jan, false)).toBe('farewell')
    expect(trackFor('battle', jan, false)).toBe('battle')
    expect(trackFor('tournamentPlay', jan, true)).toBe('battle')
    expect(trackFor('tournamentPlay', jan, false)).toBe('ranchWinter')
  })
})
