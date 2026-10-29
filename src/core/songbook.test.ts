import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { addSheet, canLearn, forgetTechnique, goodFit, learnReplacing, learnTechnique, learnableFromSongbook, masteryBonuses, masteryLevel, recordUse } from './songbook.ts'
import { makeMonster } from './test-helpers.ts'

describe('who can learn what (§10.5)', () => {
  const pup = makeMonster({ main: 'puddlepup' })

  it('universal sheets work for anyone', () => {
    expect(canLearn(pup, 'universal.beat-bump')).toEqual({ ok: true })
    expect(canLearn(makeMonster({ main: 'cinderlynx' }), 'universal.feedback-loop')).toEqual({ ok: true })
  })

  it("breed sheets need the breed's own kit", () => {
    expect(canLearn(pup, 'puddlepup.belly-flop')).toEqual({ ok: true })
    expect(canLearn(pup, 'puddlepup.splash-nip')).toEqual({ ok: false, reason: 'known' }) // a starter
    expect(canLearn(pup, 'cinderlynx.spark-pounce')).toEqual({ ok: false, reason: 'notInKit' })
    expect(canLearn(pup, 'cobblemaw.gravel-swipe')).toEqual({ ok: false, reason: 'notInKit' })
    expect(canLearn(forgetTechnique(pup, 'puddlepup.bubble-pop'), 'puddlepup.bubble-pop')).toEqual({ ok: true })
  })

  it("every monster can learn its own breed's Signature (v1.12), and no other", () => {
    expect(canLearn(pup, 'puddlepup.puddle-party')).toEqual({ ok: true })
    expect(canLearn(pup, 'cinderlynx.kindled-fury')).toEqual({ ok: false, reason: 'notInKit' })
    expect(canLearn(pup, 'nope.nothing')).toEqual({ ok: false, reason: 'unknownTechnique' })
  })

  it("an old mix keeps the other breed's Basic it knew, but can't learn it back once forgotten", () => {
    const old = makeMonster({ main: 'puddlepup' })
    old.techniques.push({ id: 'cinderlynx.spark-pounce', uses: 3, level: 1 })
    expect(canLearn(old, 'cinderlynx.spark-pounce')).toEqual({ ok: false, reason: 'known' })
    expect(canLearn(forgetTechnique(old, 'cinderlynx.spark-pounce'), 'cinderlynx.spark-pounce')).toEqual({ ok: false, reason: 'notInKit' })
  })

  it('a Chain from a sheet does not need the base at Lv3', () => {
    expect(canLearn(pup, 'puddlepup.cannonball-flop')).toEqual({ ok: true })
  })
})

describe('learning, the 12 cap, forgetting and relearning', () => {
  it('learns up to 12, then reports full until one is forgotten', () => {
    let m = makeMonster({ main: 'puddlepup' })
    const ids = ['puddlepup.frill-flick', 'puddlepup.belly-flop', 'puddlepup.soggy-cloud', 'puddlepup.slipstream-spin', 'puddlepup.geyser-burst', 'puddlepup.cannonball-flop', 'puddlepup.puddle-party', 'universal.beat-bump', 'universal.hum-pulse', 'universal.staccato-jab']
    for (const id of ids) {
      const r = learnTechnique(m, id)
      expect(r.status).toBe('learned')
      m = r.monster
    }
    expect(m.techniques).toHaveLength(12)
    expect(learnTechnique(m, 'universal.chime-bolt').status).toBe('full')
    expect(learnTechnique(m, 'universal.beat-bump').status).toBe('known')
    const swapped = learnReplacing(m, 'universal.chime-bolt', 'universal.beat-bump')
    expect(swapped.status).toBe('learned')
    expect(swapped.monster.techniques).toHaveLength(12)
    expect(swapped.monster.techniques.some((t) => t.id === 'universal.beat-bump')).toBe(false)
    const relearned = learnReplacing(swapped.monster, 'universal.beat-bump', 'universal.chime-bolt')
    expect(relearned.status).toBe('learned')
    expect(relearned.monster.techniques.at(-1)).toEqual({ id: 'universal.beat-bump', uses: 0, level: 1 })
  })

  it('never mutates the input monster', () => {
    const m = makeMonster()
    learnTechnique(m, 'universal.beat-bump')
    expect(m.techniques).toHaveLength(2)
  })
})

describe('good fit, songbook and mastery', () => {
  it('marks ★ when the technique stat is one of the top two stats', () => {
    const brawler = makeMonster({ stats: { POW: 300, LIF: 200, INT: 50 } })
    expect(goodFit(brawler, TECHNIQUE_BY_ID['universal.beat-bump']!)).toBe(true)
    expect(goodFit(brawler, TECHNIQUE_BY_ID['universal.hum-pulse']!)).toBe(false)
  })

  it('lists owned sheets the monster can still learn', () => {
    const songbook = addSheet(addSheet([], 'universal.hum-pulse'), 'cinderlynx.inferno-maul')
    expect(songbook).toEqual(['cinderlynx.inferno-maul', 'universal.hum-pulse'])
    expect(addSheet(songbook, 'universal.hum-pulse')).toEqual(songbook)
    const m = makeMonster({ main: 'puddlepup' })
    expect(learnableFromSongbook(m, songbook).map((t) => t.id)).toEqual(['universal.hum-pulse'])
  })

  it('levels up at 15 and 40 uses with +2 hit and +2 force', () => {
    expect([0, 14, 15, 39, 40, 100].map(masteryLevel)).toEqual([1, 1, 2, 2, 3, 3])
    let m = makeMonster()
    for (let i = 0; i < 15; i++) m = recordUse(m, 'puddlepup.splash-nip')
    expect(m.techniques[0]).toEqual({ id: 'puddlepup.splash-nip', uses: 15, level: 2 })
    expect(masteryBonuses(m.techniques[0]!)).toEqual({ hit: 2, force: 0 })
    expect(masteryBonuses({ id: 'x', uses: 40, level: 3 })).toEqual({ hit: 2, force: 2 })
  })
})
