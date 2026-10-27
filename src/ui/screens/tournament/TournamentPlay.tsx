import { useEffect, useMemo, useState } from 'preact/hooks'
import type { MatchResult, TournamentState } from '../../../core/state.ts'
import { callingCardFor } from '../../../audio/music/effects.ts'
import { playSfx } from '../../../audio/player.ts'
import { bracket, currentRound, eventName, isComplete, isElimination, nextPlayerMatch, opponentOf, placeChanges, playerMatchIn, relayLegs, roundCount, roundsDone, standings, type BracketSlot, type RelayLeg, type SlotSide } from '../../../core/tournament.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { EVENT_BY_ID } from '../../../data/calendar.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { BATTLE } from '../../../data/tuning.ts'
import { Segmented, Sheet, TopBar } from '../../components/Controls.tsx'
import { navigate } from '../../router.ts'
import { game } from '../../store/gameStore.ts'
import { conclude, nextRound, playMatch, playRound, recapRound, skipToFinal, watchMatch } from '../../store/tournamentStore.ts'

const p = UI_TEXT.tournament.play

/** The cup and round whose calling card already played (a re-render never plays it twice). */
let cardPlayedFor = ''

/** The named rival the round preview shows (the player's next match this round), if any. */
function previewRivalOf(tt: TournamentState | null): { key: string; rivalId: string } | null {
  if (!tt || recapRound.value !== null) return null
  const next = nextPlayerMatch(tt)
  const round = currentRound(tt)
  if (!next || round === null || next.match.round !== round) return null
  const rivalId = opponentOf(tt, next.match).rivalId
  return rivalId ? { key: `${tt.seed}:${round}`, rivalId } : null
}

type Tab = 'standings' | 'rounds' | 'bracket' | 'team' | 'legs'

/** A finished match opened from any list. `watch` is set for an NPC match that can be replayed exactly. */
interface Detail {
  title: string
  a: string
  b: string
  result: MatchResult
  watch: number | null
}

const pct = (tenths: number) => Math.round(tenths / 10)

function clock(ticks: number | undefined): string {
  if (ticks === undefined) return p.detail.unknown
  const s = Math.floor(ticks / BATTLE.ticksPerSecond)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function howOf(r: MatchResult): string {
  if (r.how === 'walkover') return p.how.walkover
  if (r.how === 'ko') return p.how.ko
  if (r.how === 'forfeit') return p.how.forfeit
  return r.winner === null ? p.how.draw : p.how.decision
}

/** "Pip beat Rex · KO · HP 62% · 0%" (HP from the winner's side first; none for a walkover). */
function resultLine(r: MatchResult, a: string, b: string): string {
  const head = r.winner === null ? fill(p.drew, { a, b }) : r.winner === 0 ? fill(p.beat, { w: a, l: b }) : fill(p.beat, { w: b, l: a })
  if (r.how === 'walkover') return `${head} · ${howOf(r)}`
  const [first, second] = r.winner === 1 ? [r.hpPct[1], r.hpPct[0]] : [r.hpPct[0], r.hpPct[1]]
  return `${head} · ${howOf(r)} · ${fill(p.hpLeft, { a: pct(first), b: pct(second) })}`
}

/** Elimination rounds are named from the end: Final, Semi-finals, Quarter-finals. */
function roundName(t: TournamentState, r: number): string {
  if (!isElimination(t)) return fill(p.round, { n: r })
  const fromEnd = roundCount(t) - r
  return fromEnd === 0 ? p.final : fromEnd === 1 ? p.semis : fromEnd === 2 ? p.quarters : fill(p.round, { n: r })
}

/**
 * Display names: the player's monster, rival breeders and wild monsters. Wild names can repeat within a cup, so a
 * repeated name gets its breed (and a number if even that repeats); the saved cup is never changed.
 */
function namesOf(t: TournamentState, playerName: string): string[] {
  const base = t.participants.map((x) => (x.player ? playerName : x.name))
  const withBreed = base.map((n, i) => (i > 0 && base.filter((m) => m === n).length > 1 ? `${n} (${BREED_BY_ID[t.participants[i]!.monster.mainBreed].name})` : n))
  return withBreed.map((n, i) => (withBreed.filter((m) => m === n).length > 1 ? `${n} ${withBreed.slice(0, i + 1).filter((m) => m === n).length}` : n))
}

/* ---------- pieces ---------- */

function StandingsTable({ t, names, upTo, arrows }: { t: TournamentState; names: string[]; upTo?: number; arrows?: boolean }) {
  const elim = isElimination(t)
  const rows = standings(t, upTo)
  const changes = arrows && upTo !== undefined ? placeChanges(t, upTo) : new Map<number, number>()
  return (
    <table class="ctable">
      <thead>
        <tr>
          <th class="ctable__place">{p.place}</th>
          <th class="ctable__name">{p.name}</th>
          {!elim && <th>{p.points}</th>}
          <th>{p.wld}</th>
          <th>{p.kos}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((s) => {
          const d = changes.get(s.index) ?? 0
          return (
            <tr key={s.index} class={s.index === 0 ? 'row--me' : ''}>
              <td class="ctable__place">{s.place}</td>
              <td class="ctable__name">
                <span class="ctable__who">{names[s.index]}</span>
                {t.koOut.includes(s.index) && <span class="ctable__tag"> KO</span>}
                {d !== 0 && (
                  <span class={`ctable__chg ${d > 0 ? 'ctable__chg--up' : 'ctable__chg--down'}`} aria-label={fill(d > 0 ? p.upLabel : p.downLabel, { n: Math.abs(d) })}>
                    {' '}
                    {fill(d > 0 ? p.up : p.down, { n: Math.abs(d) })}
                  </span>
                )}
              </td>
              {!elim && <td>{s.points}</td>}
              <td>{`${s.wins}-${s.losses}-${s.draws}`}</td>
              <td>{s.kos}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

/** One match as a row: who fights who, then the result or "upcoming". Finished rows open the details. */
function MatchRow({ t, names, index, onOpen, label }: { t: TournamentState; names: string[]; index: number; onOpen: (d: Detail) => void; label?: string }) {
  const m = t.matches[index]!
  const a = names[m.a]!
  const b = names[m.b]!
  const mine = m.a === 0 || m.b === 0
  const r = m.result
  const open = r ? () => onOpen({ title: `${label ?? roundName(t, m.round)} · ${a} vs ${b}`, a, b, result: r, watch: !mine && r.how !== 'walkover' ? index : null }) : undefined
  return (
    <button type="button" class={`cuprow ${mine ? 'cuprow--me' : ''}`} disabled={!r} onClick={open}>
      <span class="cuprow__main">
        {label && <span class="pill">{label}</span>} {a} <span class="muted">vs</span> {b}
      </span>
      <span class="cuprow__meta">{r ? resultLine(r, a, b) : p.upcoming}</span>
    </button>
  )
}

function RoundsList({ t, names, onOpen }: { t: TournamentState; names: string[]; onOpen: (d: Detail) => void }) {
  const total = roundCount(t)
  const tree = isElimination(t) ? bracket(t) : null
  return (
    <div>
      {Array.from({ length: total }, (_, k) => k + 1).map((r) => {
        const real = t.matches.map((m, i) => ({ m, i })).filter((x) => x.m.round === r)
        const future = tree ? tree[r - 1]!.filter((s) => s.match === null) : []
        return (
          <section key={r} class="cupround">
            <p class="cupround__title">{roundName(t, r)}</p>
            {real.map((x) => (
              <MatchRow key={x.i} t={t} names={names} index={x.i} onOpen={onOpen} />
            ))}
            {future.map((s) => (
              <div key={`f${s.slot}`} class="cuprow cuprow--future">
                <span class="cuprow__main">
                  {sideName(t, names, s.a)} <span class="muted">vs</span> {sideName(t, names, s.b)}
                </span>
                <span class="cuprow__meta">{p.upcoming}</span>
              </div>
            ))}
          </section>
        )
      })}
      <p class="muted small">{p.tapHint}</p>
    </div>
  )
}

/** A bracket side: a name, or "Winner of A vs B" (or of a match whose sides aren't known yet either). */
function sideName(t: TournamentState, names: string[], side: SlotSide): string {
  if (side.kind === 'p') return names[side.index]!
  const feed = bracket(t)[side.round - 1]?.[side.slot]
  if (feed && feed.a.kind === 'p' && feed.b.kind === 'p') return fill(p.winnerOf, { a: names[feed.a.index]!, b: names[feed.b.index]! })
  return fill(p.winnerOfRound, { round: roundName(t, side.round), n: side.slot + 1 })
}

function BracketView({ t, names, onOpen }: { t: TournamentState; names: string[]; onOpen: (d: Detail) => void }) {
  const tree = bracket(t)
  const slotBox = (s: BracketSlot) => {
    const m = s.match !== null ? t.matches[s.match]! : null
    const r = m?.result ?? null
    const winnerSide = r ? (r.winner === null ? (r.hpPct[0] >= r.hpPct[1] ? 0 : 1) : r.winner) : null
    const line = (side: SlotSide, k: 0 | 1) => (
      <span class={`bslot__side ${side.kind === 'p' && side.index === 0 ? 'bslot__side--me' : ''} ${winnerSide === k ? 'bslot__side--won' : ''} ${side.kind !== 'p' ? 'muted' : ''}`}>{sideName(t, names, side)}</span>
    )
    const a = s.a.kind === 'p' ? names[s.a.index]! : ''
    const b = s.b.kind === 'p' ? names[s.b.index]! : ''
    const open = r && m ? () => onOpen({ title: `${roundName(t, s.round)} · ${a} vs ${b}`, a, b, result: r, watch: m.a !== 0 && m.b !== 0 && r.how !== 'walkover' ? s.match : null }) : undefined
    return (
      <button type="button" key={`${s.round}-${s.slot}`} class="bslot" disabled={!r} onClick={open}>
        {line(s.a, 0)}
        {line(s.b, 1)}
      </button>
    )
  }
  return (
    <div class="bracket" style={{ '--cols': tree.length }}>
      {tree.map((slots, i) => (
        <div class="bracket__col" key={i}>
          <p class="bracket__title">{roundName(t, i + 1)}</p>
          <div class="bracket__slots">{slots.map(slotBox)}</div>
        </div>
      ))}
    </div>
  )
}

function LegsList({ t, names, legs, onOpen }: { t: TournamentState; names: string[]; legs: RelayLeg[]; onOpen: (d: Detail) => void }) {
  return (
    <div>
      {legs.map((leg) => {
        if (leg.player) return <MatchRow key={leg.grade} t={t} names={names} index={0} onOpen={onOpen} label={fill(p.leg, { g: leg.grade })} />
        const a = `${p.vale} ${leg.vale!.name}`
        const b = `${p.coast} ${leg.coast!.name}`
        const r = leg.result!
        return (
          <button key={leg.grade} type="button" class="cuprow" onClick={() => onOpen({ title: `${fill(p.leg, { g: leg.grade })} · ${a} vs ${b}`, a, b, result: r, watch: null })}>
            <span class="cuprow__main">
              <span class="pill">{fill(p.leg, { g: leg.grade })}</span> {a} <span class="muted">vs</span> {b}
            </span>
            <span class="cuprow__meta">{resultLine(r, a, b)}</span>
          </button>
        )
      })}
      <p class="muted small">{p.tapHint}</p>
    </div>
  )
}

function teamScore(t: TournamentState, legs: RelayLeg[]): { vale: number; coast: number } {
  let vale = 0
  let coast = 0
  for (const leg of legs) {
    const r = leg.player ? t.matches[0]!.result : leg.result
    if (!r || r.winner === null) continue
    if (r.winner === 0) vale += 1
    else coast += 1
  }
  return { vale, coast }
}

function DetailSheet({ d, onClose }: { d: Detail | null; onClose: () => void }) {
  if (!d) return null
  const r = d.result
  return (
    <Sheet open title={d.title} onClose={onClose}>
      <dl class="kv">
        <dt>{p.detail.winner}</dt>
        <dd>{r.winner === null ? p.detail.draw : r.winner === 0 ? d.a : d.b}</dd>
        <dt>{p.detail.ended}</dt>
        <dd>{howOf(r)}</dd>
        {r.how !== 'walkover' && (
          <>
            <dt>{p.detail.hp}</dt>
            <dd>
              {d.a} {pct(r.hpPct[0])}% · {d.b} {pct(r.hpPct[1])}%
            </dd>
            <dt>{p.detail.time}</dt>
            <dd>{clock(r.ticks)}</dd>
          </>
        )}
      </dl>
      <div class="sheet__actions">
        {d.watch !== null && (
          <button type="button" class="btn btn--primary" onClick={() => watchMatch(d.watch!)}>
            {p.detail.watch}
          </button>
        )}
        <button type="button" class="btn" onClick={onClose}>
          {p.detail.close}
        </button>
      </div>
    </Sheet>
  )
}

/* ---------- the screen ---------- */

/**
 * §13 a cup in progress, one round at a time: the round's preview with the player's match (Fight, Auto, Skip),
 * then the round's results and the standings after it (with place changes), then the next round. Below, the
 * tournament breakdown: Standings, Rounds and (elimination) the Bracket; for the Summit, the Team score and Legs.
 */
export function TournamentPlayScreen() {
  const g = game.value
  const tt = g?.tournament ?? null
  const event = tt ? EVENT_BY_ID[tt.eventId] : null
  const summit = event?.kind === 'summit'
  const [tab, setTab] = useState<Tab>(summit ? 'team' : 'standings')
  const [detail, setDetail] = useState<Detail | null>(null)
  const legs = useMemo(() => (tt && summit ? relayLegs(tt, tt.participants[0]!.monster.grade) : []), [tt?.seed, summit])
  // Sound 2.0 §3.6: a named rival's calling card plays over the lobby when the round preview shows them.
  const preview = previewRivalOf(tt)
  useEffect(() => {
    if (!preview || preview.key === cardPlayedFor) return
    const card = callingCardFor(preview.rivalId)
    if (!card) return
    cardPlayedFor = preview.key
    const timer = setTimeout(() => playSfx(card), 700)
    return () => clearTimeout(timer)
  }, [preview?.key, preview?.rivalId])

  useEffect(() => {
    if (!g) navigate('title')
    else if (!tt) navigate('ranch')
  }, [g === null, tt === null])

  if (!g || !tt || !event) return null
  const names = namesOf(tt, g.monster?.name ?? tt.participants[0]!.monster.name)
  const elim = isElimination(tt)
  const total = roundCount(tt)
  const complete = isComplete(tt)
  const round = currentRound(tt)
  const next = nextPlayerMatch(tt)
  const recapStored = recapRound.value
  const recap = recapStored !== null && tt.matches.some((m) => m.round === recapStored && m.result) ? recapStored : null
  const single = event.format === '1v1' || event.format === 'Relay'
  const myRound = next && round !== null && next.match.round === round ? next : null
  const defaultPlay = tt.mode === 'auto' ? 'auto' : 'fight'
  const monsterName = names[0]!
  const title = (r: number) => (summit ? fill(p.yourLeg, { g: tt.participants[0]!.monster.grade }) : single ? p.theMatch : elim ? `${roundName(tt, r)} · ${fill(p.roundOf, { n: r, total })}` : fill(p.roundOf, { n: r, total }))
  const roundRows = (r: number) =>
    tt.matches
      .map((m, i) => ({ m, i }))
      .filter((x) => x.m.round === r)
      .map((x) => <MatchRow key={x.i} t={tt} names={names} index={x.i} onOpen={setDetail} />)
  const score = summit ? teamScore(tt, legs) : null

  const tabs: { value: Tab; label: string }[] = summit
    ? [
        { value: 'team', label: p.team },
        { value: 'legs', label: p.legs },
      ]
    : [{ value: 'standings', label: p.standings }, { value: 'rounds', label: p.rounds }, ...(elim ? [{ value: 'bracket' as const, label: p.bracket }] : [])]
  const shownTab = tabs.some((x) => x.value === tab) ? tab : tabs[0]!.value

  /** After a round (and at the end): the standings, the bracket's survivors, or the Summit's score. */
  const tableAfter = (r: number | undefined) =>
    summit && score ? (
      <p class="cupscore">{fill(p.teamScore, { v: score.vale, c: score.coast })}</p>
    ) : elim && r !== undefined && !complete ? (
      <p class="muted small">
        {fill(p.stillIn, {
          names: tt.participants
            .map((_, i) => i)
            .filter((i) => !tt.eliminated.includes(i))
            .map((i) => names[i])
            .join(', '),
        })}
      </p>
    ) : (
      <StandingsTable t={tt} names={names} upTo={r} arrows={r !== undefined} />
    )

  let flow
  let actions
  if (recap !== null) {
    flow = (
      <section class="card cupflow">
        <p class="field__label">{single || summit ? title(recap) : fill(p.roundResults, { n: recap })}</p>
        <div class="cuprows">{roundRows(recap)}</div>
        <p class="field__label cupflow__sub">{complete ? p.finalStandings : summit ? p.team : fill(p.afterRound, { n: recap, total })}</p>
        {tableAfter(complete ? undefined : recap)}
      </section>
    )
    actions = complete ? (
      <button type="button" class="btn btn--primary" onClick={conclude}>
        {p.finishCup}
      </button>
    ) : (
      <button type="button" class="btn btn--primary" onClick={nextRound}>
        {fill(p.nextRound, { n: (round ?? recap + 1) })}
      </button>
    )
  } else if (complete || round === null) {
    flow = (
      <section class="card cupflow">
        <p class="field__label">{p.finalStandings}</p>
        {summit && score && <p class="cupscore">{score.vale >= 3 ? p.teamWin : p.teamLoss}</p>}
        {tableAfter(undefined)}
      </section>
    )
    actions = (
      <button type="button" class="btn btn--primary" onClick={conclude}>
        {p.finishCup}
      </button>
    )
  } else {
    const opp = myRound ? names[myRound.match.a === 0 ? myRound.match.b : myRound.match.a]! : ''
    // No match to play this round: a walkover (won or lost), out of the cup, or (an old schedule) a round off.
    const playedHere = playerMatchIn(tt, round)
    const here = playedHere !== null ? tt.matches[playedHere]! : null
    const out = next === null
    const why = (() => {
      if (here?.result?.how === 'walkover') {
        const won = here.result.winner === (here.a === 0 ? 0 : 1)
        const other = names[here.a === 0 ? here.b : here.a]!
        return won ? fill(p.walkoverWin, { name: monsterName, opp: other }) : out ? fill(p.out, { name: monsterName }) : fill(p.walkoverLoss, { name: monsterName })
      }
      return out ? fill(p.out, { name: monsterName }) : fill(p.sitsOut, { name: monsterName })
    })()
    flow = (
      <section class="card cupflow">
        <p class="field__label">{title(round)}</p>
        <div class="cuprows">{roundRows(round)}</div>
        {myRound ? (
          <>
            <p class="cupflow__mine">{fill(p.yourMatch, { a: monsterName, b: opp })}</p>
            <p class="field__hint">{fill(p.chooseHint, { name: monsterName, mode: defaultPlay === 'auto' ? p.auto : p.fight })}</p>
          </>
        ) : (
          <p class="muted small">{why}</p>
        )}
      </section>
    )
    actions = myRound ? (
      <div class="cupchoice" role="group" aria-label={p.choose}>
        {(['fight', 'auto', 'skip'] as const).map((how) => (
          <button key={how} type="button" class={`btn ${how === defaultPlay ? 'btn--primary' : ''}`} onClick={() => playMatch(how)}>
            {p[how]}
          </button>
        ))}
      </div>
    ) : (
      <div class={`cupchoice ${out ? 'cupchoice--two' : 'cupchoice--one'}`}>
        <button type="button" class="btn btn--primary" onClick={playRound}>
          {fill(p.playRound, { n: round })}
        </button>
        {out && (
          <button type="button" class="btn" onClick={skipToFinal}>
            {p.skipToFinal}
          </button>
        )}
      </div>
    )
  }

  return (
    <main class="screen">
      <TopBar title={eventName(tt.eventId)} onBack={() => navigate('ranch')} />
      {flow}
      <section class="card">
        <p class="field__label">{p.breakdown}</p>
        <Segmented options={tabs} value={shownTab} onChange={setTab} label={p.breakdown} />
        <div class="cuptab">
          {shownTab === 'standings' && <StandingsTable t={tt} names={names} upTo={complete ? undefined : roundsDone(tt)} />}
          {shownTab === 'rounds' && <RoundsList t={tt} names={names} onOpen={setDetail} />}
          {shownTab === 'bracket' && <BracketView t={tt} names={names} onOpen={setDetail} />}
          {shownTab === 'team' && score && <p class="cupscore">{fill(p.teamScore, { v: score.vale, c: score.coast })}</p>}
          {shownTab === 'legs' && <LegsList t={tt} names={names} legs={legs} onOpen={setDetail} />}
        </div>
      </section>
      <div class="spacer" />
      <div class="actionbar">{actions}</div>
      <DetailSheet d={detail} onClose={() => setDetail(null)} />
    </main>
  )
}
