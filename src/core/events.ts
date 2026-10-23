import { EXPEDITION_SITES } from '../data/expeditions.ts'
import { UNLOCKS } from '../data/tuning.ts'
import type { UnlockChain } from '../data/types.ts'
import { dateOf, isMonthStart, isUpgradeOfferWeek } from './calendar.ts'
import { countOf } from './items.ts'
import type { GameState, MailKind } from './state.ts'
import { CHAIN_BREED, cocoonReady, isUnlocked, reachedGrade, reefclawArrival, reefclawDue, startCocoon, stormChaseReady } from './unlocks.ts'
import type { WeekEvent } from './week.ts'

/**
 * GAME_DESIGN §3 step 1 and §18: what the start of a week brings besides food and charms. Invitations and
 * rumors arrive by mail, the Vigil letter follows a farewell, Ines writes about upgrades every May week 4,
 * a storm week may offer the spark, June week 4 may spin the cocoon, and June week 1 may bring the Reefclaw.
 * No randomness here: every trigger is a plain check, so the week's RNG stays in the same order as before.
 */
export function weeklyEvents(input: GameState): { state: GameState; events: WeekEvent[] } {
  const events: WeekEvent[] = []
  const m = input.monster
  if (!m || input.ended) return { state: input, events }
  let state = structuredClone(input)
  const d = dateOf(state.week)
  const monthStart = isMonthStart(state.week)

  const mail = (kind: MailKind, ref: string) => {
    const id = `${state.week}-${kind}-${ref}`
    if (state.mail.some((x) => x.id === id)) return
    state.mail.unshift({ id, week: state.week, kind, ref, read: false })
  }
  const rumor = (chain: UnlockChain) => {
    if (state.unlocks.rumorsHeard.includes(chain) || isUnlocked(state, CHAIN_BREED[chain])) return
    state.unlocks.rumorsHeard.push(chain)
    mail('rumor', chain)
    events.push({ kind: 'rumor', chain })
  }

  // 1. Invitations: week 1 of each site's months. Tomas's letter also starts the chest and archive rumors.
  if (monthStart) {
    for (const site of EXPEDITION_SITES) {
      if (!site.months.includes(d.month)) continue
      mail('expedition', site.id)
      events.push({ kind: 'invitation', site: site.id })
      if (site.id === 'thornwood-ruins') rumor('strange-chest')
      if (site.id === 'sunken-library') rumor('blueprint')
    }
  }

  // 2. Sister Mara's letter, the first week 1 after a farewell (§7, CONTENT §11).
  if (monthStart && state.unlocks.vigilPending) {
    state.unlocks.vigilPending = false
    if (!isUnlocked(state, 'ashwraith') && countOf(state.inventory, 'vigil-lantern') === 0) {
      state.unlocks.vigilOpen = true
      if (!state.unlocks.rumorsHeard.includes('vigil')) state.unlocks.rumorsHeard.push('vigil')
      mail('vigil', String(d.year))
      events.push({ kind: 'vigilMail' })
    }
  }

  // 3. Ranch upgrades: May week 4. Captain Saltmarsh's tide-pool rumor rides along.
  if (isUpgradeOfferWeek(state.week)) {
    mail('upgrades', String(d.year))
    events.push({ kind: 'upgradesMail' })
    rumor('tide-pool')
  }

  // 4. Rumors with their own triggers.
  if (m.mainBreed === 'nibblegrub' && m.ageWeeks >= UNLOCKS.grubRumorAge) rumor('cocoon')
  if (monthStart && d.month === 6) rumor('storm-chase')
  if (monthStart && d.month === UNLOCKS.masquerade.rumorMonth && reachedGrade(state, UNLOCKS.masquerade.grade) && !isUnlocked(state, 'mirrorkin')) {
    rumor('masquerade')
    state.unlocks.masqueradeInvited = true
    mail('masquerade', String(d.year))
    events.push({ kind: 'masqueradeMail' })
  }
  if (monthStart && (state.guild.crownInvite || state.guild.crownsWon.length > 0)) rumor('four-crowns')

  // 5. The storm spark: a yes-or-no card on the ranch.
  if (stormChaseReady(state)) {
    state.pendingEvent = { kind: 'stormChase' }
    events.push({ kind: 'stormSpark' })
  }

  // 6. The cocoon: June week 4, the conditions met.
  if (cocoonReady(state)) {
    state = startCocoon(state)
    events.push({ kind: 'cocoonSpun' })
  }

  // 7. The Reefclaw moves in on June week 1 after the Tide Pool.
  if (reefclawDue(state)) {
    const r = reefclawArrival(state)
    state = r.state
    events.push({ kind: 'reefclaw', placed: r.placed })
    if (r.placed) mail('reefclaw', String(d.year))
  }

  return { state, events }
}
