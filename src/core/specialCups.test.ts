import { describe, expect, it } from 'vitest'
import { NPC, TOURNAMENT } from '../data/tuning.ts'
import type { TournamentGrade } from '../data/types.ts'
import { weekIndexOf } from './calendar.ts'
import { totalStats } from './monster.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { createTournament } from './tournament.ts'

/**
 * M9: the special cups (Masquerade, Crowns, Legend) generate their opponents at the player's stat total, never
 * below the grade's band, so a monster far above its band still gets a fight. Ordinary cups and Officials keep
 * the grade's band (Corin included).
 */

const at = (year: number, month: number, week: number) => weekIndexOf({ year, month, week })
const flat = (v: number) => ({ LIF: v, POW: v, INT: v, SKI: v, SPD: v, DEF: v })

function gameAt(week: number, grade: TournamentGrade, each: number): GameState {
  const m = makeMonster({ agePct: 20, stats: flat(each) })
  m.grade = grade
  const g = createGameState({ monster: m })
  g.week = week
  g.weekPhase = 'action'
  return g
}

describe('special cups scale their opponents to the player (M9)', () => {
  it('the Masked Breeder matches a strong player and never drops below the B band', () => {
    const strong = gameAt(at(2, 10, 1), 'B', 600) // total 3,600, far above B (1,550–2,000)
    strong.unlocks.masqueradeInvited = true
    const t = createTournament(strong, 'masquerade', 'auto')
    const masked = t.participants.find((p) => p.rivalId === 'masked-breeder')!
    expect(masked.monster.mainBreed).toBe('mirrorkin')
    expect(totalStats(masked.monster.stats)).toBe(Math.round((3600 * TOURNAMENT.specialScalePct.masquerade) / 100))

    const modest = gameAt(at(2, 10, 1), 'B', 200) // total 1,200, below the band
    modest.unlocks.masqueradeInvited = true
    const t2 = createTournament(modest, 'masquerade', 'auto')
    expect(totalStats(t2.participants.find((p) => p.rivalId === 'masked-breeder')!.monster.stats)).toBe(NPC.totals.B![0])
  })

  it('the Crowns follow the player: Corin at ×1.05 and the wild entrants at the player total', () => {
    const s = gameAt(at(2, 2, 2), 'S', 800) // total 4,800, above the Crown band (2,900–3,300)
    s.guild.crownInvite = true
    const crown = createTournament(s, 'crown-of-dawn', 'auto')
    const corin = crown.participants.find((p) => p.rivalId === 'corin-hale')!
    expect(totalStats(corin.monster.stats)).toBe(Math.round(4800 * 1.05))
    for (const p of crown.participants.slice(1)) expect(totalStats(p.monster.stats)).toBeGreaterThanOrEqual(4800)
    // Never above the stat cap.
    const huge = gameAt(at(2, 2, 2), 'S', 990)
    huge.guild.crownInvite = true
    for (const p of createTournament(huge, 'crown-of-dawn', 'auto').participants.slice(1)) expect(totalStats(p.monster.stats)).toBeLessThanOrEqual(999 * 6)
  })

  it('an Official keeps Corin inside the grade band', () => {
    const g = gameAt(at(1, 3, 4), 'E', 300) // total 1,800 at grade E
    const t = createTournament(g, 'spring-ascension', 'auto')
    const corin = t.participants.find((p) => p.rivalId === 'corin-hale')!
    expect(totalStats(corin.monster.stats)).toBe(NPC.totals.E![1])
  })
})
