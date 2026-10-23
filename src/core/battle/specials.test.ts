import { describe, expect, it } from 'vitest'
import { SPECIALS } from '../../data/tuning.ts'
import { createRng } from '../rng.ts'
import { makeMonster } from '../test-helpers.ts'
import { createBattle } from './engine.ts'
import { bulwarkPct, canTrigger, clutchPct, composurePct, lastStandPct, ragePct, specialMods, tickSpecial, tryTrigger, valorPct } from './specials.ts'

function fighter(over: Partial<ReturnType<typeof createBattle>['state']['fighters'][0]> = {}) {
  const b = createBattle({ monster: makeMonster(), control: 'ai', personality: 'Steady' }, { monster: makeMonster(), control: 'ai', personality: 'Steady' }, { seed: 1, timerTicks: 1800 })
  return Object.assign(b.state.fighters[0], over)
}

describe('specials (§12.7)', () => {
  it('trigger chances follow the table', () => {
    const f = fighter({ guts: 50, loyalty: 60, nature: 40, hp: 20, maxHp: 100 })
    f.stats.DEF = 300
    expect(lastStandPct(f)).toBeCloseTo(Math.min(35, 5 + 12 + 3))
    expect(valorPct(f)).toBe(20)
    expect(valorPct(fighter({ nature: 10, hp: 10, maxHp: 100 }))).toBe(0)
    expect(valorPct(fighter({ nature: 40, hp: 50, maxHp: 100 }))).toBe(0)
    expect(ragePct(fighter({ nature: -30 }), 40)).toBe(20)
    expect(ragePct(fighter({ nature: -10 }), 40)).toBe(0)
    expect(bulwarkPct(fighter({ hitsTakenRow: 3, guts: 40 }))).toBe(20)
    expect(bulwarkPct(fighter({ hitsTakenRow: 2, guts: 40 }))).toBe(0)
    expect(composurePct(fighter({ successRow: 4, guts: 70 }))).toBe(10)
    const me = fighter({ hp: 30, maxHp: 100 })
    const them = fighter({ hp: 70, maxHp: 100 })
    expect(clutchPct(me, them)).toBe(20)
    expect(clutchPct(them, me)).toBe(0)
  })

  it('fires once per battle, blocks a second timed special, and expires', () => {
    const f = fighter({ hitsTakenRow: 3, guts: 0 })
    const rng = createRng(1)
    const log: ReturnType<typeof createBattle>['state']['log'] = []
    expect(tryTrigger(f, 'bulwark', 100, rng, 10, log)).toBe(true)
    expect(f.special).toEqual({ kind: 'bulwark', ticksLeft: SPECIALS.durationTicks })
    expect(log[0]).toMatchObject({ kind: 'special', special: 'bulwark' })
    expect(canTrigger(f, 'valor')).toBe(false) // one at a time
    expect(canTrigger(f, 'lastStand')).toBe(true) // except Last Stand
    for (let i = 0; i < SPECIALS.durationTicks; i++) tickSpecial(f)
    expect(f.special).toBeNull()
    expect(canTrigger(f, 'bulwark')).toBe(false) // used
    expect(tryTrigger(f, 'bulwark', 100, rng, 11, log)).toBe(false)
    expect(tryTrigger(f, 'clutch', 100, rng, 12, log)).toBe(true)
    expect(f.special?.ticksLeft).toBe(-1)
    tickSpecial(f)
    expect(f.special?.kind).toBe('clutch')
  })

  it('modifiers match the table', () => {
    expect(specialMods(null).dealtPct).toBe(100)
    expect(specialMods({ kind: 'valor', ticksLeft: 1 }).dealtPct).toBe(150)
    expect(specialMods({ kind: 'rage', ticksLeft: 1 })).toMatchObject({ witherDealtPct: 150, regenPct: 140, givesAdvantage: true })
    expect(specialMods({ kind: 'bulwark', ticksLeft: 1 })).toMatchObject({ takenPct: 70, regenPct: 140, dealtPct: 60 })
    expect(specialMods({ kind: 'clutch', ticksLeft: -1 }).critMul).toBe(2)
    expect(specialMods({ kind: 'composure', ticksLeft: 1 })).toMatchObject({ costPct: 70, takenPct: 150, givesDisadvantage: true })
  })
})
