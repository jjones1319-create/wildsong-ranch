import { signal } from '@preact/signals'
import { runBattle } from '../../core/battle/engine.ts'
import type { BattleOutcome, FighterSetup } from '../../core/battle/types.ts'
import { concludeTournament, enterTournament, makeTrialOpponent, resolvePendingTechnique, resolveTrial, type TrialOutcome } from '../../core/game.ts'
import type { TournamentState } from '../../core/state.ts'
import { autoStartInput, currentRound, matchOptions, matchSetup, nextPlayerMatch, playerFighter, playerMatchResult, playerMatchSetup, recordMatch, simulatePending, simulateRound, skipPlayerMatch, trialTier, type TournamentOutcome } from '../../core/tournament.ts'
import { JOURNEY_SITE_BY_ID } from '../../data/journeys.ts'
import { RIVAL_BY_ID } from '../../data/rivals.ts'
import { TOURNAMENT } from '../../data/tuning.ts'
import { navigate } from '../router.ts'
import { settings, updateSettings } from './appStore.ts'
import { startBattle, type BattleFinish } from './battleStore.ts'
import { commit, endWeekNow, game, withRng } from './gameStore.ts'

/**
 * Cups and the Journey Trial on the phone (§13, §11, §12.11). A cup is played one round at a time: the round's
 * preview, the player's match (Fight, Auto or Skip; the player's side is always under the player's control, Auto
 * being the engine's own flag), then the round's other matches resolve and its results and standings show. Every
 * step is committed, so a closed app resumes at the next round.
 */

/** How the player takes one match: on the pads, on Auto (take over any time), or simulated at once. */
export type MatchPlay = 'fight' | 'auto' | 'skip'

export const outcome = signal<TournamentOutcome | null>(null)
export const trialOutcome = signal<TrialOutcome | null>(null)
/** The round whose results and standings are on screen; null shows the next round's preview. Not saved. */
export const recapRound = signal<number | null>(null)

/** The cup default ('manual' = Fight, 'auto' = Auto) is remembered for the next entry. */
export function enter(eventId: string, mode: 'auto' | 'manual'): void {
  const g = game.value
  if (!g) return
  const next = enterTournament(g, eventId, mode)
  if (next === g) return
  if (settings.value.cupMode !== mode) void updateSettings({ cupMode: mode })
  recapRound.value = null
  commit(next)
  navigate('tournamentPlay')
}

/** The round is over for the player: its other matches resolve (never a later round's) and its recap shows. */
function closeRound(t: TournamentState, round: number): void {
  const g = game.value
  if (!g) return
  commit({ ...g, tournament: simulateRound(t, round) })
  recapRound.value = round
}

function outcomeOf(r: BattleFinish): BattleOutcome {
  return { winner: r.winner, how: r.how, hpPct: r.hpPct, ticks: r.ticks }
}

/** The player's match in the current round: Fight on the pads, Auto (watch, take over any time), or Skip. */
export function playMatch(how: MatchPlay): void {
  const g = game.value
  const t = g?.tournament
  if (!g || !t || !g.monster) return
  const next = nextPlayerMatch(t)
  if (!next) return
  const index = next.index
  const round = next.match.round
  const style = settings.value.autoStyle
  if (how === 'skip') {
    closeRound(skipPlayerMatch(t, index, style), round)
    return
  }
  const ps = playerMatchSetup(t, index, style)
  const opp = t.participants[ps.opponentIndex]!
  const rival = opp.rivalId ? RIVAL_BY_ID[opp.rivalId] : null
  const cup = { eventId: t.eventId, week: t.week }
  startBattle({
    a: ps.player.monster,
    b: opp.monster,
    aControl: 'player',
    personalityA: ps.player.personality,
    personalityB: opp.personality,
    habitB: opp.habit,
    // §12.10: the player's side is always expert (Auto included); the opponent's tier follows its grade and the event.
    tierA: 'expert',
    tierB: ps.opponent.tier,
    timerSec: TOURNAMENT.matchSeconds,
    origin: 'tournamentPlay',
    nameB: rival ? `${opp.monster.name} (${rival.name})` : opp.name,
    setups: { a: ps.player, b: ps.opponent },
    seed: ps.options.seed,
    autoStart: how === 'auto',
    onFinished: (r: BattleFinish) => {
      const cur = game.value
      const ct = cur?.tournament
      if (!cur || !ct || ct.eventId !== cup.eventId || ct.week !== cup.week) return
      closeRound(recordMatch(ct, index, playerMatchResult(outcomeOf(r), ps.playerIsA), r.techUses), round)
      navigate('tournamentPlay')
    },
  })
  navigate('battle')
}

/** The player has no match left in this round (out of the running, or a pre-v9 schedule): the round plays out and its recap shows. */
export function playRound(): void {
  const t = game.value?.tournament
  const round = t ? currentRound(t) : null
  if (!t || round === null) return
  if (t.matches.some((m) => m.round === round && m.result === null && (m.a === 0 || m.b === 0))) return
  closeRound(t, round)
}

/** With the player out, every remaining round at once, straight to the final standings. */
export function skipToFinal(): void {
  const g = game.value
  const t = g?.tournament
  if (!g || !t || nextPlayerMatch(t)) return
  commit({ ...g, tournament: simulatePending(t) })
  recapRound.value = null
}

/** From a round's recap to the next round's preview. */
export function nextRound(): void {
  recapRound.value = null
}

/**
 * Watch a recorded NPC match: the same fighters, tiers and seed the cup simulated it with, and no inputs, so it
 * plays out exactly as recorded. Nothing is written back.
 */
export function watchMatch(index: number): void {
  const t = game.value?.tournament
  const m = t?.matches[index]
  if (!t || !m?.result || m.result.how === 'walkover' || m.a === 0 || m.b === 0) return
  const s = matchSetup(t, index)
  const a = t.participants[m.a]!
  const b = t.participants[m.b]!
  startBattle({
    a: a.monster,
    b: b.monster,
    aControl: 'ai',
    personalityA: a.personality,
    personalityB: b.personality,
    habitB: b.habit,
    tierA: s.a.tier,
    tierB: s.b.tier,
    timerSec: TOURNAMENT.matchSeconds,
    origin: 'tournamentPlay',
    setups: { a: s.a, b: s.b },
    seed: s.options.seed,
    replay: true,
  })
  navigate('battle')
}

/** Applies the finished cup and opens the Results. */
export function conclude(): void {
  const g = game.value
  if (!g?.tournament) return
  const done = withRng((rng) => concludeTournament(g, rng))
  if (!done) return
  outcome.value = done.outcome
  recapRound.value = null
  commit(done.state)
  navigate('tournamentResults')
}

/** Continue from the Results: the week ends; rank 10 rolls the credits once. */
export function afterResults(): void {
  const g = game.value
  outcome.value = null
  if (g && g.breeder.rank >= TOURNAMENT.rank.max && !g.guild.creditsRolled) {
    commit({ ...g, guild: { ...g.guild, creditsRolled: true } })
    endWeekNow()
    navigate('creditsRoll')
    return
  }
  endWeekNow()
  navigate('ranch')
}

/* ---------- the Journey Trial ---------- */

/** Fight the Trial, put it on Auto (take over any time) or Skip it; the result applies through `resolveTrial`. */
export function startTrial(how: MatchPlay): void {
  const g = game.value
  if (!g?.trial || !g.monster) return
  const wild = withRng((rng) => makeTrialOpponent(g, rng))
  if (!wild) return
  const seed = withRng((rng) => rng.nextU32())
  const style = settings.value.autoStyle
  const me = playerFighter(g.monster, style)
  const them: FighterSetup = { monster: wild, control: 'ai', personality: 'Steady', tier: trialTier(wild.grade) }
  const site = JOURNEY_SITE_BY_ID[g.trial.site]
  const done = (r: BattleFinish) => {
    const cur = game.value
    if (!cur?.trial) return
    const res = withRng((rng) => resolveTrial(cur, { winner: r.winner, how: r.how }, rng))
    trialOutcome.value = res.outcome
    commit(res.state)
    navigate('ranch')
  }
  if (how === 'skip') {
    // Exactly the battle an untouched Auto run on this seed would show.
    const r = runBattle(me, them, matchOptions(seed), [autoStartInput(style)])
    done({ winner: r.outcome.winner, how: r.outcome.how, hpPct: r.outcome.hpPct, ticks: r.outcome.ticks, techUses: r.fighters[0].techUses })
    return
  }
  startBattle({
    a: g.monster,
    b: wild,
    aControl: 'player',
    personalityA: me.personality,
    personalityB: them.personality,
    tierA: 'expert',
    tierB: them.tier,
    timerSec: TOURNAMENT.matchSeconds,
    origin: 'ranch',
    nameB: `${site.name} ${wild.name.replace(/^Wild /, '')}`,
    setups: { a: me, b: them },
    seed,
    autoStart: how === 'auto',
    onFinished: done,
  })
  navigate('battle')
}

export function dismissTrialOutcome(): void {
  trialOutcome.value = null
}

/** A technique earned with a full list: forget one and learn it, or let it go. */
export function settlePendingTechnique(forgetId: string | null): void {
  const g = game.value
  if (!g) return
  const next = resolvePendingTechnique(g, forgetId)
  if (next !== g) commit(next)
}
