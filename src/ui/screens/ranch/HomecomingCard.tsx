import { welcomeWhere } from '../../../core/homecoming.ts'
import { findOwned } from '../../../core/legacy.ts'
import type { GameState } from '../../../core/state.ts'
import { variantNameOf } from '../../../core/variants.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { dismissHomecoming } from '../../store/herdStore.ts'

/**
 * §6.10 the one-time v16 homecoming: every monster that ran off long ago walked back up the lane. Each returnee's
 * portrait, name and where it lives now, with Wren's welcome; "Welcome home!" closes it for good. Works on an empty
 * ranch too. Nothing moves, so there is nothing to skip.
 */
export function HomecomingCard({ g }: { g: GameState }) {
  const t = HERD_TEXT.homecoming
  const back = g.homecoming.welcome.flatMap((id) => {
    const owned = findOwned(g, id)
    const where = welcomeWhere(g, id)
    return owned && where ? [{ m: owned.monster, where }] : []
  })
  return (
    <div class="overlay" role="dialog" aria-label={t.title}>
      <div class="overlay__inner">
        <h2 class="heading center">{t.title}</h2>
        <SpeakerCard speaker={UI_TEXT.wren}>
          <p>{t.wren}</p>
        </SpeakerCard>
        <ul class="homecoming">
          {back.map(({ m, where }) => (
            <li key={m.id} class="homecoming__row">
              <MonsterPortrait monster={m} size={72} expression="happy" animate={false} />
              <span class="homecoming__body">
                <b>{fill(t.one, { name: m.name })}</b>
                <span class="muted small">{variantNameOf(m)}</span>
                <span class="small">{fill(t[where], { name: m.name })}</span>
              </span>
            </li>
          ))}
        </ul>
        <div class="spacer" />
        <button type="button" class="btn btn--primary" onClick={dismissHomecoming}>
          {t.button}
        </button>
      </div>
    </div>
  )
}
