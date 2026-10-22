import { describe, expect, it } from 'vitest'
import { GRADES } from '../data/types.ts'
import { createRng } from './rng.ts'
import { makeMonster } from './test-helpers.ts'
import { applyReaction, baseHeavyGain, baseLightGain, baseSecondaryGain, denyRequest, outcomePercents, outcomeWeights, playAmounts, requestChancePct, resolveDrill, restAmounts, restMonster, rollRequest, truancyChancePct } from './training.ts'

const near = (actual: number, expected: number) => expect(Math.abs(actual - expected)).toBeLessThanOrEqual(1.01)

describe('outcome weights (§6.2 reference rows)', () => {
  const row = (name: string, o: Parameters<typeof makeMonster>[0], pow: number, ref: [number, number, number, number]) =>
    it(name, () => {
      const m = makeMonster({ ...o, stats: { POW: pow } })
      const p = outcomePercents(outcomeWeights(m, 'log-toss'))
      near(p.great, ref[0])
      near(p.success, ref[1])
      near(p.cheat, ref[2])
      near(p.fail, ref[3])
    })

  row('fresh baby, stage 1, 1★', { agePct: 0, fatigue: 0, stress: 0, spoil: 30, fear: 30, nature: 0 }, 70, [10, 71, 10, 9])
  row('prime, happy and loyal, 2★', { agePct: 50, fatigue: 20, stress: 10, spoil: 60, fear: 50, nature: 30 }, 300, [18, 61, 10, 10])
  row('prime but tired, 2★', { agePct: 50, fatigue: 60, stress: 20, spoil: 50, fear: 50, nature: 0 }, 300, [10, 51, 10, 28])
  row('prime, stressed and spoiled, 2★', { agePct: 50, fatigue: 30, stress: 60, spoil: 90, fear: 20, nature: -30 }, 300, [15, 31, 42, 12])
  row('old, 3★', { agePct: 78, fatigue: 30, stress: 20, spoil: 60, fear: 60, nature: 10 }, 600, [14, 61, 10, 15])
  row('neglected, stage 3, 1★', { agePct: 25, fatigue: 75, stress: 70, spoil: 20, fear: 20, nature: -10 }, 70, [3, 20, 44, 33])

  it('adds the liked-drill, disliked-drill and Training Yard bonuses to the raw weights', () => {
    const m = makeMonster({ agePct: 0, fatigue: 0, stress: 0, spoil: 30, fear: 30 })
    const base = outcomeWeights(m, 'log-toss')
    expect(outcomeWeights(m, 'puzzle-stones').great - base.great).toBe(6000)
    expect(outcomeWeights(m, 'acorn-shower').cheat - base.cheat).toBe(6000)
    expect(outcomeWeights(m, 'log-toss', { trainingYard: true }).great - base.great).toBe(5000)
  })
})

describe('truancy', () => {
  it('is impossible under fatigue 70 and scales with fatigue and loyalty', () => {
    expect(truancyChancePct(69, 0)).toBe(0)
    expect(truancyChancePct(70, 0)).toBeCloseTo(2)
    expect(truancyChancePct(80, 50)).toBeCloseTo(22 * (100 / 150))
    expect(truancyChancePct(100, 100)).toBeCloseTo(62 * (50 / 150))
  })
})

describe('gain tables (§6.3, no noise)', () => {
  it('light gain by grade and stage', () => {
    const expected = { E: [3, 3, 4, 5, 6, 6, 5, 4, 3, 2], D: [4, 5, 6, 7, 8, 8, 7, 6, 4, 3], C: [4, 6, 8, 9, 10, 10, 8, 7, 6, 4], B: [6, 8, 10, 12, 13, 13, 11, 10, 7, 5], A: [7, 9, 12, 14, 15, 15, 13, 11, 9, 5] }
    for (const g of GRADES) expect(Array.from({ length: 10 }, (_, i) => baseLightGain(g, i + 1))).toEqual(expected[g])
  })

  it('heavy main gain', () => {
    expect(Array.from({ length: 10 }, (_, i) => baseHeavyGain('E', i + 1))).toEqual([4, 6, 7, 8, 9, 9, 8, 7, 5, 3])
    expect(Array.from({ length: 10 }, (_, i) => baseHeavyGain('C', i + 1))).toEqual([7, 10, 12, 14, 16, 15, 14, 12, 9, 6])
    expect(Array.from({ length: 10 }, (_, i) => baseHeavyGain('A', i + 1))).toEqual([11, 15, 19, 20, 20, 20, 20, 18, 14, 9])
  })

  it('heavy secondary gain', () => {
    expect(Array.from({ length: 10 }, (_, i) => baseSecondaryGain('C', i + 1))).toEqual([3, 4, 5, 6, 7, 7, 6, 5, 4, 2])
    expect(Array.from({ length: 10 }, (_, i) => baseSecondaryGain('A', i + 1))).toEqual([5, 7, 8, 10, 10, 10, 9, 8, 6, 4])
  })
})

describe('resolveDrill', () => {
  it('is deterministic and never leaves a stat outside 1..999', () => {
    const m = makeMonster({ agePct: 50, fatigue: 20, stress: 10, spoil: 60, fear: 50 })
    const a = resolveDrill(m, 'plow-pull', createRng(5))
    const b = resolveDrill(m, 'plow-pull', createRng(5))
    expect(a).toEqual(b)
    expect(m.stats.POW).toBe(70) // input untouched
    for (let seed = 0; seed < 200; seed++) {
      const r = resolveDrill(m, 'plow-pull', createRng(seed))
      for (const v of Object.values(r.monster.stats)) {
        expect(v).toBeGreaterThanOrEqual(1)
        expect(v).toBeLessThanOrEqual(999)
      }
      if (r.result.outcome === 'Fail') expect(r.result.gains).toEqual({})
      if (r.result.outcome === 'Success' || r.result.outcome === 'Great') {
        expect(r.result.gains.POW).toBeGreaterThan(0)
        expect(r.result.gains.LIF).toBeGreaterThan(0)
        expect(r.result.gains.SPD).toBeLessThan(0)
        expect(r.result.pay).toBe(r.result.outcome === 'Great' ? 75 : 50)
      }
      if (r.result.outcome === 'Cheat') expect(r.result.pay).toBe(0)
    }
  })

  it('charges light drills +10 fatigue / +4 stress and heavy +15 / +9, less on Great and Cheat', () => {
    const m = makeMonster({ agePct: 50, fatigue: 0, stress: 0, spoil: 60, fear: 60 })
    const seen = new Set<string>()
    for (let seed = 0; seed < 300; seed++) {
      const light = resolveDrill(m, 'hill-sprints', createRng(seed))
      const heavy = resolveDrill(m, 'wind-chase', createRng(seed))
      seen.add(light.result.outcome)
      const relief = (o: string) => (o === 'Great' ? 3 : o === 'Cheat' ? 5 : 0)
      expect(light.result.fatigue).toBe(10 - relief(light.result.outcome))
      expect(light.result.stress).toBe(4)
      expect(heavy.result.fatigue).toBe(15 - relief(heavy.result.outcome))
      expect(heavy.result.stress).toBe(9)
      expect(light.monster.fatigue).toBe(light.result.fatigue)
    }
    expect(seen.has('Great')).toBe(true)
    expect(seen.has('Success')).toBe(true)
  })

  it('slacks off only when exhausted, with −5 fatigue and −2 stress', () => {
    const tired = makeMonster({ agePct: 50, fatigue: 100, stress: 0, spoil: 0, fear: 0 })
    let slacked = 0
    for (let seed = 0; seed < 300; seed++) {
      const r = resolveDrill(tired, 'hill-sprints', createRng(seed))
      if (r.result.outcome === 'Slacked') {
        slacked++
        expect(r.monster.fatigue).toBe(95)
        expect(r.monster.stress).toBe(0)
        expect(r.result.gains).toEqual({})
      }
    }
    expect(slacked).toBeGreaterThan(100)
    const fresh = makeMonster({ fatigue: 69 })
    for (let seed = 0; seed < 100; seed++) expect(resolveDrill(fresh, 'hill-sprints', createRng(seed)).result.outcome).not.toBe('Slacked')
  })

  it('adds the breed bonus drill +1 and an active tonic +3 on Success and Great', () => {
    const m = makeMonster({ agePct: 50, fatigue: 0, stress: 0, spoil: 80, fear: 80 })
    const tonic = structuredClone(m)
    tonic.status.tonics.SKI = 4
    for (let seed = 0; seed < 100; seed++) {
      const plain = resolveDrill(m, 'target-toss', createRng(seed))
      const boosted = resolveDrill(tonic, 'target-toss', createRng(seed))
      if (plain.result.outcome === 'Success' || plain.result.outcome === 'Great') {
        expect(boosted.result.gains.SKI).toBe(plain.result.gains.SKI! + 3)
        // Puddlepup's bonus drill is Target Toss: at least base + 1
        expect(plain.result.gains.SKI).toBeGreaterThanOrEqual(baseLightGain('B', 5) - 1 + 1)
      }
    }
  })

  it('Clockwork and Gilded traits change fatigue cost and pay', () => {
    const owl = makeMonster({ main: 'gearhoot', agePct: 50, spoil: 60, fear: 60 })
    const chest = makeMonster({ main: 'lootlid', agePct: 50, spoil: 60, fear: 60 })
    for (let seed = 0; seed < 50; seed++) {
      const a = resolveDrill(owl, 'hill-sprints', createRng(seed))
      if (a.result.outcome === 'Success') expect(a.result.fatigue).toBe(8)
      const b = resolveDrill(chest, 'hill-sprints', createRng(seed))
      if (b.result.outcome === 'Success') expect(b.result.pay).toBe(60)
    }
  })
})

describe('praise and scold (§6.4)', () => {
  it('applies the table, with good/bad nature variants and Cheerful halving scold stress', () => {
    const base = makeMonster({ spoil: 30, fear: 30, stress: 20, nature: 0, main: 'quillion' })
    expect(applyReaction(base, 'Great', 'praise')).toMatchObject({ spoil: 34, stress: 15 })
    expect(applyReaction(base, 'Great', 'scold')).toMatchObject({ fear: 33, stress: 28, spoil: 28 })
    expect(applyReaction(base, 'Great', 'skip')).toMatchObject({ stress: 25 })
    expect(applyReaction(base, 'Cheat', 'praise')).toMatchObject({ spoil: 35, nature: -2, stress: 17 })
    expect(applyReaction(base, 'Cheat', 'scold')).toMatchObject({ fear: 34, nature: 1, stress: 24 })
    const wicked = makeMonster({ spoil: 30, fear: 30, stress: 20, nature: -10, main: 'quillion' })
    expect(applyReaction(wicked, 'Cheat', 'scold')).toMatchObject({ stress: 30 })
    expect(applyReaction(wicked, 'Fail', 'scold')).toMatchObject({ stress: 25 })
    expect(applyReaction(base, 'Slacked', 'skip')).toMatchObject({ spoil: 32, nature: -1 })
    const cheerful = makeMonster({ spoil: 30, fear: 30, stress: 20, nature: 0, main: 'puddlepup' })
    expect(applyReaction(cheerful, 'Great', 'scold')).toMatchObject({ stress: 24 })
  })
})

describe('rest and play (§6.5)', () => {
  it('matches the reference table by stage', () => {
    const rest = Array.from({ length: 10 }, (_, i) => restAmounts(i + 1))
    expect(rest.map((r) => r.fatigue)).toEqual([39, 42, 45, 48, 50, 49, 47, 44, 41, 37])
    expect(rest.map((r) => r.stress)).toEqual([10, 11, 12, 13, 14, 14, 13, 12, 10, 9])
    const play = Array.from({ length: 10 }, (_, i) => playAmounts(i + 1))
    expect(play.map((r) => r.fatigue)).toEqual([18, 20, 22, 23, 24, 24, 22, 21, 20, 18])
    expect(play.map((r) => r.stress)).toEqual([15, 17, 19, 21, 22, 22, 20, 19, 17, 14])
  })

  it('applies bedding and Fluffy bonuses and raises form by 1', () => {
    const m = makeMonster({ agePct: 50, fatigue: 90, stress: 40 })
    expect(restMonster(m).monster).toMatchObject({ fatigue: 40, stress: 26, form: 1 })
    expect(restMonster(m, { beddingBonus: 10 }).monster.fatigue).toBe(30)
    const sheep = makeMonster({ main: 'nimbusheep', agePct: 60, fatigue: 90 }) // Late growth: stage 5 at 56–68%
    expect(restMonster(sheep).monster.fatigue).toBe(32)
  })
})

describe('requests (§6.7)', () => {
  it('has the reference chances and types', () => {
    expect(requestChancePct(39, 0)).toBe(0)
    expect(requestChancePct(40, 0)).toBe(8)
    expect(requestChancePct(0, 60)).toBe(24)
    expect(requestChancePct(100, 10)).toBe(56)
  })

  it('asks for rest when fatigue leads, play when stress leads, and treats only with the favorite toy', () => {
    const tiredM = makeMonster({ fatigue: 100, stress: 10 })
    const stressed = makeMonster({ fatigue: 10, stress: 100 })
    let rest = 0
    let play = 0
    let treat = 0
    for (let seed = 0; seed < 500; seed++) {
      const a = rollRequest(tiredM, createRng(seed), false)
      const b = rollRequest(stressed, createRng(seed), true)
      if (a?.kind === 'rest') rest++
      if (a?.kind === 'treat') treat += 100
      if (b?.kind === 'play') play++
      if (b?.kind === 'treat') {
        treat++
        expect(b.toy).toBe('rubber-ball')
      }
    }
    expect(rest).toBeGreaterThan(200)
    expect(play).toBeGreaterThan(200)
    expect(treat).toBeGreaterThan(10)
    expect(treat).toBeLessThan(60)
    expect(rollRequest(makeMonster({ fatigue: 39, stress: 39 }), createRng(1), true)).toBeNull()
  })

  it('denying costs +8 stress and −2 spoil', () => {
    expect(denyRequest(makeMonster({ stress: 10, spoil: 30 }))).toMatchObject({ stress: 18, spoil: 28 })
  })
})
