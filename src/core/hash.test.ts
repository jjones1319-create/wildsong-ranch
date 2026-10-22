import { describe, expect, it } from 'vitest'
import { cyrb53, normalizePhrase, phraseSeed } from './hash.ts'

describe('normalizePhrase (§14.1)', () => {
  it('lowercases, trims, collapses spaces and strips punctuation', () => {
    expect(normalizePhrase('Hello,  World!')).toBe('hello world')
    expect(normalizePhrase('  Hello - World ')).toBe('hello world')
    expect(normalizePhrase('rock&roll')).toBe('rockroll')
  })

  it('keeps letters and digits of any script and applies NFKC', () => {
    expect(normalizePhrase('Ünïcödé Ça')).toBe('ünïcödé ça')
    expect(normalizePhrase('ｆｕｌｌｗｉｄｔｈ')).toBe('fullwidth')
    expect(normalizePhrase('日本語　テスト')).toBe('日本語 テスト')
    expect(normalizePhrase('Track 7 (Live)')).toBe('track 7 live')
  })
})

describe('cyrb53', () => {
  it('matches the pinned reference values (the contract that keeps every phrase stable)', () => {
    const pinned: [string, number, number, number][] = [
      ['', 3338908027751811, 7956228673112545, 2130661745665215],
      ['a', 7929297801672961, 5368154436228575, 217965353842102],
      ['hello world', 3259054761512980, 6759793827125, 4085719586792185],
      ['wildsong', 3439105809465281, 6506171270103463, 5206119281237061],
      ['tunewick', 460274503351467, 8102973368513454, 6463433487915037],
      ['happy birthday', 8691254669674617, 7951825035804118, 7180355911651806],
      ['golden hour', 1985008249491400, 4695606725429029, 8813928559549943],
      ['the quick brown fox', 499755596815106, 695138912670952, 2284591678584662],
      ['ünïcödé', 3459507448391374, 5289718010679356, 7524300409037490],
      ['123', 2502665170145887, 1054607566265193, 5898490976483950],
    ]
    for (const [s, h0, h1, h2] of pinned) {
      expect(cyrb53(s, 0)).toBe(h0)
      expect(cyrb53(s, 1)).toBe(h1)
      expect(cyrb53(s, 2)).toBe(h2)
    }
  })

  it('stays within 53 bits and differs by seed', () => {
    for (const s of ['x', 'abc', 'Wildsong Ranch']) {
      expect(cyrb53(s, 1)).toBeLessThan(2 ** 53)
      expect(cyrb53(s, 1)).not.toBe(cyrb53(s, 2))
    }
  })
})

describe('phraseSeed', () => {
  it('normalizes both fields and uses the phrase for a missing artist', () => {
    const a = phraseSeed('Hello, World!')
    expect(a).toEqual({ phrase: 'hello world', artist: '', h1: 6759793827125, h2: 4085719586792185, seed: 1535344588 })
    expect(phraseSeed('HELLO   world').seed).toBe(a.seed)
    expect(phraseSeed('wildsong', 'anon').seed).toBe(2828244266)
    expect(phraseSeed('wildsong', 'anon').seed).not.toBe(phraseSeed('wildsong').seed)
  })
})
