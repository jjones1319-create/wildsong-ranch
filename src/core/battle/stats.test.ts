import { describe, expect, it } from 'vitest'
import { BATTLE } from '../../data/tuning.ts'
import { npcMonster } from '../npc.ts'
import { runBattle, timerTicksFor } from './engine.ts'
import { addResult, emptyStats, summarize, toCsv } from './stats.ts'
import type { FighterSetup } from './types.ts'

const ai = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'ai', personality: 'Steady' })

describe('Battle Lab stats', () => {
  it('maps swapped sides back and sums to a whole', () => {
    const a = npcMonster({ breed: 'cinderlynx', total: 2200, seed: 1 })
    const b = npcMonster({ breed: 'puddlepup', total: 900, seed: 2 })
    const stats = emptyStats()
    for (let seed = 0; seed < 20; seed++) {
      const swapped = seed % 2 === 1
      const r = swapped ? runBattle(ai(b), ai(a), { seed, timerTicks: timerTicksFor(60) }) : runBattle(ai(a), ai(b), { seed, timerTicks: timerTicksFor(60) })
      addResult(stats, r, swapped)
    }
    const s = summarize(stats, BATTLE.ticksPerSecond)
    expect(s.battles).toBe(20)
    expect(s.winPct[0] + s.winPct[1] + s.drawPct).toBeCloseTo(100, 0)
    expect(s.winPct[0]).toBeGreaterThan(s.winPct[1]) // A is far stronger, on either side
    expect(s.koPct[0]).toBeLessThanOrEqual(s.winPct[0])
    expect(s.avgSeconds).toBeGreaterThan(0)
    expect(s.avgSeconds).toBeLessThanOrEqual(60)
    expect(s.hitRatePct[0]).toBeGreaterThan(0)
    expect(s.topTechniques[0].length).toBeGreaterThan(0)
    const csv = toCsv('A, the "first"', 'B', s)
    expect(csv.split('\n')[0]).toBe('metric,A,B')
    expect(csv).toContain('"A, the ""first"""')
    expect(csv).toContain(`win %,${s.winPct[0]},${s.winPct[1]}`)
  })
})
