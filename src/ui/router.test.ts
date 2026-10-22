import { describe, expect, it } from 'vitest'
import { SCREENS, goBack, hashFor, installRouter, navigateFrom, parentOf, parseHash, parseRoute, pendingImport, returnTo, screen, type RouterHost } from './router.ts'

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
    expect(parseHash('#lab/edit')).toBe('labEdit')
    expect(parseHash('#LAB/IMPORT')).toBe('labImport')
  })

  it('round-trips every screen through hashFor', () => {
    for (const s of SCREENS) {
      expect(parseHash(hashFor(s))).toBe(s)
    }
    expect(hashFor('title')).toBe('#title')
    expect(hashFor('newGame')).toBe('#new-game')
    expect(hashFor('labCreate')).toBe('#lab/create')
  })

  it('recognises import links', () => {
    expect(parseRoute('#import=WS1-abc')).toEqual({ screen: 'labImport', importCode: 'WS1-abc' })
    expect(parseRoute('#import=nothing')).toEqual({ screen: 'title', importCode: null })
    expect(parseRoute('#lab/import')).toEqual({ screen: 'labImport', importCode: null })
  })

  it('knows every screen’s parent', () => {
    expect(parentOf('title')).toBeNull()
    expect(parentOf('lab')).toBe('title')
    for (const s of ['labCreate', 'labView', 'labEdit', 'labImport', 'labExport'] as const) expect(parentOf(s)).toBe('lab')
    for (const s of ['ranchCard', 'bag', 'songbook', 'town'] as const) expect(parentOf(s)).toBe('ranch')
    for (const s of ['shop', 'library'] as const) expect(parentOf(s)).toBe('town')
    expect(parseHash('#ranch/card')).toBe('ranchCard')
    expect(parseHash('#town/shop')).toBe('shop')
  })

  it('Back returns to where a screen was opened from when asked to', () => {
    returnTo.value = null
    navigateFrom('ranchCard', 'labEdit')
    expect(screen.value).toBe('labEdit')
    goBack()
    expect(screen.value).toBe('ranchCard')
    expect(returnTo.value).toBeNull()
    goBack()
    expect(screen.value).toBe('ranch')
    // Sub-screens of the opened screen still climb to their own parent; only the opened screen returns.
    navigateFrom('town', 'lab')
    screen.value = 'labCreate'
    goBack()
    expect(screen.value).toBe('lab')
    goBack()
    expect(screen.value).toBe('town')
  })
})

describe('installRouter', () => {
  it('reads the starting hash, follows hashchange events, and Back climbs to the parent', () => {
    let listener: (() => void) | null = null
    const replaced: string[] = []
    const fake: RouterHost = {
      location: { hash: '#lab' },
      addEventListener: (_type, cb) => {
        listener = cb
      },
      history: { replaceState: (_d, _u, url) => replaced.push(url ?? '') },
    }
    installRouter(fake)
    expect(screen.value).toBe('lab')

    fake.location.hash = '#settings'
    listener!()
    expect(screen.value).toBe('settings')

    fake.location.hash = '#garbage'
    listener!()
    expect(screen.value).toBe('title')

    fake.location.hash = '#lab/edit'
    listener!()
    expect(screen.value).toBe('labEdit')
    goBack()
    expect(fake.location.hash).toBe('#lab')

    fake.location.hash = '#import=WS1-xyz'
    listener!()
    expect(screen.value).toBe('labImport')
    expect(pendingImport.value).toBe('WS1-xyz')
    expect(replaced).toEqual(['#lab/import'])
  })
})
