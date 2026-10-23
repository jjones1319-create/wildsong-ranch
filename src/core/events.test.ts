import { describe, expect, it } from 'vitest'
import { EXPEDITION_SITES } from '../data/expeditions.ts'
import { weekIndexOf } from './calendar.ts'
import { weeklyEvents } from './events.ts'
import { beginWeek } from './game.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const at = (year: number, month: number, week: number) => weekIndexOf({ year, month, week })

function gameAt(week: number, over: Parameters<typeof makeMonster>[0] = {}): GameState {
  const m = makeMonster(over)
  m.lifespanTotal = 400
  m.ageWeeks = 20
  const g = createGameState({ monster: m })
  g.week = week
  return g
}

describe('the week’s mail and events (§18, CONTENT §8, §11)', () => {
  it('invitations arrive in week 1 of each site’s months, with the chest and archive rumors', () => {
    for (const site of EXPEDITION_SITES) {
      for (const month of site.months) {
        const r = weeklyEvents(gameAt(at(1, month, 1)))
        expect(r.state.mail.some((m) => m.kind === 'expedition' && m.ref === site.id)).toBe(true)
        expect(r.events).toContainEqual({ kind: 'invitation', site: site.id })
        expect(weeklyEvents(gameAt(at(1, month, 2))).state.mail.some((m) => m.kind === 'expedition')).toBe(false)
      }
    }
    const march = weeklyEvents(gameAt(at(1, 3, 1))).state
    expect(march.unlocks.rumorsHeard).toContain('strange-chest')
    expect(march.mail.some((m) => m.kind === 'rumor' && m.ref === 'strange-chest')).toBe(true)
    const june = weeklyEvents(gameAt(at(1, 6, 1))).state
    expect(june.unlocks.rumorsHeard).toEqual(expect.arrayContaining(['blueprint', 'storm-chase']))
    // Heard once: September brings no second chest letter.
    const sept = weeklyEvents({ ...march, week: at(1, 9, 1) }).state
    expect(sept.mail.filter((m) => m.kind === 'rumor' && m.ref === 'strange-chest')).toHaveLength(1)
  })

  it('Ines writes about upgrades every May week 4, and Saltmarsh’s tide-pool rumor rides along', () => {
    const r = weeklyEvents(gameAt(at(1, 5, 4)))
    expect(r.events).toContainEqual({ kind: 'upgradesMail' })
    expect(r.state.mail.some((m) => m.kind === 'upgrades')).toBe(true)
    expect(r.state.unlocks.rumorsHeard).toContain('tide-pool')
    expect(weeklyEvents(gameAt(at(1, 5, 3))).state.mail.some((m) => m.kind === 'upgrades')).toBe(false)
    const next = weeklyEvents({ ...r.state, week: at(2, 5, 4) }).state
    expect(next.mail.filter((m) => m.kind === 'upgrades')).toHaveLength(2)
  })

  it('Basil’s cocoon rumor waits for a year-old Nibblegrub; Ines’s wyrm rumor for a Crown invitation', () => {
    const young = gameAt(at(1, 2, 2), { main: 'nibblegrub' })
    young.monster!.ageWeeks = 47
    expect(weeklyEvents(young).state.unlocks.rumorsHeard).not.toContain('cocoon')
    const old = gameAt(at(1, 2, 2), { main: 'nibblegrub' })
    old.monster!.ageWeeks = 48
    expect(weeklyEvents(old).state.unlocks.rumorsHeard).toContain('cocoon')
    const nobody = gameAt(at(1, 2, 1))
    expect(weeklyEvents(nobody).state.unlocks.rumorsHeard).not.toContain('four-crowns')
    const invited = gameAt(at(1, 2, 1))
    invited.guild.crownInvite = true
    expect(weeklyEvents(invited).state.unlocks.rumorsHeard).toContain('four-crowns')
  })

  it('the masked card needs a grade-B monster, and comes through the controller too', () => {
    const rookie = gameAt(at(1, 9, 1))
    expect(weeklyEvents(rookie).state.unlocks.masqueradeInvited).toBe(false)
    const frozenChamp = gameAt(at(1, 9, 1))
    const champ = makeMonster({ id: 'champ' })
    champ.records.highestGrade = 'B'
    frozenChamp.freezer.push(champ)
    const r = beginWeek(frozenChamp, createRng(1))
    expect(r.state.unlocks.masqueradeInvited).toBe(true)
    expect(r.events.some((e) => e.kind === 'masqueradeMail')).toBe(true)
    expect(r.state.mail.some((m) => m.kind === 'masquerade')).toBe(true)
  })

  it('does nothing on an empty ranch and never uses the RNG', () => {
    const empty = createGameState({ monster: null })
    empty.week = at(1, 3, 1)
    expect(weeklyEvents(empty)).toEqual({ state: empty, events: [] })
    const a = beginWeek(gameAt(at(1, 3, 1)), createRng(9))
    const b = beginWeek(gameAt(at(1, 3, 1)), createRng(9))
    expect(a.state).toEqual(b.state)
  })
})
