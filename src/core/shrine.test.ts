import { describe, expect, it } from 'vitest'
import { BREED_IDS, STAT_KEYS } from '../data/types.ts'
import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { BIRTH } from '../data/tuning.ts'
import { monsterFromRoll, rollShrine, suggestName } from './shrine.ts'

const ALL = [...BREED_IDS]

describe('the Shrine of Echoes (§14.1)', () => {
  it('is deterministic and normalizes the phrase', () => {
    const a = rollShrine('Hello,  World!', '', ALL)
    const b = rollShrine('hello world', '', ALL)
    expect(a).toEqual(b)
    expect(a.seed.phrase).toBe('hello world')
    const c = rollShrine('hello world', 'someone', ALL)
    expect(c.subBreed === a.subBreed && c.offsets.lifespan === a.offsets.lifespan && c.likes.food === a.likes.food).toBe(false)
  })

  it('keeps every roll inside its range and the sub among the unlocked breeds', () => {
    for (let i = 0; i < 200; i++) {
      const r = rollShrine(`song number ${i}`, i % 3 === 0 ? 'the band' : '', STARTING_UNLOCKED)
      expect(ALL).toContain(r.mainBreed)
      expect(STARTING_UNLOCKED).toContain(r.subBreed)
      expect(r.mainLocked).toBe(!STARTING_UNLOCKED.includes(r.mainBreed))
      for (const k of STAT_KEYS) {
        expect(r.offsets.stats[k]).toBeGreaterThanOrEqual(BIRTH.statOffset.min)
        expect(r.offsets.stats[k]).toBeLessThanOrEqual(BIRTH.statOffset.max)
      }
      expect(r.offsets.lifespan).toBeGreaterThanOrEqual(BIRTH.lifespanOffset.min)
      expect(r.offsets.lifespan).toBeLessThanOrEqual(BIRTH.lifespanOffset.max)
      expect(Math.abs(r.offsets.gutsRate)).toBeLessThanOrEqual(1)
      expect(r.suggestedName.length).toBeGreaterThan(0)
      expect(r.suggestedName.length).toBeLessThanOrEqual(16)
    }
  })

  it('reaches every breed as a main over many phrases', () => {
    const seen = new Set<string>()
    for (let i = 0; i < 2000 && seen.size < ALL.length; i++) seen.add(rollShrine(`phrase ${i}`, '', ALL).mainBreed)
    expect(seen.size).toBe(ALL.length)
  })

  it('suggests the first word of the song, or the variant name', () => {
    expect(suggestName('hello world', 'Puddlepup')).toBe('Hello')
    expect(suggestName('', 'Cinder Puddlepup')).toBe('Cinder Puddlepup')
    expect(suggestName('supercalifragilisticexpialidocious', 'x')).toBe('Supercalifragili')
  })

  it('makes a newborn that carries the phrase and the suggested name', () => {
    const r = rollShrine('river song', 'the valley choir', ALL)
    const m = monsterFromRoll(r, 'id-1')
    expect(m.id).toBe('id-1')
    expect(m.seedPhrase).toBe('river song')
    expect(m.name).toBe('River')
    expect(m.mainBreed).toBe(r.mainBreed)
    expect(m.likes).toEqual(r.likes)
    expect(m.nature).toBe(r.offsets.nature)
  })

  it('pins five phrases forever (the contract: changing any roll order changes every monster)', () => {
    const summary = (phrase: string, artist: string) => {
      const r = rollShrine(phrase, artist, ALL)
      const m = monsterFromRoll(r, 'x')
      return `${r.mainBreed}/${r.subBreed} ${m.name} ${STAT_KEYS.map((k) => m.stats[k]).join('/')} life ${m.lifespanTotal} guts ${m.gutsRate} nature ${m.nature} ${m.likes.food}`
    }
    expect([
      summary('wildsong', ''),
      summary('Twinkle Twinkle Little Star', ''),
      summary('Hello,  World!', 'everyone'),
      summary('夜明けの歌', ''),
      summary('a', 'b'),
    ]).toMatchInlineSnapshot(`
      [
        "scrollopus/moatshell Wildsong 107/59/133/113/55/92 life 428 guts 13 nature -4 river-fish",
        "grumblestone/petalphant Twinkle 177/92/55/58/36/137 life 463 guts 18 nature -26 river-fish",
        "nibblegrub/galeheron Hello 148/94/60/65/45/92 life 413 guts 14 nature -7 berry-pudding",
        "tumblefox/pluckrex 夜明けの歌 113/74/79/75/90/50 life 357 guts 11 nature -27 berry-pudding",
        "grumblestone/starhowl A 141/104/60/51/45/116 life 434 guts 17 nature -24 honey-bread",
      ]
    `)
  })
})
