import { useEffect } from 'preact/hooks'
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
