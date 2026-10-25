import { describe, expect, it } from 'vitest'
import { BREEDS } from '../data/breeds.ts'
import { EVENTS, EVENT_BY_ID } from '../data/calendar.ts'
import { SECRETS } from '../data/secrets.ts'
import { WEATHERS, type TournamentGrade } from '../data/types.ts'
import { migrate, SAVE_VERSION } from '../save/migrate.ts'
import { makeSave, validateSave } from '../save/schema.ts'
import { WEEKS_PER_YEAR, weekIndexOf } from './calendar.ts'
import { busyAt, calendarWeeks, nextUp, pinKey, pinnedEventThisWeek, pinnedItems, planClashes, prunePins, togglePin, type CalendarWeek } from './calendarView.ts'
import { finishWeek } from './game.ts'
import { weeklyReport } from './report.ts'
import { createRng } from './rng.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { entryCheck, eventsForWeek } from './tournament.ts'

const at = (year: number, month: number, week: number) => weekIndexOf({ year, month, week })

function ranch(week: number, o: { grade?: TournamentGrade; age?: number; nature?: number } = {}): GameState {
  const m = makeMonster({ agePct: 20 })
  m.grade = o.grade ?? 'D'
  m.ageWeeks = o.age ?? 60
  m.lifespanTotal = 400
  if (o.nature !== undefined) m.nature = o.nature
  const g = createGameState({ monster: m })
  g.week = week
  g.weekPhase = 'action'
  return g
}

const ids = (w: CalendarWeek) => w.events.map((e) => e.event.id)

describe('calendarWeeks: what each week holds (§3, CONTENT §9)', () => {
  it('a Summit year holds the Qualifier and the Summit; other years the Heatwave and Stargazer Cups', () => {
    const g = ranch(at(4, 1, 1))
    const [jul4] = calendarWeeks(g, at(4, 7, 4), 1)
    const [aug4] = calendarWeeks(g, at(4, 8, 4), 1)
    expect(ids(jul4!)).toEqual(['summit-qualifier'])
    expect(ids(aug4!)).toEqual(['vale-coast-summit'])
    const [jul4n] = calendarWeeks(g, at(5, 7, 4), 1)
    const [aug4n] = calendarWeeks(g, at(5, 8, 4), 1)
    expect(ids(jul4n!)).toEqual(['heatwave'])
    expect(ids(aug4n!)).toEqual(['stargazer'])
    // Four years ahead always reaches the next Summit.
    for (const year of [1, 2, 3, 5, 9]) {
      const s = ranch(at(year, 1, 1))
      const weeks = calendarWeeks(s, s.week, 4 * WEEKS_PER_YEAR)
      expect(weeks.some((w) => ids(w).includes('vale-coast-summit')), `from year ${year}`).toBe(true)
    }
  })

  it('even years hold the Sprout Cup and odd years the Elders’ Cup', () => {
    const g = ranch(at(1, 1, 1))
    expect(ids(calendarWeeks(g, at(2, 6, 2), 1)[0]!)).toEqual(['sprout'])
    expect(ids(calendarWeeks(g, at(3, 6, 2), 1)[0]!)).toEqual(['elders'])
  })

  it('every week of a year holds the events of the cup calendar, with purses and rounds', () => {
    const g = ranch(at(1, 1, 1))
    const weeks = calendarWeeks(g, at(1, 1, 1), WEEKS_PER_YEAR)
    expect(weeks).toHaveLength(48)
    const spring = weeks.find((w) => ids(w).includes('spring-ascension'))!
    const ce = spring.events.find((e) => e.event.id === 'spring-ascension')!
    expect(ce.rounds).toBe(5)
    expect(ce.prize).toBe('wondercake')
    expect(ce.purse).toBeGreaterThan(0)
    expect(weeks.find((w) => ids(w).includes('thaw'))!.events[0]!.rounds).toBe(3)
    expect(weeks.find((w) => ids(w).includes('new-year-open'))!.events[0]!.rounds).toBe(3)
    expect(weeks.find((w) => ids(w).includes('snowdrift'))!.events[0]!.rounds).toBe(2)
  })

  it('invitation-only events say so until the invitation is in hand', () => {
    const g = ranch(at(1, 1, 1), { grade: 'S' })
    const year = calendarWeeks(g, g.week, WEEKS_PER_YEAR).flatMap((w) => w.events)
    for (const id of ['crown-of-dawn', 'crown-of-tides', 'crown-of-embers', 'crown-of-frost', 'wildsong-legend', 'masquerade']) {
      const ce = year.find((e) => e.event.id === id)!
      expect(ce.entry).toEqual({ eligible: false, reason: 'invitation', tooEasy: false })
    }
    g.guild.crownInvite = true
    g.guild.legendInvite = true
    g.unlocks.masqueradeInvited = true
    const invited = calendarWeeks(g, g.week, WEEKS_PER_YEAR).flatMap((w) => w.events)
    for (const id of ['crown-of-dawn', 'wildsong-legend', 'masquerade']) expect(invited.find((e) => e.event.id === id)!.entry.eligible).toBe(true)
  })

  it('for a later week only the knowable rules apply: injury and a Journey are skipped, age is projected', () => {
    const g = ranch(at(1, 1, 1), { grade: 'E', age: 40 })
    g.monster!.status.injuredWeeks = 3
    const thaw = EVENT_BY_ID.thaw!
    expect(entryCheck(g, thaw, g.week)).toMatchObject({ eligible: false, reason: 'injured' })
    expect(entryCheck(g, thaw, at(1, 2, 3))).toMatchObject({ eligible: true })
    // Sprout (age < 48): 40 weeks old today, 85 by June of year 2.
    const sprout = EVENT_BY_ID.sprout!
    expect(entryCheck(g, sprout, at(2, 6, 2))).toMatchObject({ eligible: false, reason: 'rule' })
    const baby = ranch(at(2, 5, 1), { grade: 'E', age: 10 })
    expect(entryCheck(baby, sprout, at(2, 6, 2))).toMatchObject({ eligible: true })
  })

  it('on the current week every answer matches the entry screen, for every event and many monsters', () => {
    const setups: ((g: GameState) => void)[] = [
      () => undefined,
      (g) => (g.monster!.grade = 'E'),
      (g) => (g.monster!.grade = 'C'),
      (g) => {
        g.monster!.grade = 'S'
        g.guild.crownInvite = true
        g.guild.legendInvite = true
      },
      (g) => (g.monster!.status.injuredWeeks = 2),
      (g) => (g.monster!.status.sickWeeks = 1),
      (g) => (g.monster!.nature = 40),
      (g) => (g.monster!.nature = -40),
      (g) => (g.monster!.ageWeeks = 300),
      (g) => (g.monster!.ageWeeks = 20),
      (g) => (g.unlocks.masqueradeInvited = true),
    ]
    let checked = 0
    for (const setup of setups) {
      for (let w = 0; w < 4 * WEEKS_PER_YEAR; w++) {
        const g = ranch(w)
        setup(g)
        const screen = eventsForWeek(g)
        const [week] = calendarWeeks(g, g.week, 1)
        for (const ce of week!.events) {
          const v = screen.find((x) => x.event.id === ce.event.id)!
          expect({ eligible: ce.entry.eligible, reason: ce.entry.reason, tooEasy: ce.entry.tooEasy }, `${ce.event.id} week ${w}`).toEqual({ eligible: v.eligible, reason: v.reason, tooEasy: v.tooEasy })
          checked += 1
        }
        expect(week!.events.map((e) => e.event.id).sort()).toEqual(screen.map((v) => v.event.id).sort())
      }
    }
    expect(checked).toBeGreaterThan(EVENTS.length * setups.length)
  })
})

describe('secrets and weather stay out of the calendar', () => {
  const locked = BREEDS.filter((b) => b.availability === 'locked').map((b) => b.id)

  function text(weeks: CalendarWeek[]): string {
    // Everything the screen can show: event ids, notes, expedition sites, busy marks.
    return JSON.stringify(weeks.map((w) => ({ e: w.events.map((x) => x.event.id), n: w.notes, x: w.expeditions.map((s) => s.site.id), b: w.busy })))
  }

  it('shows no locked breed, cocoon, Reefclaw or secret variant before the save records it', () => {
    const g = ranch(at(1, 1, 1))
    g.monster!.mainBreed = 'nibblegrub'
    const out = text(calendarWeeks(g, g.week, 5 * WEEKS_PER_YEAR))
    for (const id of locked) expect(out, id).not.toContain(id)
    expect(out).not.toMatch(/cocoon|reefclaw|storm|vigil|chest/i)
    for (const s of SECRETS) expect(out).not.toContain(s.adjective)
    for (const w of WEATHERS) expect(out).not.toContain(`"${w}"`)
    const keys = new Set(calendarWeeks(g, g.week, 2).flatMap((w) => Object.keys(w)))
    expect([...keys].some((k) => /weather/i.test(k))).toBe(false)
  })

  it('a discovered Reefclaw joins the summer Market note', () => {
    const g = ranch(at(1, 1, 1))
    const summer = (s: GameState) => calendarWeeks(s, at(1, 6, 1), 1)[0]!.notes.find((n) => n.kind === 'market')
    expect(summer(g)).toBeDefined()
    expect(JSON.stringify(summer(g))).not.toContain('reefclaw')
    g.unlocked = [...g.unlocked, 'reefclaw']
    expect(JSON.stringify(summer(g))).toContain('reefclaw')
  })
})

describe('dated notes', () => {
  it('birthdays fall every 48 weeks of age, on the week the age ticks over', () => {
    const g = ranch(at(1, 1, 1), { age: 40 })
    const weeks = calendarWeeks(g, g.week, 120)
    const birthdays = weeks.filter((w) => w.notes.some((n) => n.kind === 'birthday'))
    expect(birthdays.map((w) => w.offset)).toEqual([7, 55, 103])
    expect(birthdays[1]!.notes.find((n) => n.kind === 'birthday')).toEqual({ kind: 'birthday', years: 2 })
  })

  it('the Market turns over each season, the upgrade letter comes in May week 4', () => {
    const g = ranch(at(1, 1, 1))
    const weeks = calendarWeeks(g, g.week, WEEKS_PER_YEAR)
    expect(weeks.filter((w) => w.notes.some((n) => n.kind === 'market')).map((w) => w.date.month)).toEqual([3, 6, 9, 12])
    expect(weeks.filter((w) => w.notes.some((n) => n.kind === 'upgrades')).map((w) => [w.date.month, w.date.week])).toEqual([[5, 4]])
  })

  it('a Crown note a month ahead only for an S monster; the Legend note in March once all four Crowns are won', () => {
    const d = ranch(at(1, 1, 1), { grade: 'A' })
    expect(calendarWeeks(d, d.week, WEEKS_PER_YEAR).some((w) => w.notes.some((n) => n.kind === 'crown'))).toBe(false)
    const s = ranch(at(1, 1, 1), { grade: 'S' })
    const crownNotes = calendarWeeks(s, s.week, WEEKS_PER_YEAR).filter((w) => w.notes.some((n) => n.kind === 'crown'))
    expect(crownNotes.map((w) => w.week + 4)).toEqual(EVENTS.filter((e) => e.kind === 'crown').map((e) => e.week))
    expect(crownNotes[0]!.notes.find((n) => n.kind === 'crown')).toMatchObject({ invited: false })
    s.guild.legendInvite = true
    const legend = calendarWeeks(s, s.week, WEEKS_PER_YEAR).filter((w) => w.notes.some((n) => n.kind === 'legend'))
    expect(legend.map((w) => [w.date.month, w.date.week])).toEqual([[3, 1]])
  })

  it('expeditions are listed in their months with today’s requirement check', () => {
    const g = ranch(at(1, 1, 1), { grade: 'E' })
    g.monster!.fame = 10
    const march = calendarWeeks(g, at(1, 3, 1), 4)
    expect(march.every((w) => w.expeditions.some((x) => x.site.id === 'thornwood-ruins'))).toBe(true)
    expect(march[0]!.expeditions[0]!).toMatchObject({ opens: true, block: 'fame', key: pinKey(at(1, 3, 1), 'thornwood-ruins') })
    expect(march[2]!.expeditions[0]!).toMatchObject({ opens: false, key: pinKey(at(1, 3, 1), 'thornwood-ruins') })
    g.monster!.fame = 30
    expect(calendarWeeks(g, at(1, 3, 1), 1)[0]!.expeditions[0]!.block).toBeNull()
    expect(calendarWeeks(g, at(1, 6, 1), 1)[0]!.expeditions[0]!).toMatchObject({ block: 'grade' })
  })
})

describe('busy weeks and the plan', () => {
  it('marks the planned weeks, a Journey, injury and sickness', () => {
    const g = ranch(at(1, 1, 1))
    g.planner.queue = [{ kind: 'drill', drill: 'log-toss' }, { kind: 'rest' }]
    expect(busyAt(g, g.week)).toMatchObject({ kind: 'plan', index: 0 })
    expect(busyAt(g, g.week + 1)).toMatchObject({ kind: 'plan', step: { kind: 'rest' } })
    expect(busyAt(g, g.week + 2)).toBeNull()
    const j = ranch(at(1, 1, 1))
    j.journey = { site: 'iron-quarry', weekNo: 2, successes: 0, learned: null, pendingTechnique: null, gains: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }, elderMentor: false }
    expect([0, 1, 2, 3].map((o) => busyAt(j, j.week + o)?.kind ?? null)).toEqual(['journey', 'journey', 'journey', null])
    const hurt = ranch(at(1, 1, 1))
    hurt.monster!.status.injuredWeeks = 2
    expect([0, 1, 2].map((o) => busyAt(hurt, hurt.week + o)?.kind ?? null)).toEqual(['injured', 'injured', null])
  })

  it('warns when the plan runs through a notable event the monster can enter, not an ordinary cup', () => {
    const g = ranch(at(1, 3, 2), { grade: 'D' })
    g.planner.queue = [{ kind: 'rest' }, { kind: 'drill', drill: 'log-toss' }, { kind: 'drill', drill: 'log-toss' }]
    const clashes = planClashes(g)
    expect(clashes.map((c) => c.event.id)).toEqual(['spring-ascension'])
    const w = calendarWeeks(g, at(1, 3, 4), 1)[0]!
    expect(w.clashes.map((c) => c.event.id)).toEqual(['spring-ascension'])
    // Two weeks of plan stop short of it; and an ordinary cup on a planned week is no clash.
    g.planner.queue = g.planner.queue.slice(0, 2)
    expect(planClashes(g)).toEqual([])
    // A pinned ordinary cup on a planned week is.
    const c = ranch(at(1, 3, 2), { grade: 'B' })
    c.planner.queue = [{ kind: 'rest' }]
    const withPin = togglePin(c, pinKey(at(1, 3, 2), 'meadow'))
    expect(planClashes(withPin).map((x) => x.event.id)).toEqual(['meadow'])
  })
})

describe('★ reminders', () => {
  it('toggle on and off, never for a week already gone', () => {
    const g = ranch(at(1, 3, 1))
    const key = pinKey(at(1, 3, 4), 'spring-ascension')
    const on = togglePin(g, key)
    expect(on.calendarPins).toEqual([key])
    expect(togglePin(on, key).calendarPins).toEqual([])
    expect(togglePin(g, pinKey(at(1, 2, 1), 'ice-lantern')).calendarPins).toEqual([])
    expect(togglePin(g, 'nonsense').calendarPins).toEqual([])
  })

  it('past pins clean themselves up at the end of the week; an expedition pin lasts its month', () => {
    const g = ranch(at(1, 3, 1), { grade: 'E' })
    let s = togglePin(g, pinKey(at(1, 3, 1), 'bud'))
    s = togglePin(s, pinKey(at(1, 3, 4), 'spring-ascension'))
    s = togglePin(s, pinKey(at(1, 3, 1), 'thornwood-ruins'))
    expect(s.calendarPins).toHaveLength(3)
    const next = finishWeek(s, createRng(1)).state
    expect(next.week).toBe(at(1, 3, 2))
    expect(next.calendarPins).toEqual([pinKey(at(1, 3, 4), 'spring-ascension'), pinKey(at(1, 3, 1), 'thornwood-ruins')])
    expect(prunePins(next.calendarPins, at(1, 4, 1))).toEqual([])
    expect(prunePins(['garbage', '12:'], 0)).toEqual([])
  })

  it('Wren mentions a pinned cup the week before and on the week, and the Battle button gets its dot', () => {
    const g = togglePin(ranch(at(1, 3, 3), { grade: 'D' }), pinKey(at(1, 3, 4), 'spring-ascension'))
    expect(weeklyReport(g).some((l) => l.text.includes('Next week is the Spring Ascension'))).toBe(true)
    expect(pinnedEventThisWeek(g)).toBe(false)
    const on = { ...g, week: at(1, 3, 4) }
    expect(weeklyReport(on).some((l) => l.text.includes('The Spring Ascension is this week'))).toBe(true)
    expect(pinnedEventThisWeek(on)).toBe(true)
    const trip = togglePin(ranch(at(1, 2, 4), { grade: 'D' }), pinKey(at(1, 3, 1), 'thornwood-ruins'))
    expect(weeklyReport(trip).some((l) => l.text.includes('Thornwood Ruins trip opens next week'))).toBe(true)
    expect(pinnedItems(trip)[0]).toMatchObject({ kind: 'expedition', name: 'Thornwood Ruins' })
  })

  it('migrates a v9 save with an empty list, and survives a save and a load', () => {
    const g = togglePin(ranch(at(1, 3, 1)), pinKey(at(1, 3, 4), 'spring-ascension'))
    const raw = JSON.parse(JSON.stringify(makeSave(g, 3))) as { schemaVersion: number; game: Record<string, unknown> }
    const loaded = validateSave(raw)
    expect(loaded.ok && loaded.save.game.calendarPins).toEqual([pinKey(at(1, 3, 4), 'spring-ascension')])
    delete raw.game.calendarPins
    raw.schemaVersion = 9
    const up = migrate(JSON.parse(JSON.stringify(raw))) as { schemaVersion: number; game: Record<string, unknown> }
    expect(up.schemaVersion).toBe(SAVE_VERSION)
    expect(up.game.calendarPins).toEqual([])
    const r = validateSave(up)
    expect(r.ok && r.save.game.calendarPins).toEqual([])
    // Garbage is dropped, never fatal.
    const bad = JSON.parse(JSON.stringify(makeSave(g, 3))) as { game: Record<string, unknown> }
    bad.game.calendarPins = ['11:spring-ascension', 42, 'nope', '11:spring-ascension', '<script>']
    const rb = validateSave(bad)
    expect(rb.ok && rb.save.game.calendarPins).toEqual(['11:spring-ascension'])
    bad.game.calendarPins = 'all of them'
    const rc = validateSave(bad)
    expect(rc.ok && rc.save.game.calendarPins).toEqual([])
  })
})

describe('the date bar’s "Next:" line', () => {
  it('names the next notable event the monster can enter, or a sooner pin', () => {
    const g = ranch(at(1, 3, 1), { grade: 'D' })
    expect(nextUp(g)).toMatchObject({ name: 'Spring Ascension', inWeeks: 3, pinned: false })
    const pinned = togglePin(g, pinKey(at(1, 3, 1), 'bud'))
    expect(nextUp(pinned)).toMatchObject({ name: 'Bud Cup', inWeeks: 0, pinned: true })
    const later = togglePin(g, pinKey(at(1, 6, 1), 'sunny'))
    expect(nextUp(later)).toMatchObject({ name: 'Spring Ascension', pinned: false })
    expect(nextUp({ ...g, monster: null })).toBeNull()
  })
})
