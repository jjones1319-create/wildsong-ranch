import { signal } from '@preact/signals'
import { concludeTournament, enterTournament, makeTrialOpponent, resolvePendingTechnique, resolveTrial, type TrialOutcome } from '../../core/game.ts'
import { isComplete, nextPlayerMatch, opponentOf, recordMatch, simulatePending, type TournamentOutcome } from '../../core/tournament.ts'
import { JOURNEY_SITE_BY_ID } from '../../data/journeys.ts'
import { RIVAL_BY_ID } from '../../data/rivals.ts'
import { TOURNAMENT } from '../../data/tuning.ts'
import { navigate } from '../router.ts'
import { startBattle, type BattleFinish } from './battleStore.ts'
import { commit, endWeekNow, game, withRng } from './gameStore.ts'

/**
 * Cups and the Journey Trial on the phone (§13, §11): entering, fighting the player's matches on the battle
 * screen, simulating the rest, and the recap. Every step is committed, so a closed app resumes mid-cup.
 */

export const outcome = signal<TournamentOutcome | null>(null)
export const trialOutcome = signal<TrialOutcome | null>(null)

export function enter(eventId: string, mode: 'auto' | 'manual'): void {
  const g = game.value
  if (!g) return
  const next = enterTournament(g, eventId, mode)
  if (next === g) return
  commit(next)
  navigate('tournamentPlay')
}

/** Fights every match without the player; returns true when the cup is complete. */
export function simulateRest(): boolean {
  const g = game.value
  if (!g?.tournament) return false
  const t = simulatePending(g.tournament)
  if (t !== g.tournament) commit({ ...g, tournament: t })
  return isComplete(t)
}

/** Starts the player's next match on the battle screen (manual on the pads, or Auto with Skip). */
export function playNext(): void {
  const g = game.value
  if (!g?.tournament || !g.monster) return
  const t = g.tournament
  const next = nextPlayerMatch(t)
  if (!next) return
  const me = t.participants[0]!
  const opp = opponentOf(t, next.match)
  const rival = opp.rivalId ? RIVAL_BY_ID[opp.rivalId] : null
  const index = next.index
  startBattle({
    a: me.monster,
    b: opp.monster,
    aControl: t.mode === 'manual' ? 'player' : 'ai',
    personalityA: 'Steady',
    personalityB: opp.personality,
    habitB: opp.habit,
    timerSec: 60,
    origin: 'tournamentPlay',
    nameB: rival ? `${opp.monster.name} (${rival.name})` : opp.name,
    onFinished: (r: BattleFinish) => {
      const cur = game.value
      if (!cur?.tournament) return
      const aIsPlayer = cur.tournament.matches[index]!.a === 0
      const winner = r.winner === null ? null : ((aIsPlayer ? r.winner : 1 - r.winner) as 0 | 1)
      const hp: [number, number] = aIsPlayer ? r.hpPct : [r.hpPct[1], r.hpPct[0]]
      commit({ ...cur, tournament: recordMatch(cur.tournament, index, { winner, how: r.how, hpPct: hp }, r.techUses) })
      navigate('tournamentPlay')
    },
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

/** Fight the Trial (manual or auto) or simulate it; the result applies through `resolveTrial`. */
export function startTrial(how: 'manual' | 'auto' | 'skip'): void {
  const g = game.value
  if (!g?.trial || !g.monster) return
  const wild = withRng((rng) => makeTrialOpponent(g, rng))
  if (!wild) return
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
    // Simulate instantly with both sides on the CPU.
    const { runBattle, timerTicksFor } = engine
    const r = runBattle({ monster: g.monster, control: 'ai', personality: 'Steady' }, { monster: wild, control: 'ai', personality: 'Steady' }, { seed: withRng((rng) => rng.nextU32()), timerTicks: timerTicksFor(60) })
    done({ winner: r.outcome.winner, how: r.outcome.how, hpPct: r.outcome.hpPct, techUses: r.fighters[0].techUses })
    return
  }
  startBattle({ a: g.monster, b: wild, aControl: how === 'manual' ? 'player' : 'ai', personalityA: 'Steady', personalityB: 'Steady', timerSec: 60, origin: 'ranch', nameB: `${site.name} ${wild.name.replace(/^Wild /, '')}`, onFinished: done })
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

import * as engine from '../../core/battle/engine.ts'
