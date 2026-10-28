import { useState } from 'preact/hooks'
import type { Monster } from '../../../../core/monster.ts'
import { BONDS_TEXT } from '../../../../data/text/bonds.ts'
import { fill } from '../../../../data/text/format.ts'
import { BOND } from '../../../../data/tuning.ts'
import { cancelBond, finishBond, game, type BondFlow } from '../../../store/gameStore.ts'
import { Fetch } from './Fetch.tsx'
import { HideSeek } from './HideSeek.tsx'
import { ShopTrip } from './ShopTrip.tsx'

const t = BONDS_TEXT.bond

/**
 * §6.9 a Bond week's game, full screen over the ranch. A game's score (or the shopping trip's purchase) becomes the
 * week's action when the player finishes; backing out before the end leaves the week untouched.
 */
export function BondGame({ f, m, money }: { f: BondFlow; m: Monster; money: number }) {
  const [score, setScore] = useState<number | null>(null)
  const a = t.activities[f.activity]
  const owned = game.value?.keepsakes ?? []

  return (
    <div class="overlay bond" role="dialog" aria-label={a.name}>
      <div class="overlay__inner">
        <h2 class="arrival__title">
          {a.icon} {a.name}
        </h2>
        {f.activity === 'fetch' && score === null && <Fetch m={m} onDone={setScore} />}
        {f.activity === 'hide' && score === null && <HideSeek m={m} seed={f.seed} onDone={setScore} />}
        {f.activity === 'shop' && <ShopTrip m={m} find={f.find} money={money} owned={owned} onDone={(buy) => finishBond(0, buy)} />}
        {score !== null && (
          <>
            <p class="heading center">{fill(f.activity === 'fetch' ? t.fetch.result : t.hide.result, { n: score, total: f.activity === 'fetch' ? BOND.fetch.throws : BOND.hide.rounds })}</p>
            <div class="spacer" />
            <button type="button" class="btn btn--primary" onClick={() => finishBond(score, null)}>
              {t.done}
            </button>
          </>
        )}
        {score === null && f.activity !== 'shop' && (
          <button type="button" class="btn btn--small bond__cancel" onClick={cancelBond}>
            {t.cancel}
          </button>
        )}
      </div>
    </div>
  )
}
