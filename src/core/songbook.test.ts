import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { addSheet, canLearn, forgetTechnique, goodFit, learnReplacing, learnTechnique, learnableFromSongbook, masteryBonuses, masteryLevel, recordUse } from './songbook.ts'
import { makeMonster } from './test-helpers.ts'

describe('who can learn what (§10.5)', () => {
  const mixed = makeMonster({ main: 'puddlepup', sub: 'cinderlynx' })
  const pure = makeMonster({ main: 'puddlepup', sub: 'puddlepup' })

  it('universal sheets work for anyone', () => {
    expect(canLearn(mixed, 'universal.beat-bump')).toEqual({ ok: true })
    expect(canLearn(pure, 'universal.feedback-loop')).toEqual({ ok: true })
  })

  it("breed sheets need the main breed's kit or the sub's quirk", () => {
    expect(canLearn(mixed, 'puddlepup.belly-flop')).toEqual({ ok: true })
    expect(canLearn(mixed, 'cinderlynx.spark-pounce')).toEqual({ ok: false, reason: 'known' }) // the quirk is a starter
    expect(canLearn(mixed, 'cinderlynx.inferno-maul')).toEqual({ ok: false, reason: 'notInKit' })
    expect(canLearn(mixed, 'cobblemaw.gravel-swipe')).toEqual({ ok: false, reason: 'notInKit' })
    expect(canLearn(forgetTechnique(mixed, 'cinderlynx.spark-pounce'), 'cinderlynx.spark-pounce')).toEqual({ ok: true })
  })

  it('Signature sheets are for pure breeds only', () => {
    expect(canLearn(pure, 'puddlepup.puddle-party')).toEqual({ ok: true })
    expect(canLearn(mixed, 'puddlepup.puddle-party')).toEqual({ ok: false, reason: 'signatureNotPure' })
    expect(canLearn(pure, 'cinderlynx.kindled-fury')).toEqual({ ok: false, reason: 'notInKit' })
    expect(canLearn(pure, 'nope.nothing')).toEqual({ ok: false, reason: 'unknownTechnique' })
  })

  it('a Chain from a sheet does not need the base at Lv3', () => {
    expect(canLearn(pure, 'puddlepup.cannonball-flop')).toEqual({ ok: true })
  })
})

describe('learning, the 12 cap, forgetting and relearning', () => {
  it('learns up to 12, then reports full until one is forgotten', () => {
    let m = makeMonster({ main: 'puddlepup', sub: 'puddlepup' })
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
    const m = makeMonster({ main: 'puddlepup', sub: 'cinderlynx' })
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
