import { useEffect } from 'preact/hooks'
import { keepsakeSvg } from '../../../art/keepsakes.ts'
import { keepsakeStress } from '../../../core/bond.ts'
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
import { startEditActive } from '../../store/labStore.ts'

/** §21 the Monster Card in play, with the owner's three buttons: Use item · Learn technique · ✏️ Edit. */
export function MonsterCardScreen() {
  const g = game.value
  const t = UI_TEXT.card
  useEffect(() => {
    if (!g || !g.monster) navigate('ranch')
  }, [g === null])
  if (!g || !g.monster) return null
  const m = g.monster
  const tip = tipFor({ screen: 'card' })
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <MonsterSheet m={m} mode={settings.value.transparency} editCount={g.monsterHistory.length}>
        {tip && <TipCard text={tipText(g, tip)} onDismiss={() => dismissTip(tip)} />}
      </MonsterSheet>
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
      <div class="actionbar">
        <button type="button" class="btn btn--half" onClick={() => navigateFrom('ranchCard', 'bag')}>
          {t.useItem}
        </button>
        <button type="button" class="btn btn--half" onClick={() => navigateFrom('ranchCard', 'songbook')}>
          {t.learn}
        </button>
        <button
          type="button"
          class="btn btn--primary btn--half"
          onClick={() => {
            startEditActive(m, g.monsterHistory)
            navigateFrom('ranchCard', 'labEdit')
          }}
        >
          {t.edit}
        </button>
      </div>
    </main>
  )
}
