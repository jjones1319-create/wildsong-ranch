import { useEffect, useState } from 'preact/hooks'
import { dateOf, seasonOf } from '../../../core/calendar.ts'
import { sitesOpenAt } from '../../../core/expedition.ts'
import { EXPEDITION_SITE_BY_ID } from '../../../data/expeditions.ts'
import { EventCard } from './EventCard.tsx'
import { ExpeditionSheet } from './ExpeditionSheet.tsx'
import { needsFoodChoice } from '../../../core/game.ts'
import { stageOf } from '../../../core/monster.ts'
import { tipText } from '../../../core/onboarding.ts'
import { weeklyReport } from '../../../core/report.ts'
import { DRILL_BY_ID } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { STAGE_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { CalendarStrip, ConditionBars, TipCard } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { dismissTip, flow, game, menu, openTrain, settle, takeAction, tipFor, weekNews } from '../../store/gameStore.ts'
import { eventsForWeek } from '../../../core/tournament.ts'
import { JOURNEY_SITE_BY_ID } from '../../../data/journeys.ts'
import { trialOutcome } from '../../store/tournamentStore.ts'
import { versusSideA } from '../lab/LabVersus.tsx'
import { DrillResult } from './DrillResult.tsx'
import { EmptyRanch } from './EmptyRanch.tsx'
import { TrialCard } from './TrialCard.tsx'
import { FoodPrompt } from './FoodPrompt.tsx'
import { RequestCard } from './RequestCard.tsx'
import { TrainSheet } from './TrainSheet.tsx'
import { WeekSummary } from './WeekSummary.tsx'

/** §21 the ranch (home): monster on stage, calendar strip, Wren's report, condition, the action bar. */
export function RanchScreen() {
  const g = game.value
  const f = flow.value
  const t = UI_TEXT.ranch
  const mode = settings.value.transparency

  useEffect(() => {
    if (!g) navigate('title')
    else if (g.ended) navigate('farewell')
  }, [g === null, g?.ended])

  useEffect(() => {
    settle()
  }, [g?.week, g?.weekPhase, f.kind])
  const [expOpen, setExpOpen] = useState(false)

  if (!g || g.ended) return null
  if (!g.monster) return <EmptyRanch g={g} />
  const m = g.monster
  const mn = menu.value!
  const ranchTip = tipFor({ screen: 'ranch' })
  const showFood = needsFoodChoice(g) && !ranchTip && f.kind === 'idle'
  const showRequest = g.pendingRequest !== null && f.kind === 'idle' && !showFood
  const report = [...weeklyReport(g), ...weekNews.value]
  const season = seasonOf(dateOf(g.week).month).toLowerCase()
  const reason = mn.reason && mn.reason !== 'ended' && mn.reason !== 'noMonster' ? fill(t.reasons[mn.reason], { name: m.name }) : null
  const repeatWhat = mn.repeat ? (mn.repeat.kind === 'drill' ? DRILL_BY_ID[mn.repeat.drill].name : t.actions.rest) : null
  const cups = eventsForWeek(g)
  const trialPending = f.kind === 'idle' && !showFood && !showRequest && (g.trial !== null || g.journey?.pendingTechnique !== null || trialOutcome.value !== null)
  const openSites = sitesOpenAt(g.week)
  const showEvent = g.pendingEvent !== null && f.kind === 'idle' && !showFood && !showRequest && !trialPending
  const mapInProgress = g.expedition !== null && !g.expedition.ended

  return (
    <main class="screen">
      <CalendarStrip state={g} onSettings={() => navigateFrom('ranch', 'settings')} />
      <p class="eventline">{cups.length ? fill(t.eventsToday, { events: cups.map((c) => c.event.name).join(' · ') }) : t.noEvents}</p>
      {g.journey && <p class="eventline">{fill(t.journeyWeek, { week: g.journey.weekNo, site: JOURNEY_SITE_BY_ID[g.journey.site].name })}</p>}
      {g.expedition && <p class="eventline">{fill(t.expeditionWeek, { week: g.expedition.weekNo, site: EXPEDITION_SITE_BY_ID[g.expedition.site].name })}</p>}
      {!g.expedition && openSites.length > 0 && <p class="eventline">{fill(t.expeditionOpen, { site: openSites.map((s) => s.name).join(' · ') })}</p>}

      <button type="button" class={`stage stage--${season}`} onClick={() => navigate('ranchCard')} aria-label={fill(t.tapHint, { name: m.name })}>
        <div class="stage__art">
          <MonsterPortrait monster={m} size={200} />
        </div>
        <p class="stage__caption">{fill(t.stage, { stage: STAGE_NAMES[stageOf(m) - 1], name: m.name })}</p>
        <p class="stage__hint">{fill(t.tapHint, { name: m.name })}</p>
      </button>

      <section class="bubble" aria-live="polite">
        <p class="speaker">{UI_TEXT.wren}</p>
        {report.map((l, i) => (
          <p key={`${l.key}-${i}`}>{l.text}</p>
        ))}
      </section>

      {ranchTip && <TipCard text={tipText(g, ranchTip)} onDismiss={() => dismissTip(ranchTip)} />}

      <ConditionBars m={m} mode={mode} />

      <div class="spacer" />
      <div class="actionbar actionbar--stack">
        <div class="actions">
          {g.tournament ? (
            <button type="button" class="btn btn--primary" onClick={() => navigate('tournamentPlay')}>
              {t.actions.battle}
            </button>
          ) : mapInProgress ? (
            <button type="button" class="btn btn--primary" onClick={() => navigate('expedition')}>
              {UI_TEXT.expedition.continueTrip}
            </button>
          ) : mn.wait ? (
            <button type="button" class="btn btn--primary" onClick={() => takeAction({ kind: 'none' })}>
              {g.journey ? t.continueJourney : t.actions.wait}
            </button>
          ) : (
            <button type="button" class="btn btn--primary" disabled={!mn.train} onClick={openTrain}>
              {t.actions.train}
            </button>
          )}
          <button type="button" class="btn" disabled={!mn.rest} onClick={() => takeAction({ kind: 'rest' })}>
            {t.actions.rest}
          </button>
          <button type="button" class="btn" disabled={!mn.train} onClick={() => navigate('journey')}>
            {t.actions.journey}
          </button>
          <button
            type="button"
            class="btn"
            disabled={!mn.train && !g.tournament}
            onClick={() => {
              if (g.tournament) navigate('tournamentPlay')
              else if (cups.length > 0) navigate('tournament')
              else {
                versusSideA.value = { monster: structuredClone(m), source: 'active' }
                navigateFrom('ranch', 'labVersus')
              }
            }}
          >
            {t.actions.battle}
          </button>
          <button type="button" class="btn" onClick={() => navigate('town')}>
            {t.actions.town}
          </button>
        </div>
        <div class="actions__row">
          <button type="button" class="btn btn--half" onClick={() => navigate('bag')}>
            {t.actions.bag}
          </button>
          {mn.repeat && repeatWhat && (
            <button type="button" class="btn btn--half" onClick={() => takeAction(mn.repeat!)} title={fill(t.repeatHint, { what: repeatWhat })}>
              {t.actions.repeat} · {repeatWhat}
            </button>
          )}
        </div>
        {!g.expedition && openSites.length > 0 && (
          <div class="actions__row">
            <button type="button" class="btn" disabled={!mn.train} onClick={() => setExpOpen(true)}>
              🧭 {UI_TEXT.expedition.ranchButton} · {openSites.map((s) => s.name).join(' · ')}
            </button>
          </div>
        )}
        {reason && <p class="actionbar__reason">{reason}</p>}
      </div>

      <FoodPrompt open={showFood} />
      <RequestCard open={showRequest} />
      <EventCard open={showEvent} />
      <ExpeditionSheet open={expOpen} onClose={() => setExpOpen(false)} />
      {trialPending && <TrialCard />}
      <TrainSheet open={f.kind === 'train'} />
      {f.kind === 'result' && <DrillResult f={f} />}
      {f.kind === 'summary' && <WeekSummary f={f} />}
    </main>
  )
}
