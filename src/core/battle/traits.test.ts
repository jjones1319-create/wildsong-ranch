import { describe, expect, it } from 'vitest'
import { BREED_BY_ID } from '../../data/breeds.ts'
import { TRAITS } from '../../data/traits.ts'
import type { BreedId } from '../../data/types.ts'
import { npcMonster } from '../npc.ts'
import { runBattle, timerTicksFor } from './engine.ts'
import { traitDealtMul, traitExtraHits, traitHitBonus, traitImmovable, traitRegenMul, traitSpeedMul, traitTakenMul } from './traits.ts'
import type { FighterSetup } from './types.ts'

const ai = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'ai', personality: 'Steady' })
const opts = (seed: number) => ({ seed, timerTicks: timerTicksFor(60) })

describe('battle traits (CONTENT §2.1, NEW_MONSTERS §2)', () => {
  it('answers the table', () => {
    expect(traitHitBonus('glow', 4, false)).toBe(6)
    expect(traitHitBonus('glow', 3, false)).toBe(0)
    expect(traitHitBonus('en-garde', 2, false)).toBe(8)
    expect(traitHitBonus('underdog', 1, true)).toBe(8)
    expect(traitHitBonus('underdog', 1, false)).toBe(0)
    expect(traitDealtMul('heavy-hitter', { family: 'Heavy', hpPct: 1000, underdog: false, ramArmed: false })).toBe(1150)
    expect(traitDealtMul('heavy-hitter', { family: 'Hit', hpPct: 1000, underdog: false, ramArmed: false })).toBe(1000)
    expect(traitDealtMul('hot-blooded', { family: 'Hit', hpPct: 500, underdog: false, ramArmed: false })).toBe(1150)
    expect(traitDealtMul('hot-blooded', { family: 'Hit', hpPct: 501, underdog: false, ramArmed: false })).toBe(1000)
    expect(traitDealtMul('battering-ram', { family: 'Hit', hpPct: 1000, underdog: false, ramArmed: true })).toBe(1150)
    expect(traitTakenMul('fortified', { techType: 'INT', still: false })).toBe(700)
    expect(traitTakenMul('hard-shell', { techType: 'POW', still: false })).toBe(750)
    expect(traitTakenMul('hard-shell', { techType: 'INT', still: false })).toBe(1000)
    expect(traitTakenMul('unshakable', { techType: 'INT', still: false })).toBe(800)
    expect(traitTakenMul('statue-pose', { techType: 'INT', still: true })).toBe(500)
    expect(traitRegenMul('live-wire', 29)).toBe(1100)
    expect(traitRegenMul('live-wire', 30)).toBe(1000)
    expect(traitSpeedMul('tailwind')).toBe(1200)
    expect(traitImmovable('unshakable')).toBe(true)
    expect(traitExtraHits('eight-arms')).toBe(1)
    expect(traitExtraHits('cheerful')).toBe(0)
  })

  it('every one of the 30 traits can fight 20 battles without errors, and the special moments show in the log', () => {
    const seen = new Set<string>()
    for (const trait of TRAITS) {
      const breed = Object.values(BREED_BY_ID).find((b) => b.trait === trait.id)!.id as BreedId
      const m = npcMonster({ breed, total: 1800, seed: 42 })
      const opp = npcMonster({ breed: 'puddlepup', total: 1800, seed: 43 })
      for (let seed = 0; seed < 20; seed++) {
        const r = runBattle(ai(m), ai(opp), opts(seed))
        expect(r.outcome.ticks).toBeGreaterThan(0)
        for (const e of r.log) {
          if (e.kind === 'trait') seen.add(e.trait)
          if (e.kind === 'heal' && e.why === 'blessed') seen.add('blessed')
          if (e.kind === 'reflect') seen.add('reflective')
          if (e.kind === 'push' && e.blocked) seen.add('unshakable')
        }
      }
    }
    expect(seen.has('dragonheart')).toBe(true)
    expect(seen.has('blessed')).toBe(true)
  })

  it('Fortified takes less damage than a plain copy against the same attacker', () => {
    const attacker = npcMonster({ breed: 'cobblemaw', total: 2000, seed: 7 })
    const wall = npcMonster({ breed: 'moatshell', total: 2000, seed: 8 }) // fortified
    const plain = { ...structuredClone(wall), mainBreed: 'puddlepup' as BreedId } // puddlepup's trait is Cheerful (no battle effect)
    const taken = (m: typeof wall) => {
      let dmg = 0
      for (let seed = 0; seed < 30; seed++) dmg += runBattle(ai(attacker), ai(m), opts(seed)).fighters[0].damageDealt
      return dmg
    }
    expect(taken(wall)).toBeLessThan(taken(plain))
  })
})
