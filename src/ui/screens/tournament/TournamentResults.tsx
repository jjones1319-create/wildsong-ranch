import { useEffect } from 'preact/hooks'
import { eventName } from '../../../core/tournament.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { TECHNIQUE_BY_ID } from '../../../data/techniques.ts'
import { fill } from '../../../data/text/format.ts'
import { STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { STAT_KEYS } from '../../../data/types.ts'
import { TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { game } from '../../store/gameStore.ts'
import { afterResults, outcome } from '../../store/tournamentStore.ts'

/** §21 Results: placings, purse, items, fame, stat gains, condition changes, lifespan cost (Lens), and what changed at the Guild. */
export function TournamentResultsScreen() {
  const g = game.value
  const o = outcome.value
  const t = UI_TEXT.tournament.results
  useEffect(() => {
    if (!g || !g.monster) navigate('title')
    else if (!o) navigate('ranch')
  }, [g === null, o === null])
  if (!g || !g.monster || !o) return null
  const m = g.monster
  const lens = settings.value.transparency === 'lens'
  const place = o.placing === 1 ? t.place1 : o.placing === 2 ? t.place2 : o.placing === 3 ? t.place3 : fill(t.placeN, { n: o.placing })
  const vars = { name: m.name, event: eventName(o.eventId), them: 'them', grade: o.promoted ?? '', rank: o.rankAfter }
  const wren = o.died ? fill(t.died, vars) : o.koed ? fill(WREN.cupKo, vars) : o.placing === 1 ? fill(WREN.cupWin, vars) : o.placing <= 3 ? fill(WREN.cupPodium, vars) : fill(WREN.cupLoss, vars)
  const gains = STAT_KEYS.filter((k) => (o.growth[k] ?? 0) > 0)

  return (
    <main class="screen">
      <TopBar title={t.title} onBack={afterResults} />
      <div class="farewell__art">
        <MonsterPortrait monster={m} size={160} expression={o.placing === 1 ? 'happy' : o.koed ? 'sad' : undefined} />
      </div>
      <h2 class="heading center">{o.relayTeamWin === null ? place : o.relayTeamWin ? t.teamWin : t.teamLoss}</h2>
      <p class="center muted">
        {eventName(o.eventId)} · {fill(t.placing, { place: o.placing, n: o.participants })} · {fill(t.record, { w: o.playerWins, n: o.playerMatches })}
      </p>
      <SpeakerCard speaker={UI_TEXT.wren}>
        <p>{wren}</p>
        {o.promoted && <p>{fill(WREN.promoted, vars)}</p>}
        {o.rankAfter > o.rankBefore && <p>{fill(WREN.rankUp, vars)}</p>}
        {o.crownInvite && <p>{fill(WREN.crownInvite, vars)}</p>}
        {o.legendInvite && <p>{fill(WREN.legendInvite, vars)}</p>}
        {o.hallOfFame && <p>{fill(WREN.hallOfFame, vars)}</p>}
      </SpeakerCard>
      <section class="card">
        <dl class="kv">
          <dt>{t.purse}</dt>
          <dd>{gold(o.purse)}</dd>
          <dt>{t.perWin}</dt>
          <dd>{gold(o.perWinGold)}</dd>
          {o.items.length > 0 && (
            <>
              <dt>{t.items}</dt>
              <dd>{o.items.map((i) => `${ITEM_BY_ID[i.id]?.name ?? i.id} ×${i.qty}`).join(', ')}</dd>
            </>
          )}
          {o.sheets.length > 0 && (
            <>
              <dt>{t.sheets}</dt>
              <dd>{o.sheets.map((id) => TECHNIQUE_BY_ID[id]?.name ?? id).join(', ')}</dd>
            </>
          )}
          <dt>{t.fame}</dt>
          <dd>{o.fame > 0 ? `+${o.fame}` : o.fame}</dd>
          {gains.length > 0 && (
            <>
              <dt>{t.growth}</dt>
              <dd>{gains.map((k) => `${STAT_NAMES[k]} +${o.growth[k]}`).join(' · ')}</dd>
            </>
          )}
          <dt>{t.condition}</dt>
          <dd>
            {UI_TEXT.ranch.bars.fatigue} +{o.fatigue} · {UI_TEXT.ranch.bars.stress} {o.stress}
          </dd>
          {lens && (
            <>
              <dt>{t.lifespan}</dt>
              <dd>{o.lifespan} wks</dd>
            </>
          )}
          {o.injuredWeeks > 0 && (
            <>
              <dt />
              <dd class="food__tag--bad">{fill(t.injured, { n: o.injuredWeeks })}</dd>
            </>
          )}
          {o.promoted && (
            <>
              <dt />
              <dd class="food__tag">{fill(t.promoted, { g: o.promoted })}</dd>
            </>
          )}
          {o.rankAfter > o.rankBefore && (
            <>
              <dt />
              <dd class="food__tag">{fill(t.rank, { a: o.rankBefore, b: o.rankAfter })}</dd>
            </>
          )}
          {o.titles.length > 0 && (
            <>
              <dt>{t.titles}</dt>
              <dd>{o.titles.join(', ')}</dd>
            </>
          )}
          {o.crownInvite && (
            <>
              <dt />
              <dd class="food__tag">{t.crownInvite}</dd>
            </>
          )}
          {o.legendInvite && (
            <>
              <dt />
              <dd class="food__tag">{t.legendInvite}</dd>
            </>
          )}
          {o.hallOfFame && (
            <>
              <dt />
              <dd class="food__tag">{t.hallOfFame}</dd>
            </>
          )}
        </dl>
      </section>
      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" onClick={afterResults}>
          {t.continue}
        </button>
      </div>
    </main>
  )
}
