import { describe, expect, it } from 'vitest'
import { BREED_IDS } from '../../data/types.ts'
import { cyrb53 } from '../hash.ts'
import { npcMonster } from '../npc.ts'
import { runBattle, timerTicksFor } from './engine.ts'
import type { FighterSetup } from './types.ts'

/**
 * A golden record of 30 fixed-seed battles (every breed once, at three stat totals). v1.11 turned a fighter's
 * single trait into a list; a one-trait fighter must still fight bit for bit as before, so this hash was taken on
 * the commit before that change and must never move by accident.
 */
const ai = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'ai', personality: 'Steady' })

describe('battle golden record', () => {
  it('30 fixed battles give the same logs as before the trait-list change', () => {
    const logs: string[] = []
    BREED_IDS.forEach((breed, i) => {
      const total = [1000, 2000, 3000][i % 3]!
      const a = npcMonster({ breed, total, seed: 100 + i })
      const b = npcMonster({ breed: BREED_IDS[(i * 7 + 3) % BREED_IDS.length]!, total, seed: 200 + i })
      const r = runBattle(ai(a), ai(b), { seed: 300 + i, timerTicks: timerTicksFor(60) })
      logs.push(JSON.stringify([r.outcome, r.log]))
    })
    expect(cyrb53(logs.join('\n'))).toBe(8375973471465796)
  })
})
