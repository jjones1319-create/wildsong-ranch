import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { NPC } from '../data/tuning.ts'
import { STAT_KEYS } from '../data/types.ts'
import { loyaltyOf, totalStats } from './monster.ts'
import { distributeTotal, gradeForTotal, NPC_GRADES, npcMonster } from './npc.ts'

describe('the NPC generator (§13)', () => {
  it('maps totals to grades at the band edges', () => {
    expect(gradeForTotal(600)).toBe('E')
    expect(gradeForTotal(800)).toBe('E')
    expect(gradeForTotal(801)).toBe('D')
    expect(gradeForTotal(1550)).toBe('C')
    expect(gradeForTotal(2900)).toBe('S')
    expect(gradeForTotal(3000)).toBe('Crown')
    expect(gradeForTotal(9000)).toBe('Legend')
  })

  it('distributes a total exactly inside 1–999', () => {
    for (const total of [6, 500, 1500, 3000, 5994]) {
      const s = distributeTotal({ LIF: 160, POW: 215, INT: 118, SKI: 160, SPD: 160, DEF: 160 }, total)
      expect(totalStats(s)).toBe(total)
      for (const k of STAT_KEYS) expect(s[k]).toBeGreaterThanOrEqual(1)
      for (const k of STAT_KEYS) expect(s[k]).toBeLessThanOrEqual(999)
    }
  })

  it('every grade lands in its total, loyalty and fame bands with the right technique set', () => {
    for (const grade of NPC_GRADES) {
      for (let seed = 0; seed < 5; seed++) {
        const m = npcMonster({ breed: 'tumblefox', grade, seed })
        const total = totalStats(m.stats)
        expect(total).toBeGreaterThanOrEqual(NPC.totals[grade]![0])
        expect(total).toBeLessThanOrEqual(NPC.totals[grade]![1])
        expect(loyaltyOf(m)).toBeGreaterThanOrEqual(NPC.loyalty[grade]![0])
        expect(loyaltyOf(m)).toBeLessThanOrEqual(NPC.loyalty[grade]![1])
        expect(m.fame).toBeGreaterThanOrEqual(NPC.fame[grade]![0])
        expect(m.fame).toBeLessThanOrEqual(NPC.fame[grade]![1])
        const families = new Set(m.techniques.map((t) => TECHNIQUE_BY_ID[t.id]!.family))
        const gi = NPC_GRADES.indexOf(grade)
        expect(families.has('Basic')).toBe(true)
        expect(families.has('Hit')).toBe(gi >= 1)
        expect(families.has('Heavy')).toBe(gi >= 3)
        if (gi === 2) expect(families.has('Wither') !== families.has('Sharp')).toBe(true)
        if (gi >= 4) expect(families.has('Wither') && families.has('Sharp')).toBe(true)
        if (gi >= 5) expect(families.has('Special') && families.has('Chain')).toBe(true)
        expect(families.has('Signature')).toBe(false)
        const universal = m.techniques.filter((t) => TECHNIQUE_BY_ID[t.id]!.breed === 'universal').length
        if (gi >= 3) expect(universal).toBeGreaterThanOrEqual(1)
        else expect(universal).toBe(0)
        expect(m.techniques.length).toBeLessThanOrEqual(12)
      }
    }
  })

  it('a given total and seed always make the same monster; a boss knows its Signature', () => {
    const a = npcMonster({ breed: 'cobblemaw', total: 1500, seed: 3 })
    const b = npcMonster({ breed: 'cobblemaw', total: 1500, seed: 3 })
    expect(a).toEqual(b)
    expect(totalStats(a.stats)).toBe(1500)
    expect(a.grade).toBe('C')
    const boss = npcMonster({ breed: 'cobblemaw', grade: 'S', seed: 3, boss: true })
    expect(boss.techniques.some((t) => TECHNIQUE_BY_ID[t.id]!.family === 'Signature')).toBe(true)
    const mixed = npcMonster({ breed: 'cobblemaw', sub: 'wishlume', grade: 'D', seed: 3 })
    expect(mixed.techniques.some((t) => t.id.startsWith('wishlume.'))).toBe(true)
  })
})
