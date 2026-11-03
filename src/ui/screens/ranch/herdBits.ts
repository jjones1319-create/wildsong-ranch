import { availability } from '../../../core/aging.ts'
import type { Monster } from '../../../core/monster.ts'
import { isGoodOutcome } from '../../../core/outcomes.ts'
import type { GameState, MateLast, MateOrder } from '../../../core/state.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { DRILL_BY_ID } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { OUTCOME_BANNERS } from '../../../data/text/labels.ts'
import type { DrillId } from '../../../data/types.ts'

/** Small text helpers shared by the herd strip and the herd sheet (v16, GAME_DESIGN §6.11, §21). */

export type BadgeTone = 'good' | 'bad' | 'muted'

export interface MateBadge {
  text: string
  tone: BadgeTone
}

/** What the ranch-mate is doing right now (away or unwell), which wins over last week's badge. */
export function mateStatus(m: Monster): MateBadge | null {
  const a = availability(m)
  if (!a.reason) return null
  return { text: HERD_TEXT.status[a.reason], tone: 'bad' }
}

/** Last week's result as a short badge for a tile. */
export function lastBadge(last: MateLast | null): MateBadge {
  const t = HERD_TEXT.last
  if (!last) return { text: t.none, tone: 'muted' }
  switch (last.kind) {
    case 'drill': {
      const pay = last.pay > 0 ? ` ${fill(t.pay, { n: last.pay })}` : ''
      return { text: `${OUTCOME_BANNERS[last.outcome]}${pay}`, tone: isGoodOutcome(last.outcome) ? 'good' : 'bad' }
    }
    case 'rest':
      return { text: t.rest, tone: 'muted' }
    case 'play':
      return { text: t.play, tone: 'muted' }
    case 'autoRest':
      return { text: t.autoRest[last.reason], tone: 'muted' }
    case 'away':
      return { text: t.away[last.reason], tone: 'bad' }
  }
}

/** The tile's badge: the status now, else last week. */
export function tileBadge(m: Monster, last: MateLast | null): MateBadge {
  return mateStatus(m) ?? lastBadge(last)
}

/** Last week, at full length for the sheet: the drill's name and outcome (and pay), or the badge. */
export function lastLine(last: MateLast | null): string {
  if (last?.kind !== 'drill') return lastBadge(last).text
  const pay = last.pay > 0 ? ` · ${fill(HERD_TEXT.last.pay, { n: last.pay })}` : ''
  return `${fill(HERD_TEXT.last.drill, { drill: DRILL_BY_ID[last.drill]?.name ?? last.drill, outcome: OUTCOME_BANNERS[last.outcome] })}${pay}`
}

export function orderIcon(order: MateOrder): string {
  return HERD_TEXT.orders[order.kind].icon
}

/** "Train · Log Toss", "Rest" or "Play". */
export function orderLabel(order: MateOrder): string {
  const o = HERD_TEXT.orders[order.kind]
  return order.kind === 'drill' ? `${o.label} · ${DRILL_BY_ID[order.drill]?.name ?? order.drill}` : o.label
}

/** The drill a ranch-mate switches to when its order becomes Train: its breed's favourite, if the ranch can run it. */
export function defaultDrill(g: Pick<GameState, 'upgrades'>, m: Monster): DrillId {
  const fav = BREED_BY_ID[m.mainBreed]?.bonusDrill
  const drill = fav ? DRILL_BY_ID[fav] : undefined
  if (drill && (!drill.needsTrainingYard || g.upgrades.trainingYard)) return drill.id
  return 'hill-sprints'
}
