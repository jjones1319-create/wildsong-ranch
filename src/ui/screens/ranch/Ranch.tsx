import { useEffect, useMemo, useState } from 'preact/hooks'
import { ranchBackground } from '../../../art/backgrounds.ts'
import { keepsakeSvg } from '../../../art/keepsakes.ts'
import { KEEPSAKE_BY_ID } from '../../../data/keepsakes.ts'
import { BONDS_TEXT } from '../../../data/text/bonds.ts'
import { BOND } from '../../../data/tuning.ts'
import { ArrivalScene } from './ArrivalScene.tsx'
import { BondGame } from './bond/BondGame.tsx'
import { dateOf, seasonOf } from '../../../core/calendar.ts'
import { lightPreset } from '../../store/artStore.ts'
import { emoteFor } from '../../../core/emotes.ts'
import { PLANNER_MAX } from '../../../core/planner.ts'
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
import { BackupCard } from '../../components/BackupCard.tsx'
import { Emote } from '../../components/Emote.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { CalendarStrip, ConditionBars, TipCard } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { arrival, dismissTip, flow, game, menu, openTrain, plannerRunning, plannerStop, plannerView, runDeferredArrival, settle, takeAction, tipFor, weekNews } from '../../store/gameStore.ts'
import { lite } from '../../store/perf.ts'
import { PlannerSheet, PlannerSummary } from './Planner.tsx'
import { eventsForWeek } from '../../../core/tournament.ts'
import { pinnedEventThisWeek } from '../../../core/calendarView.ts'
import { JOURNEY_SITE_BY_ID } from '../../../data/journeys.ts'
import { trialOutcome } from '../../store/tournamentStore.ts'
import { versusSideA } from '../../store/versusStore.ts'
import { DrillResult } from './DrillResult.tsx'
import { EmptyRanch } from './EmptyRanch.tsx'
import { trialGateOpen } from './gates.ts'
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

  const a = arrival.value

  useEffect(() => {
    if (!g) navigate('title')
    // §6.10 a monster that left while you were away has its note to show first.
    else if (g.ended && !a) navigate('farewell')
  }, [g === null, g?.ended, a === null])

  // §6.10 a return that came during a battle is checked once the ranch shows again.
  useEffect(() => runDeferredArrival(), [])

  useEffect(() => {
    settle()
  }, [g?.week, g?.weekPhase, f.kind])
  const [expOpen, setExpOpen] = useState(false)
  const [planOpen, setPlanOpen] = useState(false)
  // A waiting card the player opened by hand (the reason line, or the ?! emote), so nothing else can hide it.
  const [forced, setForced] = useState<'event' | 'request' | null>(null)
  useEffect(() => {
    if (!g?.pendingEvent && !g?.pendingRequest) setForced(null)
  }, [g?.pendingEvent, g?.pendingRequest])
  const running = plannerRunning.value
  const summaryOpen = plannerView.value === 'summary'
  const liteMode = lite.value
  const seasonName = g ? seasonOf(dateOf(g.week).month) : 'Spring'
  const weather = g?.weather ?? 'Sunny'
  const bgSeed = g ? g.week + 1 : 1
  const bg = useMemo(() => ranchBackground({ season: seasonName, weather, lite: liteMode, seed: bgSeed }), [seasonName, weather, liteMode, bgSeed])

  if (!g) return null
  if (g.ended) return g.monster && a ? <ArrivalScene a={a} m={g.monster} /> : null
  if (!g.monster) return <EmptyRanch g={g} />
  const m = g.monster
  const mn = menu.value!
  const arrivalOpen = a !== null && f.kind === 'idle' && !running
  const quiet = f.kind === 'idle' && !running && !summaryOpen && !arrivalOpen
  const ranchTip = quiet ? tipFor({ screen: 'ranch' }) : null
  const showFood = needsFoodChoice(g) && !ranchTip && quiet
  const showRequest = g.pendingRequest !== null && (forced === 'request' || (quiet && !showFood))
  const report = [...weeklyReport(g), ...weekNews.value]
  const season = seasonName.toLowerCase()
  const emote = emoteFor(g)
  const reason = mn.reason && mn.reason !== 'ended' && mn.reason !== 'noMonster' ? fill(t.reasons[mn.reason], { name: m.name }) : null
  const repeatWhat = mn.repeat ? (mn.repeat.kind === 'drill' ? DRILL_BY_ID[mn.repeat.drill].name : t.actions.rest) : null
  const cups = eventsForWeek(g)
  const trialPending = quiet && !showFood && !showRequest && trialGateOpen(g, trialOutcome.value !== null)
  const openSites = sitesOpenAt(g.week)
  const showEvent = g.pendingEvent !== null && (forced === 'event' || (quiet && !showFood && !showRequest && !trialPending))
  const canPlan = mn.train && !running && f.kind === 'idle'
  const mapInProgress = g.expedition !== null && !g.expedition.ended
  // §3 a ★ cup this week puts a dot on the Battle button.
  const starred = pinnedEventThisWeek(g)

  return (
    <main class="screen">
      <CalendarStrip state={g} onSettings={() => navigateFrom('ranch', 'settings')} onCalendar={() => navigateFrom('ranch', 'calendar')} />
      <p class="eventline">{cups.length ? fill(t.eventsToday, { events: cups.map((c) => c.event.name).join(' · ') }) : t.noEvents}</p>
      {g.journey && <p class="eventline">{fill(t.journeyWeek, { week: g.journey.weekNo, site: JOURNEY_SITE_BY_ID[g.journey.site].name })}</p>}
      {g.expedition && <p class="eventline">{fill(t.expeditionWeek, { week: g.expedition.weekNo, site: EXPEDITION_SITE_BY_ID[g.expedition.site].name })}</p>}
      {!g.expedition && openSites.length > 0 && <p class="eventline">{fill(t.expeditionOpen, { site: openSites.map((s) => s.name).join(' · ') })}</p>}

      <button type="button" class={`stage stage--${season} stage--${weather.toLowerCase()}`} onClick={() => navigate('ranchCard')} aria-label={fill(t.tapHint, { name: m.name })}>
        <div class="stage__bg" dangerouslySetInnerHTML={{ __html: bg }} />
        {g.keepsakes.length > 0 && (
          <div class="stage__keepsakes" aria-hidden="true">
            {g.keepsakes.slice(-BOND.keepsakesShown).map((id, i) => (
              <span key={id} class={`keepsake keepsake--${i}`} dangerouslySetInnerHTML={{ __html: keepsakeSvg(id, KEEPSAKE_BY_ID[id].name) }} />
            ))}
          </div>
        )}
        <div class="stage__art">
          <MonsterPortrait monster={m} size={200} live idleActs light={lightPreset(seasonName, weather)} />
          <Emote key={emote ?? 'none'} kind={emote} name={m.name} onTap={emote === 'surprise' && (g.pendingEvent || g.pendingRequest) ? () => setForced(g.pendingEvent ? 'event' : 'request') : undefined} />
        </div>
        {(m.status.bondPct > 100 || g.settings.vacation) && (
          <p class="stage__chips">
            {m.status.bondPct > 100 && (
              <span class="chip chip--bond" aria-label={fill(BONDS_TEXT.bond.chipLabel, { x: (m.status.bondPct / 100).toFixed(2) })}>
                {fill(BONDS_TEXT.bond.chip, { x: (m.status.bondPct / 100).toFixed(2) })}
              </span>
            )}
            {g.settings.vacation && <span class="chip">{BONDS_TEXT.settings.vacationOn}</span>}
          </p>
        )}
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
      {quiet && !ranchTip && <BackupCard />}
      {running && (
        <section class="card planrun" role="status">
          <span class="planrun__text">
            {fill(UI_TEXT.planner.running, { n: g.planner.log.length + 1, total: g.planner.log.length + g.planner.queue.length })}
          </span>
          <button type="button" class="btn btn--small" onClick={plannerStop}>
            {UI_TEXT.planner.stop}
          </button>
        </section>
      )}

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
            class={`btn ${starred ? 'btn--dot' : ''}`}
            disabled={!mn.train && !g.tournament}
            aria-label={starred ? `${t.actions.battle}. ${UI_TEXT.calendar.starredBattle}` : undefined}
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
            <button type="button" class="btn btn--half" disabled={running} onClick={() => takeAction(mn.repeat!)} title={fill(t.repeatHint, { what: repeatWhat })}>
              {t.actions.repeat} · {repeatWhat}
            </button>
          )}
        </div>
        <div class="actions__row">
          <button type="button" class="btn btn--half" disabled={!canPlan} onClick={() => setPlanOpen(true)}>
            {UI_TEXT.planner.button}
            {g.planner.queue.length > 0 ? ` · ${g.planner.queue.length}/${PLANNER_MAX}` : ''}
          </button>
        </div>
        {!g.expedition && openSites.length > 0 && (
          <div class="actions__row">
            <button type="button" class="btn" disabled={!mn.train} onClick={() => setExpOpen(true)}>
              🧭 {UI_TEXT.expedition.ranchButton} · {openSites.map((s) => s.name).join(' · ')}
            </button>
          </div>
        )}
        {reason && (mn.reason === 'event' || mn.reason === 'request') ? (
          <button type="button" class="actionbar__reason actionbar__reason--link" onClick={() => setForced(mn.reason === 'event' ? 'event' : 'request')}>
            {reason}
          </button>
        ) : reason ? (
          <p class="actionbar__reason">{reason}</p>
        ) : null}
      </div>

      <FoodPrompt open={showFood} />
      <RequestCard open={showRequest} />
      <EventCard open={showEvent} />
      <ExpeditionSheet open={expOpen} onClose={() => setExpOpen(false)} />
      {trialPending && <TrialCard />}
      <PlannerSheet open={planOpen && canPlan} onClose={() => setPlanOpen(false)} />
      {summaryOpen && <PlannerSummary />}
      <TrainSheet open={f.kind === 'train'} />
      {f.kind === 'bond' && <BondGame f={f} m={m} money={g.money} />}
      {arrivalOpen && <ArrivalScene a={a!} m={m} />}
      {f.kind === 'result' && <DrillResult f={f} />}
      {f.kind === 'summary' && <WeekSummary f={f} />}
    </main>
  )
}
