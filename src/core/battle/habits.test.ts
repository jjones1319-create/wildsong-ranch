import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import type { Habit } from '../../data/types.ts'
import type { Monster } from '../monster.ts'
import { npcMonster } from '../npc.ts'
import { createBattle, currentBand, gapUnits, runBattle, step, timerTicksFor } from './engine.ts'
import type { FighterSetup } from './types.ts'

const fighter = (monster: Monster, habit: Habit): FighterSetup => ({ monster, control: 'ai', personality: 'Steady', habit })
const opts = (seed: number) => ({ seed, timerTicks: timerTicksFor(60) })

describe('rival habits (CONTENT §10)', () => {
  const heron = npcMonster({ breed: 'galeheron', grade: 'B', seed: 1 }) // has a Far Heavy (Tempest Dive)
  const pup = npcMonster({ breed: 'puddlepup', grade: 'C', seed: 2 })

  it('opens Far: the first technique fired has range 4', () => {
    for (let seed = 0; seed < 10; seed++) {
      const r = runBattle(fighter(heron, 'opensFar'), fighter(pup, 'none'), opts(seed))
      const first = r.log.find((e) => e.kind === 'fire' && e.side === 0)
      if (first && first.kind === 'fire') expect(TECHNIQUE_BY_ID[first.tech]!.range).toBe(4)
    }
  })

  it('waits at 99 guts and banks 70 for a Heavy', () => {
    const wall = npcMonster({ breed: 'moatshell', grade: 'B', seed: 3 })
    for (let seed = 0; seed < 4; seed++) {
      const b = createBattle(fighter(wall, 'waits99'), fighter(pup, 'none'), opts(seed))
      while (!b.state.outcome) {
        const guts = b.state.fighters[0].guts
        for (const e of step(b)) if (e.kind === 'fire' && e.side === 0) expect(guts).toBeGreaterThanOrEqual(99)
      }
      const c = createBattle(fighter(wall, 'banksForHeavy'), fighter(pup, 'none'), opts(seed))
      while (!c.state.outcome) {
        const guts = c.state.fighters[0].guts
        for (const e of step(c)) if (e.kind === 'fire' && e.side === 0 && TECHNIQUE_BY_ID[e.tech]!.family === 'Heavy') expect(guts).toBeGreaterThanOrEqual(70)
      }
    }
  })

  it('walks straight into Close, backs away when approached, pushes whenever touching', () => {
    const ticksInBand1 = (habit: Habit, seeds = 6) => {
      let n = 0
      for (let seed = 0; seed < seeds; seed++) {
        const b = createBattle(fighter(pup, habit), fighter(heron, 'none'), opts(seed))
        while (!b.state.outcome) {
          step(b)
          if (currentBand(b.state) === 1) n++
        }
      }
      return n
    }
    expect(ticksInBand1('walksClose')).toBeGreaterThan(ticksInBand1('none'))
    const avgGap = (habit: Habit) => {
      let total = 0
      let ticks = 0
      for (let seed = 0; seed < 6; seed++) {
        const b = createBattle(fighter(heron, habit), fighter(pup, 'walksClose'), opts(seed))
        while (!b.state.outcome) {
          step(b)
          total += gapUnits(b.state)
          ticks++
        }
      }
      return total / ticks
    }
    expect(avgGap('backsAway')).toBeGreaterThan(avgGap('none'))
    const pushes = (habit: Habit) => {
      let n = 0
      for (let seed = 0; seed < 10; seed++) n += runBattle(fighter(pup, habit), fighter(pup, 'walksClose'), opts(seed)).log.filter((e) => e.kind === 'push' && e.side === 0).length
      return n
    }
    expect(pushes('pushesWhenTouching')).toBeGreaterThan(pushes('none'))
  })

  it('spams Wither, steals guts and dashes in below half HP without breaking anything', () => {
    const snake = npcMonster({ breed: 'coilfang', grade: 'A', seed: 4 })
    const witherUses = (habit: Habit) => {
      let n = 0
      for (let seed = 0; seed < 20; seed++) for (const [id, uses] of Object.entries(runBattle(fighter(snake, habit), fighter(pup, 'none'), opts(seed)).fighters[0].techUses)) if (TECHNIQUE_BY_ID[id]!.family === 'Wither') n += uses
      return n
    }
    expect(witherUses('spamsWither')).toBeGreaterThanOrEqual(witherUses('none'))
    expect(witherUses('stealsGuts')).toBeGreaterThanOrEqual(witherUses('none'))
    const lynx = npcMonster({ breed: 'cinderlynx', grade: 'C', seed: 5 })
    const strong = npcMonster({ breed: 'cobblemaw', grade: 'A', seed: 6 })
    let dashes = 0
    for (let seed = 0; seed < 10; seed++) dashes += runBattle(fighter(lynx, 'dashesBelowHalf'), fighter(strong, 'none'), opts(seed)).log.filter((e) => e.kind === 'dash' && e.side === 0).length
    expect(dashes).toBeGreaterThan(0)
  })
})
