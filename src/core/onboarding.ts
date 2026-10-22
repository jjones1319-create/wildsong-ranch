import { fill } from '../data/text/format.ts'
import { WREN } from '../data/text/wren.ts'
import { ONBOARDING, REPORT } from '../data/tuning.ts'
import type { AgingEvent } from './aging.ts'
import { wrenVars } from './report.ts'
import type { GameState } from './state.ts'

/**
 * GAME_DESIGN §21 onboarding: Wren guides the first in-game month (first drill, praise/scold, rest, food,
 * the Monster Card), then one-time contextual tips. Each tip is shown once per save (`tipsSeen`).
 */

export const TIP_IDS = ['welcome', 'firstFood', 'firstDrill', 'praiseScold', 'firstRest', 'openCard', 'firstRequest', 'bag', 'songbook', 'repeat', 'prime', 'breakdown'] as const
export type TipId = (typeof TIP_IDS)[number]

export type TipContext =
  | { screen: 'ranch' }
  | { screen: 'food' }
  | { screen: 'request' }
  | { screen: 'result' }
  | { screen: 'card' }
  | { screen: 'summary'; events: readonly AgingEvent[] }

/** The next tip to show on this screen, or null. Tips are checked in the order a new player meets them. */
export function nextTip(state: GameState, ctx: TipContext): TipId | null {
  const m = state.monster
  if (!m || state.ended) return null
  const seen = (id: TipId) => state.tipsSeen.includes(id)
  const guided = state.week < ONBOARDING.guidedWeeks
  const c = state.counters

  switch (ctx.screen) {
    case 'food':
      return !seen('firstFood') ? 'firstFood' : null
    case 'request':
      return !seen('firstRequest') ? 'firstRequest' : null
    case 'result':
      return c.drillsDone >= 1 && !seen('praiseScold') ? 'praiseScold' : null
    case 'card':
      return state.songbook.length > 0 && !seen('songbook') ? 'songbook' : null
    case 'summary': {
      if (ctx.events.some((e) => e.kind === 'prime') && !seen('prime')) return 'prime'
      if (ctx.events.some((e) => e.kind === 'breakdown') && !seen('breakdown')) return 'breakdown'
      return null
    }
    case 'ranch': {
      if (state.pendingRequest) return null
      if (!seen('welcome')) return 'welcome'
      // Every other ranch tip waits for the week to begin, so the monthly food prompt is never hidden behind a tip.
      if (state.weekPhase !== 'action') return null
      if (!seen('firstDrill') && c.drillsDone === 0) return 'firstDrill'
      if (!seen('firstRest') && c.drillsDone >= 1 && c.restsTaken === 0 && m.fatigue >= REPORT.fresh.fatigueMax + 1) return 'firstRest'
      if (!seen('openCard') && c.drillsDone >= 1) return 'openCard'
      if (!seen('bag') && !guided && Object.keys(state.inventory).length === 0 && c.drillsDone >= 2) return 'bag'
      if (!seen('repeat') && state.lastAction !== null && c.drillsDone >= 3) return 'repeat'
      return null
    }
  }
}

/** The tip's text with the names filled in. */
export function tipText(state: GameState, id: TipId): string {
  const m = state.monster
  const name = m?.name ?? ''
  return fill(WREN.tips[id], wrenVars({ name }, { ranch: state.breeder.ranchName, breeder: state.breeder.name }))
}

export function markTipSeen(input: GameState, id: TipId): GameState {
  if (input.tipsSeen.includes(id)) return input
  const state = structuredClone(input)
  state.tipsSeen = [...state.tipsSeen, id]
  return state
}
