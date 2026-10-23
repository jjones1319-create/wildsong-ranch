import { useEffect, useState } from 'preact/hooks'
import { sheetsForSale, type SheetOffer } from '../../../core/guild.ts'
import { BREED_BY_ID, STARTING_UNLOCKED } from '../../../data/breeds.ts'
import { fill } from '../../../data/text/format.ts'
import { FAMILY_LABELS, RANGE_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import type { BreedId } from '../../../data/types.ts'
import { Chips, Segmented, TopBar } from '../../components/Controls.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { playSfx } from '../../../audio/player.ts'
import { showToast } from '../../store/appStore.ts'
import { buySongsheet, game } from '../../store/gameStore.ts'

/** §10.5 the Guild Library: universal and breed Songsheets, prices and rank gates, ★ good fit, Owned marks. */
export function GuildLibraryScreen() {
  const g = game.value
  const t = UI_TEXT.library
  const [tab, setTab] = useState<'universal' | 'breed'>('universal')
  const [breed, setBreed] = useState<BreedId | null>(null)
  useEffect(() => {
    if (!g) navigate('title')
  }, [g === null])
  if (!g) return null
  const offers = sheetsForSale(g)
  const pickedBreed = breed ?? g.monster?.mainBreed ?? 'puddlepup'
  const shown = tab === 'universal' ? offers.filter((o) => o.tech.breed === 'universal') : offers.filter((o) => o.tech.breed === pickedBreed)
  const breedOptions = STARTING_UNLOCKED.map((id) => ({ value: id, label: BREED_BY_ID[id].name }))

  const buyIt = (o: SheetOffer) => {
    const r = buySongsheet(o.tech.id)
    if (r.refused === 'money') showToast(UI_TEXT.shop.gates.money)
    else if (r.refused === 'rank') showToast(fill(UI_TEXT.shop.gates.rank, { n: o.rankMin }))
    else if (r.refused === 'debt') showToast(UI_TEXT.shop.gates.debt)
    else if (!r.refused) {
      showToast(fill(t.bought, { technique: o.tech.name }))
      playSfx('coin')
    }
  }

  return (
    <main class="screen">
      <TopBar title={t.title} right={<span class="calstrip__money">{gold(g.money)}</span>} />
      <SpeakerCard speaker={UI_TEXT.ines} tone="muted">
        <p>{t.hello}</p>
      </SpeakerCard>
      <Segmented
        options={[
          { value: 'universal', label: t.tabs.universal },
          { value: 'breed', label: t.tabs.breed },
        ]}
        value={tab}
        onChange={setTab}
        label={t.title}
      />
      {tab === 'breed' && <Chips options={breedOptions} value={pickedBreed} onChange={setBreed} label={t.tabs.breed} />}
      <section class="card">
        {shown.length === 0 && <p class="muted">{t.nothing}</p>}
        {shown.map((o) => {
          const off = o.blocked !== null || g.money < o.price
          return (
            <div class={`item ${o.blocked ? 'item--off' : ''}`} key={o.tech.id}>
              <span class="item__body">
                <span class="item__name">
                  {o.tech.name} {o.fit && o.learnable && <span class="food__tag">★</span>}
                </span>
                <span class="item__meta">
                  {FAMILY_LABELS[o.tech.family]} · {o.tech.type} · {RANGE_LABELS[o.tech.range]} · {o.tech.cost} guts
                </span>
                {o.blocked === 'rank' && <span class="item__meta food__tag--bad">{fill(UI_TEXT.shop.gates.rank, { n: o.rankMin })}</span>}
                {o.learnable === false && g.monster && <span class="item__meta">{fill(t.cantLearn, { name: g.monster.name })}</span>}
              </span>
              {o.owned ? (
                <span class="pill">{t.owned}</span>
              ) : (
                <>
                  <span class="item__price">{gold(o.price)}</span>
                  <button type="button" class="btn btn--small btn--primary" disabled={off} onClick={() => buyIt(o)}>
                    {t.buy}
                  </button>
                </>
              )}
            </div>
          )
        })}
      </section>
    </main>
  )
}
