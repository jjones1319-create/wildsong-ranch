import { describe, expect, it } from 'vitest'
import { SCREENS, hashFor, installRouter, parseHash, screen, type RouterHost } from './router.ts'

describe('parseHash', () => {
  it('treats an empty or unknown hash as the title screen', () => {
    expect(parseHash('')).toBe('title')
    expect(parseHash('#')).toBe('title')
    expect(parseHash('#nonsense')).toBe('title')
    expect(parseHash('#/ranch/42')).toBe('title')
  })

  it('accepts the slug with or without # and a leading slash, in any case', () => {
    expect(parseHash('#credits')).toBe('credits')
    expect(parseHash('#/credits')).toBe('credits')
    expect(parseHash('credits')).toBe('credits')
    expect(parseHash('#CREDITS')).toBe('credits')
    expect(parseHash('#new-game')).toBe('newGame')
  })

  it('round-trips every screen through hashFor', () => {
    for (const s of SCREENS) {
      expect(parseHash(hashFor(s))).toBe(s)
    }
    expect(hashFor('title')).toBe('#title')
    expect(hashFor('newGame')).toBe('#new-game')
  })
})

describe('installRouter', () => {
  it('reads the starting hash and follows hashchange events', () => {
    let listener: (() => void) | null = null
    const fake: RouterHost = {
      location: { hash: '#lab' },
      addEventListener: (_type, cb) => {
        listener = cb
      },
    }
    installRouter(fake)
    expect(screen.value).toBe('lab')

    fake.location.hash = '#settings'
    listener!()
    expect(screen.value).toBe('settings')

    fake.location.hash = '#garbage'
    listener!()
    expect(screen.value).toBe('title')
  })
})
