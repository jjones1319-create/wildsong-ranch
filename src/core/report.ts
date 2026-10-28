import { BREED_BY_ID } from '../data/breeds.ts'
import { EXPEDITION_SITE_BY_ID } from '../data/expeditions.ts'
import { FOOD_BY_ID } from '../data/foods.ts'
import { KEEPSAKE_BY_ID } from '../data/keepsakes.ts'
import { JOURNEY_SITE_BY_ID } from '../data/journeys.ts'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { fill } from '../data/text/format.ts'
import { WREN } from '../data/text/wren.ts'
import { REPORT } from '../data/tuning.ts'
import { availability, type AgingEvent } from './aging.ts'
import { pinnedItems } from './calendarView.ts'
import type { Monster } from './monster.ts'
import type { GameState } from './state.ts'
import type { DrillResult } from './training.ts'
import type { WeekEvent } from './week.ts'

/**
 * What Wren says (CONTENT §15): pure text selection from the state and the week's events. The UI only
 * displays these lines. Monsters have no gender in Wildsong, so Wren always says "they".
 */

export interface WrenLine {
  key: string
  text: string
}

export function wrenVars(m: Pick<Monster, 'name'>, extra: Record<string, string | number> = {}): Record<string, string | number> {
  return { name: m.name, them: 'them', their: 'their', they: 'they', ...extra }
}

export function say(key: keyof typeof WREN | string, template: string, m: Pick<Monster, 'name'>, extra: Record<string, string | number> = {}): WrenLine {
  return { key: String(key), text: fill(template, wrenVars(m, extra)) }
}

/** The ranch bubble: how the monster is this week, plus its request if it made one. */
export function weeklyReport(state: GameState): WrenLine[] {
  const m = state.monster
  if (!m) return []
  const lines: WrenLine[] = []
  const away = availability(m)
  if (away.reason === 'missing') lines.push(say('missingWeek', WREN.missingWeek, m))
  else if (away.reason === 'clinic') lines.push(say('clinicWeek', WREN.clinicWeek, m))
  else if (away.reason === 'cocoon') lines.push(say('cocoonWeek', WREN.cocoonWeek, m))
  else if (state.expedition?.ended) lines.push(say('expeditionWeek', WREN.expeditionWeek, m, { week: state.expedition.weekNo }))
  else if (away.reason === 'sick') lines.push(say('sickWeek', WREN.sickWeek, m))
  else if (away.reason === 'injured') lines.push(say('injuredWeek', WREN.injuredWeek, m))
  else if (m.fatigue >= REPORT.exhaustedFatigue) lines.push(say('weeklyExhausted', WREN.weeklyExhausted, m))
  else if (m.fatigue >= REPORT.tiredFatigue) lines.push(say('weeklyTired', WREN.weeklyTired, m))
  else if (m.stress >= REPORT.stressed) lines.push(say('stressed', WREN.stressed, m))
  else if (m.fatigue <= REPORT.fresh.fatigueMax && m.stress <= REPORT.fresh.stressMax) lines.push(say('weeklyFresh', WREN.weeklyFresh, m))
  else lines.push(say('weeklyFine', WREN.weeklyFine, m))
  if (!away.locked && m.stress >= REPORT.stressed && m.fatigue >= REPORT.tiredFatigue) lines.push(say('stressed', WREN.stressed, m))

  const r = state.pendingRequest
  if (r) lines.push(r.kind === 'rest' ? say('requestRest', WREN.requestRest, m) : r.kind === 'play' ? say('requestPlay', WREN.requestPlay, m) : say('requestTreat', WREN.requestTreat, m))
  lines.push(...pinLines(state))
  return dedupe(lines)
}

/** §3 the calendar's ★ reminders: Wren mentions a pinned cup the week before and on the week, a pinned trip the week before its month and while it's open. */
export function pinLines(state: GameState): WrenLine[] {
  const m = state.monster
  if (!m) return []
  const lines: WrenLine[] = []
  for (const p of pinnedItems(state)) {
    const ahead = p.week - state.week
    if (p.kind === 'event') {
      if (ahead === 0) lines.push(say(`pinThisWeek-${p.key}`, WREN.pinThisWeek, m, { event: p.name }))
      else if (ahead === 1) lines.push(say(`pinNextWeek-${p.key}`, WREN.pinNextWeek, m, { event: p.name }))
    } else if (ahead === 1) lines.push(say(`pinTripNextWeek-${p.key}`, WREN.pinTripNextWeek, m, { trip: p.name }))
    else if (ahead <= 0) lines.push(say(`pinTripThisMonth-${p.key}`, WREN.pinTripThisMonth, m, { trip: p.name }))
  }
  return lines
}

/** Wren's one line about a drill result (the banner's caption). */
export function drillLine(m: Monster, result: DrillResult): WrenLine {
  switch (result.outcome) {
    case 'Perfect':
      return say('perfectDrill', WREN.perfectDrill, m)
    case 'Superb':
      return say('superbDrill', WREN.superbDrill, m)
    case 'Great':
      return say('greatDrill', WREN.greatDrill, m)
    case 'Good':
      return say('goodDrill', WREN.goodDrill, m)
    case 'Success':
      return say('successDrill', WREN.successDrill, m)
    case 'Cheat':
      return say('cheat', WREN.cheat, m)
    case 'Fail':
      return say('failDrill', WREN.failDrill, m)
    case 'Slacked':
      return say('slacked', WREN.slacked, m)
  }
}

/** Does the breed change its look at Prime (§22 growth forms)? */
export function growsUpAtPrime(m: Pick<Monster, 'mainBreed'>): boolean {
  return BREED_BY_ID[m.mainBreed].art.grown !== undefined
}

function agingLine(m: Monster, e: AgingEvent): WrenLine[] {
  switch (e.kind) {
    case 'prime':
      return growsUpAtPrime(m) ? [say('grewUp', WREN.grewUp, m), say('prime', WREN.prime, m)] : [say('prime', WREN.prime, m)]
    case 'pastPrime':
      return [say('pastPrime', WREN.pastPrime, m)]
    case 'warning':
      return [e.which === 'quarterLife' ? say('quarterLifeLeft', WREN.quarterLifeLeft, m) : e.which === 'w48' ? say('fortyEightWeeksLeft', WREN.fortyEightWeeksLeft, m) : say('tenWeeksLeft', WREN.tenWeeksLeft, m)]
    case 'breakdown':
      return [e.type === 'runAway' ? say('breakdownRunAway', WREN.breakdownRunAway, m) : say('breakdownCollapse', WREN.breakdownCollapse, m), say('breakdownAdvice', WREN.breakdownAdvice, m)]
    case 'illness':
      return [say('sick', WREN.sick, m)]
    case 'returned':
      return [
        e.from === 'missing'
          ? say('returnedMissing', WREN.returnedMissing, m)
          : e.from === 'clinic'
            ? say('returnedClinic', WREN.returnedClinic, m)
            : e.from === 'sick'
              ? say('recovered', WREN.recovered, m)
              : e.from === 'injured'
                ? say('healed', WREN.healed, m)
                : say('returnedClinic', WREN.returnedClinic, m),
      ]
    case 'endOfLife':
      return [e.how === 'retired' ? say('retire', WREN.retire, m) : say('farewell', WREN.farewell, m)]
    case 'birthday':
      return [say('birthday', WREN.birthday, m)]
  }
}

/** Everything worth telling the player from a week's events, in order. Drill results have their own screen. */
export function eventLines(events: readonly WeekEvent[], m: Monster): WrenLine[] {
  const lines: WrenLine[] = []
  for (const e of events) {
    switch (e.kind) {
      case 'food': {
        const food = FOOD_BY_ID[e.food].name
        if (e.bored) lines.push(say('bored', WREN.bored, m, { food }))
        else if (e.relation === 'liked') lines.push(say('likedFood', WREN.likedFood, m, { food }))
        else if (e.relation === 'disliked') lines.push(say('dislikedFood', WREN.dislikedFood, m, { food }))
        break
      }
      case 'rest':
        lines.push(say('rested', WREN.rested, m))
        break
      case 'play':
        lines.push(say('played', WREN.played, m))
        break
      case 'bondWeek':
        if (e.activity === 'fetch') lines.push(say('bondFetch', WREN.bondFetch, m, { n: e.score }))
        else if (e.activity === 'hide') lines.push(say('bondHide', WREN.bondHide, m, { n: e.score }))
        else lines.push(say('bondShop', WREN.bondShop, m))
        if (e.bought) lines.push(say('bondBought', WREN.bondBought, m, { item: KEEPSAKE_BY_ID[e.bought].name }))
        lines.push(say('bondBoost', WREN.bondBoost, m))
        break
      case 'keepsakes':
        lines.push(say('keepsakesCalm', WREN.keepsakesCalm, m))
        break
      case 'requestDenied':
        lines.push(say('denied', WREN.denied, m))
        break
      case 'item':
        if (e.itemId === m.likes.toy) lines.push(say('treat', WREN.treat, m))
        break
      case 'aging':
        lines.push(...agingLine(m, e.event))
        break
      case 'signature':
        lines.push(say('signature', WREN.signature, m, { technique: TECHNIQUE_BY_ID[e.tech]?.name ?? e.tech }))
        break
      case 'bond':
        lines.push(say('bond', WREN.mentorBond, m, { mentor: JOURNEY_SITE_BY_ID[e.site].mentor }))
        break
      case 'sale':
        lines.push(say('sale', WREN.saleMonth, m))
        break
      case 'journeyStart':
        lines.push(say('journeyStart', WREN.journeyStart, m, { site: JOURNEY_SITE_BY_ID[e.site].name, mentor: JOURNEY_SITE_BY_ID[e.site].mentor }))
        break
      case 'journeyWeek':
        lines.push(say(e.result.success ? 'journeyGood' : 'journeyBad', e.result.success ? WREN.journeyGood : WREN.journeyBad, m, { week: e.result.week }))
        if (e.result.technique) lines.push(say('journeyLearned', WREN.journeyLearned, m, { technique: TECHNIQUE_BY_ID[e.result.technique]?.name ?? e.result.technique }))
        break
      case 'journeyDone':
        lines.push(say('journeyDone', WREN.journeyDone, m))
        break
      case 'elderMentor':
        lines.push(say('elderMentor', WREN.elderMentor, m, { elder: e.elder }))
        break
      /* M7 */
      case 'invitation':
        lines.push(say('invitation', WREN.invitation, m, { site: EXPEDITION_SITE_BY_ID[e.site].name }))
        break
      case 'rumor':
        lines.push(say('rumor', WREN.rumor, m))
        break
      case 'vigilMail':
        lines.push(say('vigilMail', WREN.vigilMail, m))
        break
      case 'upgradesMail':
        lines.push(say('upgradesMail', WREN.upgradesMail, m))
        break
      case 'masqueradeMail':
        lines.push(say('masqueradeMail', WREN.masqueradeMail, m))
        break
      case 'stormSpark':
        lines.push(say('stormSpark', WREN.stormSpark, m))
        break
      case 'stormChase':
        lines.push(say('stormChase', WREN.stormChase, m))
        break
      case 'cocoonSpun':
        lines.push(say('cocoonSpun', WREN.cocoonSpun, m))
        break
      case 'emerged':
        lines.push(say('emerged', WREN.emerged, m, { breed: BREED_BY_ID[e.breed].name }))
        break
      case 'reefclaw':
        lines.push(e.placed ? say('reefclaw', WREN.reefclaw, m) : say('reefclawNoRoom', WREN.reefclawNoRoom, m))
        break
      case 'expeditionStart':
        lines.push(say('expeditionStart', WREN.expeditionStart, m, { site: EXPEDITION_SITE_BY_ID[e.site].name }))
        break
      case 'expeditionWeek':
        lines.push(say('expeditionWeek', WREN.expeditionWeek, m, { week: e.weekNo }))
        break
      case 'expeditionHome':
        lines.push(say('expeditionHome', WREN.expeditionHome, m, { site: EXPEDITION_SITE_BY_ID[e.site].name }))
        break
      case 'titles':
        for (const title of e.titles) lines.push({ key: `title-${title}`, text: fill(WREN.newTitle, wrenVars(m, { title })) })
        break
      default:
        break
    }
  }
  return dedupe(lines)
}

export function learnedLine(m: Monster, techId: string): WrenLine {
  return say('learnedFromSheet', WREN.learnedFromSheet, m, { technique: TECHNIQUE_BY_ID[techId]?.name ?? techId })
}

export function forgotLine(m: Monster, techId: string): WrenLine {
  return say('forgot', WREN.forgot, m, { technique: TECHNIQUE_BY_ID[techId]?.name ?? techId })
}

/** Wren never nags twice in a row: the same key is kept once. */
function dedupe(lines: WrenLine[]): WrenLine[] {
  const seen = new Set<string>()
  return lines.filter((l) => (seen.has(l.key) ? false : (seen.add(l.key), true)))
}
