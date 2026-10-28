import { useEffect, useState } from 'preact/hooks'
import { playSfx } from '../../../../audio/player.ts'
import { keepsakeSvg } from '../../../../art/keepsakes.ts'
import { canBuyKeepsake } from '../../../../core/bond.ts'
import type { Monster } from '../../../../core/monster.ts'
import { KEEPSAKE_BY_ID } from '../../../../data/keepsakes.ts'
import { BONDS_TEXT } from '../../../../data/text/bonds.ts'
import { fill } from '../../../../data/text/format.ts'
import type { KeepsakeId } from '../../../../data/types.ts'
import { Emote } from '../../../components/Emote.tsx'
import { MonsterPortrait } from '../../../components/MonsterPortrait.tsx'
import { gold } from '../../../components/RanchBits.tsx'
import { reduceMotionNow } from '../../../store/fxStore.ts'

const t = BONDS_TEXT.bond.shop
const STROLL_MS = 1800

/**
 * §6.9 the shopping trip: a stroll down Market Lane until the monster stops at a stall, excited, having found a
 * keepsake it loves (chosen from the game's RNG when the trip began). Buy it, or "Not today". The purchase is made
 * by the week (core), so it can't be bought twice or without the gold.
 */
export function ShopTrip({ m, find, money, owned, onDone }: { m: Monster; find: KeepsakeId | null; money: number; owned: readonly KeepsakeId[]; onDone: (buy: KeepsakeId | null) => void }) {
  const [phase, setPhase] = useState<'stroll' | 'found' | 'chosen'>(reduceMotionNow() ? 'found' : 'stroll')
  const [choice, setChoice] = useState<KeepsakeId | null>(null)

  useEffect(() => {
    if (phase !== 'stroll') return
    const timer = setTimeout(() => {
      setPhase('found')
      playSfx('itemGet')
    }, STROLL_MS)
    return () => clearTimeout(timer)
  }, [phase])

  const k = find ? KEEPSAKE_BY_ID[find] : null
  const affordable = find ? canBuyKeepsake(money, owned, find) : false
  const say = (s: string) => fill(s, { name: m.name, they: 'they' })

  return (
    <div class="bondgame">
      <div class={`shop ${phase === 'stroll' ? 'shop--stroll' : ''}`}>
        <div class="shop__stalls" aria-hidden="true">
          <span class="shop__stall shop__stall--a" />
          <span class="shop__stall shop__stall--b" />
          <span class="shop__stall shop__stall--c" />
        </div>
        <div class="shop__mon">
          <MonsterPortrait monster={m} size={110} expression="happy" animate={false} />
          {phase !== 'stroll' && k && <Emote kind="surprise" name={m.name} />}
        </div>
        {phase !== 'stroll' && k && <div class="shop__item" dangerouslySetInnerHTML={{ __html: keepsakeSvg(k.id, k.name) }} />}
      </div>
      {phase === 'stroll' && <p class="echo__status">{say(t.strolling)}</p>}
      {phase !== 'stroll' && !k && <p class="echo__status">{say(t.foundAll)}</p>}
      {phase === 'found' && k && (
        <section class="card shop__card">
          <p class="heading">{say(t.found)}</p>
          <p>
            <b>{k.name}</b> · {gold(k.price)}
          </p>
          <p class="muted small">{k.blurb}</p>
          {!affordable && <p class="muted small">{t.cantAfford}</p>}
          <div class="row">
            <button
              type="button"
              class="btn btn--half"
              onClick={() => {
                setChoice(null)
                setPhase('chosen')
              }}
            >
              {t.notToday}
            </button>
            <button
              type="button"
              class="btn btn--primary btn--half"
              disabled={!affordable}
              onClick={() => {
                playSfx('buy')
                setChoice(k.id)
                setPhase('chosen')
              }}
            >
              {fill(t.buy, { price: gold(k.price) })}
            </button>
          </div>
        </section>
      )}
      {phase === 'chosen' && k && <p class="echo__status">{choice ? fill(t.bought, { item: k.name }) : say(t.skipped)}</p>}
      {(phase === 'chosen' || (phase === 'found' && !k)) && (
        <button type="button" class="btn btn--primary" onClick={() => onDone(choice)}>
          {BONDS_TEXT.bond.done}
        </button>
      )}
    </div>
  )
}
