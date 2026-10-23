import { useState } from 'preact/hooks'
import { upgradeOffers, type UpgradeOffer } from '../../../core/upgrades.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { Badge, Confirm, TopBar } from '../../components/Controls.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { showToast } from '../../store/appStore.ts'
import { buyUpgrade, game } from '../../store/gameStore.ts'

const t = UI_TEXT.upgrades

/** CONTENT §11 ranch upgrades: the four cards, their gates, and Buy with a confirm. Nothing here expires. */
export function UpgradesScreen() {
  const g = game.value
  const [asking, setAsking] = useState<UpgradeOffer | null>(null)
  if (!g) return null
  const offers = upgradeOffers(g)
  const gateText = (o: UpgradeOffer) => {
    if (o.blocked === 'rank') return fill(t.needsRank, { n: o.upgrade.requires.kind === 'rank' ? o.upgrade.requires.rank : 0 })
    if (o.blocked === 'memorial') return t.needsMemorial
    if (o.blocked === 'money') return t.noMoney
    return null
  }
  const confirm = () => {
    const o = asking
    setAsking(null)
    if (!o) return
    const refused = buyUpgrade(o.upgrade.id)
    if (refused) showToast(refused === 'money' ? t.noMoney : refused === 'rank' ? fill(t.needsRank, { n: o.upgrade.requires.kind === 'rank' ? o.upgrade.requires.rank : 0 }) : refused === 'memorial' ? t.needsMemorial : t.owned)
    else showToast(fill(t.bought, { name: o.upgrade.name }))
  }
  return (
    <main class="screen">
      <TopBar title={t.title} right={<span class="calstrip__money">{gold(g.money)}</span>} />
      <SpeakerCard speaker={UI_TEXT.ines} tone="muted">
        <p>{t.intro}</p>
      </SpeakerCard>
      {offers.map((o) => {
        const gate = gateText(o)
        return (
          <section class="card" key={o.upgrade.id}>
            <p class="field__label">
              {o.upgrade.name} {o.owned && <Badge tone="pure">{t.owned}</Badge>}
            </p>
            <p class="small">{t.effects[o.upgrade.id]}</p>
            {!o.owned && gate && <p class="muted small food__tag--bad">{gate}</p>}
            {!o.owned && (
              <button type="button" class="btn btn--primary" style={{ marginTop: 8 }} disabled={o.blocked !== null} onClick={() => setAsking(o)}>
                {fill(t.buy, { price: gold(o.upgrade.price) })}
              </button>
            )}
          </section>
        )
      })}
      <Confirm open={asking !== null} text={asking ? fill(t.ask, { name: asking.upgrade.name, price: gold(asking.upgrade.price) }) : ''} confirmLabel={asking ? fill(t.buy, { price: gold(asking.upgrade.price) }) : ''} onConfirm={confirm} onCancel={() => setAsking(null)} />
    </main>
  )
}
