import { useEffect, useState } from 'preact/hooks'
import { WEEKS_PER_YEAR, dateOf } from '../../../core/calendar.ts'
import { CALENDAR_YEARS_AHEAD, calendarWeeks, gradeLine, lowestEntryGrade, type CalendarEvent, type CalendarExpedition, type CalendarNote, type CalendarWeek } from '../../../core/calendarView.ts'
import type { GameState } from '../../../core/state.ts'
import { EVENT_BY_ID, isSummitYear } from '../../../data/calendar.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { DRILL_BY_ID } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { CALENDAR_NOTE_ICONS, EVENT_KIND_ICONS, EVENT_KIND_LABELS, EXPEDITION_ICON, FORMAT_LABELS, MONTH_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { CALENDAR, TOURNAMENT } from '../../../data/tuning.ts'
import { Segmented, Sheet, Toggle, TopBar } from '../../components/Controls.tsx'
import { gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { calendarCursor, calendarView, onlyEnterable, showExpeditions, toggleCalendarPin, type CalendarViewKind } from '../../store/calendarStore.ts'
import { game } from '../../store/gameStore.ts'
import { entryPreselect } from '../../store/tournamentStore.ts'

const t = UI_TEXT.calendar
const WPM = CALENDAR.weeksPerMonth

type Open = { kind: 'event'; ce: CalendarEvent; offset: number } | { kind: 'expedition'; ex: CalendarExpedition; offset: number }

const monthStartOf = (week: number) => week - (dateOf(week).week - 1)
const yearStartOf = (week: number) => week - (week % WEEKS_PER_YEAR)

function whenLabel(offset: number): string {
  if (offset === 0) return t.thisWeek
  if (offset === 1) return t.nextWeek
  if (offset === -1) return t.lastWeek
  return offset > 0 ? fill(t.inWeeks, { n: offset }) : fill(t.weeksAgo, { n: -offset })
}

/** "Can enter", "Too easy…", or why not, from the shared §13 entry check. */
function answerOf(ce: CalendarEvent, name: string): { text: string; tone: 'ok' | 'warn' | 'no' } {
  const e = ce.entry
  if (e.eligible) return e.tooEasy ? { text: t.entry.tooEasy, tone: 'warn' } : { text: t.entry.can, tone: 'ok' }
  switch (e.reason) {
    case 'minGrade':
      return { text: fill(t.entry.needsGrade, { g: ce.event.minGrade ?? '' }), tone: 'no' }
    case 'gradeTooHigh':
      return { text: fill(t.entry.needsGrade, { g: lowestEntryGrade(ce.event) ?? '' }), tone: 'no' }
    case 'invitation':
      return { text: t.entry.invitation, tone: 'no' }
    case 'rule':
      return { text: ce.event.rule ? UI_TEXT.tournament.rules[ce.event.rule] : t.entry.invitation, tone: 'no' }
    case 'noTechniques':
      return { text: t.entry.noTechniques, tone: 'no' }
    case 'noMonster':
    case null:
      return { text: t.entry.noMonster, tone: 'no' }
    default:
      return { text: fill(UI_TEXT.tournament.reasons[e.reason], { name, g: '' }), tone: 'no' }
  }
}

function gradeText(ce: CalendarEvent, g: GameState): string {
  const line = gradeLine(ce.event, g.monster?.grade ?? 'E')
  if (line.kind === 'own') return fill(ce.event.kind === 'official' ? t.grade.own : t.grade.ownPlain, { g: line.grade })
  if (line.kind === 'any') return t.grade.any
  if (line.kind === 'invite') return t.grade.invite
  return fill(t.grade.fixed, { g: line.grade })
}

function purseText(ce: CalendarEvent): string {
  if (ce.event.kind === 'summit') return fill(t.summitPurse, { team: gold(TOURNAMENT.summit.teamWin), own: gold(TOURNAMENT.summit.perOwnWin) })
  return gold(ce.purse)
}

function prizeText(ce: CalendarEvent, g: GameState): string {
  const p = TOURNAMENT.itemPrizes
  return fill(t.prizes[ce.prize], { n: ce.prize === 'sweets' ? p.lowSweets : p.highGrandSweets, pct: p.highSheetPct, breed: g.monster ? BREED_BY_ID[g.monster.mainBreed].name : '' })
}

function noteText(n: CalendarNote, g: GameState): string {
  const name = g.monster?.name ?? ''
  switch (n.kind) {
    case 'crown':
      return fill(n.invited ? t.notes.crownInvited : t.notes.crownClose, { event: eventNameOf(n.eventId) })
    case 'legend':
      return t.notes.legend
    case 'market':
      return fill(t.notes.market, { breeds: n.breeds.map((b) => BREED_BY_ID[b].name).join(', ') })
    case 'upgrades':
      return t.notes.upgrades
    case 'birthday':
      return fill(t.notes.birthday, { name, n: n.years })
  }
}

const eventNameOf = (id: string) => EVENT_BY_ID[id]?.name ?? id

/** What the filters let through: events the monster can enter (pinned ones always), expeditions when shown. */
function visibleEvents(w: CalendarWeek): CalendarEvent[] {
  return w.events.filter((ce) => !onlyEnterable.value || ce.entry.eligible || ce.pinned)
}

function visibleExpeditions(w: CalendarWeek, firstShown: boolean): CalendarExpedition[] {
  if (!showExpeditions.value) return []
  // An expedition is open all month: list it on the month's first week, or on the first week shown.
  return w.expeditions.filter((x) => x.opens || firstShown || x.pinned)
}

/* ---------- cards ---------- */

function EventCard({ ce, g, onOpen, compact }: { ce: CalendarEvent; g: GameState; onOpen: () => void; compact?: boolean }) {
  const a = answerOf(ce, g.monster?.name ?? '')
  return (
    <button type="button" class={`calcard ${ce.entry.eligible ? '' : 'calcard--off'} ${compact ? 'calcard--compact' : ''}`} onClick={onOpen}>
      <span class="calcard__icon" aria-hidden="true">
        {EVENT_KIND_ICONS[ce.event.kind]}
      </span>
      <span class="calcard__body">
        <span class="calcard__name">
          {ce.event.name} {ce.event.kind !== 'cup' && <span class="pill">{EVENT_KIND_LABELS[ce.event.kind]}</span>}
          {ce.pinned && (
            <span class="calcard__star" aria-label={t.pinnedLabel}>
              {' '}
              ★
            </span>
          )}
        </span>
        {!compact && (
          <span class="calcard__meta">
            {gradeText(ce, g)} · {FORMAT_LABELS[ce.event.format]} · {purseText(ce)}
          </span>
        )}
        <span class={`calcard__answer calcard__answer--${a.tone}`}>{a.text}</span>
      </span>
    </button>
  )
}

function ExpeditionCard({ ex, g, onOpen }: { ex: CalendarExpedition; g: GameState; onOpen: () => void }) {
  const m = g.monster
  const status = ex.block === 'grade' ? fill(t.expedition.grade, { g: ex.site.gradeMin }) : ex.block === 'fame' ? fill(t.expedition.fame, { f: ex.site.fameMin, name: m?.name ?? '', now: m?.fame ?? 0 }) : fill(t.expedition.ok, { name: m?.name ?? '' })
  return (
    <button type="button" class={`calcard ${ex.block ? 'calcard--off' : ''}`} onClick={onOpen}>
      <span class="calcard__icon" aria-hidden="true">
        {EXPEDITION_ICON}
      </span>
      <span class="calcard__body">
        <span class="calcard__name">
          {ex.site.name} <span class="pill">{ex.opens ? t.expedition.opens : t.expedition.open}</span>
          {ex.pinned && <span class="calcard__star"> ★</span>}
        </span>
        <span class="calcard__meta">{fill(t.expedition.needs, { g: ex.site.gradeMin, f: ex.site.fameMin })}</span>
        <span class={`calcard__answer calcard__answer--${ex.block ? 'no' : 'ok'}`}>{status}</span>
      </span>
    </button>
  )
}

function WeekExtras({ w, g }: { w: CalendarWeek; g: GameState }) {
  const busy = w.busy
  const busyText = busy
    ? busy.kind === 'plan'
      ? fill(t.busy.plan, { what: busy.step.kind === 'rest' ? t.busy.rest : DRILL_BY_ID[busy.step.drill].name })
      : t.busy[busy.kind]
    : null
  return (
    <>
      {busyText && <p class="calweek__busy">{busyText}</p>}
      {w.clashes.map((c) => (
        <p key={c.key} class="calweek__clash" role="note">
          ⚠ {fill(t.clash, { event: c.event.name })}
        </p>
      ))}
      {w.notes.map((n, i) => (
        <p key={i} class="calweek__note">
          <span aria-hidden="true">{CALENDAR_NOTE_ICONS[n.kind]}</span> {noteText(n, g)}
        </p>
      ))}
    </>
  )
}

/* ---------- views ---------- */

function AgendaView({ weeks, g, onOpen }: { weeks: CalendarWeek[]; g: GameState; onOpen: (o: Open) => void }) {
  const name = g.monster?.name ?? ''
  return (
    <div class="calagenda">
      {weeks.map((w, i) => {
        const events = visibleEvents(w)
        const trips = visibleExpeditions(w, i === 0)
        return (
          <section key={w.week} class={`calweek ${w.offset === 0 ? 'calweek--now' : ''} ${w.offset < 0 ? 'calweek--past' : ''}`} aria-label={fill(t.weekOf, { month: MONTH_NAMES[w.date.month - 1], week: w.date.week })}>
            <p class="calweek__head">
              <span class="calweek__when">{whenLabel(w.offset)}</span>
              <span class="muted small">{fill(t.weekOf, { month: MONTH_NAMES[w.date.month - 1], week: w.date.week })}</span>
            </p>
            <WeekExtras w={w} g={g} />
            {events.map((ce) => (
              <EventCard key={ce.key} ce={ce} g={g} onOpen={() => onOpen({ kind: 'event', ce, offset: w.offset })} />
            ))}
            {trips.map((ex) => (
              <ExpeditionCard key={ex.key} ex={ex} g={g} onOpen={() => onOpen({ kind: 'expedition', ex, offset: w.offset })} />
            ))}
            {events.length === 0 && trips.length === 0 && <p class="muted small">{onlyEnterable.value ? fill(t.nothingToEnter, { name }) : t.nothing}</p>}
          </section>
        )
      })}
    </div>
  )
}

function MonthView({ weeks, g, onOpen }: { weeks: CalendarWeek[]; g: GameState; onOpen: (o: Open) => void }) {
  return (
    <div class="calmonth">
      {weeks.map((w, i) => {
        const events = visibleEvents(w)
        const trips = visibleExpeditions(w, i === 0)
        return (
          <section key={w.week} class={`calrow ${w.offset === 0 ? 'calrow--now' : ''} ${w.offset < 0 ? 'calrow--past' : ''}`}>
            <p class="calrow__label">
              {fill(t.weekShort, { n: w.date.week })}
              {w.offset === 0 && <span class="calrow__now"> · {t.thisWeek}</span>}
            </p>
            <div class="calrow__items">
              <WeekExtras w={w} g={g} />
              {events.map((ce) => (
                <EventCard key={ce.key} ce={ce} g={g} compact onOpen={() => onOpen({ kind: 'event', ce, offset: w.offset })} />
              ))}
              {trips.map((ex) => (
                <ExpeditionCard key={ex.key} ex={ex} g={g} onOpen={() => onOpen({ kind: 'expedition', ex, offset: w.offset })} />
              ))}
              {events.length === 0 && trips.length === 0 && <p class="muted small">{t.nothing}</p>}
            </div>
          </section>
        )
      })}
    </div>
  )
}

const TILE_GROUPS = ['official', 'crown', 'open', 'invitational', 'summit'] as const
type TileGroup = (typeof TILE_GROUPS)[number] | 'expedition'
const GROUP_OF: Record<string, TileGroup | null> = { cup: null, official: 'official', crown: 'crown', open: 'open', legend: 'invitational', masquerade: 'invitational', rival: 'invitational', summit: 'summit', summitQualifier: 'summit' }
const GROUP_ICON: Record<TileGroup, string> = { official: EVENT_KIND_ICONS.official, crown: EVENT_KIND_ICONS.crown, open: EVENT_KIND_ICONS.open, invitational: EVENT_KIND_ICONS.masquerade, summit: EVENT_KIND_ICONS.summit, expedition: EXPEDITION_ICON }

function YearView({ weeks, nowWeek, onMonth }: { weeks: CalendarWeek[]; nowWeek: number; onMonth: (monthStart: number) => void }) {
  const months = Array.from({ length: 12 }, (_, i) => weeks.slice(i * WPM, i * WPM + WPM))
  return (
    <div class="calyear">
      {months.map((ws, i) => {
        if (ws.length === 0) return null
        const start = ws[0]!.week
        const groups = new Set<TileGroup>()
        let pinned = false
        for (const w of ws) {
          for (const ce of visibleEvents(w)) {
            const grp = GROUP_OF[ce.event.kind]
            if (grp) groups.add(grp)
            if (ce.pinned) pinned = true
          }
          if (showExpeditions.value && w.expeditions.length > 0) groups.add('expedition')
          if (w.expeditions.some((x) => x.pinned)) pinned = true
        }
        const now = nowWeek >= start && nowWeek < start + WPM
        const past = start + WPM <= nowWeek
        const icons = [...TILE_GROUPS, 'expedition' as const].filter((x) => groups.has(x))
        return (
          <button key={start} type="button" class={`caltile ${now ? 'caltile--now' : ''} ${past ? 'caltile--past' : ''}`} onClick={() => onMonth(start)} aria-label={MONTH_NAMES[i]}>
            <span class="caltile__name">
              {MONTH_NAMES[i]!.slice(0, 3)}
              {pinned && <span class="calcard__star"> ★</span>}
            </span>
            <span class="caltile__icons" aria-hidden="true">
              {icons.map((x) => GROUP_ICON[x]).join(' ')}
            </span>
          </button>
        )
      })}
    </div>
  )
}

/* ---------- details ---------- */

function DetailSheet({ open, g, onClose }: { open: Open | null; g: GameState; onClose: () => void }) {
  if (!open) return null
  const m = g.monster
  const name = m?.name ?? ''
  if (open.kind === 'expedition') {
    const ex = open.ex
    const pinned = g.calendarPins.includes(ex.key)
    return (
      <Sheet open title={ex.site.name} onClose={onClose}>
        <p class="muted small">{ex.site.blurb}</p>
        <dl class="kv">
          <dt>{t.details.open}</dt>
          <dd>{ex.site.months.map((mo) => MONTH_NAMES[mo - 1]).join(', ')}</dd>
          <dt>{t.details.needs}</dt>
          <dd>{fill(t.expedition.needs, { g: ex.site.gradeMin, f: ex.site.fameMin })}</dd>
          <dt>{t.details.status}</dt>
          <dd>{ex.block === 'grade' ? fill(t.expedition.grade, { g: ex.site.gradeMin }) : ex.block === 'fame' ? fill(t.expedition.fame, { f: ex.site.fameMin, name, now: m?.fame ?? 0 }) : fill(t.expedition.ok, { name })}</dd>
        </dl>
        <div class="sheet__actions">
          <button type="button" class={`btn ${pinned ? 'btn--primary' : ''}`} aria-pressed={pinned} onClick={() => toggleCalendarPin(ex.key)}>
            {pinned ? t.unpin : t.pin}
          </button>
          <button type="button" class="btn btn--ghost" onClick={onClose}>
            {t.close}
          </button>
        </div>
      </Sheet>
    )
  }
  const ce = open.ce
  const pinned = g.calendarPins.includes(ce.key)
  const a = answerOf(ce, name)
  const d = dateOf(Number(ce.key.split(':')[0]))
  const rounds = ce.rounds === 1 ? t.oneMatch : fill(t.rounds, { n: ce.rounds })
  const canEnter = open.offset === 0 && ce.entry.eligible
  return (
    <Sheet open title={ce.event.name} onClose={onClose}>
      <dl class="kv">
        <dt>{t.details.when}</dt>
        <dd>
          {fill(t.weekOf, { month: MONTH_NAMES[d.month - 1], week: d.week })} · {whenLabel(open.offset)}
        </dd>
        <dt>{t.details.grade}</dt>
        <dd>
          {gradeText(ce, g)} {ce.event.kind !== 'cup' && <span class="pill">{EVENT_KIND_LABELS[ce.event.kind]}</span>}
        </dd>
        <dt>{t.details.format}</dt>
        <dd>
          {FORMAT_LABELS[ce.event.format]} · {rounds}
        </dd>
        <dt>{t.details.purse}</dt>
        <dd>{purseText(ce)}</dd>
        <dt>{t.details.prize}</dt>
        <dd>{prizeText(ce, g)}</dd>
        <dt>{fill(t.details.entry, { name })}</dt>
        <dd class={`calcard__answer calcard__answer--${a.tone}`}>{a.text}</dd>
      </dl>
      {m && <p class="muted small">{fill(t.basedOn, { name, grade: m.grade })}</p>}
      <div class="sheet__actions">
        {open.offset === 0 && (
          <button
            type="button"
            class="btn btn--primary"
            disabled={!canEnter}
            onClick={() => {
              entryPreselect.value = ce.event.id
              onClose()
              navigate('tournament')
            }}
          >
            {t.enter}
          </button>
        )}
        <button type="button" class={`btn ${pinned ? 'btn--primary' : ''}`} aria-pressed={pinned} onClick={() => toggleCalendarPin(ce.key)}>
          {pinned ? t.unpin : t.pin}
        </button>
        <button type="button" class="btn btn--ghost" onClick={onClose}>
          {t.close}
        </button>
      </div>
    </Sheet>
  )
}

/* ---------- the screen ---------- */

/** §3 the Calendar: what's coming, week by week, to plan training around. Opened from the ranch's date bar, Town and the cup entry. */
export function CalendarScreen() {
  const g = game.value
  const [open, setOpen] = useState<Open | null>(null)
  useEffect(() => {
    if (!g) navigate('title')
  }, [g === null])
  // Opening the calendar starts on this month.
  useEffect(() => {
    calendarCursor.value = null
  }, [])
  if (!g) return null

  const now = g.week
  const thisMonth = monthStartOf(now)
  const minCursor = yearStartOf(now)
  const maxCursor = yearStartOf(now) + (CALENDAR_YEARS_AHEAD + 1) * WEEKS_PER_YEAR - WPM
  const cursor = Math.min(maxCursor, Math.max(minCursor, calendarCursor.value ?? thisMonth))
  const cd = dateOf(cursor)
  const view = calendarView.value
  const move = (weeks: number) => (calendarCursor.value = Math.min(maxCursor, Math.max(minCursor, cursor + weeks)))

  // A pin toggled in the sheet: keep the sheet's card in step with the save.
  const live = (o: Open | null): Open | null => {
    if (!o) return null
    if (o.kind === 'event') return { ...o, ce: { ...o.ce, pinned: g.calendarPins.includes(o.ce.key) } }
    return { ...o, ex: { ...o.ex, pinned: g.calendarPins.includes(o.ex.key) } }
  }

  const agendaStart = cursor === thisMonth ? now : cursor
  const weeks = view === 'agenda' ? calendarWeeks(g, agendaStart, 12) : view === 'month' ? calendarWeeks(g, cursor, WPM) : calendarWeeks(g, yearStartOf(cursor), WEEKS_PER_YEAR)
  const nd = dateOf(now)
  const viewOptions: { value: CalendarViewKind; label: string }[] = [
    { value: 'agenda', label: t.views.agenda },
    { value: 'month', label: t.views.month },
    { value: 'year', label: t.views.year },
  ]

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <section class="card calhead">
        <p class="calhead__today">{fill(t.today, { year: nd.year, month: MONTH_NAMES[nd.month - 1], week: nd.week })}</p>
        <div class="calnav">
          <button type="button" class="iconbtn" aria-label={t.prevYear} disabled={cursor - WEEKS_PER_YEAR < minCursor} onClick={() => move(-WEEKS_PER_YEAR)}>
            «
          </button>
          <button type="button" class="iconbtn" aria-label={t.prevMonth} disabled={cursor <= minCursor} onClick={() => move(-WPM)}>
            ‹
          </button>
          <p class="calnav__label" aria-live="polite">
            {view === 'year' ? fill(t.yearTitle, { year: cd.year }) : fill(t.monthTitle, { month: MONTH_NAMES[cd.month - 1], year: cd.year })}
            {isSummitYear(cd.year) && <span class="pill calnav__summit">{t.summitYear}</span>}
          </p>
          <button type="button" class="iconbtn" aria-label={t.nextMonth} disabled={cursor >= maxCursor} onClick={() => move(WPM)}>
            ›
          </button>
          <button type="button" class="iconbtn" aria-label={t.nextYear} disabled={cursor + WEEKS_PER_YEAR > maxCursor} onClick={() => move(WEEKS_PER_YEAR)}>
            »
          </button>
        </div>
        <Segmented options={viewOptions} value={view} onChange={(v) => (calendarView.value = v)} label={t.viewLabel} />
        <Toggle label={t.onlyEnterable} checked={onlyEnterable.value} onChange={(v) => (onlyEnterable.value = v)} />
        <Toggle label={t.showExpeditions} checked={showExpeditions.value} onChange={(v) => (showExpeditions.value = v)} />
      </section>

      {view === 'agenda' && <AgendaView weeks={weeks} g={g} onOpen={setOpen} />}
      {view === 'month' && <MonthView weeks={weeks} g={g} onOpen={setOpen} />}
      {view === 'year' && (
        <YearView
          weeks={weeks}
          nowWeek={now}
          onMonth={(start) => {
            calendarCursor.value = start
            calendarView.value = 'month'
          }}
        />
      )}
      <DetailSheet open={live(open)} g={g} onClose={() => setOpen(null)} />
    </main>
  )
}
