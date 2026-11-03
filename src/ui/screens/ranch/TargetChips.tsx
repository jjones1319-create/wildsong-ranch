import { useState } from 'preact/hooks'
import type { Monster } from '../../../core/monster.ts'
import type { GameState } from '../../../core/state.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { Chips } from '../../components/Controls.tsx'
import { cardId } from '../../store/herdStore.ts'

/** Who the Bag or the Songbook is aimed at: the star, or a ranch-mate by id (v16). */
export interface Target {
  monster: Monster
  /** Undefined for the star, so the core's default applies. */
  id: string | undefined
}

/**
 * The target the Bag and the Songbook start on: the monster the Card was showing, else the star. A ranch-mate that
 * has left (freed, frozen, made the star) falls back to the star.
 */
export function useTarget(g: GameState | null): [Target | null, (id: string) => void] {
  const [picked, setPicked] = useState<string | null>(() => cardId.value)
  if (!g?.monster) return [null, setPicked]
  const mate = picked ? g.ranchmates.find((r) => r.monster.id === picked) : undefined
  return [mate ? { monster: mate.monster, id: mate.monster.id } : { monster: g.monster, id: undefined }, setPicked]
}

/** The "For: ⭐ star · mates" chips row; hidden while there are no ranch-mates. */
export function TargetChips({ g, target, onPick }: { g: GameState; target: Target; onPick: (id: string) => void }) {
  if (!g.monster || g.ranchmates.length === 0) return null
  const t = HERD_TEXT.target
  const options = [{ value: g.monster.id, label: fill(t.star, { name: g.monster.name }) }, ...g.ranchmates.map((r) => ({ value: r.monster.id, label: r.monster.name }))]
  return (
    <div class="target">
      <span class="field__label">{t.label}</span>
      <Chips options={options} value={target.monster.id} onChange={onPick} label={t.label} />
    </div>
  )
}
