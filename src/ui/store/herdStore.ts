import { effect, signal } from '@preact/signals'
import {
  freeMonster as freeMonsterCore,
  freezerToPen as freezerToPenCore,
  makeStar as makeStarCore,
  penToFreezer as penToFreezerCore,
  replaceRanchmate as replaceRanchmateCore,
  setOrder as setOrderCore,
  type FreeRefusal,
  type MoveRefusal,
  type OrderRefusal,
  type StarRefusal,
} from '../../core/herd.ts'
import { dismissHomecoming as dismissHomecomingCore } from '../../core/homecoming.ts'
import type { Monster } from '../../core/monster.ts'
import type { MateOrder } from '../../core/state.ts'
import { now } from '../lib/clock.ts'
import { screen, type Screen } from '../router.ts'
import { commit, game, weekNews } from './gameStore.ts'

/**
 * v16 the herd (GAME_DESIGN §6.11): the store actions behind the herd strip, the herd sheet, the Freezer's
 * "Move to a pen" and the homecoming card. Each wraps a pure core move (`game.value` → core → `commit`) and returns
 * the refusal, if any, for a toast.
 */

/** The monster the Monster Card shows (and the Bag and Songbook aim at by default); null means the star. */
export const cardId = signal<string | null>(null)

/** The card's own screens: leaving them for anywhere else forgets the choice, so the next card is the star's. */
const CARD_SCREENS: readonly Screen[] = ['ranchCard', 'bag', 'songbook', 'labEdit']
effect(() => {
  if (!CARD_SCREENS.includes(screen.value)) cardId.value = null
})

/** ⭐ Make star: the ranch-mate and the star swap places (or it steps onto an empty ranch). */
export function makeStar(id: string): StarRefusal | null {
  const g = game.value
  if (!g) return 'notFound'
  const r = makeStarCore(g, id)
  if (!r.refused) {
    // Wren's news this week was about the old star.
    weekNews.value = []
    commit(r.state)
  }
  return r.refused
}

export function setOrder(id: string, order: MateOrder): OrderRefusal | null {
  const g = game.value
  if (!g) return 'notFound'
  const r = setOrderCore(g, id, order)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function penToFreezer(id: string): MoveRefusal | null {
  const g = game.value
  if (!g) return 'notFound'
  const r = penToFreezerCore(g, id)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function freezerToPen(id: string): MoveRefusal | null {
  const g = game.value
  if (!g) return 'notFound'
  const r = freezerToPenCore(g, id)
  if (!r.refused) commit(r.state)
  return r.refused
}

/** 🕊️ Set free (a ranch-mate or a frozen monster). Keeping a Library copy is the caller's, before this. */
export function freeMonster(id: string): FreeRefusal | null {
  const g = game.value
  if (!g) return 'notFound'
  const r = freeMonsterCore(g, id)
  if (!r.refused) commit(r.state)
  return r.refused
}

/** §19 the Lab editor saved a ranch-mate. */
export function replaceRanchmate(edited: Monster): void {
  const g = game.value
  if (!g) return
  const next = replaceRanchmateCore(g, edited, now())
  if (next !== g) commit(next)
}

/** The homecoming card was closed ("Welcome home!"). */
export function dismissHomecoming(): void {
  const g = game.value
  if (!g) return
  const next = dismissHomecomingCore(g)
  if (next !== g) commit(next)
}
