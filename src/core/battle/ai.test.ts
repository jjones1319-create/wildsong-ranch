import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI } from '../../data/tuning.ts'
import { PERSONALITIES, type Personality } from '../../data/types.ts'
import { npcMonster } from '../npc.ts'
import { createBattle, runBattle, step, timerTicksFor } from './engine.ts'
import type { FighterSetup } from './types.ts'

const ai = (monster: FighterSetup['monster'], personality: Personality): FighterSetup => ({ monster, control: 'ai', personality })
const opts = (seed: number) => ({ seed, timerTicks: timerTicksFor(60) })

describe('the CPU AI (§12.10)', () => {
  it('makes 4–12 attacks per monster per match on average (§26), for every personality', () => {
    const a = npcMonster({ breed: 'puddlepup', total: 1500, seed: 1 })
    const b = npcMonster({ breed: 'quillion', total: 1500, seed: 2 })
    for (const p of PERSONALITIES) {
      let attacks = 0
      let fights = 0
      for (let seed = 0; seed < 40; seed++) {
        const r = runBattle(ai(a, p), ai(b, 'Steady'), opts(seed))
        attacks += r.fighters[0].attacks
        fights += 1
      }
      const avg = attacks / fights
      expect(avg, p).toBeGreaterThanOrEqual(4)
      expect(avg, p).toBeLessThanOrEqual(12)
    }
  })

  it('Aggressive attacks more often than Cautious', () => {
    const a = npcMonster({ breed: 'tumblefox', total: 1500, seed: 3 })
    const b = npcMonster({ breed: 'tumblefox', total: 1500, seed: 4 })
    const count = (p: Personality) => {
      let n = 0
      for (let seed = 0; seed < 40; seed++) n += runBattle(ai(a, p), ai(b, 'Steady'), opts(seed)).fighters[0].attacks
      return n
    }
    expect(count('Aggressive')).toBeGreaterThan(count('Cautious'))
  })

  it('rookies (grade E–D) hold 45 guts before attacking', () => {
    const rookie = npcMonster({ breed: 'puddlepup', grade: 'E', seed: 9 })
    for (let seed = 0; seed < 5; seed++) {
      const b = createBattle(ai(rookie, 'Aggressive'), ai(rookie, 'Aggressive'), opts(seed))
      let fires = 0
      while (!b.state.outcome) {
        const gutsBefore = [b.state.fighters[0].guts, b.state.fighters[1].guts]
        for (const e of step(b)) {
          if (e.kind === 'fire') {
            expect(gutsBefore[e.side]).toBeGreaterThanOrEqual(AI.guts.rookieReserve)
            fires += 1
          }
        }
      }
      expect(fires).toBeGreaterThan(0)
    }
  })

  it('a Trickster uses Wither techniques at least as much as a Steady fighter', () => {
    const a = npcMonster({ breed: 'coilfang', grade: 'A', seed: 5 })
    const b = npcMonster({ breed: 'coilfang', grade: 'A', seed: 6 })
    expect(a.techniques.some((t) => isWither(t.id))).toBe(true)
    const witherUses = (p: Personality) => {
      let n = 0
      for (let seed = 0; seed < 60; seed++) {
        const r = runBattle(ai(a, p), ai(b, 'Steady'), opts(seed))
        for (const [id, uses] of Object.entries(r.fighters[0].techUses)) if (isWither(id)) n += uses
      }
      return n
    }
    expect(witherUses('Trickster')).toBeGreaterThanOrEqual(witherUses('Steady'))
  })
})

function isWither(id: string): boolean {
  return TECHNIQUE_BY_ID[id]?.family === 'Wither'
}
