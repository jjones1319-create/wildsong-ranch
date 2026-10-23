import { useEffect } from 'preact/hooks'
import { eventName, isComplete, isElimination, nextPlayerMatch, standings } from '../../../core/tournament.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
import { navigate } from '../../router.ts'
import { game } from '../../store/gameStore.ts'
import { conclude, playNext, simulateRest } from '../../store/tournamentStore.ts'

/** A cup in progress: standings or bracket, the player's next match, the rest simulated, then the results. */
export function TournamentPlayScreen() {
  const g = game.value
  const t = UI_TEXT.tournament.play
  const tt = g?.tournament ?? null
  const next = tt ? nextPlayerMatch(tt) : null

  useEffect(() => {
    if (!g) navigate('title')
    else if (!tt) navigate('ranch')
  }, [g === null, tt === null])

  // No match of ours is waiting: let the others fight until ours is ready or the cup is over.
  useEffect(() => {
    if (tt && !next && !isComplete(tt)) simulateRest()
  }, [tt?.matches.filter((m) => m.result).length, next === null])

  if (!g || !tt) return null
  const names = tt.participants.map((p) => (p.player ? g.monster!.name : p.name))
  const table = standings(tt)
  const complete = isComplete(tt)
  const elim = isElimination(tt)
  const rounds = [...new Set(tt.matches.map((m) => m.round))]

  return (
    <main class="screen">
      <TopBar title={eventName(tt.eventId)} onBack={() => navigate('ranch')} />
      <section class="card">
        <p class="field__label">{elim ? t.bracket : t.standings}</p>
        {elim ? (
          rounds.map((r) => (
            <div key={r}>
              <p class="muted small" style={{ margin: '6px 0 2px' }}>
                {fill(t.round, { n: r })}
              </p>
              {tt.matches
                .filter((m) => m.round === r)
                .map((m, i) => (
                  <div class="item" key={`${r}-${i}`}>
                    <span class="item__body">
                      <span class={`item__name ${m.a === 0 || m.b === 0 ? '' : 'muted'}`}>
                        {names[m.a]} vs {names[m.b]}
                      </span>
                      <span class="item__meta">
                        {m.result ? (m.result.winner === null ? '—' : `${names[m.result.winner === 0 ? m.a : m.b]} ${m.result.how === 'ko' ? '(KO)' : m.result.how === 'walkover' ? `(${t.walkover})` : ''}`) : t.pending}
                      </span>
                    </span>
                  </div>
                ))}
            </div>
          ))
        ) : (
          <table class="bresult__table">
            <thead>
              <tr>
                <th />
                <th>{t.points}</th>
                <th>{t.wins}</th>
                <th>{t.kos}</th>
              </tr>
            </thead>
            <tbody>
              {table.map((s) => (
                <tr key={s.index} class={s.index === 0 ? 'row--me' : ''}>
                  <td>
                    {s.place}. {names[s.index]}
                    {tt.koOut.includes(s.index) ? ' (KO)' : ''}
                  </td>
                  <td>{s.points}</td>
                  <td>{s.wins}</td>
                  <td>{s.kos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {next && (
        <section class="card">
          <p class="field__label">{t.yourMatch}</p>
          <p>{fill(t.nextMatch, { a: g.monster!.name, b: names[next.match.a === 0 ? next.match.b : next.match.a] ?? '' })}</p>
        </section>
      )}
      {!next && !complete && <p class="muted small center">{t.out}</p>}

      <div class="spacer" />
      <div class="actionbar">
        {next ? (
          <button type="button" class="btn btn--primary" onClick={playNext}>
            {tt.mode === 'manual' ? t.fight : t.watch}
          </button>
        ) : (
          <button type="button" class="btn btn--primary" disabled={!complete} onClick={conclude}>
            {t.finishCup}
          </button>
        )}
      </div>
    </main>
  )
}
