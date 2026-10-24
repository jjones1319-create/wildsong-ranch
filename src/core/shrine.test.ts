import { describe, expect, it } from 'vitest'
import { BREED_IDS, STAT_KEYS } from '../data/types.ts'
import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { BIRTH } from '../data/tuning.ts'
import { SECRETS } from '../data/secrets.ts'
import { cyrb53 } from './hash.ts'
import { monsterFromRoll, randomPhrase, rollShrine, suggestName } from './shrine.ts'
import { createRng } from './rng.ts'
import { mixBreeds } from './monster.ts'

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

  it('pins five phrases forever (the contract: changing any roll order changes every monster; two of them are secret phrases since M6)', () => {
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
        "puddlepup/puddlepup Wildsong 145/92/86/110/103/80 life 411 guts 12 nature 21 berry-pudding",
        "grumblestone/petalphant Twinkle 177/92/55/58/36/137 life 463 guts 15 nature -26 river-fish",
        "tumblefox/tumblefox Hello 100/68/94/78/163/23 life 387 guts 10 nature 16 herbal-pellets",
        "tumblefox/pluckrex 夜明けの歌 113/74/79/75/90/50 life 357 guts 11 nature -27 berry-pudding",
        "grumblestone/starhowl A 141/104/60/51/45/116 life 434 guts 14 nature -24 honey-bread",
      ]
    `)
  })
})

const SECRET_PHRASES = [
  'wildsong', 'tunewick', 'hello world', 'happy birthday', 'thunderstorm', 'teatime', 'ember', 'jade garden', 'pancakes', 'lighthouse', 'fencing',
  'sunrise', 'bedrock', 'midnight', 'farewell', 'static', 'clockwork', 'reflection', 'high tide', 'treasure', 'golden hour',
]

describe('secret phrases (CONTENT §12)', () => {
  it('every secret phrase wakes its variant: pure, with its colours id, bonus and perk', () => {
    const seen = new Set<string>()
    for (const phrase of SECRET_PHRASES) {
      const r = rollShrine(phrase, '', ALL)
      expect(r.secret).not.toBeNull()
      const s = r.secret!
      seen.add(s.id)
      expect(r.mainBreed).toBe(s.breed)
      expect(r.subBreed).toBe(s.breed)
      expect(r.variantName).toBe(`${s.adjective} ${mixBreeds(s.breed, s.breed).variantName}`)
      const m = monsterFromRoll(r, 'x')
      expect(m.variantId).toBe(s.id)
      expect(m.flags.pure).toBe(true)
      const base = mixBreeds(s.breed, s.breed).base
      for (const k of STAT_KEYS) expect(m.stats[k]).toBe(Math.min(999, Math.max(1, base[k] + r.offsets.stats[k] + (s.stats[k] ?? 0))))
      expect(m.lifespanTotal).toBe(mixBreeds(s.breed, s.breed).lifespan + r.offsets.lifespan + s.lifespan)
      if (s.perk === 'lovesHoneyBread') expect(m.likes.food).toBe('honey-bread')
    }
    expect(seen.size).toBe(SECRETS.length)
  })

  it('is case- and punctuation-blind, and the artist field never hides a secret', () => {
    expect(rollShrine('  Hello, WORLD!! ', '', ALL).secret?.id).toBe('glitch-tumblefox')
    expect(rollShrine('wildsong', 'anyone', ALL).secret?.id).toBe('songheart-puddlepup')
    expect(rollShrine('wild song', '', ALL).secret).toBeNull()
  })

  it('a secret of a sleeping breed becomes a Sleeping Stone like any other', () => {
    const r = rollShrine('treasure', '', STARTING_UNLOCKED)
    expect(r.secret?.breed).toBe('lootlid')
    expect(r.mainLocked).toBe(true)
  })

  it('Randomize draws one to three words from the list, deterministically', () => {
    const words = ['river', 'lantern', 'moon']
    const a = randomPhrase(createRng(5), words)
    expect(a).toBe(randomPhrase(createRng(5), words))
    const n = a.split(' ').length
    expect(n).toBeGreaterThanOrEqual(1)
    expect(n).toBeLessThanOrEqual(3)
    expect(a.split(' ').every((w) => words.includes(w))).toBe(true)
  })

  it('pins 1,000 phrases at once (one hash over every roll)', () => {
    const lines: string[] = []
    for (let i = 0; i < 1000; i++) {
      const r = rollShrine(`echo ${i} ${['dawn', 'dusk', 'rain'][i % 3]}`, i % 4 === 0 ? `voice ${i % 7}` : '', ALL)
      const m = monsterFromRoll(r, 'x')
      lines.push(`${r.mainBreed}/${r.subBreed}/${m.variantId ?? '-'} ${m.name} ${STAT_KEYS.map((k) => m.stats[k]).join('/')} ${m.lifespanTotal} ${m.gutsRate} ${m.nature} ${m.likes.food} ${m.likes.drill}`)
    }
    expect(cyrb53(lines.join('\n'))).toBe(8145457784466491)
  })
})
