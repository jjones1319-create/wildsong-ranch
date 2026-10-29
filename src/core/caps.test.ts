import { describe, expect, it } from 'vitest'
import { BREEDS } from '../data/breeds.ts'
import { RANGES, STAT_CAP_BY_GRADE } from '../data/tuning.ts'
import { GRADES } from '../data/types.ts'
import { damageBase, expectedDamage, finishDamage, walkPerTick } from './battle/formulas.ts'
import { divRound } from './mathx.ts'
import { traitsAny, traitsFirst, traitsMul, traitsSum, traitTakenMul, traitReflect, traitHitBonus, traitImmovable } from './battle/traits.ts'
import { giveHeartstone, heartstoneFrom } from './legacy.ts'
import { addTrained, clampMonsterMut, createMonster, hasTrait, lowerStat, statCap, sweetsOf, traitsOf, trainedOf } from './monster.ts'
import { resolveDrill } from './training.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { metamorphose } from './unlocks.ts'

/** v1.11: growth grade S, a stat cap per grade (Stat Sweets exempt), and a second, inherited trait. */

describe('grade caps (§5.2, v1.11)', () => {
  it('every grade has a cap, 100 apart, from E 1,000 to S 1,500; no breed starts with S', () => {
    expect(GRADES.map((g) => STAT_CAP_BY_GRADE[g])).toEqual([1000, 1100, 1200, 1300, 1400, 1500])
    for (const b of BREEDS) expect(Object.values(b.grades)).not.toContain('S')
  })

  it('trained points stop at the cap, sweets ride on top, and nothing above a cap is ever taken away', () => {
    const m = makeMonster({ stats: { POW: 1190 } }) // Puddlepup POW C: cap 1,200
    expect(statCap(m, 'POW')).toBe(1200)
    expect(addTrained(m, 'POW', 25)).toBe(10)
    expect(m.stats.POW).toBe(1200)
    expect(addTrained(m, 'POW', 5)).toBe(0)
    // 60 points of sweets: the cap counts trained points only, so training can still reach 1,200 + 60.
    m.records.fromSweets.POW = 60
    m.stats.POW = 1230
    expect(trainedOf(m, 'POW')).toBe(1170)
    expect(addTrained(m, 'POW', 100)).toBe(30)
    expect(m.stats.POW).toBe(1260)
    // A lowered grade leaves the points where they are.
    m.grades.POW = 'E'
    expect(addTrained(m, 'POW', 10)).toBe(0)
    expect(m.stats.POW).toBe(1260)
  })

  it('a drill drop keeps the sweets record no larger than the stat', () => {
    const m = makeMonster({ stats: { SPD: 40 } })
    m.records.fromSweets.SPD = 39
    lowerStat(m, 'SPD', 3)
    expect(m.stats.SPD).toBe(37)
    expect(m.records.fromSweets.SPD).toBe(37)
    expect(sweetsOf(m, 'SPD')).toBe(37)
  })

  it('training stops at the cap; a loaded save keeps up to 9,999 and clamps sweets to the stat', () => {
    const m = makeMonster({ agePct: 50, stats: { POW: 1199 } })
    for (let seed = 0; seed < 50; seed++) expect(resolveDrill(m, 'log-toss', createRng(seed)).monster.stats.POW).toBeLessThanOrEqual(1200)
    const big = makeMonster({ stats: { LIF: 20_000 } })
    big.records.fromSweets.DEF = 5000
    clampMonsterMut(big)
    expect(big.stats.LIF).toBe(RANGES.stat.max)
    expect(big.records.fromSweets.DEF).toBe(big.stats.DEF)
  })

  it('a newborn starts inside its caps', () => {
    const m = createMonster({ id: 'x', mainBreed: 'bloatoad', likes: makeMonster().likes, offsets: { stats: { LIF: 5000, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 } } })
    expect(m.stats.LIF).toBe(STAT_CAP_BY_GRADE[m.grades.LIF])
    expect(m.inheritedTrait).toBeNull()
  })

  it('Heartstones pass on trained points only and stop at the cap; the grant is what landed', () => {
    const donor = makeMonster({ id: 'donor', stats: { POW: 670 } })
    donor.records.fromSweets.POW = 400
    const plain = heartstoneFrom(makeMonster({ id: 'donor', stats: { POW: 670 } }), 1)
    expect(heartstoneFrom(donor, 1).gains.POW).toBe(plain.gains.POW - 400)
    const state = createGameState({ monster: makeMonster({ id: 'heir', stats: { POW: 1195 } }) })
    state.heartstones = [plain]
    const r = giveHeartstone(state, plain.id)
    expect(r.grant!.POW).toBe(5)
    expect(r.state.monster!.stats.POW).toBe(1200)
  })

  it('the cocoon keeps sweets whole, 80 % of trained gains, and any grade steps a Pearl had earned', () => {
    const grub = makeMonster({ main: 'nibblegrub', stats: { LIF: 600, INT: 300 } })
    grub.records.fromSweets.INT = 100
    grub.grades.INT = 'B' // Nibblegrub INT is D: two Pearl steps
    const moth = metamorphose(grub, 'velvesper')
    expect(moth.grades.INT).toBe('S') // Velvesper INT A, + 2 steps, stops at S
    expect(sweetsOf(moth, 'INT')).toBe(100)
    expect(moth.stats.INT).toBeGreaterThanOrEqual(100 + 140) // sweets + Velvesper's base INT at least
  })

  it('walking speed counts SPD up to 1,500 only', () => {
    expect(walkPerTick(1500)).toBeGreaterThan(walkPerTick(999))
    expect(walkPerTick(9999)).toBe(walkPerTick(1500))
  })

  it('damage math stays in safe integers at the 9,999 bound, through a crit and two traits', () => {
    const top = { force: 96, a: RANGES.stat.max, defDef: RANGES.stat.min, defSame: RANGES.stat.min, gutsAtt: 99, rateAtt: 20, gutsDef: 0, rateDef: 6 }
    let v = damageBase(top)
    // crit ×1.5, two damage traits ×1.3 each, a special ×1.25, the top roll ×1.05
    for (const mul of [1500, 1300, 1300, 1250, 1050]) {
      expect(Number.isSafeInteger(v * mul)).toBe(true)
      v = divRound(v * mul, 1000)
    }
    expect(Number.isSafeInteger(finishDamage(damageBase(top), [1500, 1300, 1300, 1250, 1050]))).toBe(true)
    expect(expectedDamage(top)).toBeGreaterThan(0)
  })
})

describe('two traits (§12.8, v1.11)', () => {
  it('traitsOf: the breed trait, then an inherited one (never twice)', () => {
    const m = makeMonster({ main: 'moatshell' })
    expect(traitsOf(m)).toEqual(['fortified'])
    m.inheritedTrait = 'nimble'
    expect(traitsOf(m)).toEqual(['fortified', 'nimble'])
    expect(hasTrait(m, 'nimble')).toBe(true)
    m.inheritedTrait = 'fortified'
    expect(traitsOf(m)).toEqual(['fortified'])
  })

  it('one trait gives exactly its own answer; two combine (multipliers multiply, bonuses add, flags use any)', () => {
    const taken = { techType: 'POW' as const, still: false }
    expect(traitsMul(['fortified'], (t) => traitTakenMul(t, taken))).toBe(traitTakenMul('fortified', taken))
    expect(traitsMul(['fortified', 'unshakable'], (t) => traitTakenMul(t, taken))).toBe(divRound(traitTakenMul('fortified', taken) * traitTakenMul('unshakable', taken), 1000))
    expect(traitsMul(['fortified', 'unshakable'], (t) => traitTakenMul(t, taken))).toBeLessThan(traitTakenMul('fortified', taken))
    expect(traitsSum(['glow', 'underdog'], (t) => traitHitBonus(t, 4, true))).toBe(traitHitBonus('glow', 4, true) + traitHitBonus('underdog', 4, true))
    expect(traitsAny(['nimble', 'unshakable'], traitImmovable)).toBe(true)
    expect(traitsAny(['nimble'], traitImmovable)).toBe(false)
    expect(traitsFirst(['nimble', 'reflective'], traitReflect)).toEqual(traitReflect('reflective'))
    expect(traitsFirst(['nimble'], traitReflect)).toBeNull()
  })
})
