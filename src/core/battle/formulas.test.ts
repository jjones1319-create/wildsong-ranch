import { describe, expect, it } from 'vitest'
import { BATTLE } from '../../data/tuning.ts'
import { bandOf, critTenths, distractionPct, expectedDamage, formAdjusted, gutsAttackMul, gutsDefenseMul, hitTenths, hpPctTenths, isqrt, walkPerTick } from './formulas.ts'

describe('isqrt', () => {
  it('is the floor square root for the sizes the formulas use', () => {
    for (const n of [0, 1, 2, 3, 4, 15, 16, 17, 999_999, 1_000_000, 111_111_111, 226_666_666, 4_599_999_999_999]) {
      const r = isqrt(n)
      expect(r * r).toBeLessThanOrEqual(n)
      expect((r + 1) * (r + 1)).toBeGreaterThan(n)
    }
  })
})

describe('§12.5 damage reference table (POW tech, 50 vs 50 guts, rate 12, no crit)', () => {
  const rows: { a: number; def: number; same: number; lif: number; dmg: [number, number, number] }[] = [
    { a: 150, def: 120, same: 120, lif: 180, dmg: [19, 29, 89] },
    { a: 400, def: 350, same: 300, lif: 420, dmg: [37, 56, 171] },
    { a: 700, def: 600, same: 500, lif: 700, dmg: [60, 89, 273] },
    { a: 950, def: 850, same: 700, lif: 950, dmg: [77, 115, 351] },
    { a: 700, def: 250, same: 150, lif: 350, dmg: [83, 124, 380] },
    { a: 300, def: 700, same: 600, lif: 800, dmg: [21, 31, 96] },
  ]
  for (const row of rows) {
    it(`A ${row.a} vs DEF ${row.def} / ${row.same} / LIF ${row.lif} → ${row.dmg.join(' / ')}`, () => {
      const got = [12, 18, 55].map((force) => expectedDamage({ force, a: row.a, defDef: row.def, defSame: row.same, gutsAtt: 50, rateAtt: 12, gutsDef: 50, rateDef: 12 }))
      expect(got).toEqual(row.dmg)
    })
  }
})

describe('§12.5 hit examples and guts multipliers', () => {
  const base = { bonus: 0, advantages: 0, disadvantage: false }
  it('reproduces the three hit examples', () => {
    expect(hitTenths({ ...base, techHit: 0, skiAtt: 300, spdDef: 300, gutsAtt: 50, gutsDef: 50 })).toBe(500)
    expect(hitTenths({ ...base, techHit: 16, skiAtt: 600, spdDef: 300, gutsAtt: 50, gutsDef: 50 })).toBe(860)
    expect(Math.floor(hitTenths({ ...base, techHit: -10, skiAtt: 300, spdDef: 700, gutsAtt: 90, gutsDef: 20 }) / 10)).toBe(27)
  })

  it('clamps to 5–95 % and applies advantage and disadvantage', () => {
    expect(hitTenths({ ...base, techHit: 80, skiAtt: 900, spdDef: 10, gutsAtt: 99, gutsDef: 0 })).toBe(950)
    expect(hitTenths({ ...base, techHit: -60, skiAtt: 10, spdDef: 999, gutsAtt: 0, gutsDef: 99 })).toBe(50)
    const even = { ...base, techHit: 0, skiAtt: 300, spdDef: 300, gutsAtt: 50, gutsDef: 50 }
    expect(hitTenths({ ...even, advantages: 1 })).toBe(750) // 100 − 50²/100
    expect(hitTenths({ ...even, advantages: 2 })).toBe(875) // 100 − 50³/10⁴
    expect(hitTenths({ ...even, disadvantage: true })).toBe(250) // 50²/100
  })

  it('guts multipliers match the doc: ×1.07–×1.25 at 99 guts, ×0.94–×0.80 at 10', () => {
    expect(gutsAttackMul(99, 6)).toBe(1074)
    expect(gutsAttackMul(99, 18)).toBe(1250)
    expect(gutsAttackMul(10, 6)).toBe(940)
    expect(gutsAttackMul(10, 18)).toBe(796)
    expect(gutsAttackMul(50, 12)).toBe(1000)
    expect(gutsDefenseMul(50, 12)).toBe(1000)
    expect(gutsDefenseMul(99, 18)).toBe(1000 - 125)
  })
})

describe('bands, walking, form, crit, distraction', () => {
  it('maps gaps to bands at the edges', () => {
    expect(bandOf(0)).toBe(1)
    expect(bandOf(159)).toBe(1)
    expect(bandOf(160)).toBe(2)
    expect(bandOf(309)).toBe(2)
    expect(bandOf(310)).toBe(3)
    expect(bandOf(479)).toBe(3)
    expect(bandOf(480)).toBe(4)
    expect(bandOf(679)).toBe(4)
    expect(bandOf(680)).toBe(5)
    expect(bandOf(300 /* the starting gap */)).toBe(2)
  })

  it('walks 70 units per second at SPD 0 and 120 at SPD 999', () => {
    expect(walkPerTick(0) * BATTLE.ticksPerSecond).toBeCloseTo(7000, -2)
    expect(walkPerTick(999) * BATTLE.ticksPerSecond).toBe(12000)
  })

  it('form makes round monsters slower and sturdier', () => {
    expect(formAdjusted({ LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 500, DEF: 500 }, 100)).toEqual({ spd: 400, def: 600 })
    expect(formAdjusted({ LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 500, DEF: 500 }, -100)).toEqual({ spd: 600, def: 400 })
    expect(formAdjusted({ LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 500, DEF: 500 }, 0)).toEqual({ spd: 500, def: 500 })
  })

  it('crit chance follows nature, fame and stress with the caps', () => {
    expect(critTenths({ sharp: 8, fame: 0, oppFame: 0, nature: 0, stress: 0, fameCapBonus: 0, bonus: 0 })).toBe(80)
    expect(critTenths({ sharp: 8, fame: 100, oppFame: 0, nature: 10, stress: 90, fameCapBonus: 0, bonus: 0 })).toBe(180)
    expect(critTenths({ sharp: 8, fame: 100, oppFame: 0, nature: 10, stress: 90, fameCapBonus: 5, bonus: 6 })).toBe(80 + 100 + 60) // Regal cap 15 but fame/10 = 10; Moonlit +6
    expect(critTenths({ sharp: 8, fame: 100, oppFame: 100, nature: -10, stress: 100, fameCapBonus: 0, bonus: 0 })).toBe(80 + 50 + 50 + 100)
  })

  it('interpolates distraction between the loyalty points', () => {
    expect(distractionPct(0)).toBe(45)
    expect(distractionPct(20)).toBe(30)
    expect(distractionPct(10)).toBe(37.5)
    expect(distractionPct(45)).toBe(14.5)
    expect(distractionPct(85)).toBe(1)
    expect(distractionPct(100)).toBe(1)
  })

  it('truncates HP % to a tenth', () => {
    expect(hpPctTenths(1, 3)).toBe(333)
    expect(hpPctTenths(0, 3)).toBe(0)
    expect(hpPctTenths(3, 3)).toBe(1000)
  })
})
