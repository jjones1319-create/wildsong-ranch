import { dateOf, weekIndexOf } from '../../../core/calendar.ts'
import { eventsAt } from '../../../data/calendar.ts'
import { purseOf } from '../../../core/tournament.ts'
import { fill } from '../../../data/text/format.ts'
import { EVENT_KIND_LABELS, FORMAT_LABELS, MONTH_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { game } from '../../store/gameStore.ts'

/** §21 the Breeders' Guild: this month's cups, rank, titles, invitations, the Hall of Fame, and the Library. */
export function GuildScreen() {
  const g = game.value
  const t = UI_TEXT.guild
  if (!g) return null
  const d = dateOf(g.week)
  const grade = g.monster?.grade ?? 'E'
  const weeks = [1, 2, 3, 4].map((w) => ({ w, events: eventsAt(weekIndexOf({ year: d.year, month: d.month, week: w }) % 48, d.year) }))
  const invites = [g.guild.crownInvite ? 'Crowns' : null, g.guild.legendInvite ? 'Wildsong Legend' : null].filter(Boolean)
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.ines} tone="muted">
        <p>{t.hello}</p>
      </SpeakerCard>
      <section class="card">
        <p class="field__label">
          {t.thisMonth} · {MONTH_NAMES[d.month - 1]}
        </p>
        {weeks.map(({ w, events }) => (
          <div class="item" key={w}>
            <span class="item__body">
              <span class={`item__name ${w === d.week ? '' : 'muted'}`}>{fill(t.week, { n: w })}</span>
              {events.map((e) => (
                <span class="item__meta" key={e.id}>
                  {e.name} · {EVENT_KIND_LABELS[e.kind]} · {e.grade === 'own' ? UI_TEXT.tournament.gradeOwn : e.grade === 'any' ? UI_TEXT.tournament.gradeAny : fill(UI_TEXT.tournament.grade, { g: e.grade })} · {FORMAT_LABELS[e.format]} · {gold(purseOf(e, grade))}
                </span>
              ))}
            </span>
          </div>
        ))}
      </section>
      <section class="card">
        <p class="field__label">{fill(t.rank, { n: g.breeder.rank })}</p>
        <p class="muted small">{t.rankHint}</p>
        <p class="small">{fill(t.officials, { list: g.guild.officialsWon.length ? g.guild.officialsWon.join(', ') : t.none })}</p>
        <p class="small">{fill(t.crowns, { n: g.guild.crownsWon.length })}</p>
        <p class="small">{fill(t.invite, { list: invites.length ? invites.join(', ') : t.none })}</p>
      </section>
      <section class="card">
        <p class="field__label">{t.titles}</p>
        {g.titles.length === 0 ? <p class="muted">{t.noTitles}</p> : <p>{g.titles.join(' · ')}</p>}
      </section>
      <section class="card">
        <p class="field__label">{t.hallOfFame}</p>
        {g.hallOfFame.length === 0 && <p class="muted">{t.noHall}</p>}
        {g.hallOfFame.map((h, i) => (
          <div class="item" key={i}>
            <MonsterPortrait monster={h.monster} size={56} animate={false} />
            <span class="item__body">
              <span class="item__name">{h.monster.name}</span>
              <span class="item__meta">
                {UI_TEXT.ranch.year.replace('{year}', String(dateOf(h.week).year))} · {MONTH_NAMES[dateOf(h.week).month - 1]}
              </span>
            </span>
          </div>
        ))}
      </section>
      <div class="spacer" />
      <div class="actionbar actionbar--stack">
        <button type="button" class="btn" onClick={() => navigate('library')}>
          {t.library}
        </button>
        <div class="actions__row">
          <button type="button" class="btn btn--half" onClick={() => navigate('journal')}>
            {t.journal}
          </button>
          <button type="button" class="btn btn--half" onClick={() => navigate('upgrades')}>
            {t.upgrades}
          </button>
        </div>
      </div>
    </main>
  )
}
