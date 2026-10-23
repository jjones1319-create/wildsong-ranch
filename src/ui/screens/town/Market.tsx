import { useState } from 'preact/hooks'
import { dateOf } from '../../../core/calendar.ts'
import { freezerFull } from '../../../core/legacy.ts'
import { marketStock, type MarketOffer } from '../../../core/market.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { Confirm, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { showToast } from '../../store/appStore.ts'
import { buyFromMarket, game } from '../../store/gameStore.ts'

/** §14.2 the Market: the four starters and the season's breed, for gold, to the ranch or the Freezer. */
export function MarketScreen() {
  const t = UI_TEXT.market
  const g = game.value
  const [asking, setAsking] = useState<MarketOffer | null>(null)
  if (!g) return null
  const offers = marketStock(dateOf(g.week).month)
  const toRanch = g.monster === null && !g.ended
  const where = toRanch ? t.toRanch : t.toFreezer

  const buy = () => {
    const offer = asking
    setAsking(null)
    if (!offer) return
    const r = buyFromMarket(offer.breed)
    if (!r || r.refused) {
      showToast(r?.refused === 'money' ? t.noMoney : r?.refused === 'freezerFull' ? t.freezerFull : UI_TEXT.pellLab.freezeBusy)
      return
    }
    showToast(fill(t.bought, { name: r.monster!.name }))
    if (r.placed === 'ranch') navigate('ranch')
  }

  return (
    <main class="screen">
      <TopBar title={t.title} right={<span class="calstrip__money">{gold(g.money)}</span>} />
      <SpeakerCard speaker={UI_TEXT.ines} tone="muted">
        <p>{t.intro}</p>
        <p class="muted small">{where}</p>
      </SpeakerCard>
      <div class="gift">
        {offers.map((o) => (
          <div key={o.breed} class="tile">
            <MonsterPortrait breed={o.breed} size={84} label={BREED_BY_ID[o.breed].name} animate={false} />
            <span class="tile__name">{BREED_BY_ID[o.breed].name}</span>
            <span class="muted small">{BREED_BY_ID[o.breed].niche}</span>
            {o.seasonal && <span class="muted small">{t.seasonal}</span>}
            <button type="button" class="btn btn--small btn--primary" disabled={g.money < o.price || (!toRanch && freezerFull(g))} onClick={() => setAsking(o)}>
              {fill(t.buy, { price: gold(o.price) })}
            </button>
          </div>
        ))}
      </div>
      <Confirm
        open={asking !== null}
        text={asking ? fill(t.buyAsk, { breed: BREED_BY_ID[asking.breed].name, price: gold(asking.price), where }) : ''}
        confirmLabel={asking ? fill(t.buy, { price: gold(asking.price) }) : ''}
        onConfirm={buy}
        onCancel={() => setAsking(null)}
      />
    </main>
  )
}
