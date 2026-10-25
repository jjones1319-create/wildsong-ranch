import { useEffect, useMemo, useState } from 'preact/hooks'
import { createTournament, eventsForWeek, gradeIndex, type WeekEventView } from '../../../core/tournament.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { RIVAL_BY_ID } from '../../../data/rivals.ts'
import { fill } from '../../../data/text/format.ts'
import { EVENT_KIND_LABELS, FORMAT_LABELS, PERSONALITY_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TOURNAMENT } from '../../../data/tuning.ts'
import { Segmented, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { gold } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { game } from '../../store/gameStore.ts'
import { enter } from '../../store/tournamentStore.ts'
import { versusSideA } from '../../store/versusStore.ts'

/** §21 Tournament entry: this week's events, eligible first, with rules, purse, opponents and the cup's default (Fight / Auto). */
export function TournamentEntryScreen() {
  const g = game.value
  const t = UI_TEXT.tournament
  const [picked, setPicked] = useState<string | null>(null)
  // §12.11 the cup's default for each of the player's matches; Fight unless the player last chose Auto.
  const [mode, setMode] = useState<'auto' | 'manual'>(settings.value.cupMode)
  useEffect(() => {
    if (!g || !g.monster) navigate('ranch')
    else if (g.tournament) navigate('tournamentPlay')
  }, [g === null, g?.tournament !== null])
  if (!g || !g.monster) return null
  const views = eventsForWeek(g)
  const chosen = views.find((v) => v.event.id === picked && v.eligible) ?? null
  const preview = useMemo(() => (chosen ? createTournament(g, chosen.event.id, mode) : null), [chosen?.event.id, g.week])
  const m = g.monster

  const gradeText = (v: WeekEventView) => (v.event.grade === 'own' ? t.gradeOwn : v.event.grade === 'any' ? t.gradeAny : fill(t.grade, { g: v.event.grade }))
  const reasonText = (v: WeekEventView) => (v.reason ? fill(t.reasons[v.reason], { name: m.name, g: v.event.minGrade ?? '' }) : '')

  return (
    <main class="screen">
      <TopBar title={t.title} />
      {views.length === 0 && <p class="empty">{t.none}</p>}
      <div class="list">
        {views.map((v) => (
          <button key={v.event.id} type="button" class={`choice ${picked === v.event.id ? 'choice--on' : ''} ${v.eligible ? '' : 'townrow--off'}`} disabled={!v.eligible} onClick={() => setPicked(v.event.id)}>
            <span class="choice__name">
              {v.event.name} <span class="pill">{EVENT_KIND_LABELS[v.event.kind]}</span>
            </span>
            <span class="choice__blurb">
              {gradeText(v)} · {FORMAT_LABELS[v.event.format]} · {fill(t.purse, { n: gold(v.purse) })}
              {v.event.rule ? ` · ${t.rules[v.event.rule]}` : ''}
            </span>
            {v.tooEasy && <span class="choice__blurb food__tag--bad">{t.tooEasy}</span>}
            {!v.eligible && <span class="choice__blurb food__tag--bad">{reasonText(v)}</span>}
          </button>
        ))}
      </div>

      {chosen && preview && (
        <section class="card">
          <p class="field__label">{t.opponents}</p>
          <p class="muted small">{fill(t.perWin, { n: TOURNAMENT.perWinGoldPerGrade * gradeIndex(m.grade) })}</p>
          {preview.participants.slice(1).map((p, i) => {
            const rival = p.rivalId ? RIVAL_BY_ID[p.rivalId] : null
            return (
              <div class="item" key={i}>
                <MonsterPortrait monster={p.monster} size={56} animate={false} />
                <span class="item__body">
                  <span class="item__name">
                    {rival ? `${rival.name} · ` : ''}
                    {p.monster.name} <span class="pill">{BREED_BY_ID[p.monster.mainBreed].name}</span>
                  </span>
                  <span class="item__meta">
                    {fill(t.grade, { g: p.monster.grade })} · {PERSONALITY_LABELS[p.personality].name}
                    {rival ? ` · ${t.habit}: ${rival.habitHint}` : ''}
                  </span>
                </span>
              </div>
            )
          })}
          <p class="field__label" style={{ marginTop: 10 }}>
            {t.mode}
          </p>
          <Segmented
            options={[
              { value: 'manual', label: t.modes.manual },
              { value: 'auto', label: t.modes.auto },
            ]}
            value={mode}
            onChange={setMode}
            label={t.mode}
          />
          <p class="field__hint">{t.modeHint}</p>
        </section>
      )}

      <div class="spacer" />
      <div class="actionbar actionbar--stack">
        <button type="button" class="btn btn--primary" disabled={!chosen} onClick={() => chosen && enter(chosen.event.id, mode)}>
          {chosen ? `${t.enter}: ${chosen.event.name}` : t.enter}
        </button>
        <div class="actions__row">
          <button
            type="button"
            class="btn btn--half btn--ghost"
            onClick={() => {
              versusSideA.value = { monster: structuredClone(m), source: 'active' }
              navigateFrom('ranch', 'labVersus')
            }}
          >
            {t.spar}
          </button>
        </div>
      </div>
    </main>
  )
}
