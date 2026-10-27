import { useEffect } from 'preact/hooks'
import { playSfx } from '../../../audio/player.ts'
import { tipText } from '../../../core/onboarding.ts'
import { fill } from '../../../data/text/format.ts'
import { WEATHER_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { TipCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { dismissTip, game, nextWeek, tipFor, type SummaryFlow } from '../../store/gameStore.ts'

const DRAMATIC = new Set(['breakdownRunAway', 'breakdownCollapse', 'sick', 'tenWeeksLeft', 'farewell', 'retire'])

/** The end of the week: aging events, fees, next week's weather, the grow-up moment, and the farewell hand-off. */
export function WeekSummary({ f }: { f: SummaryFlow }) {
  const g = game.value
  const t = UI_TEXT.week
  if (!g || !g.monster) return null
  const m = g.monster
  const breakdown = f.aging.some((e) => e.kind === 'breakdown')
  const tip = tipFor({ screen: 'summary', events: f.aging })
  useEffect(() => {
    if (f.grewUp) playSfx('growUp')
    else if (f.aging.some((e) => e.kind === 'prime')) playSfx('prime')
  }, [])
  const title = f.ended ? t.farewell : breakdown ? t.breakdown : f.grewUp ? t.grewUp : t.title
  return (
    <div class="overlay" role="dialog" aria-label={title}>
      <div class="overlay__inner">
        <h2 class="heading center">{title}</h2>
        <div class="farewell__art">
          <div class={`stage__art ${f.grewUp ? 'stage__art--glow' : ''}`}>
            <MonsterPortrait monster={m} size={180} expression={breakdown ? 'sad' : f.grewUp ? 'happy' : undefined} />
          </div>
        </div>
        <section class="card">
          <p class="speaker">{UI_TEXT.wren}</p>
          {f.lines.length === 0 && <p>{t.quiet}</p>}
          {f.lines.map((l, i) => (
            <p key={`${l.key}-${i}`} class={DRAMATIC.has(l.key) ? 'notice' : ''}>
              {l.text}
            </p>
          ))}
          {f.fees > 0 && <p class="notice">{fill(t.fees, { n: gold(f.fees) })}</p>}
          {!f.ended && <p class="muted small">{fill(t.nextWeather, { weather: WEATHER_LABELS[g.weather].toLowerCase() })}</p>}
        </section>
        {tip && <TipCard text={tipText(g, tip)} onDismiss={() => dismissTip(tip)} />}
        <div class="spacer" />
        {f.ended ? (
          <button
            type="button"
            class="btn btn--primary"
            onClick={() => {
              nextWeek()
              navigate('farewell')
            }}
          >
            {t.farewell}
          </button>
        ) : (
          <button type="button" class="btn btn--primary" onClick={nextWeek}>
            {t.next}
          </button>
        )}
      </div>
    </div>
  )
}
