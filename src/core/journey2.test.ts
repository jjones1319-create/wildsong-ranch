import { describe, expect, it } from 'vitest'
import { signatureOf, techniquesOfBreed } from '../data/techniques.ts'
import { JOURNEY, SIGNATURE } from '../data/tuning.ts'
import { bondCharmId, journeyCost, requirementValue, rollSaleMonths, signatureAtPrime, techniqueCandidates, techniqueChancePct, trialOpponent, trialReward } from './journey.ts'
import { createRng } from './rng.ts'
import { makeMonster } from './test-helpers.ts'

/** M5 additions to the Journeys: the mentor bond, sale months, the Signature and the Trial. */
describe('Journeys in play (M5)', () => {
  it('each Mentor’s Charm takes 50 off a site’s requirements', () => {
    const m = makeMonster({ stats: { SKI: 150 } }) // score = SKI + loyalty (30) = 180
    const hit = techniquesOfBreed('puddlepup').find((t) => t.family === 'Hit')! // Archer's Glade: SKI ≥ 220
    expect(requirementValue(hit)).toBe(220)
    expect(requirementValue(hit, 1)).toBe(220 - JOURNEY.bond.requirementDrop)
    expect(techniqueChancePct(m, hit)).toBe(0)
    expect(techniqueChancePct(m, hit, false, 1)).toBeGreaterThan(0)
    expect(bondCharmId('iron-quarry')).toBe('mentor-charm-iron-quarry')
  })

  it('sale months: two distinct months a year, half-price Journeys', () => {
    const months = rollSaleMonths(createRng(7))
    expect(months).toHaveLength(2)
    expect(months[0]).not.toBe(months[1])
    for (const mo of months) {
      expect(mo).toBeGreaterThanOrEqual(1)
      expect(mo).toBeLessThanOrEqual(12)
    }
    expect(rollSaleMonths(createRng(7))).toEqual(months)
    expect(journeyCost(months, months[0]!)).toBe(JOURNEY.saleCost)
    expect(journeyCost(months, ((months[1]! + 1) % 12) + 1 === months[0] ? 13 : 13)).toBe(JOURNEY.cost)
  })

  it('the Signature: at Prime with loyalty ≥ 60, or at Glacier Bastion with DEF + type ≥ 700, for every breed', () => {
    const pure = makeMonster({ spoil: 60, fear: 60 })
    const sig = signatureOf('puddlepup')
    expect(signatureAtPrime(pure)?.id).toBe(sig.id)
    expect(signatureAtPrime(makeMonster({ spoil: 50, fear: 50 }))).toBeNull()
    expect(signatureAtPrime(makeMonster({ main: 'tumblefox', spoil: 60, fear: 60 }))?.id).toBe(signatureOf('tumblefox').id)
    const full = makeMonster({ spoil: 60, fear: 60 })
    full.techniques = Array.from({ length: 12 }, (_, i) => ({ id: `universal.${['beat-bump', 'shuffle-step-kick', 'hum-pulse', 'whistle-shot', 'staccato-jab', 'downbeat-strike', 'chime-bolt', 'piccolo-dart', 'crescendo-slam', 'timpani-crash', 'grand-finale', 'fortissimo-blast'][i]}`, uses: 0, level: 1 as const }))
    expect(signatureAtPrime(full)).toBeNull()
    const strong = makeMonster({ stats: { DEF: 400, INT: 350 } })
    strong.grade = 'B'
    const cands = techniqueCandidates(strong, 'glacier-bastion')
    expect(cands.some((t) => t.family === 'Signature')).toBe(true)
    expect(requirementValue(sig)).toBe(SIGNATURE.glacierRequirement)
    expect(techniqueChancePct(strong, sig)).toBeGreaterThan(0)
    expect(techniqueCandidates(makeMonster({ main: 'tumblefox' }), 'glacier-bastion').filter((t) => t.family === 'Signature').map((t) => t.id)).toEqual([signatureOf('tumblefox').id])
  })

  it('the Trial opponent is the site’s wild breed at your grade or one up, and the reward scales by grade', () => {
    const m = makeMonster()
    m.grade = 'C'
    let ups = 0
    for (let seed = 0; seed < 30; seed++) {
      const wild = trialOpponent(m, 'iron-quarry', createRng(seed))
      expect(wild.mainBreed).toBe('cobblemaw')
      expect(['C', 'B']).toContain(wild.grade)
      if (wild.grade === 'B') ups++
    }
    expect(ups).toBeGreaterThan(5)
    expect(ups).toBeLessThan(25)
    expect(trialReward(m)).toBe(JOURNEY.trial.rewardPerGrade * 3)
  })
})
