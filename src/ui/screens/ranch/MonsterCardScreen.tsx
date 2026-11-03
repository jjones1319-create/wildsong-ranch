import { useEffect } from 'preact/hooks'
import { keepsakeSvg } from '../../../art/keepsakes.ts'
import { keepsakeStress } from '../../../core/bond.ts'
import { findOwned } from '../../../core/legacy.ts'
import { KEEPSAKE_BY_ID } from '../../../data/keepsakes.ts'
import { BONDS_TEXT } from '../../../data/text/bonds.ts'
import { fill } from '../../../data/text/format.ts'
import { tipText } from '../../../core/onboarding.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
import { MonsterSheet } from '../../components/MonsterSheet.tsx'
import { TipCard } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { dismissTip, game, tipFor } from '../../store/gameStore.ts'
import { cardId } from '../../store/herdStore.ts'
import { startEdit, startEditActive, startEditMate } from '../../store/labStore.ts'
import { FriendsSection } from './FriendsBits.tsx'

/**
 * §21 the Monster Card in play, with the owner's three buttons: Use item · Learn technique · ✏️ Edit. v16: it shows
 * any owned monster (`cardId`, from the herd sheet), falling back to the star; Edit works wherever it lives.
 */
export function MonsterCardScreen() {
  const g = game.value
  const t = UI_TEXT.card
  const owned = g ? ((cardId.value ? findOwned(g, cardId.value) : null) ?? (g.monster ? findOwned(g, g.monster.id) : null)) : null
  useEffect(() => {
    if (!g || !owned) navigate('ranch')
  }, [g === null, owned === null])
  if (!g || !owned) return null
  const m = owned.monster
  const where = owned.where
  const isStar = where === 'star'
  const mate = where === 'pen' ? g.ranchmates[owned.index]! : null
  const history = isStar ? g.monsterHistory : (mate?.history ?? [])
  // The Bag and the Songbook reach the star and the pens (and need a star on the ranch).
  const canUse = g.monster !== null && (isStar || where === 'pen')
  const tip = isStar ? tipFor({ screen: 'card' }) : null
  const edit = () => {
    if (isStar) startEditActive(m, history)
    else if (mate) startEditMate(m, history)
    else startEdit({ id: m.id, monster: m, source: 'freezer', history: [], createdAt: 0, updatedAt: 0 })
    navigateFrom('ranchCard', 'labEdit')
  }
  return (
    <main class="screen">
      <TopBar title={isStar ? t.title : `${t.title} · ${m.name}`} />
      <MonsterSheet m={m} mode={settings.value.transparency} editCount={history.length}>
        {tip && <TipCard text={tipText(g, tip)} onDismiss={() => dismissTip(tip)} />}
      </MonsterSheet>
      {isStar && (
        <section class="card">
          <p class="field__label">{BONDS_TEXT.bond.keepsakesTitle}</p>
          {g.keepsakes.length === 0 ? (
            <p class="muted small">{fill(BONDS_TEXT.bond.keepsakesNone, { name: m.name, they: 'they' })}</p>
          ) : (
            <>
              <ul class="keepsakes">
                {g.keepsakes.map((id) => (
                  <li key={id} class="keepsakes__row">
                    <span class="keepsakes__art" aria-hidden="true" dangerouslySetInnerHTML={{ __html: keepsakeSvg(id, KEEPSAKE_BY_ID[id].name) }} />
                    <span>
                      <b>{KEEPSAKE_BY_ID[id].name}</b>
                      <span class="muted small"> · {KEEPSAKE_BY_ID[id].blurb}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p class="muted small">{fill(BONDS_TEXT.bond.keepsakesCalm, { n: keepsakeStress(g.keepsakes), name: m.name })}</p>
            </>
          )}
        </section>
      )}
      <FriendsSection g={g} id={m.id} name={m.name} />
      <div class="actionbar">
        {canUse && (
          <button type="button" class="btn btn--half" onClick={() => navigateFrom('ranchCard', 'bag')}>
            {t.useItem}
          </button>
        )}
        {canUse && (
          <button type="button" class="btn btn--half" onClick={() => navigateFrom('ranchCard', 'songbook')}>
            {t.learn}
          </button>
        )}
        <button type="button" class="btn btn--primary btn--half" onClick={edit}>
          {t.edit}
        </button>
      </div>
    </main>
  )
}
